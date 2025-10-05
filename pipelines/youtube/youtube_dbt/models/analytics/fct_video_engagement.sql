{{ config(materialized='table') }}

-- KPIs d'engagement par vidéo (simple)

SELECT
    video_id,
    CHANNEL_ID,
    view_count,
    like_count,
    comment_count,

    -- Taux d'engagement
    ROUND(like_count::FLOAT / NULLIF(view_count, 0) * 100, 2) as engagement_rate,

    loaded_at

FROM {{ ref('fct_video_latest') }}
WHERE video_id IS NOT NULL
