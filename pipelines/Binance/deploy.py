"""
Déploiement Prefect - Pipeline Binance Real-Time
"""

if __name__ == "__main__":
    from main import pipeline_binance
    from prefect.runner.storage import GitRepository
    from prefect.client.schemas.schedules import CronSchedule

    # Déployer avec schedule toutes les 5 minutes (pour du quasi temps réel)
    # Note: Pour du vrai temps réel, utiliser WebSocket plus tard
    pipeline_binance.from_source(
        source=GitRepository(
            url="https://github.com/lucaszub/youtube-snowflake-pipeline.git",
            branch="main"
        ),
        entrypoint="pipelines/Binance/main.py:pipeline_binance"
    ).deploy(
        name="production-realtime-5min",
        work_pool_name="default-pool",
        schedules=[
            CronSchedule(
                cron="*/5 * * * *",  # Toutes les 5 minutes
                timezone="America/Argentina/Buenos_Aires"
            )
        ],
        tags=["production", "binance", "realtime", "crypto"],
        version="1.0.0",
        description="Pipeline Binance Real-Time → Extraction crypto data - Toutes les 5 minutes"
    )

    print("✅ Déploiement créé avec succès!")
    print("   Nom: production-realtime-5min")
    print("   Schedule: Toutes les 5 minutes (America/Argentina/Buenos_Aires)")
    print("   Tags: production, binance, realtime, crypto")
    print("\n📝 Commandes utiles:")
    print("   - Lister les déploiements: prefect deployment ls")
    print("   - Lancer manuellement: prefect deployment run 'Pipeline Binance Real-Time/production-realtime-5min'")
    print("   - Démarrer le worker: prefect worker start --pool default-pool")
    print("\n💡 Note: Pour du vrai temps réel, migrer vers WebSocket Binance plus tard")
