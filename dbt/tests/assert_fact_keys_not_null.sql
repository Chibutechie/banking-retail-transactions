{{
    config(
        severity="error",
        warn_if="!= 0",
        error_if="!= 0",
    )
}}

select transaction_key, transaction_id, customer_key, date_key
from {{ ref("fct_transactions") }}
where customer_key is null or date_key is null
