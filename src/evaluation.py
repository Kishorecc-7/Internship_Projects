import ast

import pandas as pd

from .config import (
    GROUND_TRUTH_SOURCE1_ID_COL,
    GROUND_TRUTH_MATCHED_IDS_COL,
)


def parse_match_list(value):

    if value is None:
        return set()

    value = str(value).strip()

    if value in (
        "",
        "[]",
    ):
        return set()

    # Try list representation.
    try:

        parsed = ast.literal_eval(
            value
        )

        if isinstance(
            parsed,
            list,
        ):

            return {
                str(x).strip()
                for x in parsed
                if str(x).strip()
            }

    except Exception:
        pass

    # Fallback:
    # comma-separated IDs.
    value = value.strip(
        "[]"
    )

    return {
        x.strip()
        .strip("'")
        .strip('"')
        for x in value.split(",")
        if x.strip()
    }


def load_ground_truth(path):

    df = pd.read_csv(
        path,
        sep="\t",
        dtype=str,
        keep_default_na=False,
    )

    required_columns = {
        GROUND_TRUTH_SOURCE1_ID_COL,
        GROUND_TRUTH_MATCHED_IDS_COL,
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Ground truth is missing columns: "
            f"{sorted(missing)}"
        )

    truth = {}

    for _, row in df.iterrows():

        source1_id = str(
            row[
                GROUND_TRUTH_SOURCE1_ID_COL
            ]
        ).strip()

        matches = parse_match_list(
            row[
                GROUND_TRUTH_MATCHED_IDS_COL
            ]
        )

        truth[
            source1_id
        ] = matches

    return truth


def calculate_blocking_recall(
    candidates,
    truth,
):

    if candidates.empty:
        return 0.0

    grouped = (
        candidates
        .groupby(
            "source1_id"
        )["target_id"]
        .apply(set)
        .to_dict()
    )

    total_true_pairs = 0

    recovered_true_pairs = 0

    for (
        source1_id,
        true_matches,
    ) in truth.items():

        if not true_matches:
            continue

        total_true_pairs += (
            len(true_matches)
        )

        predicted_candidates = (
            grouped.get(
                str(source1_id),
                set(),
            )
        )

        recovered_true_pairs += len(
            true_matches
            & predicted_candidates
        )

    if total_true_pairs == 0:
        return 1.0

    return (
        recovered_true_pairs
        / total_true_pairs
    )