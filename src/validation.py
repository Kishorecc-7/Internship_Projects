import json
import re
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, fbeta_score

from .config import (
    RANDOM_STATE, VALIDATION_THRESHOLDS, MIN_VALIDATION_PRECISION,
    VALIDATION_SOURCE1_FRACTION, VALIDATION_MAX_POSITIVE_PAIRS,
    VALIDATION_HARD_NEGATIVES_PER_POSITIVE, VALIDATION_EASY_NEGATIVES_PER_POSITIVE,
)
from .features import create_features
from .training import FEATURE_COLUMNS, select_training_pairs, train_model


def _label_column(df):
    for c in ("label", "is_match", "target", "match"):
        if c in df.columns:
            return c
    raise KeyError(f"Could not find match-label column. Columns: {list(df.columns)}")


def split_labeled_by_entity(labeled):
    ids = pd.Series(labeled["source1_id"].astype(str).unique())
    rng = np.random.RandomState(RANDOM_STATE)
    val_n = max(1, int(len(ids) * VALIDATION_SOURCE1_FRACTION))
    val_ids = set(rng.choice(ids.to_numpy(), size=val_n, replace=False))
    is_val = labeled["source1_id"].astype(str).isin(val_ids)
    return labeled.loc[~is_val].copy(), labeled.loc[is_val].copy()


def _balanced_validation_sample(df):
    col = _label_column(df)
    work = df.copy()
    work[col] = work[col].astype(int)
    pos = work[work[col] == 1]
    neg = work[work[col] == 0]
    npos = min(len(pos), VALIDATION_MAX_POSITIVE_PAIRS)
    if npos == 0 or neg.empty:
        raise RuntimeError("Validation split does not contain both positive and negative pairs.")
    rng = np.random.RandomState(RANDOM_STATE)
    pos = pos.sample(n=npos, random_state=RANDOM_STATE)
    # Preserve a hard/easy mixture when available by using deterministic feature similarity proxies.
    neg = neg.sample(n=min(len(neg), npos * (VALIDATION_HARD_NEGATIVES_PER_POSITIVE + VALIDATION_EASY_NEGATIVES_PER_POSITIVE)), random_state=RANDOM_STATE)
    return pd.concat([pos, neg], ignore_index=True)


def _feature_pairs(labeled, source1_df, target_df):
    pairs = labeled.merge(source1_df, left_on="source1_id", right_on="entity_id", how="left")
    pairs = pairs.rename(columns={"name_norm":"name_norm_a","address_norm":"address_norm_a","country_norm":"country_norm_a"})
    pairs = pairs.merge(target_df, left_on="target_id", right_on="entity_id", how="left", suffixes=("_a","_b"))
    pairs = pairs.rename(columns={"name_norm":"name_norm_b","address_norm":"address_norm_b","country_norm":"country_norm_b"})
    col = _label_column(pairs)
    return pairs, col


def _metrics(y, p, threshold):
    pred = (p >= threshold).astype(int)
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f0.5": float(fbeta_score(y, pred, beta=0.5, zero_division=0)),
        "predicted_positive": int(pred.sum()),
        "actual_positive": int(np.asarray(y).sum()),
    }


def train_with_validation(labeled, source1_df, target_df):
    train_labeled, val_labeled = split_labeled_by_entity(labeled)
    training_pairs = select_training_pairs(train_labeled)
    model = train_model(training_pairs)

    val_sample = _balanced_validation_sample(val_labeled)
    pairs, label_col = _feature_pairs(val_sample, source1_df, target_df)
    features = create_features(pairs[["name_norm_a","name_norm_b","address_norm_a","address_norm_b","country_norm_a","country_norm_b"]].reset_index(drop=True))
    X = pd.DataFrame(features)[FEATURE_COLUMNS]
    y = pairs[label_col].astype(int).to_numpy()
    probabilities = model.predict_proba(X)[:,1]

    rows = [_metrics(y, probabilities, t) for t in VALIDATION_THRESHOLDS]
    # Prefer the highest F0.5 among thresholds meeting the requested precision floor.
    eligible = [r for r in rows if r["precision"] >= MIN_VALIDATION_PRECISION]
    if eligible:
        chosen = max(eligible, key=lambda r: (r["f0.5"], r["precision"], -r["threshold"]))
    else:
        # If no threshold reaches the floor, use the threshold with highest precision,
        # breaking ties by F0.5. This keeps the failure mode explicit in the report.
        chosen = max(rows, key=lambda r: (r["precision"], r["f0.5"]))

    report = {
        "train_source1_entities": int(train_labeled["source1_id"].nunique()),
        "validation_source1_entities": int(val_labeled["source1_id"].nunique()),
        "training_pairs": int(len(training_pairs)),
        "validation_pairs": int(len(val_sample)),
        "threshold_results": rows,
        "selected_threshold": chosen["threshold"],
        "selected_metrics": chosen,
    }
    return model, float(chosen["threshold"]), report
