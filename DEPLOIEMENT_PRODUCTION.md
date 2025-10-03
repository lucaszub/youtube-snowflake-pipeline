# Déploiement Prefect en Production

Guide complet pour déployer Prefect sur un VPS (alternative légère à Airflow)

---

## 📋 Architecture de Production

### Composants nécessaires

```
┌─────────────────────────────────────────────────────┐
│                    VPS (Ubuntu/Debian)               │
│                                                      │
│  ┌──────────────────┐      ┌────────────────────┐  │
│  │  Prefect Server  │      │  Prefect Worker    │  │
│  │  (API + UI)      │◄────►│  (Exécute flows)   │  │
│  │  Port 4200       │      │                    │  │
│  └──────────────────┘      └────────────────────┘  │
│           │                                          │
│           ▼                                          │
│  ┌──────────────────┐                               │
│  │  PostgreSQL      │                               │
│  │  (Base de        │                               │
│  │   données)       │                               │
│  └──────────────────┘                               │
└─────────────────────────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────┐
   │  Vos services externes  │
   │  - Azure Function       │
   │  - Snowflake           │
   │  - dbt                 │
   └─────────────────────────┘
```

---

## 🚀 Option 1: Déploiement Simple (Self-Hosted)

### Étape 1: Installation sur VPS

```bash
# Se connecter au VPS
ssh user@votre-vps.com

# Installer Python et dépendances
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql

# Créer un utilisateur système pour Prefect
sudo useradd -m -s /bin/bash prefect
sudo su - prefect

# Créer l'environnement
mkdir ~/prefect-production
cd ~/prefect-production
python3.11 -m venv venv
source venv/bin/activate

# Installer Prefect + dépendances pour votre projet
pip install prefect[postgres]
pip install azure-functions
pip install snowflake-connector-python
pip install dbt-snowflake
```

### Étape 2: Configuration PostgreSQL

```bash
# Créer la base de données
sudo -u postgres psql
```

```sql
CREATE DATABASE prefect_db;
CREATE USER prefect_user WITH PASSWORD 'votre_mot_de_passe_securise';
GRANT ALL PRIVILEGES ON DATABASE prefect_db TO prefect_user;
\q
```

### Étape 3: Configuration Prefect

```bash
# Configurer Prefect pour utiliser PostgreSQL
export PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://prefect_user:votre_mot_de_passe_securise@localhost/prefect_db"

# ⚠️ IMPORTANT: Configurer l'URL de l'API
export PREFECT_API_URL="http://localhost:4200/api"

# Sauvegarder la config
prefect config set PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://prefect_user:votre_mot_de_passe_securise@localhost/prefect_db"
prefect config set PREFECT_API_URL="http://localhost:4200/api"
```

---

## 🔧 Étape 4: Créer vos Workflows

Créer le fichier: `~/prefect-production/workflows/data_pipeline.py`

