# DBT Best Practices - Projet YouTube Pipeline

## 📁 Structure de projet recommandée

```
youtube_dbt/
├── models/
│   ├── raw/                    # Couche bronze (données brutes)
│   │   └── schema.yml
│   ├── staging/                # Couche silver (nettoyage)
│   │   ├── stg_youtube_videos.sql
│   │   ├── stg_youtube_channels.sql
│   │   └── schema.yml
│   ├── analytics/              # Couche gold (métriques business)
│   │   ├── video_performance.sql
│   │   ├── channel_growth.sql
│   │   └── schema.yml
│   └── sources.yml             # Définition des sources
├── tests/
│   └── assert_no_duplicates.sql
├── macros/
│   └── custom_tests.sql
├── seeds/
│   └── video_categories.csv
└── dbt_project.yml
```

---

## 🏗️ Architecture en 3 couches (Medallion)

### 1. **RAW (Bronze)** - Données brutes
- **Matérialisation :** `view`
- **Objectif :** Mapper 1:1 les sources sans transformation
- **Naming :** `raw_[source]_[table]`

```sql
-- models/raw/raw_youtube_videos.sql
{{ config(materialized='view') }}

SELECT * 
FROM {{ source('snowflake', 'youtube_videos_json') }}
```

### 2. **STAGING (Silver)** - Nettoyage
- **Matérialisation :** `view` ou `incremental`
- **Objectif :** Typer, nettoyer, renommer
- **Naming :** `stg_[entity]`

```sql
-- models/staging/stg_youtube_videos.sql
{{ config(materialized='view') }}

SELECT 
    video_data:videoId::STRING as video_id,
    video_data:title::STRING as title,
    video_data:viewCount::NUMBER as view_count,
    video_data:likeCount::NUMBER as like_count,
    TO_TIMESTAMP(video_data:publishedAt::STRING) as published_at,
    loaded_at
FROM {{ ref('raw_youtube_videos') }}
WHERE video_id IS NOT NULL
```

### 3. **ANALYTICS (Gold)** - Métriques business
- **Matérialisation :** `table` ou `incremental`
- **Objectif :** Agrégations, KPIs, prêt pour dashboards
- **Naming :** `fct_[metric]` ou `dim_[dimension]`

```sql
-- models/analytics/video_performance.sql
{{ config(materialized='table') }}

SELECT 
    video_id,
    title,
    view_count,
    like_count,
    ROUND(like_count::FLOAT / NULLIF(view_count, 0) * 100, 2) as engagement_rate,
    DATE(published_at) as published_date
FROM {{ ref('stg_youtube_videos') }}
```

---

## 📋 Naming Conventions

### Prefixes
- `raw_*` : Couche RAW
- `stg_*` : Couche STAGING
- `fct_*` : Tables de faits (analytics)
- `dim_*` : Tables de dimensions (analytics)
- `int_*` : Modèles intermédiaires (entre staging et analytics)

### Exemples
```
✅ stg_youtube_videos
✅ fct_video_performance
✅ dim_channels
✅ int_video_metrics_daily

❌ youtube_videos_cleaned
❌ final_table
❌ temp_data
```

---

## 🧪 Tests de qualité de données

### Dans `schema.yml`
```yaml
models:
  - name: stg_youtube_videos
    description: "Vidéos YouTube nettoyées"
    columns:
      - name: video_id
        description: "ID unique de la vidéo"
        tests:
          - unique
          - not_null
      
      - name: view_count
        description: "Nombre de vues"
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
      
      - name: published_at
        description: "Date de publication"
        tests:
          - not_null
```

### Tests personnalisés
```sql
-- tests/assert_no_future_dates.sql
SELECT *
FROM {{ ref('stg_youtube_videos') }}
WHERE published_at > CURRENT_TIMESTAMP()
```

---

## 🔄 Modèles incrémentaux (pour grosses tables)

```sql
-- models/staging/stg_youtube_videos.sql
{{ config(
    materialized='incremental',
    unique_key='video_id',
    on_schema_change='sync_all_columns'
) }}

SELECT 
    video_data:videoId::STRING as video_id,
    video_data:viewCount::NUMBER as view_count,
    loaded_at
FROM {{ ref('raw_youtube_videos') }}

{% if is_incremental() %}
    -- Ne charger que les nouvelles données
    WHERE loaded_at > (SELECT MAX(loaded_at) FROM {{ this }})
{% endif %}
```

---

## 📝 Documentation (ESSENTIEL)

### `models/sources.yml`
```yaml
version: 2

sources:
  - name: snowflake
    database: youtube_db
    schema: raw
    tables:
      - name: youtube_videos_json
        description: "Données brutes des vidéos YouTube (JSON)"
        columns:
          - name: video_data
            description: "JSON complet de la vidéo"
          - name: loaded_at
            description: "Timestamp de chargement"
```

