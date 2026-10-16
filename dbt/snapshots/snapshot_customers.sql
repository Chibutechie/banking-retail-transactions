{% snapshot snapshot_customers %}

    {{
        config(
            target_schema="snapshots",
            unique_key="customer_id",
            strategy="check",
            check_cols=["customer_name", "location_state"],
        )
    }}

    with
        latest_per_customer as (

            select

                customer_id,
                customer_name,
                location_state,

                row_number() over (
                    partition by customer_id order by transaction_timestamp desc
                ) as rn

            from {{ ref("stg_transactions") }}

        )

    select customer_id, customer_name, location_state

    from latest_per_customer
    where rn = 1

{% endsnapshot %}
