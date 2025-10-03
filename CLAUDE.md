# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube data pipeline orchestrated with Prefect, extracting video metrics from YouTube API, storing in Azure Blob Storage, loading into Snowflake, and transforming with dbt.

**Tech Stack:**
- **Orchestration**: Prefect 3.x (workflow orchestration with scheduling)
- **Data Source**: YouTube Data API v3
- **Storage**: Azure Blob Storage (Parquet files)
- **Data Warehouse**: Snowflake
- **Transformation**: dbt (data build tool)

**Deployment:**
- Production-ready with systemd services
- PostgreSQL backend for Prefect metadata
- Scheduled execution (daily at 12:00 PM Europe/Paris)

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
   - Defines scheduled execution (daily at 12:00 PM Europe/Paris)
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
DBT_PROJECT_DIR=/path/to/prefect/youtube_dbt
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

**Production deployment:**
```bash
# 1. Configure Prefect (PostgreSQL backend)
prefect config set PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://user:pass@localhost/prefect_db"
prefect config set PREFECT_API_URL="http://localhost:4200/api"

# 2. Create deployment with schedule (Prefect 3.x syntax)
python deploy.py

# 3. Start worker
prefect worker start --pool default-pool

# View deployments
prefect deployment ls

# Manual trigger
prefect deployment run "Pipeline YouTube → Snowflake → dbt/production-daily-12h"
```

**Note:** `deploy.py` uses Prefect 3.x `flow.deploy()` method, not the deprecated `Deployment.build_from_flow()`.

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

### Deployment
- See `DEPLOIEMENT_PRODUCTION.md` for complete VPS deployment guide
- Requires PostgreSQL for production Prefect server
- Uses systemd services for 24/7 operation

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
