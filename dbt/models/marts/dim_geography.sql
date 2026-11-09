with

    source_geography as (

        select distinct
            lower(trim(location_state)) as source_state,
            coalesce(lower(trim(location_lga)), "") as location_lga
        from {{ ref("int_transactions_enriched") }}
        where location_state is not null and trim(location_state) != ""

    ),

    mapped_geography as (

        select
            coalesce(z.state, g.source_state) as state,
            g.location_lga,
            z.geopolitical_zone
        from source_geography g
        left join {{ ref("state_zones") }} z
            on g.source_state = z.state_alias

    )

select
    to_hex(md5(concat(state, "|", location_lga))) as geography_key,
    state,
    location_lga,
    max(geopolitical_zone) as geopolitical_zone
from mapped_geography
group by state, location_lga