with

    enriched as (select * from {{ ref("int_transactions_enriched") }}),

    customer_dim as (

        select customer_key, customer_id, customer_segment
        from {{ ref("dim_customer") }}

    ),

    date_dim as (select date_key, date from {{ ref("dim_date") }})

select
    to_hex(md5(e.transaction_id)) as transaction_key,
    e.transaction_id,
    c.customer_key,
    d.date_key,
    e.account_id,
    e.transaction_timestamp,
    e.transaction_date,
    e.transaction_hour,
    e.day_of_week,
    e.day_name,
    e.month,
    e.quarter,
    e.year,
    e.is_weekend,
    e.amount_ngn,
    e.amount_band,
    e.balance_before_ngn,
    e.balance_after_ngn,
    e.balance_change_ngn,
    e.transaction_type,
    e.transaction_type_clean,
    e.channel,
    e.channel_clean,
    e.status,
    e.status_clean,
    e.is_success,
    e.is_failed,
    e.is_reversed,
    e.is_pending,
    e.is_credit,
    e.is_debit,
    e.is_fraud,
    e.fraud_flag,
    e.merchant_category_code,
    e.merchant_name,
    e.location_lga,
    e.location_state,
    e.device_id,
    c.customer_segment

from enriched e
left join customer_dim c using (customer_id)
left join date_dim d on d.date = e.transaction_date
