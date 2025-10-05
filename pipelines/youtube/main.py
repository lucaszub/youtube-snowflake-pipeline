from prefect import flow, task
import requests
import os
from dotenv import load_dotenv

# Charge le .env du répertoire courant
load_dotenv('/home/prefect/prefect-production/youtube-snowflake-pipeline/.env')

# Vérifie que la variable est bien chargée
print("YOUTUBE_API_KEY =", os.getenv("YOUTUBE_API_KEY"))


@task(retries=3, retry_delay_seconds=60)
def api_to_blob():
    """Extrait YouTube et upload vers Blob Storage"""
    from youtube_extractor import extract_and_upload

    print("🚀 Extraction YouTube → Blob Storage...")

    nb_videos, blob_path = extract_and_upload()

    result = f"✅ Extraction completed!\nVideos extracted: {nb_videos}\nUploaded to: {blob_path}"
    print(result)

    return result

@task(retries=2, retry_delay_seconds=30)
def copy_into():
    """Snowflake COPY INTO depuis Blob Storage vers table"""
    from snowflake_connector import get_snowflake_connection

    print("📦 Lancement Snowflake COPY INTO...")

    copy_query = """
    COPY INTO YOUTUBE_RAW.INGESTION.YOUTUBE_VIDEOS
    FROM @YOUTUBE_RAW.INGESTION.YOUTUBE_BLOB_STAGE
    FILE_FORMAT = PARQUET_FORMAT
    MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
    ON_ERROR = CONTINUE
    """

    with get_snowflake_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(copy_query)
        result = cursor.fetchone()
        cursor.close()

        print(f"✅ COPY INTO terminé: {result}")
        return result

@task(retries=1, retry_delay_seconds=30)
def dbt_run():
    """Exécuter dbt run localement"""
    import subprocess

    print("🔧 Lancement dbt run...")

    # Chemin vers votre projet dbt
    # Local: /home/lucas-zubiarrain/prefect/youtube_dbt
    # Production VPS:
    dbt_project_dir = "/home/prefect/prefect-production/youtube-snowflake-pipeline/youtube_dbt"

    # Chemin absolu vers dbt dans le virtualenv de production
    dbt_executable = "/home/prefect/prefect-production/youtube-snowflake-pipeline/venv/bin/dbt"

    print(f"📂 Répertoire dbt: {dbt_project_dir}")
    print(f"🔧 Exécutable dbt: {dbt_executable}")

    # Passer les variables d'environnement à dbt
    env = os.environ.copy()

    result = subprocess.run(
        [dbt_executable, "run"],
        cwd=dbt_project_dir,
        env=env,  # Passer les variables d'environnement
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"❌ Erreur dbt:\n{result.stderr}")
        raise Exception(f"dbt run failed: {result.stderr}")

    print(f"✅ dbt run terminé:\n{result.stdout}")
    return result.stdout


@flow(name="Pipeline YouTube → Snowflake → dbt")
def pipeline_complet():
    """Pipeline complet: YouTube → Blob Storage → Snowflake → dbt"""

    # Étape 1: Extraction YouTube → Blob Storage
    blob_result = api_to_blob()

    # Étape 2: Snowflake COPY INTO
    snowflake_result = copy_into()

    # Étape 3: dbt run
    dbt_result = dbt_run()

    print("\n🎉 Pipeline terminé avec succès!")

    return {
        "youtube": blob_result,
        "snowflake": snowflake_result,
        "dbt": dbt_result
    }


if __name__ == "__main__":
    pipeline_complet()