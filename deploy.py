"""
Déploiement Prefect avec schedule automatique
Pipeline YouTube → Snowflake → dbt
"""

if __name__ == "__main__":
    from main import pipeline_complet
    from prefect.deployments.steps.core import run_step

    # Déployer avec schedule quotidien à 12h (midi)
    # Utilise le code local (git pull) au lieu de Docker
    pipeline_complet.deploy(
        name="production-daily-12h",
        work_pool_name="default-pool",
        cron="0 12 * * *",  # Tous les jours à 12h00
        tags=["production", "youtube", "daily"],
        version="1.0.0",
        description="Pipeline YouTube → Snowflake → dbt - Exécution quotidienne à midi",
        pull_steps=[
            {
                "prefect.deployments.steps.git_clone": {
                    "repository": "https://github.com/lucaszub/youtube-snowflake-pipeline.git",
                    "branch": "main"
                }
            }
        ]
    )

    print("✅ Déploiement créé avec succès!")
    print("   Nom: production-daily-12h")
    print("   Schedule: Tous les jours à 12h00 (Europe/Paris)")
    print("   Tags: production, youtube, daily")
    print("\n📝 Commandes utiles:")
    print("   - Lister les déploiements: prefect deployment ls")
    print("   - Lancer manuellement: prefect deployment run 'Pipeline YouTube → Snowflake → dbt/production-daily-12h'")
    print("   - Démarrer le worker: prefect worker start --pool default-pool")
