# Data Pipelines Collection

Collection de pipelines de données orchestrés avec Prefect 3.x

## Structure du projet

```
.
├── pipelines/
│   ├── youtube/          # Pipeline YouTube → Snowflake → dbt
│   │   ├── main.py
│   │   ├── deploy.py
│   │   ├── youtube_extractor.py
│   │   ├── snowflake_connector.py
│   │   └── youtube_dbt/
│   │
│   └── github/           # Pipeline GitHub Trending → Snowflake
│       ├── main.py
│       ├── deploy.py
│       └── github_trending.py
│
├── CLAUDE.md             # Instructions pour Claude Code
└── .env                  # Variables d'environnement
```

## Pipelines disponibles

### 🎥 YouTube Pipeline
Extrait des métriques YouTube, charge dans Snowflake et transforme avec dbt.

**Schedule:** Quotidien à 12h00 (ART)
**Déploiement:**
```bash
cd pipelines/youtube
python deploy.py
```

### 🔥 GitHub Trending Pipeline
Track les repos trending par technologie.

**Schedule:** Quotidien à 6h00 (ART)
**Déploiement:**
```bash
cd pipelines/github
python deploy.py
```

## Setup

```bash
# 1. Environnement
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Éditer .env avec vos credentials

# 3. Prefect Server (Production)
prefect config set PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://..."
prefect config set PREFECT_API_URL="http://localhost:4200/api"

# 4. Work Pool
prefect work-pool create default-pool --type process

# 5. Déployer les pipelines
cd pipelines/youtube && python deploy.py
cd ../github && python deploy.py

# 6. Démarrer le worker
prefect worker start --pool default-pool
```

## Dashboard

**Production:** https://prefect.lucaszubiarrain.com

## Documentation

Voir [CLAUDE.md](CLAUDE.md) pour les détails complets.
