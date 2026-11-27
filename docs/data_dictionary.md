# Data Dictionary and Validation Results

## Source

The project reads `electricsheepafrica/nigerian-banking-retail-transactions` from Hugging Face. The publisher describes the dataset as synthetic and lists Apache-2.0 for the dataset. The source has no bank or bank-tier field, so it cannot support cross-bank comparisons.

The downloaded Bronze Parquet file contains 5,000,000 rows. The `timestamp` field is `TIMESTAMP_NS` without timezone metadata. Observed values range from `2023-01-01 00:07` to `2024-12-30 23:59`. Neither the type metadata nor the observed range establishes whether timestamps represent UTC or WAT. The pipeline currently casts timestamps without applying a timezone shift.

## Source columns

| Column                   | Loader type         | Meaning                                                                         |
| ------------------------ | ------------------- | ------------------------------------------------------------------------------- |
| `transaction_id`         | STRING, required    | Transaction identifier.                                                         |
| `account_id`             | STRING, required    | Account identifier.                                                             |
| `customer_id`            | STRING, required    | Customer identifier.                                                            |
| `timestamp`              | TIMESTAMP, required | Transaction timestamp; timezone convention is unverified.                       |
| `amount_ngn`             | NUMERIC, required   | Transaction amount in NGN.                                                      |
| `balance_before_ngn`     | NUMERIC, nullable   | Balance before the transaction.                                                 |
| `balance_after_ngn`      | NUMERIC, nullable   | Balance after the transaction.                                                  |
| `transaction_type`       | STRING, nullable    | Credit or debit classification.                                                 |
| `channel`                | STRING, required    | Channel label.                                                                  |
| `merchant_category_code` | STRING, nullable    | Category code; source values include blanks. Staging uses `SAFE_CAST` to INT64. |
| `merchant_name`          | STRING, nullable    | Merchant label.                                                                 |
| `location_lga`           | STRING, nullable    | Local government area.                                                          |
| `location_state`         | STRING, nullable    | State or federal territory value.                                               |
| `device_id`              | STRING, nullable    | Device identifier.                                                              |
| `status`                 | STRING, required    | Transaction status.                                                             |
| `fraud_flag`             | BOOLEAN, required   | Source fraud label.                                                             |

## Validation rules

`pipeline/validator.py` requires all 16 columns above. It rejects rows with empty transaction/account/customer IDs; non-positive or non-numeric amounts; negative or non-numeric balances; null/out-of-range timestamps; states outside the normalized 36-state-plus-FCT allowlist; channels outside `mobile`, `pos`, `atm`, `web`, `ussd`, `agent`, and `branch`; statuses outside `success`, `failed`, `reversed`, and `pending`; null fraud flags; and duplicate transaction IDs among otherwise valid rows.

The validator lowercases and trims categorical values before checking. It normalizes `Abuja (FCT)` and equivalent variants to `fct`, and accepts `pending` as a valid status. It does not reject blank merchant category codes.

## Recorded validation result

A local run on 5,000,000 source rows accepted all 5,000,000 and rejected 0.

| Rejection reason                          | Rows flagged |
| ----------------------------------------- | -----------: |
| No rejection reasons | 0 |

No rows in this run were rejected for state, status, balance, or any other validation rule.

The clean Parquet file is written to `data/staging/clean_transactions.parquet`. If a future run rejects rows, they will include `error_reasons` and be written to `data/dead-letter/rejected.parquet` and `rejected.csv`. Successful BigQuery loads truncate and replace the configured raw table, verify the loaded row count, and then delete the local clean file.
