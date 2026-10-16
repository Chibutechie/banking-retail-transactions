select
    customer_segment,
    count(*) as customer_count,
    sum(total_amount_ngn) as total_volume_ngn,
    avg(total_amount_ngn) as avg_volume_per_customer_ngn,
    sum(total_transactions) as total_transactions,
    sum(fraud_transaction_count) as total_fraud_transactions,
    safe_divide(
        sum(fraud_transaction_count), sum(total_transactions)
    ) as segment_fraud_rate

from {{ ref("dim_customer") }}
group by customer_segment
order by total_volume_ngn desc
