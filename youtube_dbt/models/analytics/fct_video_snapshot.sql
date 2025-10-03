{{ config(
    materialized='incremental',
    unique_key=['video_id', 'loaded_at']
) }}

-- Historique complet des performances vidéo (une ligne par vidéo par jour)

SELECT
    VIDEOID as video_id,
    CHANNEL_ID,
    -- Métriques brutes
    CAST(VIEWCOUNT AS INTEGER) as view_count,
    CAST(LIKECOUNT AS INTEGER) as like_count,
    CAST(COMMENTCOUNT AS INTEGER) as comment_count,

    -- Date du snapshot
    DATE(loaded_at) as snapshot_date,
    loaded_at

FROM {{ ref('stg_youtube_videos') }}

{% if is_incremental() %}
    -- N'ajouter que les nouvelles données qui n'existent pas déjà
    WHERE (VIDEOID, DATE(loaded_at)) NOT IN (
        SELECT video_id, snapshot_date FROM {{ this }}
    )
{% endif %}
