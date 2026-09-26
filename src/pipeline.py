import pickle
import json
from pathlib import Path

import pandas as pd

from .config import (
    SOURCE1_BATCH_SIZE,
    BLOCKING_VERSION,

    SOURCE1_PARQUET,
    SOURCE2_PARQUET,
    SOURCE3_PARQUET,
    TARGET_PARQUET,

    GROUND_TRUTH_FILE,

    MATCHING_RESULTS_FILE,

    OUTPUT_SOURCE1_ID_COL,
    OUTPUT_MATCHED_IDS_COL,

    WORK_DIR,
    OUTPUT_DIR,
)

from .storage import (
    prepare_all_data,
)

from .evaluation import (
    load_ground_truth,
    calculate_blocking_recall,
)

from .validation import train_with_validation

from .blocking import (
    generate_candidates_for_batch,
)

from .training import (
    label_candidates,
    select_training_pairs,
    train_model,
)

from .prediction import (
    predict_candidates,
)


# ============================================================
# CHECKPOINT / MODEL FILES
# ============================================================

CHECKPOINT_DIR = WORK_DIR / "checkpoints" / BLOCKING_VERSION
TRAINING_CANDIDATES_DIR = CHECKPOINT_DIR / "training_candidates"
PREDICTIONS_DIR = CHECKPOINT_DIR / "predictions"

VALIDATION_REPORT_FILE = OUTPUT_DIR / f"validation_report_{BLOCKING_VERSION}.json"
MODEL_PICKLE_FILE = OUTPUT_DIR / f"lightgbm_model_{BLOCKING_VERSION}.pkl"

CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write_parquet(df, final_path):
    """Write a parquet checkpoint atomically."""
    final_path = Path(final_path)
    temp_path = final_path.with_suffix(final_path.suffix + ".tmp")

    if temp_path.exists():
        temp_path.unlink()

    df.to_parquet(
        temp_path,
        index=False,
        compression="zstd",
    )

    temp_path.replace(final_path)


def _batch_file(directory, batch_index):
    return directory / f"batch_{batch_index:06d}.parquet"


def _clear_checkpoints():
    """Remove only pipeline checkpoint artifacts."""
    import shutil

    for directory in (
        TRAINING_CANDIDATES_DIR,
        PREDICTIONS_DIR,
    ):
        if directory.exists():
            shutil.rmtree(directory)

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    if MODEL_PICKLE_FILE.exists():
        MODEL_PICKLE_FILE.unlink()

    print("All checkpoints and saved model removed.")


