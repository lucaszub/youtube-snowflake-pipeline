# Binance Real-Time Data Pipeline

Pipeline de données crypto orchestré avec **Prefect 3.x** qui extrait les données en temps réel depuis l'API publique Binance.

## 🎯 Objectif

Extraire automatiquement les données de marché crypto (prix, volume, spread, trades) toutes les 5 minutes pour analyse et visualisation.

## 🏗️ Architecture

```
Binance Public API → Prefect Flow → pandas DataFrame → Logs
                          ↓
                    PostgreSQL (Prefect metadata)
```

**Phases prévues:**
1. ✅ **Phase 1 (actuelle)**: Extraction des données via API Binance
2. 🔜 **Phase 2**: Upload vers Azure Blob Storage (Parquet)
3. 🔜 **Phase 3**: Chargement vers Snowflake
4. 🔜 **Phase 4**: Dashboard Next.js pour visualisation temps réel

## 📊 Données Extraites

Pour chaque symbole crypto (BTCUSDT, ETHUSDT, BNBUSDT):

- **Prix**: Dernier prix, variation 24h ($ et %), high/low 24h
- **Volume**: Volume 24h (base + quote), prix moyen pondéré
- **Order Book**: Best bid/ask, spread ($, %), quantités
- **Trades**: Prix moyen des 5 derniers trades, volume total
- **Timestamp**: Horodatage précis de l'extraction

## 🚀 Quick Start

### Prérequis

- Docker & Docker Compose
- Python 3.11+ (pour développement local)

### Démarrage avec Docker (Recommandé)

```bash
# 1. Cloner le repo
git clone <repo-url>
cd prefect

# 2. Démarrer les services (Postgres + Prefect Server + Worker)
docker compose up -d

# 3. Accéder à l'interface Prefect
# Ouvrir http://localhost:4200 dans votre navigateur

# 4. Déployer le pipeline Binance
docker compose exec prefect-worker python /app/pipelines/Binance/deploy.py

# 5. Vérifier les logs
docker compose logs -f prefect-worker
```

Le pipeline s'exécutera automatiquement toutes les 5 minutes selon le schedule configuré.

### Développement Local

```bash
# 1. Créer un environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer le pipeline manuellement
python pipelines/Binance/main.py
```

## 📁 Structure du Projet

```
.
├── pipelines/
│   └── Binance/
│       ├── main.py                # Prefect flow principal
│       ├── binance_extractor.py   # Client API Binance
│       └── deploy.py              # Configuration déploiement
├── docker-compose.yml             # Services Docker
├── Dockerfile                     # Image worker Prefect
├── requirements.txt               # Dépendances Python
└── README.md
```

## ⚙️ Configuration

### Modifier les Symboles Trackés

Éditer `pipelines/Binance/main.py`:

```python
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
```

### Changer la Fréquence d'Exécution

Éditer `pipelines/Binance/deploy.py`:

```python
# Toutes les 5 minutes (défaut)
cron="*/5 * * * *"

# Toutes les 15 minutes
cron="*/15 * * * *"

# Toutes les heures
cron="0 * * * *"
```

Puis redéployer:

```bash
docker compose exec prefect-worker python /app/pipelines/Binance/deploy.py
```

## 🔧 Commandes Utiles

```bash
# Voir les logs du worker
docker compose logs -f prefect-worker

# Voir les logs du serveur Prefect
docker compose logs -f prefect-server

# Redémarrer les services
docker compose restart

# Reconstruire l'image après modifications
docker compose up -d --build

# Arrêter tous les services
docker compose down

# Arrêter et supprimer les volumes
docker compose down -v
```

## 📊 Interface Prefect

Accéder à http://localhost:4200 pour:

- Visualiser les runs du pipeline
- Voir les logs détaillés
- Déclencher des exécutions manuelles
- Monitorer les schedules
- Consulter les métriques

## 🛠️ Technologies

- **Prefect 3.x**: Orchestration de workflows
- **Python 3.11**: Langage de développement
- **pandas**: Traitement des données
- **requests**: API HTTP
- **PostgreSQL**: Base de données pour Prefect
- **Docker**: Containerisation

## 📝 Notes Importantes

### Rate Limiting Binance

L'API publique Binance a des limites de taux:
- 1200 requêtes/minute (weight-based)
- Le pipeline respecte ces limites avec un délai de 0.2s entre symboles

### Pas d'API Key Requise

L'API publique Binance ne nécessite pas d'authentification pour les endpoints utilisés:
- `/api/v3/ticker/24hr` - Statistiques 24h
- `/api/v3/depth` - Order book
- `/api/v3/trades` - Trades récents

## 🐛 Troubleshooting

**Le worker ne démarre pas:**
- Vérifier que PostgreSQL est up: `docker compose ps`
- Vérifier les logs: `docker compose logs postgres`

**Pas d'exécutions planifiées:**
- Vérifier que le déploiement est actif dans l'UI Prefect
- Vérifier le work pool: `default-pool`

**Erreurs API Binance:**
- Vérifier la connectivité réseau
- Vérifier les logs pour rate limiting

## 📚 Ressources

- [Documentation Prefect](https://docs.prefect.io/)
- [Binance API Docs](https://binance-docs.github.io/apidocs/spot/en/)
- [Docker Documentation](https://docs.docker.com/)

## 🚦 Roadmap

- [ ] Phase 2: Upload to Azure Blob Storage (Parquet format)
- [ ] Phase 3: Load to Snowflake data warehouse
- [ ] Phase 4: Next.js dashboard with real-time charts
- [ ] Phase 5: Data quality checks and alerting
- [ ] Phase 6: Additional crypto exchanges (Coinbase, Kraken)

## 📄 License

MIT
