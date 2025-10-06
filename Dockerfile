# Multi-stage build pour optimiser la taille de l'image
FROM python:3.11-slim AS builder

# Installer les dépendances de build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les requirements
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/requirements.txt


# Image finale
FROM python:3.11-slim

# Installer uniquement git (nécessaire pour Prefect GitRepository)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Copier les wheels depuis le builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copier tout le code du projet (pipelines inclut youtube_dbt)
COPY pipelines/ /app/pipelines/

# Variables d'environnement
ENV PYTHONPATH=/app \
    DBT_PROJECT_DIR=/app/pipelines/youtube/youtube_dbt \
    PREFECT_API_URL=http://localhost:4200/api

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 prefect && \
    chown -R prefect:prefect /app

USER prefect

# Healthcheck pour vérifier que le worker est actif
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD prefect worker status || exit 1

# Commande par défaut : démarrer le worker Prefect
# Le work pool peut être surchargé via docker-compose ou CLI
CMD ["prefect", "worker", "start", "--pool", "default-pool"]
