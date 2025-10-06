"""
Déploiement LOCAL Prefect - Pipeline de Test
Pour le développement local uniquement
"""

if __name__ == "__main__":
    from main import test_pipeline
    from prefect.client.schemas.schedules import CronSchedule

    # Déployer localement (sans Git)
    test_pipeline.serve(
        name="test-local",
        cron="*/2 * * * *",  # Toutes les 2 minutes
        tags=["local", "test"],
    )