```python
from prefect import flow, task
from prefect.blocks.system import Secret
import requests
import snowflake.connector
import subprocess
from datetime import timedelta

@task(retries=3, retry_delay_seconds=60)
def declencher_azure_function():
    """Déclenche une Azure Function qui envoie des données sur Blob Storage"""

    # Récupérer le secret depuis Prefect (configuré dans l'UI)
    azure_function_url = Secret.load("azure-function-url").get()
    azure_function_key = Secret.load("azure-function-key").get()

    headers = {
        "x-functions-key": azure_function_key,
        "Content-Type": "application/json"
    }

    response = requests.post(
        azure_function_url,
        headers=headers,
        json={"action": "export_to_blob"}
    )

    response.raise_for_status()
    print(f"✅ Azure Function déclenchée: {response.status_code}")
    return response.json()


@task(retries=3, retry_delay_seconds=120)
def snowflake_copy_into():
    """Exécute COPY INTO sur Snowflake depuis Blob Storage"""

    # Récupérer les credentials Snowflake
    snowflake_account = Secret.load("snowflake-account").get()
    snowflake_user = Secret.load("snowflake-user").get()
    snowflake_password = Secret.load("snowflake-password").get()
    snowflake_warehouse = Secret.load("snowflake-warehouse").get()
    snowflake_database = Secret.load("snowflake-database").get()
    snowflake_schema = Secret.load("snowflake-schema").get()

    conn = snowflake.connector.connect(
        account=snowflake_account,
        user=snowflake_user,
        password=snowflake_password,
        warehouse=snowflake_warehouse,
        database=snowflake_database,
        schema=snowflake_schema
    )

    cursor = conn.cursor()

    # Exécuter COPY INTO
    copy_query = """
    COPY INTO ma_table_destination
    FROM @mon_stage_azure/chemin/vers/fichiers
    FILE_FORMAT = (TYPE = 'JSON')
    ON_ERROR = 'CONTINUE'
    """

    cursor.execute(copy_query)
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    print(f"✅ COPY INTO exécuté: {result}")
    return result


@task(retries=2, retry_delay_seconds=60)
def dbt_run():
    """Exécute dbt run pour transformer les données"""

    # Chemin vers votre projet dbt
    dbt_project_path = "/home/prefect/dbt-project"

    # Exécuter dbt run
    result = subprocess.run(
        ["dbt", "run", "--profiles-dir", f"{dbt_project_path}/profiles"],
        cwd=dbt_project_path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"❌ Erreur dbt: {result.stderr}")
        raise Exception(f"dbt run a échoué: {result.stderr}")

    print(f"✅ dbt run terminé:\n{result.stdout}")
    return result.stdout


@flow(
    name="Pipeline Data Complet",
    description="Azure Function → Snowflake COPY INTO → dbt",
    retries=1,
    retry_delay_seconds=300
)
def pipeline_data_complet():
    """
    Orchestration complète du pipeline de données:
    1. Déclenche Azure Function (export vers Blob Storage)
    2. Charge les données dans Snowflake (COPY INTO)
    3. Transforme avec dbt
    """

    # Étape 1: Azure Function
    azure_result = declencher_azure_function()

    # Étape 2: Snowflake COPY INTO (attend que Azure soit fini)
    snowflake_result = snowflake_copy_into()

    # Étape 3: dbt run (attend que Snowflake soit fini)
    dbt_result = dbt_run()

    print("🎉 Pipeline complet terminé avec succès!")
    return {
        "azure": azure_result,
        "snowflake": snowflake_result,
        "dbt": dbt_result
    }


if __name__ == "__main__":
    # Pour tester localement
    pipeline_data_complet()
```

---

## 📦 Étape 5: Créer un Déploiement

```bash
cd ~/prefect-production

# Créer un déploiement avec un schedule
python -c "
from workflows.data_pipeline import pipeline_data_complet
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

# Déploiement avec schedule quotidien à 2h du matin
deployment = Deployment.build_from_flow(
    flow=pipeline_data_complet,
    name='production-daily',
    work_pool_name='default-pool',
    schedule=CronSchedule(cron='0 2 * * *', timezone='Europe/Paris'),
    tags=['production', 'daily', 'data-pipeline']
)

deployment.apply()
print('✅ Déploiement créé!')
"
```

---

## 🔐 Étape 6: Configurer les Secrets

### Via l'interface web (recommandé):

1. Accéder à `http://votre-vps.com:4200`
2. Aller dans **Blocks** → **+ (Add Block)** → **Secret**
3. Créer les secrets suivants:
   - `azure-function-url`
   - `azure-function-key`
   - `snowflake-account`
   - `snowflake-user`
   - `snowflake-password`
   - `snowflake-warehouse`
   - `snowflake-database`
   - `snowflake-schema`

### Via CLI (alternative):

```bash
prefect block register -m prefect.blocks.system

# Créer les secrets
python -c "
from prefect.blocks.system import Secret

Secret(value='https://ma-function.azurewebsites.net/api/export').save(name='azure-function-url')
Secret(value='votre_function_key').save(name='azure-function-key')
Secret(value='votre_account.snowflakecomputing.com').save(name='snowflake-account')
# ... etc pour tous les secrets
"
```

---

## 🏃 Étape 7: Lancer les Services en Production

### Option A: Avec systemd (recommandé pour production)

Créer `/etc/systemd/system/prefect-server.service`:

