"""Validate Bronze Parquet locally using DuckDB before loading to BigQuery."""

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

# Exactly the columns in the BigQuery RAW_SCHEMA, in order.
# Selecting explicitly stops extra Bronze columns from breaking the load.
CLEAN_COLUMNS = [
    "transaction_id",
    "account_id",
    "customer_id",
    "timestamp",
    "amount_ngn",
    "balance_before_ngn",
    "balance_after_ngn",
    "transaction_type",
    "channel",
    "merchant_category_code",
    "merchant_name",
    "location_lga",
    "location_state",
    "device_id",
    "status",
    "fraud_flag",
]

CLEAN_SELECT_SQL = """
    transaction_id,
    account_id,
    customer_id,
    -- Plain TIMESTAMP is microsecond precision (BigQuery rejects nanos).
    -- Bronze timestamps are treated as UTC. If they are Nigerian local
    -- time (WAT), subtract INTERVAL 1 HOUR here.
    CAST(timestamp AS TIMESTAMP) AS timestamp,
    CAST(amount_ngn AS DECIMAL(18, 2)) AS amount_ngn,
    CAST(balance_before_ngn AS DECIMAL(18, 2)) AS balance_before_ngn,
    CAST(balance_after_ngn AS DECIMAL(18, 2)) AS balance_after_ngn,
    transaction_type,
    channel,
    merchant_category_code,
    merchant_name,
    location_lga,
    location_state,
    device_id,
    status,
    fraud_flag
"""


