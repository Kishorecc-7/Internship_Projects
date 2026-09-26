import argparse

from src.pipeline import run_pipeline


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Large-scale entity resolution pipeline"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Delete existing checkpoints and saved model "
            "before starting."
        ),
    )

    args = parser.parse_args()
    run_pipeline(reset=args.reset)
