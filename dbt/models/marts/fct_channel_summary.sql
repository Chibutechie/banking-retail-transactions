with

    channel as (

        select
            channel_clean as channel,
            count(*) as transaction_count,
            countif(is_fraud) as fraud_count,
            safe_divide(countif(is_fraud), count(*)) as fraud_rate,
            sum(amount_ngn) as total_amount_ngn,
            avg(amount_ngn) as avg_amount_ngn,
            sum(if(is_success, amount_ngn, 0)) as successful_amount_ngn,
            countif(is_success) as successful_count,
            countif(is_failed) as failed_count,
            countif(is_reversed) as reversed_count,
            countif(is_pending) as pending_count,
            countif(is_debit) as debit_count,
            countif(is_credit) as credit_count,
            sum(if(is_debit, amount_ngn, 0)) as total_debit_amount_ngn,
            sum(if(is_credit, amount_ngn, 0)) as total_credit_amount_ngn,
            count(distinct customer_id) as unique_customers,
            count(distinct account_id) as unique_accounts,
            min(transaction_date) as first_transaction_date,
            max(transaction_date) as last_transaction_date

        from {{ ref("fct_transactions") }}
        group by channel_clean

    )

select
    c.channel,
    c.transaction_count,
    c.fraud_count,
    c.fraud_rate,
    c.total_amount_ngn,
    c.avg_amount_ngn,
    c.successful_amount_ngn,
    c.successful_count,
    c.failed_count,
    c.reversed_count,
    c.pending_count,
    c.debit_count,
    c.credit_count,
    c.total_debit_amount_ngn,
    c.total_credit_amount_ngn,
    c.unique_customers,
    c.unique_accounts,
    c.first_transaction_date,
    c.last_transaction_date,
    row_number() over (order by c.transaction_count desc) as volume_rank,
    row_number() over (order by c.fraud_rate desc) as fraud_rate_rank

from channel as c
