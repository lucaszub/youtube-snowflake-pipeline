# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Code Guidelines

**IMPORTANT**: Always use CLI tools to interact with cloud services:

### GitHub CLI (`gh`)
- View workflow runs: `gh run list`, `gh run view <run-id> --log`
- Check PR status: `gh pr list`, `gh pr view <pr-number>`
- View issues: `gh issue list`, `gh issue view <issue-number>`
- Repository info: `gh repo view`
- Never manually construct GitHub URLs or web interface links
- Use `gh` commands for all GitHub-related queries and operations

### Azure CLI (`az`)
- View storage accounts: `az storage account list --output table`
- View containers: `az storage container list --account-name <account> --output table`
- View blobs: `az storage blob list --container-name <container> --account-name <account> --output table`
- View ACR repositories: `az acr repository list --name <registry> --output table`
- View ACR tags: `az acr repository show-tags --name <registry> --repository <repo> --output table`
- Monitor ACR: `az acr repository show --name <registry> --repository <repo>`
- Never manually construct Azure portal URLs
- Use `az` commands for all Azure-related queries and operations

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
Binance API → pandas DataFrame → Azure Blob Storage (Parquet)
     ↓              ↓                        ↓
REST API      Data extraction         binance/YYYY/MM/DD/*.parquet
```

### Key Components

1. **main.py** - Main Prefect flow orchestrating the pipeline:

   - `extract_binance_data()`: Fetches real-time crypto data from Binance API
   - `upload_to_blob()`: Uploads DataFrame to Azure Blob Storage in Parquet format
   - Currently in Phase 2: extraction + upload

2. **binance_extractor.py** - Binance API client

   - `BinanceExtractor` class: Fetches ticker data, order book, and recent trades
   - `get_binance_data()`: Main function that extracts data for configured symbols

3. **azure_blob_uploader.py** - Azure Blob Storage uploader
   - `AzureBlobUploader` class: Handles Parquet conversion and Azure Blob upload
   - `upload_binance_to_blob()`: Convenience function for uploading
   - Date-partitioned storage: `binance/YYYY/MM/DD/binance_data_YYYYMMDD_HHMMSS.parquet`

4. **deploy.py** - Prefect deployment configuration
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

Create `.env` file with Azure Blob Storage credentials:

```env
# Azure Blob Storage (required for Phase 2)
AZURE_STORAGE_CONNECTION_STRING=<your-connection-string>
BLOB_CONTAINER_NAME=raw

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

**Current Phase**: Extraction + Azure Blob Upload (Phase 2 - COMPLETED ✅)

- ✅ **Phase 1 (completed)**: Extract data from Binance API
- ✅ **Phase 2 (completed)**: Upload to Azure Blob Storage (Parquet with date partitioning)
  - Implemented `azure_blob_uploader.py` with `AzureBlobUploader` class
  - Conversion DataFrame → Parquet format
  - Partitioning par date: `binance/YYYY/MM/DD/binance_data_YYYYMMDD_HHMMSS.parquet`
  - Upload automatique vers Azure Blob Storage container "raw"
  - Intégration dans le flow Prefect `main.py`
- **Phase 3 (todo)**: Load to Snowflake with COPY INTO
- **Phase 4 (todo)**: Transform in Snowflake (dbt)
- **Phase 5 (todo)**: Next.js visualization dashboard

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
- Push sur `main` avec changements dans: `pipelines/`, `Dockerfile`, `requirements.txt`, `docker-compose.yml`, `.github/workflows/`
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
- **Uniquement** après succès du CI workflow (workflow_run)

**Actions:**
1. Connexion SSH au VPS
2. Login à Azure Container Registry
3. Pull de la dernière image
4. Mise à jour de `docker-compose.prod.yml`
5. Redémarrage des services
6. Déploiement du pipeline Prefect
7. Health check des conteneurs
8. Nettoyage des anciennes images

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

### Monitoring Azure Resources

**IMPORTANT**: Always use Azure CLI (`az`) for monitoring Azure resources.

**Azure Container Registry (ACR):**

```bash
# Voir tous les repositories
az acr repository list --name <registry> --output table

# Voir les tags d'une image
az acr repository show-tags --name <registry> --repository prefect-worker --output table --orderby time_desc

# Voir les détails d'une image
az acr repository show --name <registry> --repository prefect-worker

# Voir les manifests d'une image
az acr repository show-manifests --name <registry> --repository prefect-worker --output table

# Nettoyer les anciennes images (garder les 5 dernières)
az acr repository show-tags --name <registry> --repository prefect-worker --orderby time_desc --output tsv | tail -n +6 | xargs -I {} az acr repository delete --name <registry> --image prefect-worker:{} --yes
```

**Azure Blob Storage:**

```bash
# Lister les comptes de stockage
az storage account list --output table

# Lister les containers
az storage container list --account-name <account> --output table

# Lister les blobs dans un container (avec partitionnement par date)
az storage blob list --container-name raw --account-name <account> --prefix binance/ --output table

# Voir les blobs récents (aujourd'hui)
az storage blob list --container-name raw --account-name <account> --prefix binance/$(date +%Y/%m/%d)/ --output table

# Voir la taille totale d'un container
az storage blob list --container-name raw --account-name <account> --query "[].properties.contentLength" --output tsv | awk '{s+=$1} END {print s/1024/1024 " MB"}'

# Télécharger un blob pour inspection
az storage blob download --container-name raw --name <blob-path> --file ./local-file.parquet --account-name <account>

# Voir les propriétés d'un blob
az storage blob show --container-name raw --name <blob-path> --account-name <account>
```

**Configuration de l'authentification Azure CLI:**

```bash
# Login interactif
az login

# Login avec service principal (pour CI/CD)
az login --service-principal -u <client-id> -p <client-secret> --tenant <tenant-id>

# Définir la subscription par défaut
az account set --subscription <subscription-id>

# Vérifier le compte connecté
az account show
```

### Rollback en Cas d'Erreur

Si un déploiement échoue, vous pouvez rollback vers une version précédente:

```bash
# 1. Voir les tags disponibles dans ACR
az acr repository show-tags --name <registry> --repository prefect-worker --output table --orderby time_desc

# 2. Se connecter au VPS
ssh user@vps-host
cd ~/prefect

# 3. Lister les images disponibles localement
docker images | grep prefect-worker

# 4. Modifier docker-compose.prod.yml pour utiliser un tag spécifique
# Remplacer :latest par :main-<old-sha>

# 5. Redémarrer
docker compose -f docker-compose.prod.yml up -d
```

### Troubleshooting

**Le workflow CI échoue:**
- Vérifier que les secrets ACR sont correctement configurés
- Vérifier que le Dockerfile build localement: `docker build -t test .`
- Vérifier l'accès à ACR: `az acr login --name <registry>`

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

**Pipeline Binance ne upload pas vers Azure Blob:**
```bash
# Vérifier que le container existe
az storage container show --name raw --account-name <account>

# Vérifier les credentials dans .env
cat .env | grep AZURE_STORAGE_CONNECTION_STRING

# Tester l'upload manuellement
python pipelines/Binance/main.py

# Vérifier les blobs uploadés aujourd'hui
az storage blob list --container-name raw --account-name <account> --prefix binance/$(date +%Y/%m/%d)/ --output table
```

**ACR quota atteint:**
```bash
# Voir l'utilisation du registry
az acr show-usage --name <registry> --output table

# Nettoyer les anciennes images
az acr repository show-tags --name <registry> --repository prefect-worker --orderby time_desc --output tsv | tail -n +6 | xargs -I {} az acr repository delete --name <registry> --image prefect-worker:{} --yes
```

## Vérifier les Données Uploadées

**Voir les fichiers Parquet uploadés aujourd'hui:**

```bash
az storage blob list --container-name raw --account-name <account> --prefix binance/$(date +%Y/%m/%d)/ --output table
```

**Télécharger et inspecter un fichier Parquet:**

```bash
# Télécharger
az storage blob download --container-name raw --name binance/2025/10/08/binance_data_20251008_143022.parquet --file ./test.parquet --account-name <account>

# Inspecter avec Python
python -c "import pandas as pd; df=pd.read_parquet('./test.parquet'); print(df.head()); print(df.info())"
```

**Structure des données dans le Parquet:**

Les fichiers contiennent les colonnes suivantes pour chaque symbol:
- `symbol`: Paire de trading (ex: BTCUSDT)
- `price`: Prix actuel
- `price_change_percent`: Variation % sur 24h
- `volume`: Volume 24h
- `high_24h`: Prix max 24h
- `low_24h`: Prix min 24h
- `bid_price`: Meilleur prix d'achat
- `ask_price`: Meilleur prix de vente
- `spread`: Spread bid-ask
- `avg_trade_price`: Prix moyen des 5 derniers trades
- `timestamp`: Timestamp de l'extraction

## Next Steps (Roadmap)

1. ✅ **Phase 1 (completed)**: Extract data from Binance API
2. ✅ **Phase 2 (completed)**: Upload to Azure Blob Storage (Parquet format with date partitioning)
3. **Phase 3 (next)**: Implement Snowflake loading with COPY INTO
4. **Phase 4**: Transform in Snowflake (dbt)
5. **Phase 5**: Create Next.js dashboard for real-time visualization
6. **Phase 6**: Add data quality checks and alerting
