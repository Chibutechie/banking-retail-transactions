-- Merchant-category analysis: transaction volumes and fraud exposure by MCC.
-- Supports customer spending and merchant-category analysis dashboards.
-- MCC values are stored as integers in the enriched model; names are not
-- available in the source, so the code is presented alongside a generic label.
with

    mcc as (

        select
            cast(merchant_category_code as string) as merchant_category_code,
            count(*) as transaction_count,
            countif(is_fraud) as fraud_count,
            safe_divide(countif(is_fraud), count(*)) as fraud_rate,
            sum(amount_ngn) as total_amount_ngn,
            avg(amount_ngn) as avg_amount_ngn,
            sum(if(is_success, amount_ngn, 0)) as successful_amount_ngn,
            countif(is_success) as successful_count,
            count(distinct customer_id) as unique_customers,
            count(distinct merchant_name) as unique_merchants,
            min(transaction_date) as first_transaction_date,
            max(transaction_date) as last_transaction_date

        from {{ ref("fct_transactions") }}
        where merchant_category_code is not null
        group by merchant_category_code

    )

select
    merchant_category_code,
    transaction_count,
    fraud_count,
    fraud_rate,
    total_amount_ngn,
    avg_amount_ngn,
    successful_amount_ngn,
    successful_count,
    unique_customers,
    unique_merchants,
    first_transaction_date,
    last_transaction_date,
    row_number() over (order by total_amount_ngn desc) as volume_rank,
    row_number() over (order by fraud_rate desc) as fraud_rate_rank

from mcc