def validate() -> dict:
    """Validate Bronze data and split it into clean and rejected records."""

    if not BRONZE_PATH.exists():
        raise FileNotFoundError(f"Bronze file not found: {BRONZE_PATH}")

    # Never let a previous run's clean file leak into this run's load.
    CLEAN_STAGING_PATH.unlink(missing_ok=True)

    logger.info("Validating Bronze Parquet...")

    with duckdb.connect() as con:
        con.execute("SET threads = 8")
        logger.info("DuckDB configured to use 8 threads.")

        # ------------------------------------------------------------------
        # Read Bronze
        # ------------------------------------------------------------------
        logger.info("Reading Bronze data...")

        con.execute(
            f"""
            CREATE VIEW bronze AS
            SELECT * FROM read_parquet('{BRONZE_PATH.as_posix()}')
            """
        )

        total = con.execute("SELECT COUNT(*) FROM bronze").fetchone()[0]
        logger.info(f"Total rows: {total:,}")

        # ------------------------------------------------------------------
        # Schema check
        # ------------------------------------------------------------------
        logger.info("Checking Bronze schema...")

        existing_columns = {
            row[0].lower() for row in con.execute("DESCRIBE bronze").fetchall()
        }
        logger.info(f"Bronze columns found: {len(existing_columns)}")

        schema_errors = [
            f"Missing: {column}"
            for column in REQUIRED_COLUMNS
            if column.lower() not in existing_columns
        ]
        # Columns the loader needs even if REQUIRED_COLUMNS omits them.
        schema_errors += [
            f"Missing: {column}"
            for column in CLEAN_COLUMNS
            if column.lower() not in existing_columns
            and f"Missing: {column}" not in schema_errors
        ]

        if schema_errors:
            logger.error(f"Schema failed: {schema_errors}")
            return {
                "status": "failed",
                "total_rows": total,
                "valid_rows": 0,
                "rejected_rows": total,
                "dead_letter_path": None,
                "dead_letter_csv_path": None,
                "clean_path": None,
                "errors": schema_errors,
            }

        logger.info("Schema validation passed.")

        # ------------------------------------------------------------------
        # Business rules
        # ------------------------------------------------------------------
        logger.info("Applying business rules...")

        con.execute(
            f"""
            CREATE TEMP TABLE validated AS
            SELECT
                *,
                ROW_NUMBER() OVER () AS _rid,  -- deterministic tiebreaker

                COALESCE(
                    ARRAY_TO_STRING(
                        list_filter(
                            [
                                CASE WHEN transaction_id IS NULL
                                      OR TRIM(CAST(transaction_id AS VARCHAR)) = ''
                                     THEN 'null_transaction_id' END,

                                CASE WHEN account_id IS NULL
                                      OR TRIM(CAST(account_id AS VARCHAR)) = ''
                                     THEN 'null_account_id' END,

                                CASE WHEN customer_id IS NULL
                                      OR TRIM(CAST(customer_id AS VARCHAR)) = ''
                                     THEN 'null_customer_id' END,

                                CASE WHEN TRY_CAST(amount_ngn AS DOUBLE) IS NULL
                                      OR TRY_CAST(amount_ngn AS DOUBLE) <= 0
                                     THEN 'invalid_amount' END,

                                CASE WHEN TRY_CAST(balance_before_ngn AS DOUBLE) IS NULL
                                      OR TRY_CAST(balance_before_ngn AS DOUBLE) < 0
                                     THEN 'invalid_balance_before' END,

                                CASE WHEN TRY_CAST(balance_after_ngn AS DOUBLE) IS NULL
                                      OR TRY_CAST(balance_after_ngn AS DOUBLE) < 0
                                     THEN 'invalid_balance_after' END,

                                CASE WHEN timestamp IS NULL
                                      OR CAST(timestamp AS DATE) NOT BETWEEN
                                         DATE '{VALID_DATE_MIN}' AND DATE '{VALID_DATE_MAX}'
                                     THEN 'invalid_timestamp' END,

                                CASE WHEN location_state IS NULL
                                      OR LOWER(TRIM(CAST(location_state AS VARCHAR)))
                                         NOT IN ({_sql_set(NIGERIAN_STATES)})
                                     THEN 'invalid_state' END,

                                CASE WHEN channel IS NULL
                                      OR LOWER(TRIM(CAST(channel AS VARCHAR)))
                                         NOT IN ({_sql_set(ALLOWED_CHANNELS)})
                                     THEN 'invalid_channel' END,

                                CASE WHEN status IS NULL
                                      OR LOWER(TRIM(CAST(status AS VARCHAR)))
                                         NOT IN ({_sql_set(ALLOWED_STATUSES)})
                                     THEN 'invalid_status' END,

                                CASE WHEN fraud_flag IS NULL
                                     THEN 'null_fraud_flag' END
                            ],
                            x -> x IS NOT NULL
                        ),
                        ', '
                    ),
                    ''
                ) AS _errors

            FROM bronze
            """
        )

        logger.info("Business-rule validation completed.")

        # ------------------------------------------------------------------
        # Duplicate detection
        # Rank only among rows that passed the business rules, so an invalid
        # earlier copy can never cause a valid later copy to be dropped.
        # ------------------------------------------------------------------
        logger.info("Checking for duplicate transaction IDs...")

        con.execute(
            """
            CREATE TEMP TABLE deduped AS
            WITH ranked AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY transaction_id, (_errors = '')
                        ORDER BY timestamp, _rid
                    ) AS _dup_rank
                FROM validated
            )
            SELECT
                * EXCLUDE (_errors, _dup_rank),
                NULLIF(
                    CASE
                        WHEN _errors = '' AND _dup_rank > 1
                            THEN 'duplicate_transaction_id'
                        ELSE _errors
                    END,
                    ''
                ) AS error_reasons
            FROM ranked
            """
        )

        logger.info("Duplicate detection completed.")

        # ------------------------------------------------------------------
        # Counts
        # ------------------------------------------------------------------
        valid_count = con.execute(
            "SELECT COUNT(*) FROM deduped WHERE error_reasons IS NULL"
        ).fetchone()[0]

        rejected_count = con.execute(
            "SELECT COUNT(*) FROM deduped WHERE error_reasons IS NOT NULL"
        ).fetchone()[0]

        logger.info(f"Valid: {valid_count:,} | Rejected: {rejected_count:,}")

        # ------------------------------------------------------------------
        # Clean staging file
        # ------------------------------------------------------------------
        clean_path = None

        if valid_count > 0:
            logger.info("Writing clean staging data...")

            CLEAN_STAGING_PATH.parent.mkdir(parents=True, exist_ok=True)

            clean = con.execute(
                f"""
                SELECT {CLEAN_SELECT_SQL}
                FROM deduped
                WHERE error_reasons IS NULL
                ORDER BY _rid
                """
            ).fetch_arrow_table()

            pq.write_table(
                clean,
                CLEAN_STAGING_PATH,
                compression="snappy",
                coerce_timestamps="us",
                allow_truncated_timestamps=True,
            )

            clean_path = str(CLEAN_STAGING_PATH)

            # Confirm the file really has microsecond timestamps.
            ts_type = pq.read_schema(CLEAN_STAGING_PATH).field("timestamp").type
            logger.info(f"Clean staging file written: {CLEAN_STAGING_PATH}")
            logger.info(f"Clean timestamp column type: {ts_type}")
        else:
            logger.error("No valid rows. Clean staging file not written.")

        # ------------------------------------------------------------------
        # Dead-letter output
        # ------------------------------------------------------------------
        dead_letter_path = None
        dead_letter_csv_path = None

        if rejected_count > 0:
            logger.info("Writing rejected records to dead-letter...")

            DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)

            dead_letter_path = DEAD_LETTER_DIR / "rejected.parquet"
            dead_letter_csv_path = DEAD_LETTER_DIR / "rejected.csv"

            rejected_sql = """
                SELECT * EXCLUDE (_rid)
                FROM deduped
                WHERE error_reasons IS NOT NULL
                ORDER BY _rid
            """

            rejected = con.execute(rejected_sql).fetch_arrow_table()

            pq.write_table(rejected, dead_letter_path, compression="snappy")
            logger.warning(f"Dead-letter Parquet created: {dead_letter_path}")

            con.execute(
                f"""
                COPY ({rejected_sql})
                TO '{dead_letter_csv_path.as_posix()}'
                WITH (FORMAT CSV, HEADER TRUE)
                """
            )
            logger.warning(f"Dead-letter CSV created: {dead_letter_csv_path}")
        else:
            logger.info("No rejected records. Dead-letter files not created.")

    # ----------------------------------------------------------------------
    # Result
    # ----------------------------------------------------------------------
    if valid_count == 0:
        status = "failed"
    elif rejected_count == 0:
        status = "passed"
    else:
        status = "completed_with_rejections"

    logger.info(f"Validation finished with status: {status}")

    return {
        "status": status,
        "total_rows": total,
        "valid_rows": valid_count,
        "rejected_rows": rejected_count,
        "dead_letter_path": str(dead_letter_path) if dead_letter_path else None,
        "dead_letter_csv_path": (
            str(dead_letter_csv_path) if dead_letter_csv_path else None
        ),
        "clean_path": clean_path,
        "errors": [] if valid_count > 0 else ["No valid rows after validation"],
    }


def _sql_set(values: frozenset[str]) -> str:
    """Convert a set of strings into normalized SQL IN-list literals."""

    return ", ".join(f"'{value.lower().strip()}'" for value in sorted(values))