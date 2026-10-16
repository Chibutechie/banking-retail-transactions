-- Executive KPI summary: platform-wide headline metrics for the Executive KPIs
-- Looker Studio dashboard. One row per run snapshot (the latest transaction
-- date is used as the "as of" anchor).

with

    base as (

        select * from fct_transactions

    ),

    totals as (

        select

            count(*) as total_transactions,
            count_if(is_fraud) as total_fraud_transactions,
            safe_divide(count_if(is_fraud), count(*)) as overall_fraud_rate,
            sum(amount_ngn) as total_transaction_value_ngn,
            avg(amount_ngn) as avg_transaction_value_ngn,
            count(distinct customer_id) as total_customers,
            count(distinct account_id) as total_accounts,
            count(distinct location_state) as states_covered,
            count(distinct channel_clean) as channels_active,
            min(transaction_date) as first_transaction_date,
            max(transaction_date) as last_transaction_date

        from base

    ),

    daily_latest as (

        -- most recent day's volume for "today" KPIs
        select
            count(*) as latest_day_transactions,
            sum(amount_ngn) as latest_day_value_ngn,
            count_if(is_fraud) as latest_day_fraud_count

        from base
        where transaction_date = (select max(transaction_date) from base)

    )

select
    t.total_transactions,
    t.total_fraud_transactions,
    t.overall_fraud_rate,
    t.total_transaction_value_ngn,
    t.avg_transaction_value_ngn,
    t.total_customers,
    t.total_accounts,
    t.states_covered,
    t.channels_active,
    t.first_transaction_date,
    t.last_transaction_date,
    d.latest_day_transactions,
    d.latest_day_value_ngn,
    d.latest_day_fraud_count,
    t.last_transaction_date as kpi_as_of_date

from totals t
cross join daily_latest d
