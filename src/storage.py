import duckdb
import pandas as pd

from .config import (
    SOURCE1_FILE,
    SOURCE2_FILE,
    SOURCE3_FILE,

    SOURCE1_PARQUET,
    SOURCE2_PARQUET,
    SOURCE3_PARQUET,

    TARGET_PARQUET,

    DUCKDB_MEMORY_LIMIT,
    DUCKDB_THREADS,
)

from .preprocessing import (
    prepare_dataframe,
)


def get_connection():

    con = duckdb.connect()

    con.execute(
        f"SET memory_limit="
        f"'{DUCKDB_MEMORY_LIMIT}'"
    )

    con.execute(
        f"SET threads={DUCKDB_THREADS}"
    )

    return con


def convert_tsv_to_parquet(
    input_file,
    output_file,
    source_name,
):
    print()
    print(
        f"Loading {input_file}"
    )

    df = pd.read_csv(
        input_file,
        sep="\t",
        dtype=str,
        keep_default_na=False,
    )

    print(
        f"{source_name}: "
        f"{len(df):,} records"
    )

    df = prepare_dataframe(
        df=df,
        source_name=source_name,
    )

    df.to_parquet(
        output_file,
        index=False,
        compression="zstd",
    )

    print(
        f"Written: {output_file}"
    )


def prepare_all_data():

    # --------------------------------------------------------
    # Source 1
    # --------------------------------------------------------

    convert_tsv_to_parquet(
        SOURCE1_FILE,
        SOURCE1_PARQUET,
        "source1",
    )

    # --------------------------------------------------------
    # Source 2
    # --------------------------------------------------------

    convert_tsv_to_parquet(
        SOURCE2_FILE,
        SOURCE2_PARQUET,
        "source2",
    )

    # --------------------------------------------------------
    # Source 3
    # --------------------------------------------------------

    convert_tsv_to_parquet(
        SOURCE3_FILE,
        SOURCE3_PARQUET,
        "source3",
    )

    # --------------------------------------------------------
    # Combine Source 2 + Source 3
    # --------------------------------------------------------

    print()
    print(
        "Combining Source 2 and Source 3..."
    )

    con = get_connection()

    con.execute(
        f"""
        COPY (
            SELECT *
            FROM read_parquet(
                '{SOURCE2_PARQUET}'
            )

            UNION ALL

            SELECT *
            FROM read_parquet(
                '{SOURCE3_PARQUET}'
            )
        )
        TO '{TARGET_PARQUET}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )

    con.close()

    print(
        f"Target parquet created: "
        f"{TARGET_PARQUET}"
    )