```ini
[Unit]
Description=Prefect Server
After=network.target postgresql.service

[Service]
Type=simple
User=prefect
WorkingDirectory=/home/prefect/prefect-production
Environment="PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect_user:password@localhost/prefect_db"
Environment="PREFECT_API_URL=http://localhost:4200/api"
ExecStart=/home/prefect/prefect-production/venv/bin/prefect server start --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Créer `/etc/systemd/system/prefect-worker.service`:

```ini
[Unit]
Description=Prefect Worker
After=network.target prefect-server.service

[Service]
Type=simple
User=prefect
WorkingDirectory=/home/prefect/prefect-production
Environment="PREFECT_API_URL=http://localhost:4200/api"
ExecStart=/home/prefect/prefect-production/venv/bin/prefect worker start --pool default-pool
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activer les services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable prefect-server
sudo systemctl enable prefect-worker
sudo systemctl start prefect-server
sudo systemctl start prefect-worker

# Vérifier le status
sudo systemctl status prefect-server
sudo systemctl status prefect-worker
```

### Option B: Avec screen (pour tests rapides)

```bash
# Terminal 1: Server
screen -S prefect-server
cd ~/prefect-production
source venv/bin/activate
prefect server start --host 0.0.0.0
# Ctrl+A puis D pour détacher

# Terminal 2: Worker
screen -S prefect-worker
cd ~/prefect-production
source venv/bin/activate
prefect worker start --pool default-pool
# Ctrl+A puis D pour détacher

# Pour réattacher:
screen -r prefect-server
screen -r prefect-worker
```

---

## 🌐 Étape 8: Exposer l'UI (HTTPS optionnel)

### Sans HTTPS (développement/test):

```bash
# Ouvrir le port 4200 sur le firewall
sudo ufw allow 4200/tcp

