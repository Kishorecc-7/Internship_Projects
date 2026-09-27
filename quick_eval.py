import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    SOURCE1_BATCH_SIZE,
    SOURCE1_PARQUET,
    TARGET_PARQUET,
    GROUND_TRUTH_FILE,
    WORK_DIR,
)
from .storage import prepare_all_data
from .evaluation import load_ground_truth, calculate_blocking_recall
from .training import label_candidates, select_training_pairs, train_model, FEATURE_COLUMNS
from .prediction import prepare_prediction_pairs
from .features import create_features


QUICK_EVAL_DIR = WORK_DIR / "checkpoints" / "quick_eval"
QUICK_EVAL_CANDIDATES_DIR = QUICK_EVAL_DIR / "candidates"
QUICK_EVAL_TRAINING_DIR = QUICK_EVAL_DIR / "training"
QUICK_EVAL_PREDICTIONS_DIR = QUICK_EVAL_DIR / "predictions"
QUICK_EVAL_MODEL = QUICK_EVAL_DIR / "lightgbm_model.pkl"
QUICK_EVAL_REPORT = QUICK_EVAL_DIR / "quick_eval_report.json"

# Existing production blocking checkpoints are read-only inputs.
PRODUCTION_CANDIDATE_DIRS = [
    WORK_DIR / "checkpoints" / "production" / "training_candidates",
    WORK_DIR / "checkpoints" / "training_candidates",
]


def _batch_file(directory, batch_index):
    return directory / f"batch_{batch_index:06d}.parquet"


