# Image de base Python légère
FROM python:3.12-slim

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Copier requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Variables d'environnement pour dbt
ENV DBT_PROJECT_DIR=/app/youtube_dbt

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 prefect && \
    chown -R prefect:prefect /app

USER prefect

# Commande par défaut : démarrer le worker Prefect
# (Le serveur Prefect tourne séparément)
CMD ["prefect", "worker", "start", "--pool", "default-pool"]
