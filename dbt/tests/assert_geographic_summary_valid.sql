{{
    config(
        severity = "error",
        warn_if = "!= 0",
        error_if = "!= 0",
    )
}}

-- Every state row must have non-negative fraud rate and amount.
-- Also sanity-check: fraud_count cannot exceed transaction_count.

select
    state,
    transaction_count,
    fraud_count,
    fraud_rate,
    total_amount_ngn
from {{ ref("fct_geographic_summary") }}
where
    fraud_count > transaction_count
    or fraud_rate < 0
    or fraud_rate > 1
    or total_amount_ngn < 0
