{{ config(materialized='view') }}

-- Vue 1:1 sur la table source Snowflake
-- Aucune transformation, juste mapper la source


SELECT * FROM YOUTUBE_RAW.INGESTION.YOUTUBE_VIDEOS


