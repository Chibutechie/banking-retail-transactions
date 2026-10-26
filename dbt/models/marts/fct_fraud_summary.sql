with

    fraud_patterns as (

        select
            channel_clean as channel,
            location_state as state,
            count(*) as transaction_count,
            countif(is_fraud) as fraud_count,
            safe_divide(countif(is_fraud), count(*)) as fraud_rate,
            sum(if(is_fraud, amount_ngn, 0)) as fraud_amount_ngn,
            safe_divide(
                sum(if(is_fraud, amount_ngn, 0)), sum(amount_ngn)
            ) as fraud_value_rate,
            min(transaction_date) as first_fraud_date,
            max(transaction_date) as last_fraud_date

        from {{ ref("fct_transactions") }}
        group by channel_clean, location_state

    )

select
    channel,
    state,
    transaction_count,
    fraud_count,
    fraud_rate,
    fraud_amount_ngn,
    fraud_value_rate,
    first_fraud_date,
    last_fraud_date,
    row_number() over (order by fraud_count desc) as fraud_count_rank,
    row_number() over (order by fraud_rate desc) as fraud_rate_rank

from fraud_patterns
