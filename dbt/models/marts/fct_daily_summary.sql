with

    daily as (

        select
            d.date_key,
            d.date,
            f.channel_clean as channel,
            f.transaction_type_clean as transaction_type,
            f.status_clean as status,
            count(*) as transaction_count,
            countif(f.is_fraud) as fraud_count,
            sum(f.amount_ngn) as total_amount_ngn,
            avg(f.amount_ngn) as avg_amount_ngn,
            sum(if(f.is_success, f.amount_ngn, 0)) as successful_amount_ngn,
            countif(f.is_success) as successful_count

        from {{ ref("fct_transactions") }} f
        join {{ ref("dim_date") }} d on d.date_key = f.date_key
        group by
            d.date_key,
            d.date,
            f.channel_clean,
            f.transaction_type_clean,
            f.status_clean

    )

select
    date_key,
    date,
    channel,
    transaction_type,
    status,
    transaction_count,
    fraud_count,
    total_amount_ngn,
    avg_amount_ngn,
    successful_amount_ngn,
    successful_count,
    case
        when transaction_count = 0
        then 0
        else safe_divide(fraud_count, transaction_count)
    end as fraud_rate

from daily
