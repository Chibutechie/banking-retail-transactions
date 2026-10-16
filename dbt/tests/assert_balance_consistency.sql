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
    transaction_type_clean,
    amount_ngn,
    balance_before_ngn,
    balance_after_ngn,
    balance_change_ngn
from {{ ref("int_transactions_enriched") }}
where
    (
        transaction_type_clean = 'credit'
        and balance_after_ngn <> balance_before_ngn + amount_ngn
    )
    or (
        transaction_type_clean = 'debit'
        and balance_after_ngn <> balance_before_ngn - amount_ngn
    )
