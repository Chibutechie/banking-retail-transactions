-- Channel adoption and performance metrics across Mobile, POS, ATM, Web, USSD,
-- Agent, and Branch banking.
-- Dashboard-ready aggregate for the Channel Performance Looker Studio dashboard.

with

    channel as (

        select
            channel_clean as channel,
            count(*) as transaction_count,
            count_if(is_fraud) as fraud_count,
            safe_divide(count_if(is_fraud), count(*)) as fraud_rate,
            sum(amount_ngn) as total_amount_ngn,
            avg(amount_ngn) as avg_amount_ngn,
            sum(if(is_success, amount_ngn, 0)) as successful_amount_ngn,
            count_if(is_success) as successful_count,
            count_if(is_failed) as failed_count,
            count_if(is_reversed) as reversed_count,
            count_if(is_pending) as pending_count,
            count_if(is_debit) as debit_count,
            count_if(is_credit) as credit_count,
            sum(if(is_debit, amount_ngn, 0)) as total_debit_amount_ngn,
            sum(if(is_credit, amount_ngn, 0)) as total_credit_amount_ngn,
            count(distinct customer_id) as unique_customers,
            count(distinct account_id) as unique_accounts,
            min(transaction_date) as first_transaction_date,
            max(transaction_date) as last_transaction_date

        from fct_transactions
        group by channel_clean

    )

select
    channel,
    transaction_count,
    fraud_count,
    fraud_rate,
    total_amount_ngn,
    avg_amount_ngn,
    successful_amount_ngn,
    successful_count,
    failed_count,
    reversed_count,
    pending_count,
    debit_count,
    credit_count,
    total_debit_amount_ngn,
    total_credit_amount_ngn,
    unique_customers,
    unique_accounts,
    first_transaction_date,
    last_transaction_date,
    row_number() over (order by transaction_count desc) as volume_rank,
    row_number() over (order by fraud_rate desc) as fraud_rate_rank

from channel
