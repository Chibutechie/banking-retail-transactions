"""Pipeline configuration with fail-fast validation."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent

# Load .env from the project root regardless of the current working directory.
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT_DIR / "data"))

BRONZE_PATH = DATA_DIR / "bronze" / "transactions.parquet"
CLEAN_STAGING_PATH = DATA_DIR / "staging" / "clean_transactions.parquet"
DEAD_LETTER_DIR = DATA_DIR / "dead-letter"
LOG_DIR = DATA_DIR / "logs"
MANIFESTS_DIR = DATA_DIR / "manifests"

# Source-controlled dbt project: never created at runtime, only checked.
DBT_DIR = ROOT_DIR / "dbt"

_OUTPUT_DIRS = (
    BRONZE_PATH.parent,
    CLEAN_STAGING_PATH.parent,
    DEAD_LETTER_DIR,
    LOG_DIR,
    MANIFESTS_DIR,
)


def ensure_dirs() -> None:
    """Create runtime output directories on pipeline startup."""
    for directory in _OUTPUT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


# ── Source & Warehouse Config ─────────────────────────────────────────────────

HF_REPO_ID = "electricsheepafrica/nigerian-banking-retail-transactions"

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
BQ_DATASET_RAW = os.getenv("BQ_DATASET_RAW", "raw")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")

BQ_TABLE = f"{GCP_PROJECT_ID}.{BQ_DATASET_RAW}.transactions"

REQUIRED_ENV = ("GCP_PROJECT_ID",)


# ── Validation Rules ──────────────────────────────────────────────────────────
# Categorical values are lowercase: the validator must strip/lowercase the
# incoming data before comparing.

VALID_DATE_MIN = date(2023, 1, 1)
VALID_DATE_MAX = date(2024, 12, 31)

REQUIRED_COLUMNS = frozenset(
    """
    transaction_id account_id customer_id timestamp amount_ngn
    balance_before_ngn balance_after_ngn transaction_type channel
    merchant_category_code merchant_name location_lga location_state
    device_id status fraud_flag
    """.split()
)

ALLOWED_CHANNELS = frozenset("mobile pos atm web ussd agent branch".split())
ALLOWED_STATUSES = frozenset("success failed reversed".split())

# 36 states + FCT. Commas (not split) because several names contain spaces.
NIGERIAN_STATES = frozenset(
    name.strip()
    for name in """
    abia, adamawa, akwa ibom, anambra, bauchi, bayelsa, benue, borno,
    cross river, delta, ebonyi, edo, ekiti, enugu, gombe, imo, jigawa,
    kaduna, kano, katsina, kebbi, kogi, kwara, lagos, nasarawa, niger,
    ogun, ondo, osun, oyo, plateau, rivers, sokoto, taraba, yobe, zamfara,
    fct
    """.split(",")
)


def validate_env() -> None:
    """Fail fast if the environment or project layout is misconfigured."""
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise EnvironmentError(
            f"Missing: {', '.join(missing)}. Set in .env or environment."
        )

    if not (DBT_DIR / "dbt_project.yml").is_file():
        raise EnvironmentError(f"dbt project not found at {DBT_DIR}")


if __name__ == "__main__":
    validate_env()
    ensure_dirs()

    print("Configuration validated successfully.")
    print(f"Project root: {ROOT_DIR}")
    print(f"Bronze path: {BRONZE_PATH}")
    print(f"Clean staging path: {CLEAN_STAGING_PATH}")
    print(f"BigQuery table: {BQ_TABLE}")