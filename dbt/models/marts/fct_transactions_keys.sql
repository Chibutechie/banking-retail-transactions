with

    transactions as (select * from {{ ref("int_transactions_enriched") }}),

    geography_matches as (

        select
            t.transaction_id,
            t.customer_id,
            t.channel_clean,
            t.transaction_date,
            coalesce(z.state, lower(trim(t.location_state))) as state,
            coalesce(lower(trim(t.location_lga)), "") as location_lga
        from transactions t
        left join {{ ref("state_zones") }} z
            on lower(trim(t.location_state)) = z.state_alias

    )

select
    t.transaction_id,
    c.customer_key,
    ch.channel_key,
    g.geography_key,
    d.date_key
from geography_matches t
left join {{ ref("dim_customers") }} c using (customer_id)
left join {{ ref("dim_channel") }} ch on ch.channel = t.channel_clean
left join {{ ref("dim_geography") }} g
    on g.state = t.state and g.location_lga = t.location_lga
left join {{ ref("dim_date") }} d on d.date = t.transaction_date
