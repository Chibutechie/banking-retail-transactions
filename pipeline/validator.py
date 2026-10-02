"""Validates Bronze Parquet locally using DuckDB before any data reaches BigQuery."""

from datetime import datetime

import duckdb
import pyarrow.parquet as pq

from pipeline.config import (
    ALLOWED_CHANNELS,
    ALLOWED_STATUSES,
    BRONZE_PATH,
    CLEAN_STAGING_PATH,
    DEAD_LETTER_DIR,
    NIGERIAN_STATES,
    REQUIRED_COLUMNS,
    VALID_DATE_MAX,
    VALID_DATE_MIN,
)
from pipeline.logger import logger


def validate() -> dict:
    """
    Schema check → Business rules → Duplicates.
    Returns: status, total_rows, valid_rows, rejected_rows, dead_letter_path, clean_path, errors
    """
    if not BRONZE_PATH.exists():
        raise FileNotFoundError(f"Bronze file not found: {BRONZE_PATH}")

    logger.info("Validating Bronze Parquet...")

    with duckdb.connect() as con:
        con.execute(f"CREATE VIEW bronze AS SELECT * FROM read_parquet('{BRONZE_PATH}')")

        total = con.execute("SELECT COUNT(*) FROM bronze").fetchone()[0]
        logger.info(f"Total rows: {total:,}")

        # Schema check
        existing = {row[0].lower() for row in con.execute("DESCRIBE bronze").fetchall()}
        schema_errors = [f"Missing: {c}" for c in REQUIRED_COLUMNS if c.lower() not in existing]
        if schema_errors:
            logger.error(f"Schema failed: {schema_errors}")
            return {
                "status": "failed",
                "total_rows": total,
                "valid_rows": 0,
                "rejected_rows": total,
                "dead_letter_path": None,
                "clean_path": None,
                "errors": schema_errors,
            }

        # Business rules + null checks in one pass
        business_rules_sql = f"""
            SELECT *,
                ARRAY_TO_STRING(list_filter([
                    CASE WHEN transaction_id IS NULL OR TRIM(CAST(transaction_id AS VARCHAR)) = '' THEN 'null_id' END,
                    CASE WHEN customer_id IS NULL OR TRIM(CAST(customer_id AS VARCHAR)) = '' THEN 'null_customer' END,
                    CASE WHEN TRY_CAST(amount AS DOUBLE) IS NULL OR CAST(amount AS DOUBLE) <= 0 THEN 'invalid_amount' END,
                    CASE WHEN TRY_CAST(balance_after AS DOUBLE) IS NULL OR CAST(balance_after AS DOUBLE) < 0 THEN 'negative_balance' END,
                    CASE WHEN TRY_CAST(transaction_date AS DATE) IS NULL OR CAST(transaction_date AS DATE) NOT BETWEEN DATE '{VALID_DATE_MIN}' AND DATE '{VALID_DATE_MAX}' THEN 'invalid_date' END,
                    CASE WHEN LOWER(TRIM(CAST(state AS VARCHAR))) NOT IN ({_sql_set(NIGERIAN_STATES)}) THEN 'invalid_state' END,
                    CASE WHEN LOWER(TRIM(CAST(channel AS VARCHAR))) NOT IN ({_sql_set(ALLOWED_CHANNELS)}) THEN 'invalid_channel' END,
                    CASE WHEN LOWER(TRIM(CAST(transaction_status AS VARCHAR))) NOT IN ({_sql_set(ALLOWED_STATUSES)}) THEN 'invalid_status' END,
                    CASE WHEN is_fraud NOT IN (0, 1) THEN 'invalid_fraud' END
                ], x -> x IS NOT NULL), ', ') AS _errors
            FROM bronze
        """

        all_rows = con.execute(business_rules_sql).arrow()
        con.register("validated", all_rows)

        # Duplicate detection with stable secondary sort
        dedup_sql = """
            SELECT *,
                CASE
                    WHEN ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY transaction_date, transaction_id) > 1
                    THEN CASE WHEN _errors = '' OR _errors IS NULL THEN 'duplicate_id' ELSE _errors || ', duplicate_id' END
                    ELSE _errors
                END AS error_reasons
            FROM validated
        """

        all_deduped = con.execute(dedup_sql).arrow()
        con.register("deduped", all_deduped)

        # Split clean and rejected
        clean = con.execute("SELECT * EXCLUDE (error_reasons, _errors) FROM deduped WHERE error_reasons IS NULL OR TRIM(error_reasons) = ''").arrow()
        rejected = con.execute("SELECT * EXCLUDE (_errors) FROM deduped WHERE error_reasons IS NOT NULL AND TRIM(error_reasons) != ''").arrow()

        valid_count = len(clean)
        rejected_count = len(rejected)

        logger.info(f"Valid: {valid_count:,} | Rejected: {rejected_count:,}")

        # Write clean and dead-letter
        CLEAN_STAGING_PATH.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(clean, CLEAN_STAGING_PATH, compression="snappy")

        dead_letter_path = None
        if rejected_count > 0:
            ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            dead_letter_path = DEAD_LETTER_DIR / f"rejected_{ts}.parquet"
            DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)
            pq.write_table(rejected, dead_letter_path, compression="snappy")
            logger.warning(f"Dead-letter: {dead_letter_path}")

    return {
        "status": "passed",
        "total_rows": total,
        "valid_rows": valid_count,
        "rejected_rows": rejected_count,
        "dead_letter_path": str(dead_letter_path) if dead_letter_path else None,
        "clean_path": str(CLEAN_STAGING_PATH),
        "errors": [],
    }


def _sql_set(values: frozenset[str]) -> str:
    """Convert frozenset to SQL IN (...) literals."""
    return ", ".join(f"'{v}'" for v in sorted(values))