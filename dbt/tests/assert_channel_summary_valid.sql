{{
    config(
        severity = "error",
        warn_if = "!= 0",
        error_if = "!= 0",
    )
}}

-- Channel summary: fraud_count <= transaction_count, fraud_rate in [0,1],
-- amounts non-negative.

select
    channel,
    transaction_count,
    fraud_count,
    fraud_rate,
    total_amount_ngn
from {{ ref("fct_channel_summary") }}
where
    fraud_count > transaction_count
    or fraud_rate < 0
    or fraud_rate > 1
    or total_amount_ngn < 0
