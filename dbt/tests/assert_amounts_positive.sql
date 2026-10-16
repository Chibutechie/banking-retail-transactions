{{
    config(
        severity="error",
        warn_if="!= 0",
        error_if="!= 0",
    )
}}

select transaction_id, customer_id, amount_ngn, transaction_timestamp
from {{ ref("stg_transactions") }}
where amount_ngn <= 0
