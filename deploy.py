"""
Déploiement Prefect avec schedule automatique
Pipeline YouTube → Snowflake → dbt
"""

if __name__ == "__main__":
    from main import pipeline_complet
    from prefect.runner.storage import GitRepository
    from prefect.client.schemas.schedules import CronSchedule

    # Déployer avec schedule quotidien à 12h (midi)
    # Utilise Git pour récupérer le code (pas de Docker)
    pipeline_complet.from_source(
        source=GitRepository(
            url="https://github.com/lucaszub/youtube-snowflake-pipeline.git",
            branch="main"
        ),
        entrypoint="main.py:pipeline_complet"
    ).deploy(
        name="production-daily-12h",
        work_pool_name="default-pool",
        schedules=[
            CronSchedule(
                cron="0 12 * * *",
                timezone="America/Argentina/Buenos_Aires"
            )
        ],
        tags=["production", "youtube", "daily"],
        version="1.0.0",
        description="Pipeline YouTube → Snowflake → dbt - Exécution quotidienne à midi"
    )

    print("✅ Déploiement créé avec succès!")
    print("   Nom: production-daily-12h")
    print("   Schedule: Tous les jours à 12h00 (America/Argentina/Buenos_Aires)")
    print("   Tags: production, youtube, daily")
    print("\n📝 Commandes utiles:")
    print("   - Lister les déploiements: prefect deployment ls")
    print("   - Lancer manuellement: prefect deployment run 'Pipeline YouTube → Snowflake → dbt/production-daily-12h'")
    print("   - Démarrer le worker: prefect worker start --pool default-pool")
