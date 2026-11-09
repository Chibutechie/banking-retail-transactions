with

    customer_metrics as (

        select
            customer_id,
            min(transaction_timestamp) as first_transaction_time,
            max(transaction_timestamp) as last_transaction_time,
            count(*) as transaction_count,
            sum(if(is_success, amount_ngn, 0)) as successful_spend_ngn,
            count(distinct account_id) as distinct_accounts,
            count(distinct device_id) as distinct_devices,
            countif(is_fraud) as fraud_count
        from {{ ref("int_transactions_enriched") }}
        group by customer_id

    ),

    ranked_customers as (

        select
            *,
            ntile(4) over (
                order by successful_spend_ngn, customer_id
            ) as spend_quartile
        from customer_metrics

    )

select
    to_hex(md5(customer_id)) as customer_key,
    customer_id,
    first_transaction_time,
    last_transaction_time,
    transaction_count,
    successful_spend_ngn,
    distinct_accounts,
    distinct_devices,
    fraud_count,
    spend_quartile
from ranked_customers
