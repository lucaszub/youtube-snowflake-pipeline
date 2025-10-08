"""
Azure Blob Storage Uploader for Binance Data

Uploads Binance cryptocurrency data to Azure Blob Storage in Parquet format.
"""
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContentSettings
from typing import Dict, Any


class AzureBlobUploader:
    """
    Uploads DataFrames to Azure Blob Storage in Parquet format

    The blob naming convention is:
    binance/YYYY/MM/DD/binance_data_YYYYMMDD_HHMMSS.parquet

    This allows for:
    - Easy partitioning by date
    - Time-based queries
    - Incremental data loading
    """

    def __init__(self, connection_string: str = None, container_name: str = None):
        """
        Initialize Azure Blob uploader

        Args:
            connection_string: Azure Storage connection string (from .env if not provided)
            container_name: Blob container name (from .env if not provided)
        """
        self.connection_string = connection_string or os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.container_name = container_name or os.getenv('BLOB_CONTAINER_NAME', 'raw')

        if not self.connection_string:
            raise ValueError("Azure Storage connection string not found. Set AZURE_STORAGE_CONNECTION_STRING in .env")

        # Initialize Blob Service Client
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

        # Ensure container exists
        self._ensure_container_exists()

    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                print(f"✅ Created container: {self.container_name}")
        except Exception as e:
            print(f"⚠️  Container check/creation warning: {e}")

    def generate_blob_path(self, timestamp: datetime = None) -> str:
        """
        Generate blob path with date partitioning

        Format: binance/YYYY/MM/DD/binance_data_YYYYMMDD_HHMMSS.parquet

        Args:
            timestamp: Datetime to use for path (defaults to now)

        Returns:
            Blob path string
        """
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime('%Y%m%d')
        time_str = timestamp.strftime('%H%M%S')

        # Partitioned by year/month/day for easier querying
        blob_path = (
            f"binance/"
            f"{timestamp.year}/"
            f"{timestamp.month:02d}/"
            f"{timestamp.day:02d}/"
            f"binance_data_{date_str}_{time_str}.parquet"
        )

        return blob_path

    def upload_dataframe(self, df: pd.DataFrame, blob_path: str = None) -> Dict[str, Any]:
        """
        Upload DataFrame to Azure Blob Storage as Parquet

        Args:
            df: DataFrame to upload
            blob_path: Custom blob path (auto-generated if not provided)

        Returns:
            Dict with upload metadata (blob_path, size, timestamp, row_count)
        """
        if df is None or df.empty:
            raise ValueError("DataFrame is empty, cannot upload")

        # Generate blob path if not provided
        if blob_path is None:
            # Use timestamp from first row if available
            if 'timestamp' in df.columns and not df.empty:
                try:
                    first_timestamp = pd.to_datetime(df['timestamp'].iloc[0])
                    blob_path = self.generate_blob_path(first_timestamp)
                except:
                    blob_path = self.generate_blob_path()
            else:
                blob_path = self.generate_blob_path()

        print(f"\n📤 Uploading to Azure Blob Storage...")
        print(f"  📁 Container: {self.container_name}")
        print(f"  📄 Blob: {blob_path}")
        print(f"  📊 Rows: {len(df)}")
        print(f"  📋 Columns: {len(df.columns)}")

        # Convert DataFrame to Parquet in memory
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, engine='pyarrow', compression='snappy', index=False)
        parquet_buffer.seek(0)

        parquet_size = len(parquet_buffer.getvalue())
        print(f"  💾 Parquet size: {parquet_size / 1024:.2f} KB")

        # Upload to blob
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )

        try:
            # Set content type for Parquet
            content_settings = ContentSettings(content_type='application/octet-stream')

            blob_client.upload_blob(
                parquet_buffer,
                overwrite=True,
                content_settings=content_settings
            )

            upload_timestamp = datetime.now()

            result = {
                'success': True,
                'blob_path': blob_path,
                'container': self.container_name,
                'size_bytes': parquet_size,
                'size_kb': round(parquet_size / 1024, 2),
                'row_count': len(df),
                'column_count': len(df.columns),
                'upload_timestamp': upload_timestamp.isoformat(),
                'url': blob_client.url
            }

            print(f"  ✅ Upload successful!")
            print(f"  🔗 URL: {result['url']}")

            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'blob_path': blob_path
            }
            print(f"  ❌ Upload failed: {e}")
            raise Exception(f"Failed to upload to blob: {e}") from e


def upload_binance_to_blob(df: pd.DataFrame, connection_string: str = None, container_name: str = None) -> Dict[str, Any]:
    """
    Convenience function to upload Binance DataFrame to Azure Blob

    Args:
        df: Binance data DataFrame
        connection_string: Azure Storage connection string (optional, reads from .env)
        container_name: Container name (optional, reads from .env)

    Returns:
        Upload metadata dict
    """
    uploader = AzureBlobUploader(connection_string, container_name)
    return uploader.upload_dataframe(df)


if __name__ == "__main__":
    # Test with sample data
    print("🧪 Testing Azure Blob Uploader...")

    # Create sample DataFrame
    test_data = {
        'symbol': ['BTCUSDT', 'ETHUSDT'],
        'timestamp': [datetime.now().isoformat()] * 2,
        'last_price': [50000.0, 3000.0],
        'volume_24h': [1000.0, 5000.0]
    }
    test_df = pd.DataFrame(test_data)

    print("\n📊 Sample DataFrame:")
    print(test_df)

    try:
        from dotenv import load_dotenv
        load_dotenv()

        result = upload_binance_to_blob(test_df)
        print("\n✅ Test successful!")
        print(f"📋 Result: {result}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
