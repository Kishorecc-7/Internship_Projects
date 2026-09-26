import pandas as pd

from .config import (
    ID_COL,
    OUTPUT_SOURCE1_ID_COL,
    OUTPUT_MATCHED_IDS_COL,
)


# ============================================================
# WRITE MATCHING RESULTS
# ============================================================

def write_matching_results(
    source1,
    predictions,
    output_path
):
    """
    Create the final competition submission.

    Required columns:

        source1_entity_id
        matched_entity_ids

    matched_entity_ids contains:
        - comma-separated matching IDs when matches exist
        - [] when there are no matches
    """

    rows = []

    for s1_id in source1[ID_COL]:

        s1_id = str(s1_id).strip()

        matches = sorted(
            predictions.get(
                s1_id,
                set()
            )
        )

        # ----------------------------------------------------
        # If matches exist
        # ----------------------------------------------------

        if matches:

            matched_ids = ",".join(matches)

        # ----------------------------------------------------
        # If no matches exist
        # ----------------------------------------------------

        else:

            matched_ids = "[]"

        rows.append(
            {
                OUTPUT_SOURCE1_ID_COL: s1_id,

                OUTPUT_MATCHED_IDS_COL: matched_ids,
            }
        )

    result = pd.DataFrame(
        rows,
        columns=[
            OUTPUT_SOURCE1_ID_COL,
            OUTPUT_MATCHED_IDS_COL,
        ]
    )

    result.to_csv(
        output_path,
        sep="\t",
        index=False
    )