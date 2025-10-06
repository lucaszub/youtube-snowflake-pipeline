"""
Script pour extraire les trending repos GitHub par technologie
"""
import requests
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv
import json

load_dotenv()

def get_trending_repos(topic="data-engineering", stars_min=500):
    """
    Récupère les repos GitHub par topic

    Args:
        topic: Topic GitHub (data-engineering, workflow, etl, orchestration, etc.)
        stars_min: Nombre minimum d'étoiles (défaut: 500)

    Returns:
        list: Liste de dictionnaires avec les infos des repos
    """
    # Query GitHub Search API
    url = "https://api.github.com/search/repositories"

    params = {
        "q": f"topic:{topic} stars:>{stars_min}",
        "sort": "stars",
        "order": "desc",
        "per_page": 50  # Top 20 repos
    }

    headers = {
        "Accept": "application/vnd.github.v3+json"
    }

    # Si tu as un token GitHub, décommenter et ajouter dans .env
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Erreur GitHub API: {response.status_code} - {response.text}")

    data = response.json()

    repos = []
    for i, item in enumerate(data["items"], 1):
        repos.append({
            "rank": i,
            "name": item["full_name"],
            "stars": item["stargazers_count"],
            "language": item.get("language", "N/A"),
            "description": item["description"][:80] if item["description"] else "Pas de description",
            "url": item["html_url"]
        })

    print(f"\n🏆 TOP 20 REPOS - TOPIC: {topic.upper()}\n" + "="*60)
    for repo in repos:
        print(f"{repo['rank']}. {repo['name']} - ⭐ {repo['stars']:,} stars ({repo['language']})")
        print(f"   {repo['description']}")
        print(f"   {repo['url']}\n")

    return repos


if __name__ == "__main__":
    print(get_trending_repos())
