{{ config(materialized='table') }}

with dim_channel as (
    select DISTINCT
        CHANNEL_ID,
        CHANNELTITLE,
    from {{ ref('stg_youtube_videos') }}
)


select * from dim_channel