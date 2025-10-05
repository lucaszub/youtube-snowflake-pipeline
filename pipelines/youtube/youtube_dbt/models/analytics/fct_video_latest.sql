{{ config(materialized='table') }}

-- Dernières performances de chaque vidéo (vue matérialisée du snapshot le plus récent)

SELECT 
    video_id,
    CHANNEL_ID,
    view_count,
    like_count,
    comment_count,
    snapshot_date,
    loaded_at
    
FROM {{ ref('fct_video_snapshot') }}

-- Prendre seulement la ligne la plus récente par vidéo
QUALIFY ROW_NUMBER() OVER (PARTITION BY video_id ORDER BY snapshot_date DESC) = 1
