{{
    config(
        severity = "error",
        warn_if = "!= 0",
        error_if = "!= 0",
    )
}}

-- Fraud summary: fraud_count <= transaction_count, fraud_amount <= total
-- implied by per-row amounts (no total column here, so check rate bounds).

select
    channel,
    state,
    transaction_count,
    fraud_count,
    fraud_rate,
    fraud_amount_ngn
from {{ ref("fct_fraud_summary") }}
where
    fraud_count > transaction_count
    or fraud_rate < 0
    or fraud_rate > 1
    or fraud_amount_ngn < 0
