import pandas as pd

from .config import (
    ML_THRESHOLD,
    MAX_ML_CANDIDATES_PER_ENTITY,
    CHEAP_PREFILTER_ENABLED,
    CHEAP_PREFILTER_NAME_THRESHOLD,
    CHEAP_PREFILTER_ADDRESS_THRESHOLD,
    CHEAP_PREFILTER_TOP_K,
)
from .features import create_features
from .training import FEATURE_COLUMNS


def prepare_prediction_pairs(candidates, source1_df, target_df):
    pairs = candidates.merge(source1_df, left_on="source1_id", right_on="entity_id", how="left")
    pairs = pairs.rename(columns={"name_norm":"name_norm_a","address_norm":"address_norm_a","country_norm":"country_norm_a"})
    pairs = pairs.merge(target_df, left_on="target_id", right_on="entity_id", how="left", suffixes=("_a","_b"))
    return pairs.rename(columns={"name_norm":"name_norm_b","address_norm":"address_norm_b","country_norm":"country_norm_b"})


def _cheap_prefilter(pairs):
    if not CHEAP_PREFILTER_ENABLED or pairs.empty:
        return pairs
    try:
        from rapidfuzz.fuzz import ratio
    except ImportError:
        print("WARNING: rapidfuzz is not installed; cheap prefilter skipped.")
        return pairs

    name_a = pairs["name_norm_a"].fillna("").astype(str).tolist()
    name_b = pairs["name_norm_b"].fillna("").astype(str).tolist()
    addr_a = pairs["address_norm_a"].fillna("").astype(str).tolist()
    addr_b = pairs["address_norm_b"].fillna("").astype(str).tolist()
    name_score = [ratio(a,b)/100.0 if a and b else 0.0 for a,b in zip(name_a,name_b)]
    addr_score = [ratio(a,b)/100.0 if a and b else 0.0 for a,b in zip(addr_a,addr_b)]
    pairs = pairs.copy()
    pairs["_cheap_name"] = name_score
    pairs["_cheap_addr"] = addr_score
    pairs["_cheap_score"] = pairs["_cheap_name"]*0.7 + pairs["_cheap_addr"]*0.3
    keep = (pairs["_cheap_name"] >= CHEAP_PREFILTER_NAME_THRESHOLD) | (pairs["_cheap_addr"] >= CHEAP_PREFILTER_ADDRESS_THRESHOLD)
    pairs = pairs[keep].copy()
    if pairs.empty:
        return pairs
    pairs = pairs.sort_values(["source1_id","_cheap_score"], ascending=[True,False])
    pairs = pairs.groupby("source1_id", as_index=False).head(CHEAP_PREFILTER_TOP_K).copy()
    return pairs.drop(columns=["_cheap_name","_cheap_addr","_cheap_score"], errors="ignore")


def score_pairs(model, pairs):
    if pairs.empty:
        return pairs.copy()
    feature_input = pairs[["name_norm_a","name_norm_b","address_norm_a","address_norm_b","country_norm_a","country_norm_b"]]
    feature_data = create_features(feature_input.reset_index(drop=True))
    X = pd.DataFrame(feature_data)[FEATURE_COLUMNS]
    out = pairs[["source1_id","target_id","target_source"]].copy()
    out["probability"] = model.predict_proba(X)[:,1]
    return out


def predict_candidates(model, candidates, source1_df, target_df, threshold=None):
    if candidates.empty:
        return pd.DataFrame(columns=["source1_id","target_id","target_source","probability"])
    pairs = prepare_prediction_pairs(candidates, source1_df, target_df)
    pairs = _cheap_prefilter(pairs)
    if pairs.empty:
        return pd.DataFrame(columns=["source1_id","target_id","target_source","probability"])
    result = score_pairs(model, pairs)
    threshold = ML_THRESHOLD if threshold is None else threshold
    result = result[result["probability"] >= threshold].copy()
    if result.empty:
        return result
    return (result.sort_values(["source1_id","probability"], ascending=[True,False])
            .groupby("source1_id", as_index=False).head(MAX_ML_CANDIDATES_PER_ENTITY))
