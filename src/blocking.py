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

# Persistent DuckDB database containing the reusable blocking structures.
# It is built once and then opened read-only for every Source1 batch.
BLOCKING_INDEX_DB = RARE_TOKEN_INDEX_PARQUET.parent / "blocking_indexes.duckdb"
BLOCKING_INDEX_VERSION = "v2_reusable_exact_prefix_rare"


def get_connection(read_only=False):
    con = duckdb.connect(str(BLOCKING_INDEX_DB), read_only=read_only)
    con.execute(f"SET memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    con.execute(f"SET threads={DUCKDB_THREADS}")
    return con


def _index_is_ready():
    if not BLOCKING_INDEX_DB.exists():
        return False
    con = get_connection(read_only=True)
    try:
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' AND table_name IN "
            "('target_exact_index','target_prefix_index','rare_token_index')"
        ).fetchall()
        return {r[0] for r in rows} == {
            'target_exact_index', 'target_prefix_index', 'rare_token_index'
        }
    except Exception:
        return False
    finally:
        con.close()


def build_blocking_indexes(force=False):
    """Materialize exact, prefix and rare-token lookup structures once."""
    if _index_is_ready() and not force:
        return

    BLOCKING_INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    if BLOCKING_INDEX_DB.exists():
        BLOCKING_INDEX_DB.unlink()

    con = get_connection(read_only=False)
    try:
        con.execute("DROP TABLE IF EXISTS target_exact_index")
        con.execute("DROP TABLE IF EXISTS target_prefix_index")
        con.execute("DROP TABLE IF EXISTS rare_token_index")

        # Reusable exact/prefix lookup tables.  Keeping only the columns needed
        # by blocking makes the persistent database substantially smaller than
        # duplicating the whole target dataset.
        con.execute(f"""
            CREATE TABLE target_exact_index AS
            SELECT country_norm, name_norm, entity_id AS target_id, source AS target_source
            FROM read_parquet('{TARGET_PARQUET}')
            WHERE country_norm <> '' AND name_norm <> ''
        """)

        con.execute(f"""
            CREATE TABLE target_prefix_index AS
            SELECT country_norm, name_prefix, entity_id AS target_id, source AS target_source
            FROM read_parquet('{TARGET_PARQUET}')
            WHERE country_norm <> '' AND name_prefix <> ''
        """)

        con.execute(f"""
            CREATE TABLE rare_token_index AS
            WITH token_rows AS (
                SELECT country_norm,
                       entity_id AS target_id,
                       source AS target_source,
                       UNNEST(string_split(name_norm, ' ')) AS token
                FROM read_parquet('{TARGET_PARQUET}')
                WHERE country_norm <> '' AND name_norm <> ''
            ),
            valid_tokens AS (
                SELECT country_norm, token,
                       COUNT(DISTINCT target_id) AS token_df
                FROM token_rows
                WHERE length(token) >= 4 AND token <> ''
                GROUP BY country_norm, token
                HAVING COUNT(DISTINCT target_id) <= {RARE_TOKEN_MAX_DF}
            )
            SELECT DISTINCT r.country_norm, r.token, r.target_id,
                            r.target_source, v.token_df
            FROM token_rows r
            JOIN valid_tokens v
              ON r.country_norm = v.country_norm
             AND r.token = v.token
            WHERE length(r.token) >= 4
        """)

        # ART indexes make repeated equality lookups cheap.  DuckDB may choose
        # another join strategy when that is cheaper; the indexes are hints,
        # not a forced execution plan.
        con.execute("CREATE INDEX idx_exact ON target_exact_index(country_norm, name_norm)")
        con.execute("CREATE INDEX idx_prefix ON target_prefix_index(country_norm, name_prefix)")
        con.execute("CREATE INDEX idx_rare ON rare_token_index(country_norm, token)")
        con.execute("CHECKPOINT")
    finally:
        con.close()


def _candidate_columns():
    return ["source1_id", "target_id", "target_source", "block_priority"]


