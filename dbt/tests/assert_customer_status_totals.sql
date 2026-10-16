{{
    config(
        severity="error",
        warn_if="!= 0",
        error_if="!= 0",
    )
}}

select
    customer_id,
    total_transactions,
    successful_transactions,
    failed_transactions,
    reversed_transactions,
    pending_transactions,
    credit_transaction_count,
    debit_transaction_count
from {{ ref("int_customer_metrics") }}
where
    successful_transactions
    + failed_transactions
    + reversed_transactions
    + pending_transactions
    <> total_transactions
    or credit_transaction_count + debit_transaction_count <> total_transactions
