"""
Déploiement Prefect avec schedule automatique
Pipeline YouTube → Snowflake → dbt
"""
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from main import pipeline_complet

# Déploiement production avec schedule quotidien à 12h (midi)
deployment = Deployment.build_from_flow(
    flow=pipeline_complet,
    name="production-daily-12h",
    work_pool_name="default-pool",
    schedule=CronSchedule(
        cron="0 12 * * *",  # Tous les jours à 12h00
        timezone="Europe/Paris"
    ),
    tags=["production", "youtube", "daily"],
    version="1.0.0",
    description="Pipeline YouTube → Snowflake → dbt - Exécution quotidienne à midi"
)

if __name__ == "__main__":
    deployment.apply()
    print("✅ Déploiement créé avec succès!")
    print("   Nom: production-daily-12h")
    print("   Schedule: Tous les jours à 12h00 (Europe/Paris)")
    print("   Tags: production, youtube, daily")
    print("\n📝 Commandes utiles:")
    print("   - Lister les déploiements: prefect deployment ls")
    print("   - Lancer manuellement: prefect deployment run 'Pipeline YouTube → Snowflake → dbt/production-daily-12h'")
    print("   - Démarrer le worker: prefect worker start --pool default-pool")
