import pandas as pd

from lightgbm import LGBMClassifier

from .config import (
    N_ESTIMATORS,
    MAX_DEPTH,
    MIN_SAMPLES_LEAF,
    RANDOM_STATE,
)


# ============================================================
# FEATURES USED BY MODEL
# ============================================================

FEATURE_COLUMNS = [

    "country_exact",

    "country_missing",

    "name_ratio",

    "name_token_ratio",

    "name_wratio",

    "name_jaccard",

    "name_exact",

    "address_ratio",

    "address_token_ratio",

    "address_wratio",

    "address_jaccard",

    "address_exact",

    "name_length_diff",

    "address_length_diff",
]


# ============================================================
# TRAIN MODEL
# ============================================================

def train_model(training_df):

    X = training_df[FEATURE_COLUMNS]

    y = training_df["label"]

    # LightGBM replacement for the previous RandomForest model.
    #
    # Existing config variables are retained so no other project
    # files need to be changed:
    #   N_ESTIMATORS     -> n_estimators
    #   MAX_DEPTH        -> max_depth
    #   MIN_SAMPLES_LEAF -> min_child_samples
    #
    # class_weight="balanced" preserves the previous handling of
    # the positive/negative class imbalance.

    model = LGBMClassifier(

        n_estimators=N_ESTIMATORS,

        max_depth=MAX_DEPTH,

        min_child_samples=MIN_SAMPLES_LEAF,

        class_weight="balanced",

        random_state=RANDOM_STATE,

        n_jobs=-1,

        verbosity=-1,
    )

    model.fit(X, y)

    return model


# ============================================================
# PREDICT PROBABILITY
# ============================================================

def predict_probabilities(
    model,
    feature_df
):

    X = feature_df[FEATURE_COLUMNS]

    probabilities = model.predict_proba(X)

    # Positive class probability

    if probabilities.shape[1] == 1:

        # Model only saw one class.
        # Return either all 0 or all 1.

        only_class = model.classes_[0]

        if only_class == 1:

            return probabilities[:, 0]

        return probabilities[:, 0] * 0.0

    positive_index = list(
        model.classes_
    ).index(1)

    return probabilities[:, positive_index]