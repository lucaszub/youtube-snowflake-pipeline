{{ config(materialized='table') }}

with dim_video as (
    select DISTINCT
        VIDEOID as video_id,
        TITLE as video_title,
        DESCRIPTION,
        TO_TIMESTAMP(PUBLISHEDAT) as published_at,
        THUMBNAILS,
        DURATION

    from {{ ref('stg_youtube_videos') }}
)


select * from dim_video