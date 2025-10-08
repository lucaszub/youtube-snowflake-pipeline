# GitHub Actions Workflows

Ce dossier contient les workflows CI/CD pour le déploiement automatisé du pipeline Prefect.

## Workflows Disponibles

### 1. CI - Build and Push to ACR (`ci.yml`)

**Objectif:** Construire l'image Docker et la pousser vers Azure Container Registry.

**Déclencheurs:**
- Push sur `main` (changements dans pipelines/, Dockerfile, requirements.txt, docker-compose.yml)
- Pull requests vers `main`

**Étapes:**
1. Checkout du code
2. Setup Docker Buildx
3. Login à Azure Container Registry
4. Build de l'image Docker
5. Push vers ACR avec tags multiples

**Sortie:**
- Image: `<ACR_SERVER>/prefect-worker:latest`
- Image: `<ACR_SERVER>/prefect-worker:main-<sha>`

### 2. CD - Deploy to VPS (`cd.yml`)

**Objectif:** Déployer l'application sur le VPS après le build réussi.

**Déclencheurs:**
- **Uniquement** après succès du workflow CI (workflow_run)

**Étapes:**
1. Connexion SSH au VPS
2. Login à ACR depuis le VPS
3. Pull de la dernière image
4. Création/mise à jour de `docker-compose.prod.yml`
5. Arrêt des anciens conteneurs
6. Démarrage des nouveaux conteneurs
7. Health check
8. Nettoyage des anciennes images

## Configuration Requise

### Secrets GitHub

Allez dans **Settings → Secrets and variables → Actions** et ajoutez:

| Secret | Description | Exemple |
|--------|-------------|---------|
| `ACR_LOGIN_SERVER` | URL du registry Azure | `myregistry.azurecr.io` |
| `ACR_USERNAME` | Username ACR | `myregistry` |
| `ACR_PASSWORD` | Password ACR | `***` |
| `VPS_HOST` | IP ou hostname du VPS | `51.210.xxx.xxx` |
| `VPS_USER` | Username SSH | `ubuntu` |
| `VPS_SSH_KEY` | Clé privée SSH | `-----BEGIN OPENSSH...` |

### Obtenir les Credentials ACR

```bash
# Via Azure CLI
az acr credential show --name <registry-name>

# Via Azure Portal
# ACR → Access keys → Enable Admin user
```

### Générer une Clé SSH

```bash
# Sur votre machine locale
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_key

# Copier la clé publique sur le VPS
ssh-copy-id -i ~/.ssh/github_actions_key.pub user@vps-host

# Copier la clé privée dans GitHub Secrets
cat ~/.ssh/github_actions_key
```

## Utilisation

### Déploiement Automatique

Simplement push sur `main`:

```bash
git add .
git commit -m "feat: update pipeline"
git push origin main
```

Les workflows s'exécuteront automatiquement en séquence:
1. **CI** build et push l'image vers ACR
2. **CD** attend la fin du CI, puis déploie sur le VPS (uniquement si CI réussit)

### Monitoring

```bash
# Lister les runs
gh run list

# Voir les détails d'un run
gh run view <run-id>

# Voir les logs
gh run view <run-id> --log

# Re-run un workflow failed
gh run rerun <run-id>
```

### Déploiement Manuel

Si vous devez déclencher manuellement:

```bash
# Via GitHub CLI
gh workflow run ci.yml
gh workflow run cd.yml

# Via interface web
# Actions → Select workflow → Run workflow
```

## Architecture du Déploiement

```
┌─────────────────┐
│   Developer     │
│   git push      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GitHub Actions │
│   CI Workflow   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Azure Container│
│    Registry     │ ◄──────┐
└────────┬────────┘        │
         │                 │
         │                 │
         ▼                 │
┌─────────────────┐        │
│  GitHub Actions │        │
│   CD Workflow   │        │
└────────┬────────┘        │
         │                 │
         ▼                 │
┌─────────────────┐        │
│      VPS        │        │
│  docker pull    │────────┘
│  docker compose │
│      up -d      │
└─────────────────┘
```

## Troubleshooting

### Le workflow CI échoue

**Erreur:** `Error: denied: authentication required`
- **Solution:** Vérifier les secrets `ACR_*` dans GitHub

**Erreur:** `Error: failed to solve: failed to read dockerfile`
- **Solution:** Vérifier que le Dockerfile existe et est valide

### Le workflow CD échoue

**Erreur:** `Permission denied (publickey)`
- **Solution:** Vérifier la clé SSH dans `VPS_SSH_KEY`
- Tester manuellement: `ssh -i key user@host`

**Erreur:** `docker: command not found`
- **Solution:** Installer Docker sur le VPS (voir CLAUDE.md)

**Erreur:** `Error response from daemon: Get https://...: unauthorized`
- **Solution:** Vérifier les credentials ACR sur le VPS

### Les conteneurs ne démarrent pas

```bash
# Sur le VPS
ssh user@vps-host
cd ~/prefect

# Voir les logs
docker compose -f docker-compose.prod.yml logs

# Vérifier le statut
docker compose -f docker-compose.prod.yml ps

# Redémarrer manuellement
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Rollback

Pour revenir à une version précédente:

```bash
# 1. Identifier le commit SHA de la version stable
gh run list --workflow=ci.yml --status=success

# 2. Se connecter au VPS
ssh user@vps-host
cd ~/prefect

# 3. Modifier docker-compose.prod.yml
# Remplacer :latest par :main-<old-sha>

# 4. Redémarrer
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Best Practices

1. **Toujours tester localement** avant de push:
   ```bash
   docker build -t test .
   docker compose up -d
   ```

2. **Utiliser des Pull Requests** pour les changements importants

3. **Monitorer les logs** après chaque déploiement:
   ```bash
   gh run list --limit=1
   ```

4. **Faire des commits atomiques** avec des messages clairs

5. **Taguer les releases** pour faciliter les rollbacks:
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```

## Ressources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [SSH Action](https://github.com/appleboy/ssh-action)
- [Azure Container Registry Docs](https://docs.microsoft.com/en-us/azure/container-registry/)
