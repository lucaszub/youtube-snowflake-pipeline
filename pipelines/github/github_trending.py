"""
Script pour extraire les trending repos GitHub par technologie
"""
import requests
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def get_trending_repos(language="python", days=7, stars_min=100):
    """
    Récupère les repos trending sur GitHub pour une technologie donnée

    Args:
        language: Langage de programmation (python, javascript, go, rust, etc.)
        days: Nombre de jours pour "trending" (défaut: 7 jours)
        stars_min: Nombre minimum d'étoiles (défaut: 100)

    Returns:
        list: Liste de dictionnaires avec les infos des repos
    """
    # Date de création minimale (repos créés dans les X derniers jours)
    date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Query GitHub Search API
    url = "https://api.github.com/search/repositories"

    params = {
        "q": f"language:{language} created:>{date_threshold} stars:>{stars_min}",
        "sort": "stars",
        "order": "desc",
        "per_page": 30  # Top 30 repos
    }

    headers = {
        "Accept": "application/vnd.github.v3+json"
    }

    # Si tu as un token GitHub, décommenter et ajouter dans .env
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    print(f"🔍 Recherche des repos {language} trending (derniers {days} jours, min {stars_min} stars)...")

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Erreur GitHub API: {response.status_code} - {response.text}")

    data = response.json()

    repos = []
    for item in data["items"]:
        repo = {
            "repo_id": item["id"],
            "repo_name": item["full_name"],
            "description": item["description"],
            "stars": item["stargazers_count"],
            "forks": item["forks_count"],
            "watchers": item["watchers_count"],
            "open_issues": item["open_issues_count"],
            "language": item["language"],
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
            "url": item["html_url"],
            "topics": ",".join(item.get("topics", [])),
            "license": item["license"]["name"] if item.get("license") else None,
            "extracted_at": datetime.now().isoformat()
        }
        repos.append(repo)

    print(f"✅ Trouvé {len(repos)} repos trending")

    return repos


def main():
    """
    Pipeline simple: GitHub API → Affichage console
    """
    # Technologies à tracker
    technologies = ["python", "javascript", "typescript", "go", "rust"]

    all_repos = []

    for tech in technologies:
        print(f"\n{'='*60}")
        print(f"🔥 Traitement: {tech.upper()}")
        print(f"{'='*60}")

        try:
            repos = get_trending_repos(language=tech, days=30, stars_min=50)
            all_repos.extend(repos)

            # Afficher quelques résultats
            if repos:
                print(f"\n📊 Top 5 repos {tech}:")
                for i, repo in enumerate(repos[:5], 1):
                    print(f"  {i}. {repo['repo_name']} - ⭐ {repo['stars']} stars")
                    print(f"     {repo['description'][:80]}..." if repo['description'] else "")

        except Exception as e:
            print(f"❌ Erreur pour {tech}: {e}")
            continue

    # Créer DataFrame
    df = pd.DataFrame(all_repos)

    print(f"\n{'='*60}")
    print(f"📊 RÉSUMÉ TOTAL")
    print(f"{'='*60}")
    print(f"Total repos extraits: {len(df)}")
    print(f"\nRépartition par langage:")
    print(df['language'].value_counts())

    print(f"\n✅ Extraction terminée!")
    print(f"📊 Nombre total de repos: {len(df)}")


if __name__ == "__main__":
    main()
