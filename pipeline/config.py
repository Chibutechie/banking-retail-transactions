"""Minimal pipeline configuration with fail-fast validation."""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

BRONZE_PATH = DATA_DIR / "bronze" / "transactions.parquet"
DEAD_LETTER_DIR = DATA_DIR / "dead-letter"
LOG_DIR = DATA_DIR / "logs"


def ensure_dirs() -> None:
    """Create required directories on pipeline startup."""
    for directory in (
        BRONZE_PATH.parent,
        DEAD_LETTER_DIR,
        LOG_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


# ── Source & Warehouse Config ─────────────────────────────────────────────────

HF_REPO_ID = "electricsheepafrica/nigerian-banking-retail-transactions"

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
BQ_DATASET_RAW = os.getenv("BQ_DATASET_RAW", "raw")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")

BQ_TABLE = f"{GCP_PROJECT_ID}.{BQ_DATASET_RAW}.transactions"


# ── Validation Rules ──────────────────────────────────────────────────────────

VALID_DATE_RANGE = (
    date(2023, 1, 1),
    date(2024, 12, 31),
)

REQUIRED_COLS = frozenset({
    "transaction_id",
    "customer_id",
    "bank_name",
    "bank_tier",
    "channel",
    "amount",
    "balance_before",
    "balance_after",
    "transaction_date",
    "state",
    "merchant_name",
    "merchant_category",
    "is_fraud",
    "transaction_status",
    "device_type",
})

ALLOWED_CHANNELS = frozenset({
    "mobile",
    "pos",
    "atm",
    "web",
    "ussd",
    "agent",
    "branch",
})

ALLOWED_STATUSES = frozenset({
    "success",
    "failed",
    "reversed",
})

NIGERIAN_STATES = frozenset({
    "abia",
    "adamawa",
    "akwa ibom",
    "anambra",
    "bauchi",
    "bayelsa",
    "benue",
    "borno",
    "cross river",
    "delta",
    "ebonyi",
    "edo",
    "ekiti",
    "enugu",
    "gombe",
    "imo",
    "jigawa",
    "kaduna",
    "kano",
    "katsina",
    "kebbi",
    "kogi",
    "kwara",
    "lagos",
    "nasarawa",
    "niger",
    "ogun",
    "ondo",
    "osun",
    "oyo",
    "plateau",
    "rivers",
    "sokoto",
    "taraba",
    "yobe",
    "zamfara",
    "fct",
})


def validate_env() -> None:
    """Fail fast if critical environment variables are missing."""
    missing = [
        variable
        for variable in ("GCP_PROJECT_ID",)
        if not os.getenv(variable)
    ]

    if missing:
        raise EnvironmentError(
            f"Missing: {', '.join(missing)}. "
            "Set in .env or environment."
        )


if __name__ == "__main__":
    validate_env()
    ensure_dirs()

    print("Configuration validated successfully.")
    print(f"Project root: {ROOT_DIR}")
    print(f"Bronze path: {BRONZE_PATH}")
    print(f"BigQuery table: {BQ_TABLE}")