"""Load clean staging Parquet into BigQuery raw.transactions."""

from google.cloud import bigquery

from pipeline.config import (
    BQ_LOCATION,
    BQ_TABLE,
    CLEAN_STAGING_PATH,
    GCP_PROJECT_ID,
)

from pipeline.logger import logger


# Explicit schema matching the source dataset.
# The raw BigQuery table preserves the validated source structure.
RAW_SCHEMA = [
    bigquery.SchemaField(
        "transaction_id",
        "STRING",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "account_id",
        "STRING",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "customer_id",
        "STRING",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "timestamp",
        "TIMESTAMP",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "amount_ngn",
        "NUMERIC",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "balance_before_ngn",
        "NUMERIC",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "balance_after_ngn",
        "NUMERIC",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "transaction_type",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "channel",
        "STRING",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "merchant_category_code",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "merchant_name",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "location_lga",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "location_state",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "device_id",
        "STRING",
        mode="NULLABLE",
    ),
    bigquery.SchemaField(
        "status",
        "STRING",
        mode="REQUIRED",
    ),
    bigquery.SchemaField(
        "fraud_flag",
        "BOOLEAN",
        mode="REQUIRED",
    ),
]


def load(expected_row_count: int) -> dict:

    # 1. Check clean staging file
    

    if not CLEAN_STAGING_PATH.exists():
        raise FileNotFoundError(
            f"Clean staging not found: {CLEAN_STAGING_PATH}"
        )

    logger.info(
        f"Clean staging file found: {CLEAN_STAGING_PATH}"
    )

    
    # 2. Get BigQuery destination

    bq_table = BQ_TABLE

    logger.info(
        f"Loading clean data to BigQuery: {bq_table}"
    )

    # 3. Create BigQuery client
    

    client = bigquery.Client(
        project=GCP_PROJECT_ID
    )

    # 4. Configure BigQuery load job

    job_config = bigquery.LoadJobConfig(
        schema=RAW_SCHEMA,
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE
        ),
    )

    
    # 5. Load Parquet into BigQuery
    

    logger.info(
        "Starting BigQuery load job..."
    )

    with open(
        CLEAN_STAGING_PATH,
        "rb",
    ) as file:

        job = client.load_table_from_file(
            file,
            bq_table,
            location=BQ_LOCATION,
            job_config=job_config,
        )

    logger.info(
        f"BigQuery load job started: {job.job_id}"
    )

    # 6. Wait for BigQuery job
    

    try:

        job.result()

    except Exception as exc:

        logger.error(
            f"BigQuery load failed: {exc}"
        )

        return {
            "status": "failed",
            "bq_table": bq_table,
            "rows_loaded": 0,
            "error": str(exc),
        }

    logger.info(
        "BigQuery load job completed successfully."
    )

    # 7. Verify loaded table

    table = client.get_table(
        bq_table
    )

    rows_in_bq = table.num_rows

    logger.info(
        f"Rows currently in BigQuery: "
        f"{rows_in_bq:,}"
    )

    # 8. Validate row count

    if rows_in_bq != expected_row_count:

        error = (
            f"Row count mismatch: "
            f"expected {expected_row_count:,}, "
            f"got {rows_in_bq:,}"
        )

        logger.error(error)

        return {
            "status": "failed",
            "bq_table": bq_table,
            "rows_loaded": rows_in_bq,
            "error": error,
        }

    logger.info(
        f"Row count verification passed: "
        f"{rows_in_bq:,} rows."
    )

    # 9. Remove local staging file
    

    CLEAN_STAGING_PATH.unlink(
        missing_ok=True
    )

    logger.info(
        f"Clean staging file removed: "
        f"{CLEAN_STAGING_PATH}"
    )

    # 10. Return successful result
    

    return {
        "status": "success",
        "bq_table": bq_table,
        "rows_loaded": rows_in_bq,
        "error": None,
    }