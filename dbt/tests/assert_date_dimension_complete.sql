{{
    config(
        severity="warn",
        warn_if="!= 0",
        error_if="!= 0",
    )
}}

with

    expected as (select date "2023-01-01" as start_date, date "2024-12-31" as end_date),

    actual as (

        select count(distinct date_key) as actual_days from {{ ref("dim_date") }}

    ),

    span as (

        select
            date_diff(
                (select end_date from expected), (select start_date from expected), day
            )
            + 1 as expected_days

    )

select actual_days, expected_days, actual_days - expected_days as day_gap
from actual, span
where actual_days <> expected_days
