with

    base as (

        select
            customer_id,
            amount_ngn,
            transaction_date,
            channel_clean,
            transaction_type_clean,
            is_success,
            is_failed,
            is_reversed,
            is_pending,
            is_fraud,
            is_credit,
            is_debit,
            location_state

        from {{ ref("int_transactions_enriched") }}

    ),

    customer_agg as (

        select

            customer_id,
            count(*) as total_transactions,
            countif(is_success) as successful_transactions,
            countif(is_failed) as failed_transactions,
            countif(is_reversed) as reversed_transactions,
            countif(is_pending) as pending_transactions,
            countif(is_fraud) as fraud_transaction_count,

            sum(amount_ngn) as total_amount_ngn,
            avg(amount_ngn) as avg_amount_ngn,
            min(amount_ngn) as min_amount_ngn,
            max(amount_ngn) as max_amount_ngn,

            sum(if(is_credit, amount_ngn, 0)) as total_credit_amount_ngn,
            sum(if(is_debit, amount_ngn, 0)) as total_debit_amount_ngn,
            countif(is_credit) as credit_transaction_count,
            countif(is_debit) as debit_transaction_count,

            min(transaction_date) as first_transaction_date,
            max(transaction_date) as last_transaction_date,
            date_diff(
                max(transaction_date), min(transaction_date), day
            ) as customer_tenure_days,

            array_agg(distinct location_state ignore nulls) as states

        from base
        group by customer_id

    ),

    channel_pref as (

        select customer_id, channel_clean as preferred_channel
        from
            (
                select
                    customer_id,
                    channel_clean,
                    count(*) as cnt,
                    row_number() over (
                        partition by customer_id order by count(*) desc, channel_clean
                    ) as rn
                from base
                group by customer_id, channel_clean
            )
        where rn = 1

    )

select
    a.customer_id,
    a.total_transactions,
    a.successful_transactions,
    a.failed_transactions,
    a.reversed_transactions,
    a.pending_transactions,
    a.fraud_transaction_count,
    a.total_amount_ngn,
    a.avg_amount_ngn,
    a.min_amount_ngn,
    a.max_amount_ngn,
    a.total_credit_amount_ngn,
    a.total_debit_amount_ngn,
    a.credit_transaction_count,
    a.debit_transaction_count,
    a.first_transaction_date,
    a.last_transaction_date,
    a.customer_tenure_days,
    coalesce(p.preferred_channel, '') as preferred_channel,
    a.states

from customer_agg a
left join channel_pref p using (customer_id)
