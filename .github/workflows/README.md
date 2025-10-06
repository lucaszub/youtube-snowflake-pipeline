# GitHub Actions Workflows

Ce dossier contient les workflows CI/CD pour les pipelines Prefect.

## 📋 Workflows disponibles

### 1. `ci.yml` - Continuous Integration

**Déclenchement:**

- Push sur `main` ou `develop`
- Pull Request vers `main`

**Actions:**

1. Lint du code (ruff)
2. Tests unitaires (pytest)
3. Validation dbt
4. Build image Docker
5. Push vers GitHub Container Registry (`ghcr.io`)

**Tags créés:**

- `main` - Pour les commits sur main
- `main-abc1234` - SHA court du commit
- `latest` - Dernière version de main

### 2. `cd.yml` - Continuous Deployment

**Déclenchement:**

- Push sur `main` (automatique)
- Manuel via GitHub UI (workflow_dispatch)

**Actions:**

1. SSH vers VPS de production
2. Pull nouvelle image Docker
3. Backup PostgreSQL
4. Redémarrage worker (zero-downtime)
5. Redéploiement flows Prefect
6. Health checks
7. Notification Slack (optionnel)

## 🔧 Configuration requise

### Secrets GitHub à configurer

**Settings → Secrets and variables → Actions → New repository secret**

| Secret          | Description                                  | Exemple                                    |
| --------------- | -------------------------------------------- | ------------------------------------------ |
| `VPS_SSH_KEY`   | Clé SSH privée pour accéder au VPS           | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` |
| `VPS_USER`      | Username sur le VPS                          | `prefect`                                  |
| `VPS_HOST`      | IP ou hostname du VPS                        | `192.168.1.100` ou `vps.example.com`       |
| `SLACK_WEBHOOK` | (Optionnel) Webhook Slack pour notifications | `https://hooks.slack.com/services/...`     |

### Générer la clé SSH

```bash
# Sur votre machine locale
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions

# Copier la clé publique sur le VPS
ssh-copy-id -i ~/.ssh/github_actions.pub user@vps-ip

# Afficher la clé privée (à copier dans GitHub Secrets)
cat ~/.ssh/github_actions
```

## 🚀 Utilisation

### Déclenchement automatique

```bash
# Tout commit sur main déclenche CI + CD
git add .
git commit -m "feat: nouvelle feature"
git push origin main

# GitHub Actions:
# 1. Build l'image Docker
# 2. Push vers ghcr.io
# 3. Déploie automatiquement sur le VPS
```

### Déclenchement manuel

**Via GitHub UI:**

1. Aller sur l'onglet "Actions"
2. Sélectionner "CD - Deploy to Production"
3. Cliquer "Run workflow"
4. Choisir la branche (main)
5. Cliquer "Run workflow"

**Via GitHub CLI:**

```bash
gh workflow run cd.yml
```

## 🔍 Monitoring

### Voir les runs en cours

```bash
# Via GitHub CLI
gh run list

# Via l'UI
https://github.com/votre-user/votre-repo/actions
```

### Voir les logs

```bash
# Derniers logs
gh run view

# Logs d'un run spécifique
gh run view 123456789 --log
```

## 📦 Images Docker

### Accéder aux images

Les images sont publiées sur GitHub Container Registry:

```
ghcr.io/votre-username/prefect:latest
ghcr.io/votre-username/prefect:main
ghcr.io/votre-username/prefect:main-abc1234
```

### Pull une image localement

```bash
# Login (une seule fois)
echo $GITHUB_TOKEN | docker login ghcr.io -u votre-username --password-stdin

# Pull
docker pull ghcr.io/votre-username/prefect:latest
```

### Rendre le package public

**Settings → Packages → prefect → Package settings → Change visibility → Public**

## 🛠️ Troubleshooting

### "Resource not accessible by integration"

**Cause:** Permissions insuffisantes pour GITHUB_TOKEN

**Solution:** Settings → Actions → General → Workflow permissions → "Read and write permissions"

### "Permission denied (publickey)"

**Cause:** Clé SSH mal configurée

**Solutions:**

1. Vérifier que `VPS_SSH_KEY` contient la clé privée complète
2. Vérifier que la clé publique est dans `~/.ssh/authorized_keys` sur le VPS
3. Tester manuellement: `ssh -i ~/.ssh/github_actions user@vps-ip`

### Workflow bloqué sur "Waiting for approval"

**Cause:** Environment protection rules activées

**Solution:** Settings → Environments → production → Remove protection rules (ou approuver manuellement)

### Build échoue sur "docker: command not found"

**Cause:** Le runner n'a pas Docker (rare sur ubuntu-latest)

**Solution:** Ajouter step:

```yaml
- name: Setup Docker
  uses: docker/setup-buildx-action@v3
```

## 📊 Métriques

### Temps de build moyen

- Lint & Tests: ~2 minutes
- Build Docker: ~3-5 minutes (avec cache)
- Déploiement: ~1-2 minutes

### Consommation GitHub Actions

- Minutes gratuites: 2000/mois (compte gratuit)
- Estimation: ~10 minutes par déploiement complet
- Capacité: ~200 déploiements/mois

## 🔄 Rollback

### Rollback automatique (si échec)

Le workflow CD ne modifie pas les containers si une étape échoue (`set -e`).

### Rollback manuel

```bash
# Option 1: Redéployer un commit précédent
git revert HEAD
git push origin main  # Déclenche automatiquement CD

# Option 2: Déployer une image spécifique
# Sur le VPS:
docker pull ghcr.io/user/prefect:main-abc1234  # Version stable
docker tag ghcr.io/user/prefect:main-abc1234 prefect-pipelines:latest
docker compose up -d --no-deps prefect-worker
```

## 📝 Customisation

### Ajouter des tests

Créer le dossier `tests/` à la racine:

```bash
mkdir -p tests/unit tests/integration
```

Le workflow CI les exécutera automatiquement.

### Changer le registry (AWS ECR, Docker Hub)

Modifier dans `ci.yml`:

```yaml
env:
  REGISTRY: docker.io # ou 123456789.dkr.ecr.us-east-1.amazonaws.com
  IMAGE_NAME: username/prefect-pipelines
```

### Ajouter un environment staging

Créer `.github/workflows/cd-staging.yml` avec:

```yaml
on:
  push:
    branches: [develop]

jobs:
  deploy:
    environment: staging # Déploie sur staging au lieu de prod
```

## 🔗 Liens utiles

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [SSH Action](https://github.com/appleboy/ssh-action)
