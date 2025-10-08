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

Pipeline de données crypto orchestré avec Prefect 3.x qui extrait les données en temps réel depuis l'API Binance.

**Tech Stack:**

- **Orchestration**: Prefect 3.x (workflow orchestration with scheduling)
- **Data Source**: Binance Public REST API (no API key required)
- **Data Processing**: pandas
- **Deployment**: Docker-based deployment with docker-compose
- **Backend**: PostgreSQL for Prefect metadata

**Project Structure:**

```
pipelines/
  Binance/     - Pipeline Binance crypto real-time (every 5 minutes)
```

## Architecture

### Pipeline Flow

```
Binance API → pandas DataFrame → Logs
     ↓              ↓                ↓
REST API      Data extraction    Console output
```

### Key Components

1. **main.py** - Main Prefect flow orchestrating the extraction:

   - `extract_binance_data()`: Fetches real-time crypto data from Binance API
   - Currently in Phase 1: extraction only

2. **binance_extractor.py** - Binance API client

   - `BinanceExtractor` class: Fetches ticker data, order book, and recent trades
   - `get_binance_data()`: Main function that extracts data for configured symbols

3. **deploy.py** - Prefect deployment configuration
   - Defines scheduled execution (every 5 minutes: _/5 _ \* \* \*)
   - Production deployment with tags and versioning

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

Create `.env` file (optional, not required for Binance pipeline):

```env
# Currently no environment variables needed
# Binance Public API doesn't require authentication
```

### Running Locally

**Run complete pipeline:**

```bash
python pipelines/Binance/main.py
```

**Test Binance extractor directly:**

```bash
python pipelines/Binance/binance_extractor.py
```

### Prefect Development

**Docker-based deployment (recommended):**

```bash
# 1. Start all services (Postgres + Prefect Server + Worker)
docker compose up -d

# 2. Access Prefect UI
# http://localhost:4200

# 3. Deploy flow
docker compose exec prefect-worker python /app/pipelines/Binance/deploy.py

# 4. View logs
docker compose logs -f prefect-worker

# 5. Stop services
docker compose down
```

**Workflow evolution (after code changes):**

```bash
# 1. Modify code locally
vim pipelines/Binance/main.py

# 2. Rebuild & restart
docker compose up -d --build

# 3. Redeploy flow
docker compose exec prefect-worker python /app/pipelines/Binance/deploy.py

# 4. Test in UI
# http://localhost:4200 → Deployments → Quick Run
```

## Binance Pipeline Details

**Pipeline Binance Real-Time** (`pipelines/Binance/`):

- **Schedule**: Every 5 minutes (_/5 _ \* \* \*)
- **Data Source**: Binance Public REST API (no API key required)
- **Symbols tracked**: BTCUSDT, ETHUSDT, BNBUSDT
- **Data extracted**:
  - 24h ticker data (price, price change %, volume, high/low)
  - Order book (best bid/ask, spread)
  - Recent trades (last 5 trades average price)

**Current Phase**: Extraction only (Phase 1)

- **Phase 2 (todo)**: Upload to Azure Blob Storage
- **Phase 3 (todo)**: Load to Snowflake
- **Phase 4 (todo)**: Transform in Snowflake (dbt)
- **Phase 4 (todo)**: Next.js visualization dashboard

**Run locally**:

```bash
python pipelines/Binance/main.py
```

**Deploy to Prefect**:

```bash
docker compose exec prefect-worker python /app/pipelines/Binance/deploy.py
```

## Modifying the Pipeline

### Adding New Crypto Symbols

Edit `pipelines/Binance/main.py` line 22, add symbols to the list:

```python
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
```

### Changing Schedule

Edit `deploy.py` line 13:

```python
cron="*/5 * * * *",  # Every 5 minutes
cron="*/15 * * * *", # Every 15 minutes
cron="0 * * * *",    # Every hour
```

Then redeploy:

```bash
docker compose exec prefect-worker python /app/pipelines/Binance/deploy.py
```

## Common Issues

**Binance API rate limiting**: Free API has rate limits (1200 requests/minute for weight). Current implementation respects limits with 0.2s delay between symbols.

**Worker not picking up scheduled runs**: Ensure worker is running with correct work pool (`default-pool`)

**Docker build fails**: Make sure you have the latest requirements.txt and Dockerfile changes

## CI/CD Pipeline

