import snowflake.connector
import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


@contextmanager
def get_snowflake_connection():
    """
    Context manager pour gérer la connexion Snowflake

    Usage:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """

    # Récupérer les credentials depuis les variables d'environnement
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),      # ex: "abc12345.eu-west-1"
        user=os.getenv("SNOWFLAKE_USER"),            # ex: "lucas"
        password=os.getenv("SNOWFLAKE_PASSWORD"),    # votre mot de passe
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),  # ex: "COMPUTE_WH"
        database=os.getenv("SNOWFLAKE_DATABASE"),    # ex: "YOUTUBE_DB"
        schema=os.getenv("SNOWFLAKE_SCHEMA"),        # ex: "RAW"
        role=os.getenv("SNOWFLAKE_ROLE", "SYSADMIN") # optionnel, défaut: SYSADMIN
    )

    try:
        yield conn
    finally:
        conn.close()


def test_connection():
    """Tester la connexion Snowflake"""
    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_ROLE()")
            result = cursor.fetchone()
            cursor.close()

            print("✅ Connexion Snowflake réussie!")
            print(f"   Version: {result[0]}")
            print(f"   User: {result[1]}")
            print(f"   Role: {result[2]}")

            return True
    except Exception as e:
        print(f"❌ Erreur de connexion Snowflake: {str(e)}")
        return False


if __name__ == "__main__":
    # Test de connexion
    test_connection()
