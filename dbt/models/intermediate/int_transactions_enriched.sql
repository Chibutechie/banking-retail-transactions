with

    enriched as (

        select

            transaction_id,
            account_id,
            customer_id,
            transaction_timestamp,

            cast(transaction_timestamp as date) as transaction_date,
            extract(hour from transaction_timestamp) as transaction_hour,
            extract(dayofweek from transaction_timestamp) as day_of_week,
            format_date('%A', cast(transaction_timestamp as date)) as day_name,
            extract(month from transaction_timestamp) as month,
            extract(quarter from transaction_timestamp) as quarter,
            extract(year from transaction_timestamp) as year,

            case
                when
                    extract(dayofweek from cast(transaction_timestamp as date))
                    in (1, 7)
                then true
                else false
            end as is_weekend,

            case
                when amount_ngn < 1000
                then 'micro'
                when amount_ngn < 10000
                then 'small'
                when amount_ngn < 100000
                then 'medium'
                else 'large'
            end as amount_band,

            cast(
                balance_after_ngn - balance_before_ngn as numeric
            ) as balance_change_ngn,

            lower(trim(channel)) as channel_clean,
            lower(trim(transaction_type)) as transaction_type_clean,
            lower(trim(status)) as status_clean,

            case
                when lower(trim(status)) = 'success' then true else false
            end as is_success,
            case
                when lower(trim(status)) = 'failed' then true else false
            end as is_failed,
            case
                when lower(trim(status)) = 'reversed' then true else false
            end as is_reversed,
            case
                when lower(trim(status)) = 'pending' then true else false
            end as is_pending,

            case
                when lower(trim(transaction_type)) = 'credit' then true else false
            end as is_credit,
            case
                when lower(trim(transaction_type)) = 'debit' then true else false
            end as is_debit,

            cast(fraud_flag as bool) as is_fraud,

            amount_ngn,
            balance_before_ngn,
            balance_after_ngn,
            transaction_type,
            channel,
            status,
            merchant_category_code,
            merchant_name,
            location_lga,
            location_state,
            device_id,
            fraud_flag

        from {{ ref("stg_transactions") }}

    )

select *
from enriched
