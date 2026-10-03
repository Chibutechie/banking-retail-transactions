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


def validate() -> dict:
    """Validate Bronze data and split it into clean and rejected records."""

    if not BRONZE_PATH.exists():
        raise FileNotFoundError(
            f"Bronze file not found: {BRONZE_PATH}"
        )

    logger.info("Validating Bronze Parquet...")

    with duckdb.connect() as con:

        # DuckDB configuration

        con.execute("SET threads = 8")

        logger.info(
            "DuckDB configured to use 8 threads."
        )

                 #  READ BRONZE DATA 

        logger.info("Reading Bronze data...")

        con.execute(
            f"""
            CREATE VIEW bronze AS
            SELECT *
            FROM read_parquet('{BRONZE_PATH}')
            """
        )

        total = con.execute(
            "SELECT COUNT(*) FROM bronze"
        ).fetchone()[0]

        logger.info(
            f"Total rows: {total:,}"
        )

                    # Validate schema

        logger.info("Checking Bronze schema...")

        existing_columns = {
            row[0].lower()
            for row in con.execute(
                "DESCRIBE bronze"
            ).fetchall()
        }

        logger.info(
            f"Bronze columns found: {len(existing_columns)}"
        )

        schema_errors = [
            f"Missing: {column}"
            for column in REQUIRED_COLUMNS
            if column.lower() not in existing_columns
        ]

        if schema_errors:
            logger.error(
                f"Schema failed: {schema_errors}"
            )

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

        
                # Apply business rules
        
        logger.info("Applying business rules...")

        business_rules_sql = f"""
            CREATE TEMP TABLE validated AS

            SELECT
                *,

                ARRAY_TO_STRING(
                    list_filter(
                        [
                            CASE
                                WHEN transaction_id IS NULL
                                    OR TRIM(
                                        CAST(
                                            transaction_id AS VARCHAR
                                        )
                                    ) = ''
                                THEN 'null_transaction_id'
                            END,

                            CASE
                                WHEN account_id IS NULL
                                    OR TRIM(
                                        CAST(
                                            account_id AS VARCHAR
                                        )
                                    ) = ''
                                THEN 'null_account_id'
                            END,

                            CASE
                                WHEN customer_id IS NULL
                                    OR TRIM(
                                        CAST(
                                            customer_id AS VARCHAR
                                        )
                                    ) = ''
                                THEN 'null_customer_id'
                            END,

                            CASE
                                WHEN TRY_CAST(
                                    amount_ngn AS DOUBLE
                                ) IS NULL
                                    OR CAST(
                                        amount_ngn AS DOUBLE
                                    ) <= 0
                                THEN 'invalid_amount'
                            END,

                            CASE
                                WHEN TRY_CAST(
                                    balance_before_ngn AS DOUBLE
                                ) IS NULL
                                    OR CAST(
                                        balance_before_ngn AS DOUBLE
                                    ) < 0
                                THEN 'invalid_balance_before'
                            END,

                            CASE
                                WHEN TRY_CAST(
                                    balance_after_ngn AS DOUBLE
                                ) IS NULL
                                    OR CAST(
                                        balance_after_ngn AS DOUBLE
                                    ) < 0
                                THEN 'invalid_balance_after'
                            END,

                            CASE
                                WHEN timestamp IS NULL
                                    OR CAST(
                                        timestamp AS DATE
                                    ) NOT BETWEEN
                                        DATE '{VALID_DATE_MIN}'
                                        AND DATE '{VALID_DATE_MAX}'
                                THEN 'invalid_timestamp'
                            END,

                            CASE
                                WHEN location_state IS NULL
                                    OR LOWER(
                                        TRIM(
                                            CAST(
                                                location_state AS VARCHAR
                                            )
                                        )
                                    ) NOT IN (
                                        {_sql_set(NIGERIAN_STATES)}
                                    )
                                THEN 'invalid_state'
                            END,

                            CASE
                                WHEN channel IS NULL
                                    OR LOWER(
                                        TRIM(
                                            CAST(
                                                channel AS VARCHAR
                                            )
                                        )
                                    ) NOT IN (
                                        {_sql_set(ALLOWED_CHANNELS)}
                                    )
                                THEN 'invalid_channel'
                            END,

                            CASE
                                WHEN status IS NULL
                                    OR LOWER(
                                        TRIM(
                                            CAST(
                                                status AS VARCHAR
                                            )
                                        )
                                    ) NOT IN (
                                        {_sql_set(ALLOWED_STATUSES)}
                                    )
                                THEN 'invalid_status'
                            END,

                            CASE
                                WHEN fraud_flag IS NULL
                                THEN 'null_fraud_flag'
                            END
                        ],
                        x -> x IS NOT NULL
                    ),
                    ', '
                ) AS _errors

            FROM bronze
        """

        con.execute(business_rules_sql)

        logger.info(
            "Business-rule validation completed."
        )

                 # Detect duplicate transaction IDs

        logger.info(
            "Checking for duplicate transaction IDs..."
        )

        con.execute(
            """
            CREATE TEMP TABLE deduped AS

            SELECT
                *,

                CASE
                    WHEN transaction_id IS NOT NULL
                        AND ROW_NUMBER() OVER (
                            PARTITION BY transaction_id
                            ORDER BY timestamp, transaction_id
                        ) > 1
                    THEN
                        CASE
                            WHEN _errors IS NULL
                                OR TRIM(_errors) = ''
                            THEN 'duplicate_transaction_id'

                            ELSE
                                _errors
                                || ', duplicate_transaction_id'
                        END

                    ELSE _errors
                END AS error_reasons

            FROM validated
            """
        )

        logger.info(
            "Duplicate detection completed."
        )

                #  Count clean and rejected records
        

        logger.info(
            "Counting clean and rejected records..."
        )

        valid_count = con.execute(
            """
            SELECT COUNT(*)
            FROM deduped
            WHERE error_reasons IS NULL
                OR TRIM(error_reasons) = ''
            """
        ).fetchone()[0]

        rejected_count = con.execute(
            """
            SELECT COUNT(*)
            FROM deduped
            WHERE error_reasons IS NOT NULL
                AND TRIM(error_reasons) != ''
            """
        ).fetchone()[0]

        logger.info(
            f"Valid: {valid_count:,} | "
            f"Rejected: {rejected_count:,}"
        )

        
                # Write clean staging data

        logger.info(
            "Writing clean staging data..."
        )

        CLEAN_STAGING_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        clean = con.execute(
            """
            SELECT *
            EXCLUDE (
                error_reasons,
                _errors
            )
            FROM deduped
            WHERE error_reasons IS NULL
                OR TRIM(error_reasons) = ''
            """
        ).fetch_arrow_table()

        pq.write_table(
            clean,
            CLEAN_STAGING_PATH,
            compression="snappy",
        )

        logger.info(
            f"Clean staging file written: "
            f"{CLEAN_STAGING_PATH}"
        )

            
                # Write rejected records to dead-letter
        

        dead_letter_path = None
        dead_letter_csv_path = None

        if rejected_count > 0:

            logger.info(
                "Writing rejected records to dead-letter..."
            )

            DEAD_LETTER_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )

            dead_letter_path = (
                DEAD_LETTER_DIR
                / "rejected.parquet"
            )

            dead_letter_csv_path = (
                DEAD_LETTER_DIR
                / "rejected.csv"
            )

                    
                        #  Write rejected Parquet
            

            rejected = con.execute(
                """
                SELECT *
                EXCLUDE (_errors)
                FROM deduped
                WHERE error_reasons IS NOT NULL
                    AND TRIM(error_reasons) != ''
                """
            ).fetch_arrow_table()

            pq.write_table(
                rejected,
                dead_letter_path,
                compression="snappy",
            )

            logger.warning(
                f"Dead-letter Parquet created: "
                f"{dead_letter_path}"
            )

                     # Write rejected CSV

            con.execute(
                f"""
                COPY (
                    SELECT *
                    EXCLUDE (_errors)
                    FROM deduped
                    WHERE error_reasons IS NOT NULL
                        AND TRIM(error_reasons) != ''
                )
                TO '{dead_letter_csv_path}'
                WITH (
                    FORMAT CSV,
                    HEADER TRUE
                )
                """
            )

            logger.warning(
                f"Dead-letter CSV created: "
                f"{dead_letter_csv_path}"
            )

        else:

            logger.info(
                "No rejected records. "
                "Dead-letter files not created."
            )

                
                 # Determine validation status

    if rejected_count == 0:
        status = "passed"
    else:
        status = "completed_with_rejections"

    
                     #  Return validation result

    logger.info(
        "Validation completed successfully."
    )

    return {
        "status": status,
        "total_rows": total,
        "valid_rows": valid_count,
        "rejected_rows": rejected_count,
        "dead_letter_path": (
            str(dead_letter_path)
            if dead_letter_path
            else None
        ),
        "dead_letter_csv_path": (
            str(dead_letter_csv_path)
            if dead_letter_csv_path
            else None
        ),
        "clean_path": str(
            CLEAN_STAGING_PATH
        ),
        "errors": [],
    }


def _sql_set(
    values: frozenset[str],
) -> str:
    """Convert a set of strings into normalized SQL IN-list literals."""

    return ", ".join(
        f"'{value.lower().strip()}'"
        for value in sorted(values)
    )