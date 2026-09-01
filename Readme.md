# Historical Retail Payments Intelligence Platform

A lean, batch-driven lakehouse project for analysing approximately five million historical Nigerian retail banking transactions from 2023–2024.

## Scope

The current dataset is a finite Hugging Face Parquet snapshot, not a live feed. The first release therefore runs on demand through one Python command rather than an orchestration platform or a collection of streaming microservices.

The flow is:

```text
Hugging Face Parquet snapshot
        -> immutable Bronze object in MinIO
        -> validation and dead-letter output
        -> dbt models on DuckDB
        -> Gold marts in MinIO
        -> Apache Superset dashboards
```

## Layout

```text
src/retail_payments_pipeline/  Python pipeline code
dbt/models/                    dbt transformations
tests/                         unit, integration, and fixture data
docs/                          architecture and operating notes
superset/                      versioned dashboard exports and future configuration
local-data/minio/              ignored local persistence for the MinIO container
docker-compose.yml             local MinIO service
```

## What is intentionally absent

- No Airflow: a finite source and one linear run do not need a scheduler.
- No streaming producers, consumers, or Kafka services.
- No dedicated warehouse product: MinIO stores Parquet and DuckDB performs analytical queries.

Airflow becomes appropriate only when scheduled source arrivals, backfills, retries, alerts, or multiple upstream dependencies are real requirements.

## Next implementation steps

1. Implement download and immutable MinIO upload in `src/retail_payments_pipeline/ingestion.py`.
2. Implement set-based validation and dead-letter handling in `validation.py`.
3. Add staging and mart models under `dbt/models/`.
4. Add a DuckDB-compatible Superset connection and dashboard exports.
