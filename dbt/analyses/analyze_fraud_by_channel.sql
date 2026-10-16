select
    channel_clean as channel,
    count(*) as total_transactions,
    count_if(is_fraud) as fraud_transactions,
    safe_divide(count_if(is_fraud), count(*)) as fraud_rate,
    sum(amount_ngn) as total_amount_ngn,
    sum(if(is_fraud, amount_ngn, 0)) as fraud_amount_ngn,
    safe_divide(sum(if(is_fraud, amount_ngn, 0)), sum(amount_ngn)) as fraud_value_rate

from {{ ref("fct_transactions") }}
group by channel_clean
order by fraud_rate desc
