{{
    config(
        severity = "warn",
        warn_if = "!= 0",
        error_if = "!= 0",
    )
}}

-- Geographic summary should cover all 36 states plus FCT (37 rows).
-- Warn if coverage is incomplete.

with

    actual as (

        select count(distinct state) as state_count from fct_geographic_summary

    )

select
    state_count,
    37 as expected_states,
    37 - state_count as missing_states
from actual
where state_count <> 37
