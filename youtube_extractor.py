"""Extraction YouTube et upload vers Azure Blob Storage"""
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
from googleapiclient.discovery import build
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()


class YouTubeSearcher:
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def get_channel_info(self, channel_id):
        """Récupère toutes les infos détaillées d'une chaîne YouTube"""
        # Infos de base
        channel_response = self.youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=channel_id
        ).execute()

        channel = channel_response['items'][0]
        stats = channel['statistics']

        # Toutes les vidéos avec détails
        videos = []
        next_page = None

        while True:
            search_response = self.youtube.search().list(
                channelId=channel_id,
                part='snippet',
                type='video',
                maxResults=50,
                pageToken=next_page,
                order='date'
            ).execute()

            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

            # Récupérer les stats de chaque vidéo
            if video_ids:
                videos_response = self.youtube.videos().list(
                    part='statistics,contentDetails',
                    id=','.join(video_ids)
                ).execute()

                for i, item in enumerate(search_response.get('items', [])):
                    video_stats = videos_response['items'][i]['statistics']
                    video_details = videos_response['items'][i]['contentDetails']

                    videos.append({
                        'videoId': item['id']['videoId'],
                        'channelTitle': item['snippet']['channelTitle'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'publishedAt': item['snippet']['publishedAt'],
                        'thumbnails': item['snippet']['thumbnails']['high']['url'],
                        'viewCount': video_stats.get('viewCount', '0'),
                        'likeCount': video_stats.get('likeCount', '0'),
                        'commentCount': video_stats.get('commentCount', '0'),
                        'duration': video_details.get('duration', ''),
                        'loaded_at': datetime.now().isoformat()
                    })

            next_page = search_response.get('nextPageToken')
            if not next_page:
                break

        return {
            'channelId': channel_id,
            'title': channel['snippet']['title'],
            'description': channel['snippet']['description'],
            'customUrl': channel['snippet'].get('customUrl', ''),
            'publishedAt': channel['snippet']['publishedAt'],
            'country': channel['snippet'].get('country', ''),
            'thumbnails': channel['snippet']['thumbnails']['high']['url'],
            'viewCount': stats.get('viewCount', '0'),
            'subscriberCount': stats.get('subscriberCount', '0'),
            'videoCount': stats.get('videoCount', '0'),
            'videos': videos
        }


def extract_and_upload():
    """Fonction principale d'extraction et upload vers Blob Storage"""

    # Configuration depuis les environment variables
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "raw")

    # Liste des channel IDs à extraire
    channel_ids = [
        "UCoOae5nYA7VqaXzerajD0lg",  # Ali Abdaal
        "UCAq9f7jFEA7Mtl3qOZy2h1A",  # Data with Zach
        "UCChmJrVa8kDg05JfCmxpLRw",  # Darshil Parmar
    ]

    all_videos = []
    total_videos_count = 0

    # Extraction YouTube pour chaque chaîne
    searcher = YouTubeSearcher(API_KEY)

    for channel_id in channel_ids:
        print(f'📺 Extracting channel: {channel_id}')

        try:
            info = searcher.get_channel_info(channel_id)

            # Créer le DataFrame pour cette chaîne
            df_channel = pd.DataFrame(info['videos'])

            # Ajouter les infos de la chaîne
            df_channel['channel_id'] = info['channelId']
            df_channel['channel_title'] = info['title']
            df_channel['channel_subscribers'] = info['subscriberCount']
            df_channel['channel_total_views'] = info['viewCount']
            df_channel['channel_video_count'] = info['videoCount']

            all_videos.append(df_channel)
            total_videos_count += len(df_channel)

            print(f'✅ Extracted {len(df_channel)} videos from {info["title"]}')

        except Exception as e:
            print(f'❌ Error extracting channel {channel_id}: {str(e)}')
            continue

    if not all_videos:
        raise Exception("No videos extracted from any channel")

    # Combiner toutes les vidéos
    df = pd.concat(all_videos, ignore_index=True)

    print(f'✅ Total extracted: {len(df)} videos from {len(channel_ids)} channels')

    # Convertir en Parquet
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
    parquet_buffer.seek(0)

    # Upload vers Blob Storage (partitionné par date)
    today = datetime.now()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    day = today.strftime("%d")

    blob_path = f"youtube/{year}/{month}/{day}/videos_{today.strftime('%H%M%S')}.parquet"

    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(
        container=CONTAINER_NAME,
        blob=blob_path
    )

    blob_client.upload_blob(parquet_buffer.read(), overwrite=True)

    print(f'✅ Successfully uploaded to {blob_path}')
    print(f'📊 Total videos: {len(df)}')

    return len(df), blob_path
