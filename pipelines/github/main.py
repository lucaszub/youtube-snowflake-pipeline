from prefect import flow, task
import os
from dotenv import load_dotenv
from github_trending import get_trending_repos

# Charge le .env du répertoire racine
load_dotenv('/home/prefect/prefect-production/youtube-snowflake-pipeline/.env')


@task(retries=2, retry_delay_seconds=30)
def extract_github_trending():
    """Extrait les repos trending de GitHub"""
 
    repos = get_trending_repos(topic="data-engineering", stars_min=500)
    return repos


@task(retries=1, retry_delay_seconds=30)
def upload_to_blob():
    """Upload vers Azure Blob Storage"""
    # TODO: Implémenter l'upload vers Blob
    return "upload_skipped"


@task(retries=1, retry_delay_seconds=30)
def load_to_snowflake():
    """Charge dans Snowflake"""
    # TODO: Implémenter COPY INTO Snowflake
    return "load_skipped"


@flow(name="Pipeline GitHub Trending", log_prints=True)
def pipeline_github_trending():
    """
    Pipeline complet GitHub Trending
    GitHub API → Azure Blob → Snowflake
    """
    nb_repos = extract_github_trending()

    # Étape 2: Upload vers Blob (à implémenter)
    # blob_result = upload_to_blob()

    # Étape 3: Load vers Snowflake (à implémenter)
    # snowflake_result = load_to_snowflake()

    return nb_repos


if __name__ == "__main__":
    pipeline_github_trending()
