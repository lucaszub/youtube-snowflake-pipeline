from prefect import flow, task
from dotenv import load_dotenv
from binance_extractor import get_binance_data

# Charge le .env du répertoire racine
load_dotenv('/home/prefect/prefect-production/youtube-snowflake-pipeline/.env')


@task(retries=2, retry_delay_seconds=30)
def extract_binance_data():
    """
    Extrait les données Binance en temps réel

    Données extraites:
    - Prix actuel + variation 24h
    - Volume 24h
    - High/Low 24h
    - Bid/Ask spread
    - Trades récents
    """
    # Symboles à tracker (BTC, ETH, BNB vs USDT)
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    df = get_binance_data(symbols)

    print(f"\n✅ Extracted {len(df)} symbols from Binance")
    print(f"📊 Columns: {list(df.columns)}")
    print(f"💾 Memory usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")

    return df


@task(retries=1, retry_delay_seconds=30)
def upload_to_blob():
    """Upload vers Azure Blob Storage"""
    # TODO: Implémenter l'upload vers Blob (prochaine étape)
    return "upload_skipped"


@task(retries=1, retry_delay_seconds=30)
def load_to_snowflake():
    """Charge dans Snowflake"""
    # TODO: Implémenter COPY INTO Snowflake (prochaine étape)
    return "load_skipped"


@flow(name="Pipeline Binance Real-Time", log_prints=True)
def pipeline_binance():
    """
    Pipeline Binance - Extraction temps réel

    Phase actuelle: Extraction uniquement (GET data)
    Binance API → DataFrame pandas

    Prochaines étapes:
    - Upload vers Azure Blob Storage
    - Load vers Snowflake
    - Visualisation Next.js
    """
    df = extract_binance_data()

    # Étape 2: Upload vers Blob (à implémenter plus tard)
    # blob_result = upload_to_blob(df)

    # Étape 3: Load vers Snowflake (à implémenter plus tard)
    # snowflake_result = load_to_snowflake()

    return df


if __name__ == "__main__":
    result = pipeline_binance()

    print("\n" + "="*80)
    print("📋 FINAL RESULT - DataFrame Summary")
    print("="*80)
    print(result.to_string())
    print("\n✅ Pipeline completed successfully!")
