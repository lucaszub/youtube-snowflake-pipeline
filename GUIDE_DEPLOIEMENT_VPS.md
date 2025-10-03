# Guide complet : Déployer votre pipeline Prefect sur VPS avec schedule

Ce guide vous explique **étape par étape** comment déployer votre pipeline YouTube → Snowflake → dbt sur un VPS avec un schedule automatique (tous les jours à 12h).

---

## 📋 Vue d'ensemble

**Ce que vous allez faire :**
1. Préparer votre code (Git)
2. Configurer le VPS (installation)
3. Créer un déploiement avec schedule
4. Faire tourner Prefect 24/7 avec systemd
5. Le pipeline s'exécutera automatiquement tous les jours à 12h

---

## 🎯 Étape 1 : Préparer votre code localement

### 1.1 Créer le fichier de déploiement

Créez un fichier `deploy.py` à la racine de votre projet :

```python
# deploy.py
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from main import pipeline_complet

# Déploiement avec schedule quotidien à 12h (midi)
deployment = Deployment.build_from_flow(
    flow=pipeline_complet,
    name="production-daily-12h",
    work_pool_name="default-pool",
    schedule=CronSchedule(
        cron="0 12 * * *",  # Tous les jours à 12h00
        timezone="Europe/Paris"
    ),
    tags=["production", "youtube", "daily"],
    version="1.0.0",
    description="Pipeline YouTube → Snowflake → dbt - Exécution quotidienne à midi"
)

if __name__ == "__main__":
    deployment.apply()
    print("✅ Déploiement créé avec succès!")
    print("   Nom: production-daily-12h")
    print("   Schedule: Tous les jours à 12h00 (Europe/Paris)")
```

**Exemples de cron pour différents schedules :**
```python
# Toutes les heures
cron="0 * * * *"

# Tous les jours à 2h du matin
cron="0 2 * * *"

# Tous les jours à 12h (midi)
cron="0 12 * * *"

# Toutes les 6 heures
cron="0 */6 * * *"

# Tous les lundis à 9h
cron="0 9 * * 1"

# Le 1er de chaque mois à minuit
cron="0 0 1 * *"
```

### 1.2 Créer le .gitignore

```bash
# .gitignore
venv/
.env
__pycache__/
*.pyc
youtube_dbt/target/
youtube_dbt/logs/
youtube_dbt/dbt_packages/
.prefect/
*.log
```

### 1.3 Préparer Git

```bash
cd /home/lucas-zubiarrain/prefect

# Initialiser git
git init

# Ajouter tous les fichiers (sauf ceux dans .gitignore)
git add .

# Premier commit
git commit -m "Initial commit - Prefect YouTube pipeline"

# Pousser sur GitHub/GitLab
git remote add origin https://github.com/votre-user/prefect-youtube-pipeline.git
git branch -M main
git push -u origin main
```

---

## 🖥️ Étape 2 : Configurer le VPS

### 2.1 Se connecter au VPS

```bash
# Depuis votre PC local
ssh root@votre-vps-ip
# Exemple: ssh root@123.45.67.89
```

### 2.2 Installer les dépendances système

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Python 3.11, PostgreSQL et Git
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql git

# Vérifier les versions
python3.11 --version
psql --version
git --version
```

### 2.3 Créer un utilisateur dédié (recommandé)

```bash
# Créer l'utilisateur 'prefect'
sudo useradd -m -s /bin/bash prefect

# Donner un mot de passe (optionnel)
sudo passwd prefect

# Se connecter en tant que prefect
sudo su - prefect
```

### 2.4 Cloner votre code

```bash
# En tant qu'utilisateur prefect
cd ~
git clone https://github.com/votre-user/prefect-youtube-pipeline.git prefect-production
cd prefect-production
```

### 2.5 Créer l'environnement virtuel

```bash
# Créer le venv
python3.11 -m venv venv

# Activer le venv
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.6 Créer le fichier .env sur le VPS

```bash
# Créer le fichier .env
nano .env
```

Copier-coller vos credentials :

```env
# YouTube API
YOUTUBE_API_KEY=AIzaSy...

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
BLOB_CONTAINER_NAME=raw

# Snowflake
SNOWFLAKE_ACCOUNT=IAHIKEH-YS87921
SNOWFLAKE_USER=LUCASZUB
SNOWFLAKE_PASSWORD=votre_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=YOUTUBE_RAW
SNOWFLAKE_SCHEMA=INGESTION
SNOWFLAKE_ROLE=ACCOUNTADMIN

# dbt
DBT_PROJECT_DIR=/home/prefect/prefect-production/youtube_dbt
```

Sauvegarder : `Ctrl+X`, puis `Y`, puis `Enter`

---

