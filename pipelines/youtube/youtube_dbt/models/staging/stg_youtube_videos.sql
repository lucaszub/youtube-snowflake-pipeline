{{ config(materialized='view') }}

with stg_youtube_videos as (
    select
        VIDEOID,
        CHANNELTITLE,
        TITLE,
        DESCRIPTION,
        PUBLISHEDAT,
        THUMBNAILS,
        VIEWCOUNT,
        LIKECOUNT,
        COMMENTCOUNT,
        
        -- Format lisible HH:MM:SS
        LPAD(COALESCE(REGEXP_REPLACE(REGEXP_SUBSTR(DURATION, '\\d+H'), 'H', ''), '0'), 2, '0') || ':' ||
        LPAD(COALESCE(REGEXP_REPLACE(REGEXP_SUBSTR(DURATION, '\\d+M'), 'M', ''), '0'), 2, '0') || ':' ||
        LPAD(COALESCE(REGEXP_REPLACE(REGEXP_SUBSTR(DURATION, '\\d+S'), 'S', ''), '0'), 2, '0')
        AS DURATION,
        CHANNEL_ID,
        CHANNEL_SUBSCRIBERS,
        CHANNEL_TOTAL_VIEWS,
        CHANNEL_VIDEO_COUNT,
        TO_TIMESTAMP_NTZ(loaded_at) as loaded_at


    from {{ ref('raw_youtube_videos') }}
)


select * from stg_youtube_videos