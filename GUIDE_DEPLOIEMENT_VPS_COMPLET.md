# Guide de Déploiement VPS - Pipeline YouTube → Snowflake → dbt

Guide complet et à jour pour déployer votre pipeline Prefect sur un VPS avec schedule automatique.

---

## 📋 Vue d'ensemble

**Ce que vous allez déployer :**

- Pipeline YouTube → Azure Blob → Snowflake → dbt
- Orchestré par Prefect avec schedule quotidien (12h)
- Serveur Prefect + Worker tournant 24/7
- Base de données PostgreSQL pour Prefect
- Services systemd pour redémarrage automatique

**Prérequis :**

- Un VPS Ubuntu/Debian (recommandé : 2GB RAM minimum)
- Accès SSH root
- Votre code pushé sur GitHub/GitLab

---

## 🖥️ PARTIE 1 : Configuration du VPS (en tant que ROOT)

### Étape 1.1 : Connexion et mise à jour

```bash
# Depuis votre PC local
ssh root@votre-vps-ip

# Sur le VPS - Mettre à jour le système
apt update && apt upgrade -y
```

### Étape 1.2 : Vérifier la version Python disponible

```bash
# Vérifier quelle version de Python est disponible
python3 --version
```

**Si Python 3.10, 3.11 ou 3.12** → Parfait, continuez !
**Si Python < 3.10** → Installez Python 3.12 :

```bash
# Ajouter le PPA pour Python récent
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.12 python3.12-venv
```

### Étape 1.3 : Installer les dépendances système

```bash
# Installer Python, venv, pip, PostgreSQL et Git
apt install -y python3 python3-venv python3-pip postgresql git

# Ou si vous avez installé Python 3.12
apt install -y python3.12 python3.12-venv python3-pip postgresql git

# Vérifier les installations
python3 --version
psql --version
git --version
```

### Étape 1.4 : Créer l'utilisateur `prefect`

**Pourquoi ?** Pour la sécurité - l'application ne tournera pas avec les droits root.

```bash
# Créer l'utilisateur avec home directory et shell bash
useradd -m -s /bin/bash prefect

# Vérifier la création
ls /home/prefect/  # Doit exister
```

