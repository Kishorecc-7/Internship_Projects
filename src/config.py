from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WORK_DIR = BASE_DIR / "work"
OUTPUT_DIR = BASE_DIR / "output"
WORK_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

SOURCE1_FILE = DATA_DIR / "train_source1.tsv"
SOURCE2_FILE = DATA_DIR / "train_source2.tsv"
SOURCE3_FILE = DATA_DIR / "train_source3.tsv"
GROUND_TRUTH_FILE = DATA_DIR / "train_ground_truth.tsv"

ENTITY_ID_COL = "entity_id"
BUSINESS_NAME_COL = "business_name"
BUSINESS_ADDRESS_COL = "business_address"
COUNTRY_COL = "country"
GROUND_TRUTH_SOURCE1_ID_COL = "source1_entity_id"
GROUND_TRUTH_MATCHED_IDS_COL = "matched_entity_ids"
OUTPUT_SOURCE1_ID_COL = "source1_entity_id"
OUTPUT_MATCHED_IDS_COL = "matched_entity_ids"
MATCHING_RESULTS_FILE = OUTPUT_DIR / "matching_results.tsv"

SOURCE1_PARQUET = WORK_DIR / "train_source1.parquet"
SOURCE2_PARQUET = WORK_DIR / "train_source2.parquet"
SOURCE3_PARQUET = WORK_DIR / "train_source3.parquet"
TARGET_PARQUET = WORK_DIR / "combined_targets.parquet"
RARE_TOKEN_INDEX_PARQUET = WORK_DIR / "rare_token_index.parquet"

SOURCE1_BATCH_SIZE = 10_000
MAX_CANDIDATES_PER_ENTITY = 50
MIN_CANDIDATES_BEFORE_FALLBACK = 20
MAX_ML_CANDIDATES_PER_ENTITY = 20

# Larger, still controlled training set. The candidate pool is generated from all records;
# only the training pairs are sampled.
MAX_POSITIVE_PAIRS = 500_000
HARD_NEGATIVES_PER_POSITIVE = 4
EASY_NEGATIVES_PER_POSITIVE = 1
RANDOM_STATE = 42

MAX_ITER = 250
LEARNING_RATE = 0.08
MAX_LEAF_NODES = 31
MIN_SAMPLES_LEAF = 30
L2_REGULARIZATION = 1.0

# Validation is used to select the production threshold instead of assuming 0.70.
VALIDATION_SOURCE1_FRACTION = 0.20
VALIDATION_MAX_POSITIVE_PAIRS = 100_000
VALIDATION_HARD_NEGATIVES_PER_POSITIVE = 4
VALIDATION_EASY_NEGATIVES_PER_POSITIVE = 1
VALIDATION_THRESHOLDS = tuple(round(x, 2) for x in [0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.92,0.94,0.96])
MIN_VALIDATION_PRECISION = 0.90

ML_THRESHOLD = 0.70

NAME_PREFIX_LENGTH = 4
MIN_TOKEN_LENGTH = 3
RARE_TOKEN_MAX_DF = 500
RARE_TOKEN_MAX_PER_ENTITY = 3

CHEAP_PREFILTER_ENABLED = True
CHEAP_PREFILTER_NAME_THRESHOLD = 0.55
CHEAP_PREFILTER_ADDRESS_THRESHOLD = 0.35
CHEAP_PREFILTER_TOP_K = 100

BLOCKING_VERSION = "adaptive_rare_prefilter_v2_eval"
DUCKDB_MEMORY_LIMIT = "12GB"
DUCKDB_THREADS = 8