### `models/staging/schema.yml`
```yaml
version: 2

models:
  - name: stg_youtube_videos
    description: "Vidéos YouTube nettoyées et typées"
    columns:
      - name: video_id
        description: "ID unique YouTube"
        tests:
          - unique
          - not_null
```

---

## ⚙️ Configuration `dbt_project.yml`

```yaml
name: 'youtube_dbt'
version: '1.0.0'
profile: 'youtube_dbt'

model-paths: ["models"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]

models:
  youtube_dbt:
    raw:
      +materialized: view
      +schema: raw
    staging:
      +materialized: view
      +schema: staging
    analytics:
      +materialized: table
      +schema: analytics
      
vars:
  start_date: '2020-01-01'
```

---

## 🎯 Commandes DBT essentielles

```bash
# Installer les dépendances
dbt deps

# Compiler sans exécuter
dbt compile

# Tester les connexions
dbt debug

# Exécuter tous les modèles
dbt run

# Exécuter un modèle spécifique
dbt run --select stg_youtube_videos

# Exécuter tous les tests
dbt test

# Générer la documentation
dbt docs generate
dbt docs serve

# Exécuter staging puis analytics
dbt run --select staging+
```

---

## 📦 Packages utiles

### `packages.yml`
```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
  - package: calogica/dbt_expectations
    version: 0.10.0
```

Installer avec : `dbt deps`

---

## 🚨 Erreurs courantes à éviter

### ❌ **Ne pas faire**
```sql
-- Hardcoder les noms de tables
SELECT * FROM raw.youtube_videos

-- Pas de tests
-- Pas de documentation

-- Tout dans une seule couche
SELECT 
    video_id,
    SUM(views) as total_views
FROM raw_table
```

### ✅ **Faire**
```sql
-- Utiliser ref() et source()
SELECT * FROM {{ ref('stg_youtube_videos') }}

-- Toujours tester
-- Toujours documenter

-- Séparer en couches
-- staging/stg_youtube_videos.sql
SELECT * FROM {{ source('raw', 'videos') }}

-- analytics/video_performance.sql
SELECT video_id, SUM(views)
FROM {{ ref('stg_youtube_videos') }}
```

---

## 🔐 Configuration profiles.yml

**Localisation :** `~/.dbt/profiles.yml`

```yaml
youtube_dbt:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: abc123.eu-west-1
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: TRANSFORMER
      database: YOUTUBE_DEV
      warehouse: COMPUTE_WH
      schema: dbt_dev
      threads: 4
      
    prod:
      type: snowflake
      account: abc123.eu-west-1
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: TRANSFORMER
      database: YOUTUBE_PROD
      warehouse: COMPUTE_WH
      schema: analytics
      threads: 8
```

---

## 📊 Macros personnalisées

```sql
-- macros/cents_to_dollars.sql
{% macro cents_to_dollars(column_name, decimal_places=2) %}
    ROUND({{ column_name }} / 100.0, {{ decimal_places }})
{% endmacro %}

-- Usage dans un modèle
SELECT 
    {{ cents_to_dollars('revenue') }} as revenue_dollars
FROM {{ ref('stg_payments') }}
```

---

## 🔄 Workflow recommandé

1. **Développement local**
   ```bash
   dbt run --select stg_youtube_videos
   dbt test --select stg_youtube_videos
   ```

2. **Avant commit**
   ```bash
   dbt run
   dbt test
   dbt docs generate
   ```

3. **CI/CD (GitHub Actions)**
   - Run dbt on merge to main
   - Deploy docs automatically

---

## 📈 Métriques à tracker

Dans `analytics/`, créer :

1. **video_performance.sql** - Performance par vidéo
2. **channel_growth.sql** - Croissance de la chaîne
3. **content_analysis.sql** - Analyse du contenu
4. **engagement_metrics.sql** - Taux d'engagement

---

## 🎓 Ressources

- [DBT Docs](https://docs.getdbt.com)
- [DBT Style Guide](https://github.com/dbt-labs/corp/blob/main/dbt_style_guide.md)
- [DBT Best Practices](https://docs.getdbt.com/guides/best-practices)
- [DBT Discourse](https://discourse.getdbt.com)

---

## ✅ Checklist avant de push

- [ ] Tous les modèles ont un `schema.yml`
- [ ] Tous les modèles sont testés
- [ ] `dbt run` passe
- [ ] `dbt test` passe
- [ ] Documentation à jour
- [ ] Naming conventions respectées
- [ ] Pas de hardcoding (utiliser `var()` et `env_var()`)