Le projet utilise GitHub Actions pour l'intégration continue (CI) et le déploiement continu (CD) vers Azure Container Registry (ACR) et un VPS.

### Architecture CI/CD

```
GitHub Push → CI Workflow → Build Docker → Push to ACR → CD Workflow → Deploy to VPS
```

### Workflows

#### CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**
- Push sur `main` avec changements dans: `pipelines/`, `Dockerfile`, `requirements.txt`, `docker-compose.yml`
- Pull requests vers `main`

**Actions:**
1. Build de l'image Docker `prefect-worker`
2. Tag avec commit SHA et `latest`
3. Push vers Azure Container Registry

**Tags créés:**
- `main-<sha>` pour les commits sur main
- `pr-<number>` pour les pull requests
- `latest` pour la branche principale

#### CD Workflow (`.github/workflows/cd.yml`)

**Triggers:**
- Après succès du CI workflow
- Push direct sur `main`

**Actions:**
1. Connexion SSH au VPS
2. Login à Azure Container Registry
3. Pull de la dernière image
4. Mise à jour de `docker-compose.prod.yml`
5. Redémarrage des services
6. Health check des conteneurs
7. Nettoyage des anciennes images

### Secrets GitHub Requis

Les secrets suivants doivent être configurés dans GitHub (Settings → Secrets and variables → Actions):

```bash
ACR_LOGIN_SERVER   # URL du registry ACR (ex: myregistry.azurecr.io)
ACR_USERNAME       # Username ACR
ACR_PASSWORD       # Password ACR
VPS_HOST           # IP ou hostname du VPS
VPS_USER           # Username SSH du VPS
VPS_SSH_KEY        # Clé privée SSH pour se connecter au VPS
```

### Configuration du VPS

**Prérequis sur le VPS:**

```bash
# 1. Installer Docker et Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 2. Créer le répertoire du projet
mkdir -p ~/prefect
cd ~/prefect

# 3. Vérifier que le port 4200 est disponible
sudo ufw allow 4200/tcp
```

### Déploiement Manuel (si nécessaire)

Si vous devez déployer manuellement sans CI/CD:

```bash
# 1. Se connecter au VPS
ssh user@vps-host

# 2. Aller dans le répertoire
cd ~/prefect

# 3. Login à ACR
echo "ACR_PASSWORD" | docker login myregistry.azurecr.io -u ACR_USERNAME --password-stdin

# 4. Pull l'image
docker pull myregistry.azurecr.io/prefect-worker:latest

# 5. Démarrer les services
docker compose -f docker-compose.prod.yml up -d

# 6. Vérifier le statut
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f prefect-worker
```

### Monitoring des Workflows

**Voir les runs:**
```bash
gh run list
gh run view <run-id> --log
```

**Voir les derniers logs d'un workflow:**
```bash
gh run list --workflow=ci.yml --limit=1
gh run list --workflow=cd.yml --limit=1
```

**Re-run un workflow failed:**
```bash
gh run rerun <run-id>
```

### Rollback en Cas d'Erreur

Si un déploiement échoue, vous pouvez rollback vers une version précédente:

```bash
# 1. Se connecter au VPS
ssh user@vps-host
cd ~/prefect

# 2. Lister les images disponibles
docker images | grep prefect-worker

# 3. Modifier docker-compose.prod.yml pour utiliser un tag spécifique
# Remplacer :latest par :main-<old-sha>

# 4. Redémarrer
docker compose -f docker-compose.prod.yml up -d
```

### Troubleshooting

**Le workflow CI échoue:**
- Vérifier que les secrets ACR sont correctement configurés
- Vérifier que le Dockerfile build localement: `docker build -t test .`

**Le workflow CD échoue:**
- Vérifier la connexion SSH: `ssh -i ~/.ssh/key user@vps-host`
- Vérifier que Docker est installé sur le VPS
- Vérifier les logs: `gh run view <run-id> --log`

**Les conteneurs ne démarrent pas:**
```bash
# Sur le VPS
docker compose -f docker-compose.prod.yml logs
docker compose -f docker-compose.prod.yml ps
```

## Next Steps (Roadmap)

1. **Phase 2**: Implement Azure Blob Storage upload (Parquet format)
2. **Phase 3**: Implement Snowflake loading with COPY INTO
3. **Phase 4**: Create Next.js dashboard for real-time visualization
4. **Phase 5**: Add data quality checks and alerting
