import pandas as pd

from lightgbm import LGBMClassifier

from .config import (
    RANDOM_STATE,
    MAX_POSITIVE_PAIRS,
    HARD_NEGATIVES_PER_POSITIVE,
    EASY_NEGATIVES_PER_POSITIVE,
    MAX_ITER,
    LEARNING_RATE,
    MAX_LEAF_NODES,
    MIN_SAMPLES_LEAF,
    L2_REGULARIZATION,
)

from .features import (
    create_features,
)


FEATURE_COLUMNS = [
    "country_exact",
    "country_missing",
    "country_mismatch",

    "name_ratio",
    "name_token_ratio",
    "name_wratio",
    "name_exact",

    "address_ratio",
    "address_token_ratio",
    "address_wratio",
    "address_exact",

    "name_length_diff",
    "address_length_diff",

    "name_len_a",
    "name_len_b",

    "address_len_a",
    "address_len_b",
]


def label_candidates(
    candidates,
    source1_df,
    target_df,
    truth,
):
    """
    Label candidate pairs.

    1 = true match
    0 = non-match
    """

    if candidates.empty:
        return candidates

    pair_rows = []

    for _, candidate in candidates.iterrows():

        source1_id = str(
            candidate["source1_id"]
        )

        target_id = str(
            candidate["target_id"]
        )

        true_matches = truth.get(
            source1_id,
            set(),
        )

        label = int(
            target_id in true_matches
        )

        pair_rows.append(
            {
                "source1_id":
                    source1_id,

                "target_id":
                    target_id,

                "target_source":
                    candidate[
                        "target_source"
                    ],

                "label":
                    label,
            }
        )

    pair_df = pd.DataFrame(
        pair_rows
    )

    # --------------------------------------------------------
    # Attach Source 1 data
    # --------------------------------------------------------

    pair_df = pair_df.merge(
        source1_df,
        left_on="source1_id",
        right_on="entity_id",
        how="left",
    )

    pair_df = pair_df.rename(
        columns={
            "name_norm":
                "name_norm_a",

            "address_norm":
                "address_norm_a",

            "country_norm":
                "country_norm_a",
        }
    )

    # --------------------------------------------------------
    # Attach target data
    # --------------------------------------------------------

    pair_df = pair_df.merge(
        target_df,
        left_on="target_id",
        right_on="entity_id",
        how="left",
        suffixes=(
            "_a",
            "_b",
        ),
    )

    pair_df = pair_df.rename(
        columns={
            "name_norm":
                "name_norm_b",

            "address_norm":
                "address_norm_b",

            "country_norm":
                "country_norm_b",
        }
    )

    return pair_df


def select_training_pairs(
    pair_df,
):
    """
    Keep a controlled number of positive
    and negative examples.

    Hard negatives are candidates that look
    similar but are known to be incorrect.
    """

    if pair_df.empty:
        raise RuntimeError(
            "Candidate dataset is empty."
        )

    positives = pair_df[
        pair_df["label"] == 1
    ].copy()

    negatives = pair_df[
        pair_df["label"] == 0
    ].copy()

    print(
        f"Available positive pairs: "
        f"{len(positives):,}"
    )

    print(
        f"Available negative pairs: "
        f"{len(negatives):,}"
    )

    if positives.empty:
        raise RuntimeError(
            "No positive pairs found."
        )

    # --------------------------------------------------------
    # Limit positive pairs
    # --------------------------------------------------------

    if (
        len(positives)
        > MAX_POSITIVE_PAIRS
    ):

        positives = positives.sample(
            n=MAX_POSITIVE_PAIRS,
            random_state=RANDOM_STATE,
        )

    # --------------------------------------------------------
    # Score negatives
    # --------------------------------------------------------

    if not negatives.empty:

        negative_input = negatives[
            [
                "name_norm_a",
                "name_norm_b",
                "address_norm_a",
                "address_norm_b",
                "country_norm_a",
                "country_norm_b",
            ]
        ].reset_index(
            drop=True
        )

        negative_features = (
            create_features(
                negative_input
            )
        )

        negative_features = (
            pd.DataFrame(
                negative_features
            )
        )

        negatives = negatives.copy()

        negatives["hard_score"] = (
            0.50
            * negative_features[
                "name_wratio"
            ].values

            +

            0.30
            * negative_features[
                "address_wratio"
            ].values

            +

            0.20
            * negative_features[
                "country_exact"
            ].values
        )

        negatives = negatives.sort_values(
            "hard_score",
            ascending=False,
        )

    # --------------------------------------------------------
    # Hard negatives
    # --------------------------------------------------------

    hard_count = (
        len(positives)
        * HARD_NEGATIVES_PER_POSITIVE
    )

    hard_negatives = (
        negatives.head(
            hard_count
        )
    )

    # --------------------------------------------------------
    # Easy negatives
    # --------------------------------------------------------

    remaining = negatives.iloc[
        len(hard_negatives):
    ]

    easy_count = (
        len(positives)
        * EASY_NEGATIVES_PER_POSITIVE
    )

    if len(remaining) > easy_count:

        easy_negatives = (
            remaining.sample(
                n=easy_count,
                random_state=RANDOM_STATE,
            )
        )

    else:

        easy_negatives = remaining

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    training_df = pd.concat(
        [
            positives,
            hard_negatives,
            easy_negatives,
        ],
        ignore_index=True,
    )

    training_df = training_df.sample(
        frac=1.0,
        random_state=RANDOM_STATE,
    ).reset_index(
        drop=True
    )

    return training_df


def train_model(
    training_df,
):

    print()
    print(
        "Training LightGBM model..."
    )

    print(
        f"Training pairs: "
        f"{len(training_df):,}"
    )

    positive_count = int(
        training_df["label"].sum()
    )

    negative_count = (
        len(training_df)
        - positive_count
    )

    print(
        f"Positive: {positive_count:,}"
    )

    print(
        f"Negative: {negative_count:,}"
    )

    feature_input = training_df[
        [
            "name_norm_a",
            "name_norm_b",
            "address_norm_a",
            "address_norm_b",
            "country_norm_a",
            "country_norm_b",
        ]
    ].reset_index(
        drop=True
    )

    feature_data = create_features(
        feature_input
    )

    X = pd.DataFrame(
        feature_data
    )

    X = X[
        FEATURE_COLUMNS
    ]

    y = (
        training_df["label"]
        .astype(int)
    )

    # --------------------------------------------------------
    # LightGBM model
    #
    # Existing config values are reused so that the rest of
    # the project does not need to change.
    #
    # MAX_ITER          -> n_estimators
    # MAX_LEAF_NODES    -> num_leaves
    # MIN_SAMPLES_LEAF  -> min_child_samples
    # LEARNING_RATE      -> learning_rate
    # L2_REGULARIZATION  -> reg_lambda
    # --------------------------------------------------------

    model = LGBMClassifier(
        n_estimators=MAX_ITER,
        learning_rate=LEARNING_RATE,
        num_leaves=MAX_LEAF_NODES,
        min_child_samples=MIN_SAMPLES_LEAF,
        reg_lambda=L2_REGULARIZATION,
        random_state=RANDOM_STATE,
        class_weight="balanced",
        n_jobs=-1,
        verbosity=-1,
    )

    model.fit(
        X,
        y,
    )

    print(
        "LightGBM model training completed."
    )

    return model
