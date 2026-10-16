{{
    config(
        severity = "error",
        warn_if = "!= 0",
        error_if = "!= 0",
    )
}}

-- Executive KPIs: exactly one row expected, fraud rate in [0,1],
-- customer and account counts positive.

select
    total_transactions,
    total_fraud_transactions,
    overall_fraud_rate,
    total_customers,
    total_accounts
from {{ ref("mart_executive_kpis") }}
where
    overall_fraud_rate < 0
    or overall_fraud_rate > 1
    or total_customers <= 0
    or total_accounts <= 0
