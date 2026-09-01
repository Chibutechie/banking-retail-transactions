# Architecture Notes

## Active design

- **Source:** one historical Hugging Face Parquet dataset.
- **Storage:** MinIO, with one `lake` bucket and logical `bronze`, `dead-letter`, `silver`, `gold`, and `manifests` prefixes.
- **Transformations:** dbt models executed by DuckDB.
- **Dashboards:** Superset reads curated Gold models through a DuckDB-compatible connection.
- **Execution:** an explicit Python command. The source is finite, so there is no scheduler in the first release.

## Data layers

1. Bronze is the original source snapshot and is never modified.
2. Dead-letter contains invalid records and a validation reason.
3. Silver contains clean, standardised transactions.
4. Gold contains dashboard-ready analytical marts.
