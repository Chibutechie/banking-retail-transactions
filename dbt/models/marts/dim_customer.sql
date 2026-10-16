with

    metrics as (select * from {{ ref("int_customer_metrics") }}),

    keyed as (

        select
            to_hex(md5(customer_id)) as customer_key,
            customer_id,
            total_transactions,
            total_amount_ngn,
            avg_amount_ngn,
            fraud_transaction_count,
            first_transaction_date,
            last_transaction_date,
            customer_tenure_days,
            preferred_channel,
            states,

            case
                when total_amount_ngn >= 1000000
                then 'high_value'
                when total_amount_ngn >= 100000
                then 'mid_value'
                else 'low_value'
            end as customer_segment

        from metrics

    )

select *
from keyed
