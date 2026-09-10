# Stack Checklist

Work through this in order. Do not move to the next section until the current one works.

## 1. Project basics

- [-] Python 3.11 or newer installed
- [-] Virtual environment created
- [-] Project dependencies installed from `pyproject.toml`
- [-] Git repository has an initial commit

## 2. Docker and storage

- [-] Docker Desktop installed and running
- [-] `docker compose up -d minio` starts MinIO
- [-] MinIO console opens at `http://localhost:9001`
- [-] `lake` bucket created
- [-] Bronze, dead-letter, Silver, Gold, and manifests prefixes created

## 3. Python pipeline

- [ ] Download the historical Hugging Face Parquet dataset
- [ ] Write the untouched source file to MinIO Bronze
- [ ] Validate required fields, amounts, dates, states, channels, and duplicate IDs
- [ ] Write rejected rows with error reasons to Dead Letter
- [ ] Write a run manifest with source hash and row counts

## 4. DuckDB and dbt

- [ ] Install and configure `dbt-duckdb`
- [ ] Create one staging model for clean transactions
- [ ] Add dbt tests for transaction ID, amount, channel, and state
- [ ] Create one Gold mart: fraud analysis
- [ ] Materialise Silver and Gold outputs as Parquet

## 5. Quality checks

- [ ] Add small valid, invalid, and duplicate fixture datasets
- [ ] Add unit tests for Python validation rules
- [ ] Run the full pipeline against fixture data
- [ ] Confirm the manifest, dead-letter output, and Gold mart are created

## 6. Dashboards

- [ ] Set up Apache Superset after the Gold mart is ready
- [ ] Connect Superset to the curated DuckDB/Gold data
- [ ] Build one Fraud Analysis dashboard
- [ ] Export the dashboard configuration to `superset/exports/`

## Not in version one

- [ ] Apache Airflow
- [ ] Kafka or live streaming
- [ ] A cloud warehouse such as Snowflake, BigQuery, or Redshift
