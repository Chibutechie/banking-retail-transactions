{{
    config(
        severity="warn",
        warn_if="!= 0"
    )
}}

select
    transaction_id,
    customer_id,
    transaction_type_clean,
    amount_ngn,
    balance_before_ngn,
    balance_after_ngn,
    balance_change_ngn,
    balance_after_ngn - balance_before_ngn as observed_delta
from {{ ref("int_transactions_enriched") }}
where status_clean = 'success'
  and transaction_type_clean in ('credit', 'debit')
  and balance_before_ngn is not null
  and balance_after_ngn is not null
  and amount_ngn is not null
  and (
      (
          transaction_type_clean = 'credit'
          and abs(balance_change_ngn - amount_ngn) > 0.01
      )
      or (
          transaction_type_clean = 'debit'
          and abs(balance_change_ngn + amount_ngn) > 0.01
      )
  )