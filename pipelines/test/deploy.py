"""
Déploiement Prefect - Pipeline de Test
"""

if __name__ == "__main__":
    from main import test_pipeline
    from prefect.client.schemas.schedules import CronSchedule
    from prefect.runner.storage import GitRepository

    # Déployer avec schedule toutes les 2 minutes depuis Git
    test_pipeline.from_source(
        source=GitRepository(
            url="https://github.com/lucaszub/youtube-snowflake-pipeline.git",
            branch="main"
        ),
        entrypoint="pipelines/test/main.py:test_pipeline"
    ).deploy(
        name="production-2min",
        work_pool_name="default-pool",
        schedules=[
            CronSchedule(
                cron="*/2 * * * *",  # Toutes les 2 minutes
                timezone="America/Argentina/Buenos_Aires"
            )
        ],
        tags=["production", "test", "frequent"],
        version="1.0.0",
        description="Pipeline de test - Exécution toutes les 2 minutes pour validation"
    )

    print("✅ Déploiement Test Pipeline créé avec succès!")
    print("   Nom: production-2min")
    print("   Schedule: Toutes les 2 minutes")
    print("   Tags: production, test, frequent")
    print("\n📝 Commandes utiles:")
    print("   - Lister les déploiements: prefect deployment ls")
    print("   - Lancer manuellement: prefect deployment run 'Test Pipeline/production-2min'")
