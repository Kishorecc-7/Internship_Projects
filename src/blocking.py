import duckdb
import pandas as pd
from pathlib import Path

from .config import (
    MAX_CANDIDATES_PER_ENTITY,
    MIN_CANDIDATES_BEFORE_FALLBACK,
    RARE_TOKEN_INDEX_PARQUET,
    RARE_TOKEN_MAX_DF,
    RARE_TOKEN_MAX_PER_ENTITY,
    TARGET_PARQUET,
    DUCKDB_MEMORY_LIMIT,
    DUCKDB_THREADS,
)


def get_connection():
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    con.execute(f"SET threads={DUCKDB_THREADS}")
    return con


def build_rare_token_index(force=False):
    if RARE_TOKEN_INDEX_PARQUET.exists() and not force:
        return
    con = get_connection()
    tmp = str(RARE_TOKEN_INDEX_PARQUET) + ".tmp"
    con.execute(f"DROP TABLE IF EXISTS rare_tokens")
    query = f"""
    WITH token_rows AS (
        SELECT country_norm, entity_id AS target_id, source AS target_source,
               UNNEST(string_split(name_norm, ' ')) AS token
        FROM read_parquet('{TARGET_PARQUET}')
        WHERE name_norm <> '' AND country_norm <> ''
    ),
    valid_tokens AS (
        SELECT country_norm, token, COUNT(DISTINCT target_id) AS token_df
        FROM token_rows
        WHERE length(token) >= 4 AND token <> ''
        GROUP BY country_norm, token
        HAVING COUNT(DISTINCT target_id) <= {RARE_TOKEN_MAX_DF}
    )
    SELECT DISTINCT r.country_norm, r.token, r.target_id, r.target_source,
                    v.token_df
    FROM token_rows r
    INNER JOIN valid_tokens v
      ON r.country_norm = v.country_norm AND r.token = v.token
    WHERE length(r.token) >= 4
    """
    con.execute(f"COPY ({query}) TO '{tmp}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    con.close()
    Path(tmp).replace(RARE_TOKEN_INDEX_PARQUET)


def generate_candidates_for_batch(source1_batch):
    if source1_batch.empty:
        return pd.DataFrame(columns=["source1_id","target_id","target_source","block_priority"])

    build_rare_token_index()
    con = get_connection()
    con.register("source1_batch", source1_batch)

    query = f"""
    WITH exact AS (
        SELECT s.entity_id source1_id, t.entity_id target_id, t.source target_source,
               1 block_priority
        FROM source1_batch s
        JOIN read_parquet('{TARGET_PARQUET}') t
          ON s.country_norm=t.country_norm AND s.name_norm=t.name_norm
        WHERE s.name_norm <> ''
    ),
    exact_counts AS (
        SELECT source1_id, COUNT(*) exact_count FROM exact GROUP BY source1_id
    ),
    rare_raw AS (
        SELECT s.entity_id source1_id, r.target_id, r.target_source,
               MIN(r.token_df) token_df, 2 block_priority
        FROM source1_batch s
        JOIN read_parquet('{RARE_TOKEN_INDEX_PARQUET}') r
          ON s.country_norm=r.country_norm
         AND list_contains(string_split(s.name_norm, ' '), r.token)
        LEFT JOIN exact e
          ON e.source1_id=s.entity_id AND e.target_id=r.target_id
        WHERE e.target_id IS NULL
          AND COALESCE((SELECT exact_count FROM exact_counts ec WHERE ec.source1_id=s.entity_id),0) < {MIN_CANDIDATES_BEFORE_FALLBACK}
        GROUP BY s.entity_id, r.target_id, r.target_source
    ),
    rare AS (
        SELECT source1_id,target_id,target_source,block_priority
        FROM (
            SELECT *, ROW_NUMBER() OVER(PARTITION BY source1_id ORDER BY token_df,target_id) rn
            FROM rare_raw
        ) x
        WHERE rn <= {RARE_TOKEN_MAX_PER_ENTITY * MAX_CANDIDATES_PER_ENTITY}
    ),
    rare_counts AS (
        SELECT source1_id, COUNT(*) rare_count FROM rare GROUP BY source1_id
    ),
    prefix AS (
        SELECT s.entity_id source1_id, t.entity_id target_id, t.source target_source,
               3 block_priority
        FROM source1_batch s
        JOIN read_parquet('{TARGET_PARQUET}') t
          ON s.country_norm=t.country_norm AND s.name_prefix=t.name_prefix
        WHERE s.name_prefix <> ''
          AND COALESCE((SELECT exact_count FROM exact_counts ec WHERE ec.source1_id=s.entity_id),0)
              + COALESCE((SELECT rare_count FROM rare_counts rc WHERE rc.source1_id=s.entity_id),0) < {MIN_CANDIDATES_BEFORE_FALLBACK}
    ),
    all_candidates AS (
        SELECT * FROM exact
        UNION ALL SELECT * FROM rare
        UNION ALL SELECT * FROM prefix
    ),
    dedup AS (
        SELECT source1_id,target_id,target_source,MIN(block_priority) block_priority
        FROM all_candidates GROUP BY source1_id,target_id,target_source
    ),
    ranked AS (
        SELECT *, ROW_NUMBER() OVER(PARTITION BY source1_id ORDER BY block_priority,target_id) rn
        FROM dedup
    )
    SELECT source1_id,target_id,target_source,block_priority
    FROM ranked WHERE rn <= {MAX_CANDIDATES_PER_ENTITY}
    """
    try:
        return con.execute(query).fetchdf()
    finally:
        con.close()
