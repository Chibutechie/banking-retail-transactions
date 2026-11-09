with

    channels as (

        select distinct lower(trim(channel_clean)) as channel
        from {{ ref("int_transactions_enriched") }}
        where channel_clean is not null and trim(channel_clean) != ""

    )

select to_hex(md5(channel)) as channel_key, channel
from channels