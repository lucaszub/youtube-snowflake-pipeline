"""
Déploiement Prefect - Pipeline Binance Real-Time
"""

if __name__ == "__main__":
    from main import pipeline_binance
    from prefect.client.schemas.schedules import CronSchedule

    # Servir le flow avec schedule toutes les 5 minutes (pour du quasi temps réel)
    # Note: Pour du vrai temps réel, utiliser WebSocket plus tard
    # serve() permet un déploiement local sans besoin de GitRepository ou Docker image
    pipeline_binance.serve(
        name="production-realtime-5min",
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
