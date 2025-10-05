"""
Déploiement Prefect - Pipeline GitHub Trending
"""

if __name__ == "__main__":
    from main import pipeline_github_trending
    from prefect.runner.storage import GitRepository
    from prefect.client.schemas.schedules import CronSchedule

    # Déployer avec schedule quotidien à 6h du matin
    pipeline_github_trending.from_source(
        source=GitRepository(
            url="https://github.com/lucaszub/youtube-snowflake-pipeline.git",
            branch="main"
        ),
        entrypoint="pipelines/github/main.py:pipeline_github_trending"
    ).deploy(
        name="production-daily-6am",
        work_pool_name="default-pool",
        schedules=[
            CronSchedule(
                cron="0 6 * * *",
                timezone="America/Argentina/Buenos_Aires"
            )
        ],
        tags=["production", "github", "daily"],
        version="1.0.0",
        description="Pipeline GitHub Trending → Snowflake - Exécution quotidienne à 6h"
    )

    print("✅ Déploiement créé avec succès!")
    print("   Nom: production-daily-6am")
    print("   Schedule: Tous les jours à 6h00 (America/Argentina/Buenos_Aires)")
    print("   Tags: production, github, daily")
    print("\n📝 Commandes utiles:")
    print("   - Lister les déploiements: prefect deployment ls")
    print("   - Lancer manuellement: prefect deployment run 'Pipeline GitHub Trending/production-daily-6am'")
    print("   - Démarrer le worker: prefect worker start --pool default-pool")