def _save_model(model, threshold, validation_report):
    """
    Save the trained LightGBM model as a pickle.

    The model is saved atomically so an interrupted write
    cannot leave a partially written pickle.
    """
    temp_path = MODEL_PICKLE_FILE.with_suffix(".pkl.tmp")

    if temp_path.exists():
        temp_path.unlink()

    payload = {
        "model": model,
        "model_type": "LightGBM",
        "source1_batch_size": SOURCE1_BATCH_SIZE,
        "threshold": threshold,
        "validation_report": validation_report,
        "blocking_version": BLOCKING_VERSION,
    }

    with open(temp_path, "wb") as f:
        pickle.dump(
            payload,
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    temp_path.replace(MODEL_PICKLE_FILE)

    if validation_report is not None:
        with open(VALIDATION_REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(validation_report, f, indent=2)

    print()
    print("Saved trained model:")
    print(MODEL_PICKLE_FILE)


def _load_saved_model():
    """Load the previously saved model and calibrated threshold."""
    if not MODEL_PICKLE_FILE.exists():
        return None

    print()
    print("Saved model found. Loading:")
    print(MODEL_PICKLE_FILE)

    with open(MODEL_PICKLE_FILE, "rb") as f:
        payload = pickle.load(f)

    if isinstance(payload, dict) and "model" in payload:
        return payload["model"], float(payload.get("threshold", 0.70)), payload.get("validation_report")

    # Backward-compatible fallback if a raw sklearn/lightgbm
    # estimator was saved instead of the wrapped payload.
    return payload, 0.70, None


def load_parquet(path):
    return pd.read_parquet(path)


def build_training_candidates(
    source1,
    target,
    truth,
):
    """
    Generate blocked candidate pairs for training.

    Every Source-1 batch is persisted as a parquet checkpoint.
    Existing completed batches are skipped automatically.
    """

    print()
    print("Generating training candidates with checkpoints...")

    total = len(source1)
    candidate_parts = []

    for batch_index, start in enumerate(
        range(
            0,
            total,
            SOURCE1_BATCH_SIZE,
        )
    ):
        end = min(
            start + SOURCE1_BATCH_SIZE,
            total,
        )

        checkpoint_file = _batch_file(
            TRAINING_CANDIDATES_DIR,
            batch_index,
        )

        if checkpoint_file.exists():
            print(
                f"Training blocking batch "
                f"{batch_index + 1}: "
                f"{start:,} - {end:,} "
                f"/ {total:,} -> SKIP (checkpoint)"
            )

            candidates = pd.read_parquet(
                checkpoint_file
            )

        else:
            print(
                f"Training blocking batch "
                f"{batch_index + 1}: "
                f"{start:,} - {end:,} "
                f"/ {total:,}"
            )

            batch = source1.iloc[
                start:end
            ].copy()

            candidates = generate_candidates_for_batch(
                batch
            )

            # Always write a checkpoint, including an empty
            # result. This makes an empty batch resumable too.
            _atomic_write_parquet(
                candidates,
                checkpoint_file,
            )

            print(
                f"  Checkpoint saved: "
                f"{checkpoint_file.name}"
            )

        if not candidates.empty:
            candidate_parts.append(candidates)

    if not candidate_parts:
        raise RuntimeError(
            "No candidate pairs were generated."
        )

    candidates = pd.concat(
        candidate_parts,
        ignore_index=True,
    )

    print()
    print(
        f"Total candidate pairs: "
        f"{len(candidates):,}"
    )

    recall = calculate_blocking_recall(
        candidates,
        truth,
    )

    print(
        f"Blocking recall: "
        f"{recall:.4%}"
    )

    return candidates


def create_training_model(
    source1,
    target,
    truth,
):
    candidates = build_training_candidates(
        source1,
        target,
        truth,
    )

    print()
    print("Labelling candidate pairs...")

    labeled = label_candidates(
        candidates,
        source1,
        target,
        truth,
    )

    print(
        f"Labeled pairs: "
        f"{len(labeled):,}"
    )

    print()
    print("Selecting training pairs...")

    print()
    print("Training LightGBM with source-entity validation split...")
    model, threshold, validation_report = train_with_validation(
        labeled, source1, target
    )

    print()
    print(f"Selected production threshold: {threshold:.2f}")
    metrics = validation_report.get("selected_metrics", {})
    print(f"Validation precision: {metrics.get('precision', 0.0):.4%}")
    print(f"Validation recall:    {metrics.get('recall', 0.0):.4%}")
    print(f"Validation F0.5:      {metrics.get('f0.5', 0.0):.4f}")

    return model, threshold, validation_report


def run_prediction(
    model,
    source1,
    target,
    threshold=None,
):
    """
    Run prediction in Source-1 batches.

    Every batch is saved independently. Existing prediction
    checkpoints are skipped automatically on resume.
    """

    print()
    print("Starting prediction with checkpoints...")

    total = len(source1)
    prediction_parts = []

    prediction_columns = [
        "source1_id",
        "target_id",
        "target_source",
        "probability",
    ]

    for batch_index, start in enumerate(
        range(
            0,
            total,
            SOURCE1_BATCH_SIZE,
        )
    ):
        end = min(
            start + SOURCE1_BATCH_SIZE,
            total,
        )

        checkpoint_file = _batch_file(
            PREDICTIONS_DIR,
            batch_index,
        )

        if checkpoint_file.exists():
            print(
                f"Prediction batch "
                f"{batch_index + 1}: "
                f"{start:,} - {end:,} "
                f"/ {total:,} -> SKIP (checkpoint)"
            )

            predictions = pd.read_parquet(
                checkpoint_file
            )

        else:
            print(
                f"Prediction batch "
                f"{batch_index + 1}: "
                f"{start:,} - {end:,} "
                f"/ {total:,}"
            )

            batch = source1.iloc[
                start:end
            ].copy()

            candidates = generate_candidates_for_batch(
                batch
            )

            if candidates.empty:
                predictions = pd.DataFrame(
                    columns=prediction_columns
                )
            else:
                predictions = predict_candidates(
                    model=model,
                    candidates=candidates,
                    source1_df=batch,
                    target_df=target,
                    threshold=threshold,
                )

            _atomic_write_parquet(
                predictions,
                checkpoint_file,
            )

            print(
                f"  Checkpoint saved: "
                f"{checkpoint_file.name}"
            )

        if not predictions.empty:
            prediction_parts.append(predictions)

    if not prediction_parts:
        return pd.DataFrame(
            columns=prediction_columns
        )

    return pd.concat(
        prediction_parts,
        ignore_index=True,
    )


def write_final_output(
    source1,
    predictions,
):
    """
    Produce exactly:

        source1_entity_id
        matched_entity_ids
    """

    print()
    print("Creating final submission...")

    prediction_map = {}

    if not predictions.empty:
        for source1_id, group in predictions.groupby(
            "source1_id"
        ):
            matches = (
                group["target_id"]
                .astype(str)
                .drop_duplicates()
                .tolist()
            )

            prediction_map[
                str(source1_id)
            ] = sorted(matches)

    rows = []

    for source1_id in source1["entity_id"]:
        source1_id = str(
            source1_id
        ).strip()

        matches = prediction_map.get(
            source1_id,
            [],
        )

        if matches:
            matched_ids = ",".join(matches)
        else:
            matched_ids = "[]"

        rows.append(
            {
                OUTPUT_SOURCE1_ID_COL:
                    source1_id,
                OUTPUT_MATCHED_IDS_COL:
                    matched_ids,
            }
        )

    result = pd.DataFrame(
        rows,
        columns=[
            OUTPUT_SOURCE1_ID_COL,
            OUTPUT_MATCHED_IDS_COL,
        ],
    )

    result.to_csv(
        MATCHING_RESULTS_FILE,
        sep="\t",
        index=False,
    )

    print()
    print("Final output:")
    print(MATCHING_RESULTS_FILE)
    print(
        f"Rows written: "
        f"{len(result):,}"
    )


def run_pipeline(reset=False):
    """
    Run the complete pipeline with automatic resume.

    By default, completed checkpoints and a saved model are reused.
    Pass reset=True to intentionally start from scratch.
    """

    if reset:
        _clear_checkpoints()

    print()
    print("=" * 70)
    print("LARGE-SCALE ENTITY RESOLUTION")
    print("=" * 70)

    # ========================================================
    # STEP 1
    # ========================================================

    print()
    print("STEP 1: Preparing data...")

    if not (
        SOURCE1_PARQUET.exists()
        and SOURCE2_PARQUET.exists()
        and SOURCE3_PARQUET.exists()
        and TARGET_PARQUET.exists()
    ):
        prepare_all_data()
    else:
        print(
            "Processed Parquet files "
            "already exist."
        )

    # ========================================================
    # STEP 2
    # ========================================================

    print()
    print("STEP 2: Loading processed datasets...")

    source1 = load_parquet(
        SOURCE1_PARQUET
    )

    source2 = load_parquet(
        SOURCE2_PARQUET
    )

    source3 = load_parquet(
        SOURCE3_PARQUET
    )

    target = load_parquet(
        TARGET_PARQUET
    )

    print(
        f"Source 1: {len(source1):,}"
    )

    print(
        f"Source 2: {len(source2):,}"
    )

    print(
        f"Source 3: {len(source3):,}"
    )

    print(
        f"Combined target: {len(target):,}"
    )

    # ========================================================
    # STEP 3
    # ========================================================

    print()
    print("STEP 3: Loading ground truth...")

    truth = load_ground_truth(
        GROUND_TRUTH_FILE
    )

    print(
        f"Ground-truth entities: "
        f"{len(truth):,}"
    )

    # ========================================================
    # STEP 4
    # ========================================================

    print()
    print("STEP 4: Training/loading model...")

    loaded = _load_saved_model()

    if loaded is None:
        model, threshold, validation_report = create_training_model(
            source1, target, truth
        )

        _save_model(model, threshold, validation_report)

    else:
        model, threshold, validation_report = loaded
        print(
            "Using saved LightGBM model and calibrated threshold; "
            "training will not be repeated."
        )

    # ========================================================
    # STEP 5
    # ========================================================

    print()
    print("STEP 5: Running prediction...")

    predictions = run_prediction(
        model, source1, target, threshold=threshold
    )

    print()
    print(
        f"Predicted pairs: "
        f"{len(predictions):,}"
    )

    # ========================================================
    # STEP 6
    # ========================================================

    print()
    print("STEP 6: Writing final output...")

    write_final_output(
        source1,
        predictions,
    )

    # ========================================================
    # DONE
    # ========================================================

    print()
    print("=" * 70)
    print("PIPELINE COMPLETED")
    print("=" * 70)

    print()
    print("Output file:")
    print(MATCHING_RESULTS_FILE)

    print()
    print("Model pickle:")
    print(MODEL_PICKLE_FILE)