# Accéder via:
# http://votre-vps-ip:4200
```

### Avec HTTPS (production recommandée):

Utiliser nginx comme reverse proxy + Let's Encrypt:

```bash
# Installer nginx et certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Créer la config nginx
sudo nano /etc/nginx/sites-available/prefect
```

```nginx
server {
    listen 80;
    server_name prefect.votre-domaine.com;

    location / {
        proxy_pass http://localhost:4200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Pour les WebSockets (UI en temps réel)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/prefect /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Obtenir le certificat SSL
sudo certbot --nginx -d prefect.votre-domaine.com

# Accéder via HTTPS:
# https://prefect.votre-domaine.com
```

**⚠️ Note importante**: HTTPS n'est **pas obligatoire** pour que Prefect fonctionne. C'est uniquement pour:
- Sécuriser l'accès à l'UI web
- Protéger les credentials si vous accédez depuis l'extérieur

Si votre VPS n'est accessible que par vous (VPN, SSH tunnel), HTTP suffit largement.

---

## 📊 Étape 9: Gestion des Déploiements

### Lister les déploiements

```bash
prefect deployment ls
```

### Modifier un schedule

```python
from prefect.deployments import Deployment

# Changer le schedule pour toutes les heures
deployment = Deployment(
    name="production-daily",
    flow_name="Pipeline Data Complet",
    schedule=CronSchedule(cron="0 * * * *")  # Toutes les heures
)
deployment.apply()
```

### Déclencher manuellement un run

```bash
# Via CLI
prefect deployment run "Pipeline Data Complet/production-daily"

# Ou via l'UI web:
# http://votre-vps.com:4200 → Deployments → Quick Run
```

### Voir les logs en temps réel

```bash
# Via CLI
prefect flow-run logs --follow <flow-run-id>

# Ou via l'UI (plus pratique)
```

---

## 🔄 Workflow de Développement

### 1. Développement local

```bash
# Sur votre machine locale
git clone votre-repo
cd prefect-project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Tester localement
python workflows/data_pipeline.py
```

### 2. Déployer sur le VPS

```bash
# Sur votre VPS
cd ~/prefect-production
git pull origin main

# Redémarrer le worker pour charger les nouveaux flows
sudo systemctl restart prefect-worker

# Ou créer/mettre à jour le déploiement
python workflows/deploy.py
```

### 3. Itérer rapidement

**Bonne pratique**: Utiliser un fichier `deploy.py` pour gérer tous vos déploiements:

```python
# workflows/deploy.py
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from workflows.data_pipeline import pipeline_data_complet

# Déploiement production (quotidien)
prod_deployment = Deployment.build_from_flow(
    flow=pipeline_data_complet,
    name="production-daily",
    work_pool_name="default-pool",
    schedule=CronSchedule(cron="0 2 * * *", timezone="Europe/Paris"),
    tags=["production", "daily"]
)

# Déploiement test (toutes les heures)
test_deployment = Deployment.build_from_flow(
    flow=pipeline_data_complet,
    name="test-hourly",
    work_pool_name="default-pool",
    schedule=CronSchedule(cron="0 * * * *"),
    tags=["test", "hourly"]
)

if __name__ == "__main__":
    prod_deployment.apply()
    test_deployment.apply()
    print("✅ Déploiements mis à jour!")
```

---

## 🎯 Résumé des Commandes Essentielles

```bash
# Démarrer les services
sudo systemctl start prefect-server
sudo systemctl start prefect-worker

# Voir les logs
sudo journalctl -u prefect-server -f
sudo journalctl -u prefect-worker -f

# Redémarrer après changements
sudo systemctl restart prefect-worker

# Lister les flows/déploiements
prefect flow ls
prefect deployment ls

# Déclencher un run manuel
prefect deployment run "Pipeline Data Complet/production-daily"

# Voir les runs actifs
prefect flow-run ls --limit 10
```

---

## 💡 Conseils pour Production

### 1. Monitoring et Alertes

```python
from prefect import flow
from prefect.blocks.notifications import SlackWebhook

@flow
def pipeline_avec_alertes():
    try:
        # Votre code
        pass
    except Exception as e:
        # Envoyer une alerte Slack
        slack = SlackWebhook.load("mon-webhook-slack")
        slack.notify(f"❌ Pipeline échoué: {str(e)}")
        raise
```

### 2. Gestion des Erreurs

```python
@task(
    retries=3,
    retry_delay_seconds=[60, 120, 300]  # Backoff exponentiel
)
def task_critique():
    pass
```

### 3. Logs structurés

```python
from prefect import get_run_logger

@task
def ma_task():
    logger = get_run_logger()
    logger.info("Début du traitement", extra={"row_count": 1000})
    logger.error("Erreur critique", extra={"error_code": "E001"})
```

### 4. Backups PostgreSQL

```bash
# Créer un cron pour backup quotidien
0 3 * * * pg_dump -U prefect_user prefect_db > /backup/prefect_$(date +\%Y\%m\%d).sql
```

---

## ❓ FAQ

### Q: Dois-je utiliser HTTPS obligatoirement?
**R**: Non. HTTP suffit si:
- Vous accédez uniquement depuis votre réseau local
- Vous utilisez un tunnel SSH
- Vous avez un VPN

HTTPS est recommandé uniquement si l'UI est accessible publiquement.

### Q: Quelle est la différence avec Airflow?
**R**:
- Prefect: Plus léger, facile à déployer, moderne (Python natif)
- Airflow: Plus lourd, plus de features enterprise, plus complexe

Pour un VPS, Prefect est idéal.

### Q: Comment gérer plusieurs projets?
**R**: Utilisez des **tags** et des **work pools** différents:
```python
Deployment.build_from_flow(
    flow=mon_flow,
    work_pool_name="projet-1-pool",
    tags=["projet-1", "production"]
)
```

### Q: Combien ça coûte?
**R**: Prefect est **gratuit** en self-hosted. Coûts:
- VPS: ~5-10€/mois
- PostgreSQL: Inclus
- Prefect Cloud (optionnel): Gratuit jusqu'à 10k runs/mois

---

## 📚 Ressources

- [Documentation Prefect](https://docs.prefect.io)
- [Prefect Deployments Guide](https://docs.prefect.io/concepts/deployments)
- [Prefect Blocks (Secrets)](https://docs.prefect.io/concepts/blocks)
- [Work Pools](https://docs.prefect.io/concepts/work-pools)

---

**Prêt à déployer? Bon courage! 🚀**
