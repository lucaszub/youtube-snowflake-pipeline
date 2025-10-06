# Guide CI/CD - Pipelines Prefect

## 📋 Table des matières

1. [Architecture actuelle](#architecture-actuelle)
2. [Vue d'ensemble CI/CD](#vue-densemble-cicd)
3. [Setup GitHub Actions](#setup-github-actions)
4. [Workflow de développement](#workflow-de-développement)
5. [Déploiement production](#déploiement-production)
6. [Monitoring & Rollback](#monitoring--rollback)
7. [Best Practices](#best-practices)

---

## Architecture actuelle

### ✅ Ce qui est déjà en place

```
prefect/
├── Dockerfile                    # Image Docker unifiée pour toutes les pipelines
├── docker-compose.yml            # Orchestration locale (Postgres + Server + Worker)
├── .dockerignore                # Optimisation du build
├── pipelines/
│   ├── youtube/
│   │   ├── main.py              # Flow YouTube
│   │   ├── deploy.py            # Script de déploiement
│   │   └── youtube_dbt/         # Transformations dbt
│   └── github/
│       ├── main.py              # Flow GitHub Trending
│       └── deploy.py            # Script de déploiement
└── requirements.txt
```

### 🏗️ Infrastructure Docker

**3 containers orchestrés:**
- `prefect-postgres` - Base de données (état Prefect)
- `prefect-server` - API + UI (http://localhost:4200)
- `prefect-worker` - Exécuteur de flows

---

## Vue d'ensemble CI/CD

### Workflow complet: Dev → Staging → Production

```
┌─────────────────────────────────────────────────────────────────┐
│  DÉVELOPPEMENT LOCAL                                            │
│  ├─ Modifier code Python                                        │
│  ├─ docker compose up -d --build                                │
│  ├─ Tester localement                                           │
│  └─ git push origin feature/xyz                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  CI (GitHub Actions)                                            │
│  ├─ Lint & Tests (pytest, ruff)                                │
│  ├─ Build image Docker                                          │
│  ├─ Tag: ghcr.io/user/prefect-pipelines:sha-abc123             │
│  └─ Push vers GitHub Container Registry                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼ (merge vers main)
┌─────────────────────────────────────────────────────────────────┐
│  CD (Déploiement automatique)                                   │
│  ├─ SSH vers VPS/serveur production                             │
│  ├─ Pull nouvelle image                                         │
│  ├─ docker compose up -d --no-deps prefect-worker               │
│  ├─ Redeploy flows Prefect                                      │
│  └─ Health check + notification Slack                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup GitHub Actions

### Étape 1: Créer le workflow CI

**Fichier: `.github/workflows/ci.yml`**

```yaml
name: CI - Tests & Build

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    name: Lint & Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install ruff pytest pytest-cov

      - name: Lint with ruff
        run: |
          ruff check pipelines/ --output-format=github

      - name: Run tests
        run: |
          pytest pipelines/ -v --cov=pipelines --cov-report=term
        continue-on-error: true  # Temporaire si pas encore de tests

      - name: Validate dbt project
        run: |
          cd pipelines/youtube/youtube_dbt
          dbt parse
        continue-on-error: true

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Étape 2: Créer le workflow CD (déploiement)

**Fichier: `.github/workflows/cd.yml`**

```yaml
name: CD - Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:  # Permet le déclenchement manuel

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  deploy:
    name: Deploy to VPS
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.VPS_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.VPS_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to VPS
        env:
          VPS_USER: ${{ secrets.VPS_USER }}
          VPS_HOST: ${{ secrets.VPS_HOST }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          ssh $VPS_USER@$VPS_HOST << 'EOF'
            set -e

            # Navigation vers le répertoire du projet
            cd /home/prefect/prefect-production

            # Pull dernières modifications
            git pull origin main

            # Login au registry
            echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

            # Pull nouvelle image
            docker pull ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main-${{ env.IMAGE_TAG }}

            # Tag comme latest
            docker tag ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main-${{ env.IMAGE_TAG }} prefect-pipelines:latest

            # Restart worker uniquement (zero-downtime)
            docker compose up -d --no-deps --build prefect-worker

            # Redeploy flows Prefect
            docker compose exec -T prefect-worker python /app/pipelines/youtube/deploy.py
            docker compose exec -T prefect-worker python /app/pipelines/github/deploy.py

            # Health check
            sleep 10
            docker compose ps

            echo "✅ Déploiement réussi!"
          EOF

      - name: Notify Slack (optional)
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK }}
          payload: |
            {
              "text": "Déploiement ${{ job.status }} - ${{ github.repository }}@${{ github.sha }}"
            }
```

### Étape 3: Configurer les secrets GitHub

**Settings → Secrets and variables → Actions → New repository secret**

Créer ces secrets:

```bash
VPS_SSH_KEY          # Clé SSH privée pour accéder au VPS
VPS_USER             # Username sur le VPS (ex: prefect)
VPS_HOST             # IP ou hostname du VPS
SLACK_WEBHOOK        # (Optionnel) Pour notifications
```

**Générer la clé SSH:**
```bash
# Sur ta machine locale
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions

# Copier la clé publique sur le VPS
ssh-copy-id -i ~/.ssh/github_actions.pub user@vps-ip

# Copier le contenu de la clé privée dans le secret GitHub
cat ~/.ssh/github_actions
```

---

## Workflow de développement

### Scénario 1: Nouvelle feature

```bash
# 1. Créer une branche
git checkout -b feature/github-trending-enhancement

# 2. Modifier le code
vim pipelines/github/main.py

# 3. Tester localement
docker compose up -d --build
docker compose exec prefect-worker python /app/pipelines/github/deploy.py

# 4. Tester dans l'UI
# http://localhost:4200 → Quick Run

# 5. Commit & Push
git add .
git commit -m "feat: amélioration extraction GitHub Trending"
git push origin feature/github-trending-enhancement

# 6. Créer Pull Request
# GitHub Actions va lancer les tests automatiquement

# 7. Merge → déploiement auto en prod
```

### Scénario 2: Hotfix urgent

```bash
# 1. Branche depuis main
git checkout main
git pull
git checkout -b hotfix/api-quota-error

# 2. Fix rapide
vim pipelines/youtube/youtube_extractor.py

# 3. Test local
docker compose up -d --build

# 4. Commit + push + merge rapide
git add .
git commit -m "fix: gestion quota YouTube API"
git push origin hotfix/api-quota-error

# 5. Merge direct → deploy auto
```

### Scénario 3: Tester une branche en staging

```bash
# Créer un environnement staging dans docker-compose
# (voir section suivante)

# Déployer la branche de test
git checkout feature/xyz
docker compose -f docker-compose.staging.yml up -d --build

# Tester sur port différent (ex: 4201)
# http://localhost:4201
```

---

## Déploiement production

### Option A: VPS Linux (recommandé)

**Prérequis sur le VPS:**

```bash
# 1. Installer Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 2. Installer Git
sudo apt update && sudo apt install -y git

# 3. Cloner le repo
git clone https://github.com/ton-username/prefect-pipelines.git
cd prefect-pipelines

# 4. Créer .env avec les credentials
vim .env

# 5. Lancer l'infrastructure
docker compose up -d

# 6. Vérifier
docker compose ps
curl http://localhost:4200/api/health
```

**Configuration systemd (optionnel - auto-restart):**

```bash
# /etc/systemd/system/prefect.service
[Unit]
Description=Prefect Data Pipelines
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/prefect/prefect-production
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=prefect

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable prefect
sudo systemctl start prefect
```

### Option B: Kubernetes (pour scale)

**Fichier: `k8s/deployment.yml`** (à créer si besoin)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prefect-worker
spec:
  replicas: 3  # Scaler horizontalement
  selector:
    matchLabels:
      app: prefect-worker
  template:
    metadata:
      labels:
        app: prefect-worker
    spec:
      containers:
      - name: worker
        image: ghcr.io/username/prefect-pipelines:latest
        env:
        - name: PREFECT_API_URL
          value: "http://prefect-server:4200/api"
        envFrom:
        - secretRef:
            name: prefect-secrets
```

---

## Monitoring & Rollback

### Health Checks

**Script de monitoring: `scripts/healthcheck.sh`**

```bash
#!/bin/bash
set -e

echo "🔍 Health Check Prefect Infrastructure"

# 1. Vérifier containers
echo "📦 Checking containers..."
docker compose ps

# 2. Vérifier API Prefect
echo "🌐 Checking Prefect API..."
curl -f http://localhost:4200/api/health || exit 1

# 3. Vérifier worker
echo "👷 Checking worker status..."
docker compose exec prefect-worker prefect worker status

# 4. Vérifier derniers runs
echo "📊 Last 5 flow runs..."
docker compose exec prefect-worker prefect flow-run ls --limit 5

# 5. Vérifier PostgreSQL
echo "🗄️  Checking database..."
docker compose exec postgres pg_isready -U prefect

echo "✅ All systems operational!"
```

### Rollback en cas d'erreur

**Rollback automatique (si tests échouent en prod):**

```bash
# Identifier la dernière version stable
docker images | grep prefect-pipelines

# Rollback vers version précédente
docker tag ghcr.io/user/prefect-pipelines:main-abc123 prefect-pipelines:latest
docker compose up -d --no-deps prefect-worker

# Redeploy flows
docker compose exec prefect-worker python /app/pipelines/youtube/deploy.py
docker compose exec prefect-worker python /app/pipelines/github/deploy.py
```

**Rollback Git:**

```bash
# Annuler le dernier commit
git revert HEAD
git push origin main

# GitHub Actions va redéployer automatiquement l'ancienne version
```

### Logs & Debugging

```bash
# Logs en temps réel
docker compose logs -f prefect-worker

# Logs d'un flow spécifique (depuis l'UI ou CLI)
docker compose exec prefect-worker \
  prefect flow-run logs <flow-run-id>

# Inspecter un container
docker compose exec prefect-worker bash

# Vérifier variables d'environnement
docker compose exec prefect-worker env | grep PREFECT
```

---

## Best Practices

### 🔒 Sécurité

**1. Secrets management**

❌ **Ne JAMAIS commit:**
```bash
.env
*.key
credentials.json
```

✅ **Utiliser:**
- GitHub Secrets pour CI/CD
- Variables d'environnement Docker
- Azure Key Vault / AWS Secrets Manager en prod

**2. Scan de vulnérabilités**

```yaml
# Ajouter dans .github/workflows/ci.yml
- name: Scan Docker image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'
```

### 📊 Tests & Qualité

**Structure de tests recommandée:**

```
tests/
├── unit/
│   ├── test_youtube_extractor.py
│   └── test_github_trending.py
├── integration/
│   ├── test_snowflake_connection.py
│   └── test_blob_upload.py
└── conftest.py  # Fixtures pytest
```

**Exemple test unitaire:**

```python
# tests/unit/test_github_trending.py
import pytest
from pipelines.github.github_trending import get_trending_repos

def test_get_trending_repos_returns_list():
    repos = get_trending_repos(language="python", days=7, stars_min=100)
    assert isinstance(repos, list)
    assert len(repos) > 0

def test_repo_structure():
    repos = get_trending_repos(language="python", days=7, stars_min=100)
    repo = repos[0]
    assert "repo_id" in repo
    assert "repo_name" in repo
    assert "stars" in repo
```

### 🚀 Performance

**1. Optimisation Docker build**

```dockerfile
# Multi-stage build (déjà en place)
# Cache pip packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

**2. Parallélisation des flows**

```python
# pipelines/youtube/main.py
from prefect import flow
from prefect.task_runners import ConcurrentTaskRunner

@flow(task_runner=ConcurrentTaskRunner())
def pipeline_youtube():
    # Les tasks s'exécutent en parallèle si possible
    pass
```

### 📈 Monitoring en production

**Intégrations recommandées:**

1. **Prefect Cloud** (gratuit jusqu'à 20k runs/mois)
   - Monitoring centralisé
   - Alertes automatiques
   - Logs persistants

2. **Grafana + Prometheus**
   - Métriques custom
   - Dashboards

3. **Slack/Discord webhooks**
   ```python
   from prefect.blocks.notifications.slack import SlackWebhook

   slack = SlackWebhook.load("production-alerts")
   slack.notify("Pipeline failed!")
   ```

### 🔄 Versioning des déploiements

**Stratégie de tags:**

```bash
# Semantic versioning
git tag -a v1.2.3 -m "Release 1.2.3: ajout pipeline GitHub"
git push origin v1.2.3

# GitHub Actions construit automatiquement:
# - ghcr.io/user/prefect-pipelines:v1.2.3
# - ghcr.io/user/prefect-pipelines:latest
```

---

## 📝 Checklist de déploiement

### Avant le premier déploiement

- [ ] Docker installé sur VPS
- [ ] Clés SSH configurées
- [ ] Secrets GitHub configurés
- [ ] `.env` créé en production avec credentials
- [ ] DNS/Firewall configuré (port 4200 accessible si UI publique)
- [ ] PostgreSQL volume backup activé
- [ ] Tests passent en CI

### Avant chaque release

- [ ] Tests locaux OK
- [ ] Lint/formatting OK (ruff)
- [ ] Variables d'environnement à jour
- [ ] dbt models validés (`dbt parse`)
- [ ] Changelog mis à jour
- [ ] Version bumped (`git tag`)

### Après déploiement

- [ ] Health check OK
- [ ] Deployments visibles dans UI
- [ ] Run manuel de test réussi
- [ ] Logs sans erreur
- [ ] Backup PostgreSQL OK
- [ ] Notification équipe (Slack)

---

## 🆘 Troubleshooting

### Container unhealthy

```bash
# Vérifier logs
docker compose logs prefect-worker --tail 50

# Recréer le container
docker compose up -d --force-recreate prefect-worker
```

### GitHub Actions échoue

```bash
# Vérifier les secrets
# Settings → Secrets → Actions

# Tester localement avec act
act -j build
```

### Deployment invisible dans UI

```bash
# Vérifier qu'il existe
docker compose exec prefect-worker prefect deployment ls

# Recréer
docker compose exec prefect-worker python /app/pipelines/github/deploy.py
```

### Worker ne pick pas les runs

```bash
# Vérifier le work pool
docker compose exec prefect-worker prefect work-pool ls

# Créer si absent
docker compose exec prefect-worker \
  prefect work-pool create default-pool --type process
```

---

## 📚 Ressources

- [Prefect Documentation](https://docs.prefect.io)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)

---

**Prochaines étapes recommandées:**

1. Créer les workflows GitHub Actions (`.github/workflows/`)
2. Ajouter des tests unitaires (`tests/`)
3. Configurer Prefect Cloud (monitoring)
4. Setup CI/CD vers VPS de production
5. Implémenter blue/green deployment (optionnel)
