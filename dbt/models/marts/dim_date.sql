with

    date_grid as (

        select date_value
        from
            unnest(
                generate_date_array(
                    date '2023-01-01', date '2024-12-31', interval 1 day
                )
            ) as date_value

    )

select
    cast(date_value as date) as date_key,
    date_value as date,
    extract(year from date_value) as year,
    extract(quarter from date_value) as quarter,
    extract(month from date_value) as month,
    extract(day from date_value) as day,
    extract(dayofweek from date_value) as day_of_week,
    format_date('%A', date_value) as day_name,
    format_date('%B', date_value) as month_name,
    case
        when extract(dayofweek from date_value) in (1, 7) then true else false
    end as is_weekend,
    case
        when extract(month from date_value) in (1, 2, 3)
        then 'Q1'
        when extract(month from date_value) in (4, 5, 6)
        then 'Q2'
        when extract(month from date_value) in (7, 8, 9)
        then 'Q3'
        else 'Q4'
    end as fiscal_quarter

from date_grid
order by date_key