## 🗄️ Étape 3 : Configurer PostgreSQL

### 3.1 Créer la base de données Prefect

```bash
# Revenir en root
exit  # ou Ctrl+D

# Se connecter à PostgreSQL
sudo -u postgres psql
```

Dans psql, exécuter :

```sql
-- Créer la base de données
CREATE DATABASE prefect_db;

-- Créer l'utilisateur
CREATE USER prefect_user WITH PASSWORD 'mot_de_passe_securise_123';

-- Donner les droits
GRANT ALL PRIVILEGES ON DATABASE prefect_db TO prefect_user;

-- Quitter
\q
```

### 3.2 Configurer Prefect pour utiliser PostgreSQL

```bash
# Revenir en tant que prefect
sudo su - prefect
cd ~/prefect-production
source venv/bin/activate

# Configurer l'URL de la base de données
prefect config set PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://prefect_user:mot_de_passe_securise_123@localhost/prefect_db"

# Configurer l'URL de l'API
prefect config set PREFECT_API_URL="http://localhost:4200/api"
```

---

## 📦 Étape 4 : Créer le déploiement avec schedule

### 4.1 Décommenter l'extraction YouTube dans main.py

**Important** : Avant de déployer, assurez-vous que l'extraction YouTube est active dans `main.py` :

```python
# main.py - ligne ~82
# Étape 1: Extraction YouTube → Blob Storage
blob_result = api_to_blob()  # ← Décommenter cette ligne
```

### 4.2 Créer le déploiement

```bash
# En tant que prefect, dans ~/prefect-production
source venv/bin/activate

# Lancer le script de déploiement
python deploy.py
```

Vous devriez voir :
```
✅ Déploiement créé avec succès!
   Nom: production-daily-12h
   Schedule: Tous les jours à 12h00 (Europe/Paris)
```

### 4.3 Vérifier le déploiement

```bash
# Lister les déploiements
prefect deployment ls
```

Vous devriez voir votre déploiement `Pipeline YouTube → Snowflake → dbt/production-daily-12h`

---

## 🔧 Étape 5 : Configurer les services systemd (pour tourner 24/7)

### 5.1 Créer le service Prefect Server

```bash
# Revenir en root
exit  # ou Ctrl+D

# Créer le fichier service
sudo nano /etc/systemd/system/prefect-server.service
```

Contenu du fichier :

```ini
[Unit]
Description=Prefect Server
After=network.target postgresql.service

[Service]
Type=simple
User=prefect
WorkingDirectory=/home/prefect/prefect-production
Environment="PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect_user:mot_de_passe_securise_123@localhost/prefect_db"
Environment="PREFECT_API_URL=http://localhost:4200/api"
ExecStart=/home/prefect/prefect-production/venv/bin/prefect server start --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Sauvegarder : `Ctrl+X`, `Y`, `Enter`

### 5.2 Créer le service Prefect Worker

```bash
sudo nano /etc/systemd/system/prefect-worker.service
```

Contenu du fichier :

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

Sauvegarder : `Ctrl+X`, `Y`, `Enter`

### 5.3 Démarrer les services

```bash
# Recharger systemd
sudo systemctl daemon-reload

# Activer les services au démarrage
sudo systemctl enable prefect-server
sudo systemctl enable prefect-worker

# Démarrer les services maintenant
sudo systemctl start prefect-server
sudo systemctl start prefect-worker

# Vérifier le statut
sudo systemctl status prefect-server
sudo systemctl status prefect-worker
```

Vous devriez voir `active (running)` pour les deux services.

---

## 🌐 Étape 6 : Accéder à l'interface web

### Option A : Via tunnel SSH (recommandé pour débuter)

Depuis votre PC local :

```bash
ssh -L 4200:localhost:4200 prefect@votre-vps-ip
```

Puis ouvrir dans votre navigateur : `http://localhost:4200`

### Option B : Avec nginx (pour accès direct)

Sur le VPS :

```bash
# Installer nginx
sudo apt install -y nginx

# Créer la configuration
sudo nano /etc/nginx/sites-available/prefect
```

Contenu :

```nginx
server {
    listen 80;
    server_name votre-vps-ip;  # ou votre domaine

    location / {
        proxy_pass http://localhost:4200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Activer :

```bash
sudo ln -s /etc/nginx/sites-available/prefect /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Ouvrir le port 80
sudo ufw allow 80/tcp
```

Accéder via : `http://votre-vps-ip`

---

## ✅ Étape 7 : Vérifier que tout fonctionne

### 7.1 Vérifier les logs

```bash
# Logs du serveur Prefect
sudo journalctl -u prefect-server -f

# Logs du worker
sudo journalctl -u prefect-worker -f
```

### 7.2 Vérifier dans l'UI

