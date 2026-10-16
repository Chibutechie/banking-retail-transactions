-- Geographic transaction and fraud trends by Nigerian state (36 states + FCT).
-- Dashboard-ready aggregate for the Geographic Insights Looker Studio dashboard.

with

    geo as (

        select
            location_state as state,
            count(*) as transaction_count,
            count_if(is_fraud) as fraud_count,
            safe_divide(count_if(is_fraud), count(*)) as fraud_rate,
            sum(amount_ngn) as total_amount_ngn,
            avg(amount_ngn) as avg_amount_ngn,
            sum(if(is_success, amount_ngn, 0)) as successful_amount_ngn,
            count_if(is_success) as successful_count,
            count_if(is_debit) as debit_count,
            count_if(is_credit) as credit_count,
            count(distinct customer_id) as unique_customers,
            count(distinct account_id) as unique_accounts,
            min(transaction_date) as first_transaction_date,
            max(transaction_date) as last_transaction_date

        from fct_transactions
        group by location_state

    )

select
    state,
    transaction_count,
    fraud_count,
    fraud_rate,
    total_amount_ngn,
    avg_amount_ngn,
    successful_amount_ngn,
    successful_count,
    debit_count,
    credit_count,
    unique_customers,
    unique_accounts,
    first_transaction_date,
    last_transaction_date,
    -- rank states by transaction volume for benchmarking
    row_number() over (order by transaction_count desc) as volume_rank,
    row_number() over (order by fraud_rate desc) as fraud_rate_rank

from geo
