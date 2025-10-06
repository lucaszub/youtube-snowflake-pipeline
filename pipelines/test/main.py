from prefect import flow, task
from datetime import datetime


@task(retries=1)
def hello_task():
    """Tâche de test simple"""
    print(f"👋 Hello from test pipeline at {datetime.now()}")
    return "Hello World!"


@task
def goodbye_task(message: str):
    """Tâche de fermeture"""
    print(f"👋 Goodbye! Message was: {message}")
    return "Goodbye!"


@flow(name="Test Pipeline", log_prints=True)
def test_pipeline():
    """
    Pipeline de test simple pour valider le déploiement
    """
    print("🚀 Starting test pipeline...")

    # Task 1
    result = hello_task()

    # Task 2
    goodbye_task(result)

    print("✅ Test pipeline completed!")
    return "Success"


if __name__ == "__main__":
    test_pipeline()
