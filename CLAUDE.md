# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Code Guidelines

**IMPORTANT**: Always use GitHub CLI (`gh`) to interact with GitHub:
- View workflow runs: `gh run list`, `gh run view <run-id> --log`
- Check PR status: `gh pr list`, `gh pr view <pr-number>`
- View issues: `gh issue list`, `gh issue view <issue-number>`
- Repository info: `gh repo view`
- Never manually construct GitHub URLs or web interface links
- Use `gh` commands for all GitHub-related queries and operations

## Project Overview

Collection of data pipelines orchestrated with Prefect 3.x.

### Pipelines disponibles:

1. **YouTube Pipeline** - Extrait métriques YouTube → Azure Blob → Snowflake → dbt
2. **GitHub Trending Pipeline** - Track repos trending par technologie → Azure Blob → Snowflake
3. **Test Pipeline** - Pipeline de validation (exécution toutes les 2 minutes)

**Tech Stack:**

- **Orchestration**: Prefect 3.x (workflow orchestration with scheduling)
- **Data Sources**: YouTube Data API v3, GitHub API
- **Storage**: Azure Blob Storage (Parquet files)
- **Data Warehouse**: Snowflake
- **Transformation**: dbt (data build tool)

**Project Structure:**

```
pipelines/
  youtube/     - Pipeline YouTube (daily 12h ART)
  github/      - Pipeline GitHub Trending (daily 6h ART)
  test/        - Pipeline de test (every 2 minutes)
```

**Deployment:**

- Docker-based deployment with docker-compose
- PostgreSQL backend for Prefect metadata
- Scheduled execution (daily at 12:00 PM America/Argentina/Buenos_Aires)
- CI/CD with GitHub Actions → Azure Container Registry
- Automated deployment via GitHub Actions workflows

## Architecture

### Pipeline Flow

```
YouTube API → Azure Blob Storage → Snowflake → dbt transformations
     ↓              ↓                   ↓            ↓
youtube_extractor  Parquet files    COPY INTO   Analytics models
```

### Key Components

1. **main.py** - Main Prefect flow orchestrating 3 tasks:

   - `api_to_blob()`: Extracts YouTube data and uploads to Blob Storage
   - `copy_into()`: Loads Parquet files from Blob into Snowflake raw table
   - `dbt_run()`: Executes dbt transformations

2. **youtube_extractor.py** - YouTube API client

   - `YouTubeSearcher` class: Fetches channel and video metadata
   - `extract_and_upload()`: Main function that extracts from configured channels and uploads as Parquet

3. **snowflake_connector.py** - Snowflake connection manager

   - Context manager for safe connection handling
   - Uses credentials from environment variables

4. **deploy.py** - Prefect deployment configuration
   - Defines scheduled execution (daily at 12:00 PM America/Argentina/Buenos_Aires)
   - Production deployment with tags and versioning

### dbt Project Structure (`youtube_dbt/`)

**Models hierarchy:**

- `staging/stg_youtube_videos.sql`: Cleaned raw data from `YOUTUBE_RAW.INGESTION.YOUTUBE_VIDEOS`
- `analytics/`:
  - `dim_channel.sql`: Channel dimension (deduped by channel_id)
  - `dim_video.sql`: Video dimension (video metadata)
  - `fct_video_snapshot.sql`: **Incremental** fact table tracking video metrics over time (unique_key: video_id + loaded_at)
  - `fct_video_latest.sql`: Latest snapshot per video
  - `fct_video_engagement.sql`: Engagement metrics (like_rate, comment_rate)
  - `fact_video.sql`: Core fact table

**Important**: `fct_video_snapshot` uses `unique_key=['video_id', 'loaded_at']` to track metrics evolution. If you need to reload everything, use `dbt run --full-refresh --select fct_video_snapshot`.

## Development Commands

### Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

Create `.env` file with:

```env
YOUTUBE_API_KEY=your_key
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
BLOB_CONTAINER_NAME=raw
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=YOUTUBE_RAW
SNOWFLAKE_SCHEMA=INGESTION
SNOWFLAKE_ROLE=ACCOUNTADMIN
DBT_PROJECT_DIR=/home/prefect/prefect-production/youtube-snowflake-pipeline/youtube_dbt  # Production VPS path
```

### Running Locally

**Run complete pipeline:**

```bash
python main.py
```

**Test Snowflake connection:**