def _atomic_write_parquet(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    df.to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(path)


def _load_first_100k_candidates(limit):
    """Read already-completed production blocking checkpoints only."""
    candidate_dir = next((p for p in PRODUCTION_CANDIDATE_DIRS if p.exists()), None)
    if candidate_dir is None:
        raise FileNotFoundError(
            "No production candidate checkpoint directory found. "
            "Run blocking first and save the first 100k Source1 records."
        )

    batch_count = (limit + SOURCE1_BATCH_SIZE - 1) // SOURCE1_BATCH_SIZE
    parts = []
    missing = []

    for batch_index in range(batch_count):
        path = _batch_file(candidate_dir, batch_index)
        if not path.exists():
            missing.append(path.name)
            continue
        parts.append(pd.read_parquet(path))

    if missing:
        raise RuntimeError(
            "Quick evaluation requires the complete first "
            f"{limit:,} Source1 blocking records. Missing checkpoints: "
            + ", ".join(missing)
        )

    candidates = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    candidates = candidates[candidates["source1_id"].isin(
        set(pd.read_parquet(SOURCE1_PARQUET, columns=["entity_id"]).head(limit)["entity_id"])
    )].copy()

    _atomic_write_parquet(candidates, QUICK_EVAL_CANDIDATES_DIR / "blocked_100k.parquet")
    return candidates


def _save_model(model):
    QUICK_EVAL_DIR.mkdir(parents=True, exist_ok=True)
    tmp = QUICK_EVAL_MODEL.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump({"model": model, "model_type": "LightGBM", "scope": "quick_eval"}, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(QUICK_EVAL_MODEL)


def _load_model():
    if not QUICK_EVAL_MODEL.exists():
        return None
    with open(QUICK_EVAL_MODEL, "rb") as f:
        payload = pickle.load(f)
    return payload["model"] if isinstance(payload, dict) and "model" in payload else payload


def _truth_pairs(truth):
    total = 0
    mapping = {}
    for source1_id, matched in truth.items():
        sid = str(source1_id).strip()
        if matched is None:
            ids = set()
        elif isinstance(matched, (set, list, tuple)):
            ids = {str(x).strip() for x in matched if str(x).strip()}
        else:
            text = str(matched).strip()
            if text in ("", "[]"):
                ids = set()
            else:
                ids = {x.strip() for x in text.strip("[]").split(",") if x.strip()}
        mapping[sid] = ids
        total += len(ids)
    return mapping, total


def _split_source1(source1, seed=42, validation_fraction=0.20):
    ids = source1["entity_id"].astype(str).str.strip().drop_duplicates().to_numpy()
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    n_val = max(1, int(round(len(ids) * validation_fraction)))
    val_ids = set(ids[:n_val])
    train_ids = set(ids[n_val:])
    return train_ids, val_ids


def _score(candidates, source1_df, target_df, model, chunk_size=100_000):
    parts = []
    for start in range(0, len(candidates), chunk_size):
        chunk = candidates.iloc[start:start + chunk_size].copy()
        pairs = prepare_prediction_pairs(chunk, source1_df, target_df)
        feature_input = pairs[[
            "name_norm_a", "name_norm_b",
            "address_norm_a", "address_norm_b",
            "country_norm_a", "country_norm_b",
        ]]
        feature_data = create_features(feature_input.reset_index(drop=True))
        X = pd.DataFrame(feature_data)[FEATURE_COLUMNS]
        probabilities = model.predict_proba(X)[:, 1]
        out = chunk[["source1_id", "target_id", "target_source"]].copy()
        out["probability"] = probabilities
        parts.append(out)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["source1_id", "target_id", "target_source", "probability"]
    )


def _metrics(scored, truth_map, validation_ids, threshold):
    pred = scored[scored["probability"] >= threshold]
    predicted_pairs = {
        (str(r.source1_id), str(r.target_id).strip())
        for r in pred.itertuples(index=False)
    }
    true_pairs = {
        (sid, tid)
        for sid in validation_ids
        for tid in truth_map.get(sid, set())
    }
    tp = len(predicted_pairs & true_pairs)
    fp = len(predicted_pairs - true_pairs)
    fn = len(true_pairs - predicted_pairs)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    beta2 = 0.5 ** 2
    f05 = ((1 + beta2) * precision * recall / (beta2 * precision + recall)) if (beta2 * precision + recall) else 0.0
    return {
        "threshold": threshold,
        "true_positive_pairs": tp,
        "false_positive_pairs": fp,
        "false_negative_pairs": fn,
        "precision": precision,
        "recall": recall,
        "f0.5": f05,
        "predicted_pairs": len(predicted_pairs),
        "ground_truth_pairs": len(true_pairs),
    }


def run_quick_eval(limit=100_000, validation_fraction=0.20, seed=42, reset=False):
    if reset and QUICK_EVAL_DIR.exists():
        import shutil
        shutil.rmtree(QUICK_EVAL_DIR)

    for d in (QUICK_EVAL_DIR, QUICK_EVAL_CANDIDATES_DIR, QUICK_EVAL_TRAINING_DIR, QUICK_EVAL_PREDICTIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    if not (SOURCE1_PARQUET.exists() and TARGET_PARQUET.exists()):
        prepare_all_data()

    source1 = pd.read_parquet(SOURCE1_PARQUET).head(limit).copy()
    target = pd.read_parquet(TARGET_PARQUET)
    truth = load_ground_truth(GROUND_TRUTH_FILE)

    candidates = _load_first_100k_candidates(limit)
    if candidates.empty:
        raise RuntimeError("The first 100k blocking checkpoint contains no candidates.")

    truth_map, truth_pair_count_all = _truth_pairs(truth)
    train_ids, val_ids = _split_source1(source1, seed=seed, validation_fraction=validation_fraction)

    train_candidates = candidates[candidates["source1_id"].astype(str).isin(train_ids)].copy()
    val_candidates = candidates[candidates["source1_id"].astype(str).isin(val_ids)].copy()

    # Persist the split so a stopped evaluation can resume without touching production.
    _atomic_write_parquet(train_candidates, QUICK_EVAL_TRAINING_DIR / "train_candidates.parquet")
    _atomic_write_parquet(val_candidates, QUICK_EVAL_TRAINING_DIR / "validation_candidates.parquet")

    blocking_recall = calculate_blocking_recall(candidates, truth)
    val_blocking_recall = calculate_blocking_recall(val_candidates, truth)

    model = _load_model()
    if model is None:
        labeled_train = label_candidates(train_candidates, source1, target, truth)
        _atomic_write_parquet(labeled_train, QUICK_EVAL_TRAINING_DIR / "labeled_train.parquet")
        training_pairs = select_training_pairs(labeled_train)
        model = train_model(training_pairs)
        _save_model(model)
    else:
        print(f"Using existing quick-eval model: {QUICK_EVAL_MODEL}")

    scored = _score(val_candidates, source1, target, model)
    _atomic_write_parquet(scored, QUICK_EVAL_PREDICTIONS_DIR / "validation_scores.parquet")

    thresholds = [round(x, 2) for x in np.arange(0.50, 0.97, 0.01)]
    metrics = [_metrics(scored, truth_map, val_ids, t) for t in thresholds]
    eligible = [m for m in metrics if m["precision"] >= 0.90]
    selected = max(eligible, key=lambda m: m["f0.5"]) if eligible else max(metrics, key=lambda m: m["precision"])

    report = {
        "evaluation_type": "temporary_100k_quick_eval",
        "source1_records": len(source1),
        "train_source1_records": len(train_ids),
        "validation_source1_records": len(val_ids),
        "candidate_pairs": len(candidates),
        "train_candidate_pairs": len(train_candidates),
        "validation_candidate_pairs": len(val_candidates),
        "blocking_recall_all_100k": blocking_recall,
        "blocking_recall_validation": val_blocking_recall,
        "selected_threshold": selected["threshold"],
        "selected_metrics": selected,
        "threshold_metrics": metrics,
        "quick_eval_checkpoint_dir": str(QUICK_EVAL_DIR),
        "production_candidate_dir_used": str(next(p for p in PRODUCTION_CANDIDATE_DIRS if p.exists())),
    }
    with open(QUICK_EVAL_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\nQUICK EVALUATION COMPLETE")
    print(json.dumps({
        "blocking_recall": blocking_recall,
        "validation_blocking_recall": val_blocking_recall,
        "selected_threshold": selected["threshold"],
        "precision": selected["precision"],
        "recall": selected["recall"],
        "f0.5": selected["f0.5"],
    }, indent=2))
    print(f"Report: {QUICK_EVAL_REPORT}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Temporary 100k model evaluation using existing blocking checkpoints.")
    parser.add_argument("--limit", type=int, default=100_000)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true", help="Clear only quick-eval checkpoints; never production checkpoints.")
    args = parser.parse_args()
    run_quick_eval(args.limit, args.validation_fraction, args.seed, args.reset)
