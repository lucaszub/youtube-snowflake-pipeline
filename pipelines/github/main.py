from prefect import flow, task
import os
from dotenv import load_dotenv

# Charge le .env du répertoire racine
load_dotenv('/home/prefect/prefect-production/youtube-snowflake-pipeline/.env')


@task(retries=2, retry_delay_seconds=30)
def extract_github_trending():
    """Extrait les repos trending de GitHub"""
    from github_trending import get_trending_repos
    import pandas as pd

    print("🔍 Extraction des repos GitHub trending...")

    # Technologies à tracker
    technologies = ["python", "javascript", "typescript", "go", "rust"]
    all_repos = []

    for tech in technologies:
        print(f"\n🔥 Traitement: {tech.upper()}")

        try:
            repos = get_trending_repos(language=tech, days=30, stars_min=50)
            all_repos.extend(repos)
            print(f"✅ {len(repos)} repos extraits pour {tech}")
        except Exception as e:
            print(f"❌ Erreur pour {tech}: {e}")
            continue

    df = pd.DataFrame(all_repos)
    print(f"\n✅ Total: {len(df)} repos extraits")

    return len(df)


@task(retries=1, retry_delay_seconds=30)
def upload_to_blob():
    """Upload vers Azure Blob Storage"""
    # TODO: Implémenter l'upload vers Blob
    print("📤 Upload vers Azure Blob Storage...")
    print("⚠️ À implémenter")
    return "upload_skipped"


@task(retries=1, retry_delay_seconds=30)
def load_to_snowflake():
    """Charge dans Snowflake"""
    # TODO: Implémenter COPY INTO Snowflake
    print("📦 Chargement vers Snowflake...")
    print("⚠️ À implémenter")
    return "load_skipped"


@flow(name="Pipeline GitHub Trending", log_prints=True)
def pipeline_github_trending():
    """
    Pipeline complet GitHub Trending
    GitHub API → Azure Blob → Snowflake
    """
    print("=" * 60)
    print("🚀 Démarrage Pipeline GitHub Trending")
    print("=" * 60)

    # Étape 1: Extraction GitHub
    nb_repos = extract_github_trending()

    # Étape 2: Upload vers Blob (à implémenter)
    # blob_result = upload_to_blob()

    # Étape 3: Load vers Snowflake (à implémenter)
    # snowflake_result = load_to_snowflake()

    print("=" * 60)
    print(f"✅ Pipeline terminé - {nb_repos} repos traités")
    print("=" * 60)

    return nb_repos


if __name__ == "__main__":
    pipeline_github_trending()