```bash
python snowflake_connector.py
```

**Run dbt only:**

```bash
cd youtube_dbt
dbt run                                    # Run all models
dbt run --select stg_youtube_videos        # Run specific model
dbt run --select tag:youtube               # Run by tag
dbt run --full-refresh                     # Full rebuild (drops tables first)
dbt test                                   # Run data quality tests
```

### Prefect Development

**Local testing (temporary server):**

```bash
python main.py  # Starts temporary Prefect server automatically
```

**Docker-based deployment (recommended):**

```bash
# 1. Start all services (Postgres + Prefect Server + Worker)
docker compose up -d

# 2. Access Prefect UI
# http://localhost:4200

# 3. Deploy flows
docker compose exec prefect-worker python /app/pipelines/youtube/deploy.py
docker compose exec prefect-worker python /app/pipelines/github/deploy.py

# 4. View logs
docker compose logs -f prefect-worker

# 5. Stop services
docker compose down
```

**Workflow evolution (after code changes):**

```bash
# 1. Modify code locally
vim pipelines/github/main.py

# 2. Rebuild & restart
docker compose up -d --build

# 3. Redeploy flows
docker compose exec prefect-worker python /app/pipelines/github/deploy.py

# 4. Test in UI
# http://localhost:4200 → Deployments → Quick Run
```

## Snowflake Configuration

The pipeline expects:

- Database: `YOUTUBE_RAW`
- Schema: `INGESTION`
- Table: `YOUTUBE_VIDEOS` (target for COPY INTO)
- External Stage: `YOUTUBE_BLOB_STAGE` pointing to Azure Blob Storage
- File Format: `PARQUET_FORMAT`

The COPY INTO command in `main.py` line 30-36 loads from the external stage.

## Important Notes

### YouTube API Quota

- Default quota: 10,000 units/day
- Resets at midnight Pacific Time
- If quota exceeded, comment out `api_to_blob()` call in `main.py` line 83 and run with existing Blob files

### dbt Incremental Models

- `fct_video_snapshot` is incremental with `unique_key=['video_id', 'loaded_at']`
- On each run, only new combinations are inserted
- To reload everything: `dbt run --full-refresh --select fct_video_snapshot`
- If model is out of sync with source, drop the table in Snowflake and run `dbt run`

### CI/CD & Deployment

- See `CI_CD_GUIDE.md` for complete CI/CD setup
- Docker images automatically built and pushed to Azure Container Registry
- GitHub Actions workflows in `.github/workflows/`:
  - `ci.yml` - Build & push Docker image to ACR
  - `cd.yml` - Deploy to production VPS
- Setup script: `scripts/setup_azure_acr.sh` to create Azure Container Registry
- Secrets required in GitHub: `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`

**Docker Cache Management:**

The Dockerfile uses a `CACHE_BUST` build argument to force invalidation of Docker layer cache when pipeline files change. This ensures that new pipeline directories (like `test/`) are properly included in the Docker image even when GitHub Actions cache is enabled. Without this, the `COPY pipelines/` layer could use stale cached data from before new files were added.

## Modifying the Pipeline

### Adding New YouTube Channels

Edit `youtube_extractor.py` line ~87, add channel IDs to the list:

```python
channel_ids = [
    "UCoOae5nYA7VqaXzerajD0lg",
    "NEW_CHANNEL_ID",
]
```

### Changing Schedule

Edit `deploy.py` line 13:

```python
cron="0 12 * * *",  # Daily at 12:00 PM
cron="0 */6 * * *", # Every 6 hours
```

Then redeploy:

```bash
python deploy.py
systemctl restart prefect-worker  # On VPS
```

### Adding New dbt Models

Place in appropriate folder:

- `youtube_dbt/models/staging/` for source cleaning
- `youtube_dbt/models/analytics/` for business logic

Tag models for selective execution:

```sql
{{ config(
    materialized='table',
    tags=['youtube', 'daily']
) }}
```

Then run: `dbt run --select tag:youtube`

## Common Issues

**"No videos extracted from any channel"**: YouTube API quota exceeded, wait for reset or use new API key

**dbt models out of sync**: Run `dbt run --full-refresh` or drop tables in Snowflake

**Snowflake connection fails**: Verify `.env` credentials and network access to Snowflake

**Worker not picking up scheduled runs**: Ensure worker is running with correct work pool (`default-pool`)
