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


@task(retries=2, retry_delay_seconds=30)
def upload_to_blob(df):
    """
    Upload DataFrame vers Azure Blob Storage en format Parquet

    Args:
        df: DataFrame Binance à uploader

    Returns:
        Dict avec métadonnées d'upload (blob_path, size, timestamp, etc.)
    """
    from azure_blob_uploader import upload_binance_to_blob

    print(f"\n📤 Starting Azure Blob upload...")
    print(f"  📊 DataFrame shape: {df.shape}")

    result = upload_binance_to_blob(df)

    print(f"\n✅ Blob upload completed:")
    print(f"  📁 Path: {result['blob_path']}")
    print(f"  💾 Size: {result['size_kb']} KB")
    print(f"  📊 Rows uploaded: {result['row_count']}")

    return result


@task(retries=1, retry_delay_seconds=30)
def load_to_snowflake():
    """Charge dans Snowflake"""
    # TODO: Implémenter COPY INTO Snowflake (prochaine étape)
    return "load_skipped"


@flow(name="Pipeline Binance Real-Time", log_prints=True)
def pipeline_binance():
    """
    Pipeline Binance - Extraction + Upload vers Azure Blob

    Phase actuelle: Phase 2 - Extract & Upload
    Binance API → DataFrame pandas → Azure Blob Storage (Parquet)

    Prochaines étapes:
    - Load vers Snowflake (Phase 3)
    - Visualisation 
    Next.js (Phase 4)
    """
    # Étape 1: Extract data from Binance
    df = extract_binance_data()

    # Étape 2: Upload vers Azure Blob Storage
    blob_result = upload_to_blob(df)

    # Étape 3: Load vers Snowflake (à implémenter plus tard)
    # snowflake_result = load_to_snowflake()

    return {
        'extraction': {
            'rows': len(df),
            'symbols': df['symbol'].tolist() if 'symbol' in df.columns else []
        },
        'upload': blob_result
    }


if __name__ == "__main__":
    result = pipeline_binance()

    print("\n" + "="*80)
    print("📋 FINAL RESULT - Pipeline Summary")
    print("="*80)
    print(f"Extraction: {result['extraction']}")
    print(f"Upload: {result['upload']}")
    print("\n✅ Pipeline completed successfully!")
