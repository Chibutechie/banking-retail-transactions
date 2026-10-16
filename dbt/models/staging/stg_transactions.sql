with

    source as (select * from {{ source("raw", "transactions") }}),

    final as (

        select
            cast(transaction_id as string) as transaction_id,
            cast(account_id as string) as account_id,
            cast(`timestamp` as timestamp) as transaction_timestamp,
            cast(amount_ngn as numeric) as amount_ngn,
            cast(balance_before_ngn as numeric) as balance_before_ngn,
            cast(balance_after_ngn as numeric) as balance_after_ngn,
            cast(transaction_type as string) as transaction_type,
            cast(channel as string) as channel,
            safe_cast(merchant_category_code as int64) as merchant_category_code,
            cast(merchant_name as string) as merchant_name,
            cast(location_lga as string) as location_lga,
            cast(location_state as string) as location_state,
            cast(device_id as string) as device_id,
            cast(fraud_flag as bool) as fraud_flag

        from source
        where transaction_id is not null

    )

select *
from final