**Note :** L'utilisateur `prefect` n'a PAS les droits sudo (c'est voulu pour la sécurité).

---

## 🗄️ PARTIE 2 : Configuration PostgreSQL (en tant que ROOT)

### Étape 2.1 : Créer la base de données Prefect

```bash
# Se connecter à PostgreSQL en tant qu'utilisateur postgres
sudo -u postgres psql
```

Dans l'interface PostgreSQL, exécuter :

```sql
-- Créer la base de données
CREATE DATABASE prefect_db;

-- Créer l'utilisateur (CHANGEZ le mot de passe !)
CREATE USER prefect_user WITH PASSWORD 'changez_moi_mot_de_passe_fort_123';

-- Donner tous les droits
GRANT ALL PRIVILEGES ON DATABASE prefect_db TO prefect_user;

-- Quitter PostgreSQL
\q
```

**⚠️ IMPORTANT : Notez le mot de passe choisi, vous en aurez besoin !**

---

## 👤 PARTIE 3 : Déploiement du code (en tant que PREFECT)

### Étape 3.1 : Devenir l'utilisateur prefect

```bash
# Depuis root, devenir prefect
su - prefect

# Vérifier que vous êtes bien prefect
whoami
# Doit afficher: prefect

pwd
# Doit afficher: /home/prefect
```

### Étape 3.2 : Cloner le code depuis Git

```bash
# Cloner votre repo
git clone https://github.com/votre-username/youtube-data-orchestration.git prefect-production

# Aller dans le projet
cd prefect-production

# Vérifier les fichiers
ls
# Vous devriez voir: main.py, deploy.py, requirements.txt, etc.
```

### Étape 3.3 : Créer l'environnement virtuel Python

```bash
# Créer le venv (utiliser python3 ou python3.12 selon votre installation)
python3 -m venv venv

# Activer le venv
source venv/bin/activate

# Vérifier l'activation (le prompt doit commencer par (venv))
# (venv) prefect@srv$

# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances du projet
pip install -r requirements.txt
```

**Cette étape peut prendre 2-5 minutes.**

### Étape 3.4 : Créer le fichier .env avec vos credentials

```bash
# Créer le fichier .env
nano .env
```

Copier-coller vos credentials (adaptez avec vos vraies valeurs) :

```env
# YouTube API
YOUTUBE_API_KEY=AIzaSy...

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;EndpointSuffix=...
BLOB_CONTAINER_NAME=raw

# Snowflake
SNOWFLAKE_ACCOUNT=votre_account
SNOWFLAKE_USER=votre_user
SNOWFLAKE_PASSWORD=votre_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=YOUTUBE_RAW
SNOWFLAKE_SCHEMA=INGESTION
SNOWFLAKE_ROLE=ACCOUNTADMIN

# dbt (adapter le chemin avec votre vrai chemin VPS)
DBT_PROJECT_DIR=/home/prefect/prefect-production/youtube_dbt
```

**Sauvegarder :** `Ctrl+X`, puis `Y`, puis `Enter`

**🔒 Sécurité :** Vérifiez les permissions du .env :

```bash
chmod 600 .env
ls -la .env
# Doit afficher: -rw------- (uniquement prefect peut lire)
```

### Étape 3.5 : Configurer Prefect

```bash
# Configurer l'URL de la base de données PostgreSQL
# ⚠️ CHANGEZ le mot de passe par celui que vous avez choisi à l'étape 2.1
prefect config set PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://prefect_user:Medard44@localhost/prefect_db"

# Configurer l'URL de l'API Prefect
prefect config set PREFECT_API_URL="http://localhost:4200/api"

# Vérifier la configuration
prefect config view
```

### Étape 3.6 : Créer le déploiement avec schedule

```bash
# Toujours dans le venv, en tant que prefect
python deploy.py
```

Vous devriez voir :

```
✅ Déploiement créé avec succès!
   Nom: production-daily-12h
   Schedule: Tous les jours à 12h00 (Europe/Paris)
```

### Étape 3.7 : Vérifier le déploiement

```bash
# Lister les déploiements
prefect deployment ls

# Vous devriez voir:
# Pipeline YouTube → Snowflake → dbt/production-daily-12h
```

---

## 🚀 PARTIE 4 : Démarrer les services en production (ROOT)

### Étape 4.1 : Sortir de l'utilisateur prefect

```bash
# Depuis prefect
exit

# Vous êtes maintenant root
whoami
# Doit afficher: root
```

### Étape 4.2 : Créer le service systemd pour Prefect Server

```bash
# En tant que root
nano /etc/systemd/system/prefect-server.service
```

Copier-coller ce contenu (**ADAPTEZ le mot de passe PostgreSQL**) :

```ini
[Unit]
Description=Prefect Server
After=network.target postgresql.service

[Service]
Type=simple
User=prefect
WorkingDirectory=/home/prefect/prefect-production
Environment="PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect_user:changez_moi_mot_de_passe_fort_123@localhost/prefect_db"
Environment="PREFECT_API_URL=http://localhost:4200/api"
ExecStart=/home/prefect/prefect-production/venv/bin/prefect server start --host 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Sauvegarder :** `Ctrl+X`, `Y`, `Enter`

### Étape 4.3 : Créer le service systemd pour Prefect Worker

```bash
nano /etc/systemd/system/prefect-worker.service
```

Copier-coller :

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

**Sauvegarder :** `Ctrl+X`, `Y`, `Enter`

### Étape 4.4 : Activer et démarrer les services

```bash
# Recharger systemd pour prendre en compte les nouveaux services
systemctl daemon-reload

# Activer les services au démarrage du serveur
systemctl enable prefect-server
systemctl enable prefect-worker

# Démarrer les services maintenant
systemctl start prefect-server
systemctl start prefect-worker

# Attendre 10 secondes que tout démarre
sleep 10

# Vérifier que les services tournent
systemctl status prefect-server
systemctl status prefect-worker
```

**Vous devez voir :** `Active: active (running)` en vert pour les deux services.

**Si un service est en erreur :**

```bash
# Voir les logs d'erreur
journalctl -u prefect-server -n 50
journalctl -u prefect-worker -n 50
```

---

## 🌐 PARTIE 5 : Accéder à l'interface web

### Option A : Via tunnel SSH (le plus simple)

**Depuis votre PC local** (pas sur le VPS) :

```bash
ssh -L 4200:localhost:4200 prefect@votre-vps-ip
```

Puis ouvrir dans votre navigateur : `http://localhost:4200`

**Garder ce terminal ouvert** tant que vous voulez accéder à l'UI.

### Option B : Accès direct avec nginx (plus avancé)

Si vous voulez accéder directement sans tunnel SSH :

```bash
# Sur le VPS, en tant que root
apt install -y nginx

# Créer la configuration nginx
nano /etc/nginx/sites-available/prefect
```

Copier :

```nginx
server {
    listen 80;
    server_name votre-vps-ip;  # Ou votre nom de domaine

    location / {
        proxy_pass http://localhost:4200;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Support WebSocket pour l'UI temps réel
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Activer :

```bash
ln -s /etc/nginx/sites-available/prefect /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default  # Supprimer la config par défaut
nginx -t  # Tester la config
systemctl restart nginx

# Ouvrir le port 80
ufw allow 80/tcp
```

Accéder via : `http://votre-vps-ip`

---

## ✅ PARTIE 6 : Vérifications finales

### 6.1 : Vérifier que les services tournent

```bash
# Status des services
systemctl status prefect-server
systemctl status prefect-worker

# Logs en temps réel
journalctl -u prefect-server -f
journalctl -u prefect-worker -f
```

### 6.2 : Vérifier l'interface web

1. Accéder à l'UI (via tunnel SSH ou nginx)
2. Aller dans **Deployments**
3. Vous devriez voir : `Pipeline YouTube → Snowflake → dbt / production-daily-12h`
4. Vérifier le schedule : "Every day at 12:00 PM"

### 6.3 : Tester manuellement le pipeline

**Option 1 - Via l'UI :**

- Cliquer sur le déploiement
- Cliquer sur **Quick Run**
- Suivre l'exécution en temps réel

**Option 2 - Via CLI :**

```bash
# Devenir prefect
su - prefect
cd ~/prefect-production
source venv/bin/activate

# Lancer manuellement
prefect deployment run "Pipeline YouTube → Snowflake → dbt/production-daily-12h"

# Voir les runs
prefect flow-run ls --limit 5
```

---

## 🔄 PARTIE 7 : Workflow d'itération (modifier le code)

### Sur votre PC local

```bash
# 1. Modifier le code
nano main.py

# 2. Tester localement
python main.py

# 3. Commiter et pousser
git add .
git commit -m "Amélioration du pipeline"
git push origin main
```

### Sur le VPS

```bash
# 1. Se connecter en SSH
ssh root@votre-vps-ip

# 2. Devenir prefect
su - prefect

# 3. Mettre à jour le code
cd ~/prefect-production
git pull

# 4. Redémarrer le worker pour charger le nouveau code
exit  # Revenir en root
systemctl restart prefect-worker

# 5. Vérifier
systemctl status prefect-worker
```

**Note :** Pas besoin de redémarrer le serveur Prefect, juste le worker !

---

## 📊 Commandes utiles

### Gestion des services

```bash
# Voir les logs en temps réel
journalctl -u prefect-server -f
journalctl -u prefect-worker -f

# Voir les dernières erreurs
journalctl -u prefect-server -n 50
journalctl -u prefect-worker -n 50

# Redémarrer un service
systemctl restart prefect-server
systemctl restart prefect-worker

# Arrêter un service
systemctl stop prefect-server
systemctl stop prefect-worker

# Status
systemctl status prefect-server
systemctl status prefect-worker
```

### Gestion Prefect (en tant que prefect)

```bash
su - prefect
cd ~/prefect-production
source venv/bin/activate

# Lister les déploiements
prefect deployment ls

# Lister les flows
prefect flow ls

# Voir les runs récents
prefect flow-run ls --limit 10

# Déclencher manuellement
prefect deployment run "Pipeline YouTube → Snowflake → dbt/production-daily-12h"

# Voir les logs d'un run spécifique
prefect flow-run logs <flow-run-id>
```

---

## 🐛 Troubleshooting

### Problème : Le service ne démarre pas

```bash
# Voir les logs détaillés
journalctl -u prefect-server -n 100
journalctl -u prefect-worker -n 100

# Vérifier les permissions
ls -la /home/prefect/prefect-production/
chown -R prefect:prefect /home/prefect/prefect-production/

# Tester manuellement
su - prefect
cd ~/prefect-production
source venv/bin/activate
prefect server start  # Voir l'erreur directement
```

### Problème : Erreur de connexion PostgreSQL

```bash
# Vérifier que PostgreSQL tourne
systemctl status postgresql

# Tester la connexion
su - prefect
psql -U prefect_user -d prefect_db -h localhost
# Taper le mot de passe quand demandé
```

### Problème : Le schedule ne se déclenche pas

```bash
# Vérifier que le worker tourne
systemctl status prefect-worker

# Vérifier que le déploiement existe
su - prefect
cd ~/prefect-production
source venv/bin/activate
prefect deployment ls

# Vérifier le work pool
prefect work-pool ls
```

### Problème : Quota YouTube dépassé

Le pipeline échoue avec "quotaExceeded" → Attendez le lendemain (reset à minuit heure Pacifique US)

**Solution temporaire :** Commentez l'appel à `api_to_blob()` dans `main.py` ligne 83.

---

## 📝 Checklist de déploiement

- [ ] VPS accessible en SSH
- [ ] Python 3.10+ installé
- [ ] PostgreSQL installé et base de données créée
- [ ] Utilisateur `prefect` créé
- [ ] Code cloné depuis Git
- [ ] Environnement virtuel créé et dépendances installées
- [ ] Fichier `.env` créé avec tous les credentials
- [ ] Configuration Prefect effectuée (`prefect config set ...`)
- [ ] Déploiement créé (`python deploy.py`)
- [ ] Services systemd créés
- [ ] Services démarrés et `active (running)`
- [ ] UI accessible (via tunnel SSH ou nginx)
- [ ] Test manuel du pipeline réussi

---

## 🎉 Félicitations !

Votre pipeline est maintenant en production et s'exécutera automatiquement tous les jours à 12h !

**Prochaines étapes (optionnel) :**

- Configurer des alertes Slack/Email en cas d'échec
- Ajouter HTTPS avec Let's Encrypt
- Monitorer les performances
- Ajouter d'autres pipelines

**Support :**

- Documentation Prefect : https://docs.prefect.io
- Voir `CLAUDE.md` pour l'architecture du projet