def generate_candidates_for_batch(source1_batch):
    if source1_batch.empty:
        return pd.DataFrame(columns=_candidate_columns())

    build_blocking_indexes()
    con = get_connection(read_only=True)
    con.register("source1_batch", source1_batch)

    # The important optimization here is that the Source1 batch is tokenized
    # once into relational rows.  This avoids list_contains(string_split(...))
    # against the entire rare-token table.
    query = f"""
    WITH source1_tokens AS (
        SELECT s.entity_id AS source1_id,
               s.country_norm,
               token
        FROM source1_batch s,
             UNNEST(string_split(s.name_norm, ' ')) AS u(token)
        WHERE s.country_norm <> ''
          AND s.name_norm <> ''
          AND length(token) >= 4
          AND token <> ''
    ),
    exact AS (
        SELECT s.entity_id AS source1_id,
               t.target_id,
               t.target_source,
               1 AS block_priority
        FROM source1_batch s
        JOIN target_exact_index t
          ON s.country_norm = t.country_norm
         AND s.name_norm = t.name_norm
        WHERE s.name_norm <> ''
    ),
    exact_counts AS (
        SELECT source1_id, COUNT(*) AS exact_count
        FROM exact
        GROUP BY source1_id
    ),
    rare_raw AS (
        SELECT st.source1_id,
               r.target_id,
               r.target_source,
               MIN(r.token_df) AS token_df,
               2 AS block_priority
        FROM source1_tokens st
        JOIN rare_token_index r
          ON st.country_norm = r.country_norm
         AND st.token = r.token
        LEFT JOIN exact e
          ON e.source1_id = st.source1_id
         AND e.target_id = r.target_id
        WHERE e.target_id IS NULL
          AND COALESCE((
              SELECT ec.exact_count
              FROM exact_counts ec
              WHERE ec.source1_id = st.source1_id
          ), 0) < {MIN_CANDIDATES_BEFORE_FALLBACK}
        GROUP BY st.source1_id, r.target_id, r.target_source
    ),
    rare AS (
        SELECT source1_id, target_id, target_source, block_priority, token_df
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY source1_id
                       ORDER BY token_df ASC, hash(target_id)
                   ) AS rn
            FROM rare_raw
        ) x
        WHERE rn <= {RARE_TOKEN_MAX_PER_ENTITY * MAX_CANDIDATES_PER_ENTITY}
    ),
    rare_counts AS (
        SELECT source1_id, COUNT(*) AS rare_count
        FROM rare
        GROUP BY source1_id
    ),
    prefix AS (
        SELECT s.entity_id AS source1_id,
               t.target_id,
               t.target_source,
               3 AS block_priority
        FROM source1_batch s
        JOIN target_prefix_index t
          ON s.country_norm = t.country_norm
         AND s.name_prefix = t.name_prefix
        WHERE s.name_prefix <> ''
          AND COALESCE((
              SELECT ec.exact_count
              FROM exact_counts ec
              WHERE ec.source1_id = s.entity_id
          ), 0)
          + COALESCE((
              SELECT rc.rare_count
              FROM rare_counts rc
              WHERE rc.source1_id = s.entity_id
          ), 0) < {MIN_CANDIDATES_BEFORE_FALLBACK}
    ),
    all_candidates AS (
        SELECT source1_id, target_id, target_source, block_priority, 0 AS token_df
        FROM exact
        UNION ALL
        SELECT source1_id, target_id, target_source, block_priority, token_df
        FROM rare
        UNION ALL
        SELECT source1_id, target_id, target_source, block_priority, 999999999 AS token_df
        FROM prefix
    ),
    dedup AS (
        SELECT source1_id,
               target_id,
               target_source,
               MIN(block_priority) AS block_priority,
               MIN(token_df) AS token_df
        FROM all_candidates
        GROUP BY source1_id, target_id, target_source
    ),
    -- Do not let a huge exact-name bucket consume every output slot.
    -- Candidate slots are distributed by blocking stage.  Rare-token matches
    -- are ordered by rarity; ties are deterministically hashed instead of
    -- sorted by target_id, which avoids systematic target-id bias.
    staged AS (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY source1_id, block_priority
                   ORDER BY token_df ASC, hash(target_id)
               ) AS stage_rn
        FROM dedup
    ),
    quota AS (
        SELECT *,
               CASE
                   WHEN block_priority = 1 THEN
                       CASE
                           WHEN COUNT(*) OVER (PARTITION BY source1_id, block_priority)
                                <= {MAX_CANDIDATES_PER_ENTITY}
                           THEN {MAX_CANDIDATES_PER_ENTITY}
                           ELSE GREATEST(1, CAST(ROUND({MAX_CANDIDATES_PER_ENTITY} * 0.60) AS BIGINT))
                       END
                   WHEN block_priority = 2 THEN
                       GREATEST(1, CAST(ROUND({MAX_CANDIDATES_PER_ENTITY} * 0.25) AS BIGINT))
                   ELSE
                       GREATEST(1, {MAX_CANDIDATES_PER_ENTITY} -
                           CAST(ROUND({MAX_CANDIDATES_PER_ENTITY} * 0.60) AS BIGINT) -
                           CAST(ROUND({MAX_CANDIDATES_PER_ENTITY} * 0.25) AS BIGINT))
               END AS stage_quota
        FROM staged
    ),
    selected AS (
        SELECT source1_id, target_id, target_source, block_priority
        FROM quota
        WHERE stage_rn <= stage_quota
    ),
    final_ranked AS (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY source1_id
                   ORDER BY block_priority,
                            hash(target_id)
               ) AS rn
        FROM selected
    )
    SELECT source1_id, target_id, target_source, block_priority
    FROM final_ranked
    WHERE rn <= {MAX_CANDIDATES_PER_ENTITY}
    """
    try:
        return con.execute(query).fetchdf()
    finally:
        con.close()
