select
    date,
    count(*) as transaction_count,
    sum(amount_ngn) as total_amount_ngn,
    count_if(is_fraud) as fraud_count,
    safe_divide(count_if(is_fraud), count(*)) as fraud_rate

from {{ ref("fct_transactions") }}
group by date
order by date