1. Ouvrir l'UI Prefect (`http://localhost:4200` via tunnel SSH)
2. Aller dans **Deployments**
3. Vous devriez voir : `Pipeline YouTube → Snowflake → dbt / production-daily-12h`
4. Cliquer dessus pour voir le schedule : "Tous les jours à 12h00"

### 7.3 Tester manuellement (optionnel)

Pour tester immédiatement sans attendre 12h :

```bash
# Via CLI
prefect deployment run "Pipeline YouTube → Snowflake → dbt/production-daily-12h"

# Ou via l'UI : cliquer sur "Quick Run"
```

---

## 🔄 Étape 8 : Workflow d'itération (modifier le code plus tard)

### 8.1 Sur votre PC local

```bash
# Modifier le code
nano main.py

# Commiter et pousser
git add .
git commit -m "Amélioration du pipeline"
git push
```

### 8.2 Sur le VPS

```bash
# Se connecter
ssh prefect@votre-vps-ip

# Aller dans le projet
cd ~/prefect-production

# Mettre à jour le code
git pull

# Redémarrer le worker pour charger le nouveau code
sudo systemctl restart prefect-worker

# Pas besoin de redémarrer le serveur !
```

**Important** : Le worker charge le code Python **à chaque exécution**, donc après un `git pull` + redémarrage du worker, le prochain run utilisera le nouveau code.

---

## 📊 Commandes utiles

### Gestion des services

```bash
# Voir les logs en temps réel
sudo journalctl -u prefect-server -f
sudo journalctl -u prefect-worker -f

# Redémarrer un service
sudo systemctl restart prefect-server
sudo systemctl restart prefect-worker

# Arrêter un service
sudo systemctl stop prefect-server
sudo systemctl stop prefect-worker

# Statut des services
sudo systemctl status prefect-server
sudo systemctl status prefect-worker
```

### Gestion Prefect

```bash
# Lister les déploiements
prefect deployment ls

# Lister les flows
prefect flow ls

# Voir les runs récents
prefect flow-run ls --limit 10

# Déclencher manuellement un run
prefect deployment run "Pipeline YouTube → Snowflake → dbt/production-daily-12h"
```

### Gestion du code

```bash
# Mettre à jour le code depuis Git
cd ~/prefect-production
git pull

# Voir les logs d'un run spécifique
prefect flow-run logs <flow-run-id>
```

---

## 🐛 Troubleshooting

### Le worker ne démarre pas

```bash
# Vérifier les logs
sudo journalctl -u prefect-worker -n 50

# Vérifier que l'environnement virtuel existe
ls /home/prefect/prefect-production/venv

# Vérifier les permissions
sudo chown -R prefect:prefect /home/prefect/prefect-production
```

### Le schedule ne se déclenche pas

```bash
# Vérifier que le worker est actif
sudo systemctl status prefect-worker

# Vérifier le déploiement
prefect deployment ls

# Vérifier le work pool
prefect work-pool ls
```

### Erreur de connexion PostgreSQL

```bash
# Vérifier que PostgreSQL tourne
sudo systemctl status postgresql

# Tester la connexion
psql -U prefect_user -d prefect_db -h localhost
```

### Le pipeline échoue

```bash
# Voir les logs dans l'UI Prefect
# Ou via CLI:
prefect flow-run ls --limit 5

# Voir les logs d'un run spécifique
prefect flow-run logs <flow-run-id>
```

---

## 📝 Checklist finale

- [ ] Code poussé sur Git
- [ ] `deploy.py` créé avec le bon schedule
- [ ] VPS configuré (Python, PostgreSQL, Git)
- [ ] Code cloné sur le VPS
- [ ] `.env` créé avec les bonnes credentials
- [ ] PostgreSQL configuré
- [ ] Déploiement créé (`python deploy.py`)
- [ ] Services systemd créés et démarrés
- [ ] Services `active (running)`
- [ ] UI accessible (via tunnel ou nginx)
- [ ] Déploiement visible dans l'UI avec le schedule
- [ ] Test manuel réussi

---

## 🎉 C'est fait !

Votre pipeline s'exécutera automatiquement **tous les jours à 12h** :

1. ✅ Extraction YouTube → Blob Storage
2. ✅ Snowflake COPY INTO
3. ✅ dbt run
4. ✅ Logs et historique disponibles dans l'UI Prefect

**Prochaines étapes (optionnel) :**
- Ajouter des alertes (Slack, email) en cas d'échec
- Configurer HTTPS avec nginx + Let's Encrypt
- Ajouter d'autres pipelines (Sales, Marketing, etc.)
- Monitorer les performances

---

**Besoin d'aide ?** Consultez la [documentation Prefect](https://docs.prefect.io)
