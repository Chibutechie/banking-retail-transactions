{{
    config(
        severity="error",
        warn_if="!= 0",
        error_if="!= 0",
    )
}}

select
    transaction_id,
    customer_id,
    transaction_timestamp,
    cast(transaction_timestamp as date) as transaction_date
from {{ ref("stg_transactions") }}
where
    cast(transaction_timestamp as date) < date "2023-01-01"
    or cast(transaction_timestamp as date) > date "2024-12-31"
