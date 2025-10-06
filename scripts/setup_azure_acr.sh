#!/bin/bash
set -e

# Script de création et configuration d'Azure Container Registry
# Pour les pipelines Prefect

echo "🚀 Setup Azure Container Registry"
echo "=================================="

# Variables à configurerRegistry
RESOURCE_GROUP="${RESOURCE_GROUP:-prefect-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-prefectpipelineslucaszub}"  # Doit être unique globalement
SKU="${SKU:-Basic}"  # Basic, Standard, ou Premium

echo ""
echo "Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  ACR Name: $ACR_NAME"
echo "  SKU: $SKU"
echo ""

read -p "Continuer avec cette configuration? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Annulé"
    exit 1
fi

# 1. Vérifier que Azure CLI est installé
echo ""
echo "📋 Vérification Azure CLI..."
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI n'est pas installé"
    echo "Installer avec: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi
echo "✅ Azure CLI installé"

# 2. Login Azure (si pas déjà connecté)
echo ""
echo "🔐 Vérification connexion Azure..."
if ! az account show &> /dev/null; then
    echo "Connexion Azure requise..."
    az login
else
    echo "✅ Déjà connecté"
    CURRENT_SUB=$(az account show --query name -o tsv)
    echo "   Subscription: $CURRENT_SUB"
fi

# 3. Créer le Resource Group (si inexistant)
echo ""
echo "📦 Création Resource Group..."
if az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo "✅ Resource Group '$RESOURCE_GROUP' existe déjà"
else
    az group create \
        --name $RESOURCE_GROUP \
        --location $LOCATION
    echo "✅ Resource Group créé"
fi

# 4. Créer l'Azure Container Registry
echo ""
echo "🐳 Création Azure Container Registry..."
if az acr show --name $ACR_NAME &> /dev/null; then
    echo "✅ ACR '$ACR_NAME' existe déjà"
else
    az acr create \
        --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME \
        --sku $SKU \
        --location $LOCATION
    echo "✅ ACR créé"
fi

# 5. Activer l'admin user (pour GitHub Actions)
echo ""
echo "👤 Activation admin user..."
az acr update \
    --name $ACR_NAME \
    --admin-enabled true
echo "✅ Admin user activé"

# 6. Récupérer les credentials
echo ""
echo "🔑 Récupération credentials..."
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# 7. Afficher les credentials
echo ""
echo "=================================="
echo "✅ Setup terminé!"
echo "=================================="
echo ""
echo "📝 Secrets à configurer dans GitHub:"
echo ""
echo "Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ Secret Name       │ Value                                   │"
echo "├─────────────────────────────────────────────────────────────┤"
echo "│ ACR_LOGIN_SERVER  │ $ACR_LOGIN_SERVER"
echo "│ ACR_USERNAME      │ $ACR_USERNAME"
echo "│ ACR_PASSWORD      │ $ACR_PASSWORD"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "🔐 IMPORTANT: Copier le password maintenant, il ne sera plus affiché!"
echo ""

# 8. Sauvegarder dans un fichier (optionnel)
OUTPUT_FILE=".acr_credentials.txt"
cat > $OUTPUT_FILE << EOF
Azure Container Registry Credentials
=====================================
Created: $(date)

ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER
ACR_USERNAME=$ACR_USERNAME
ACR_PASSWORD=$ACR_PASSWORD

Login command:
az acr login --name $ACR_NAME

Docker login:
docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME -p $ACR_PASSWORD

Push example:
docker tag prefect-pipelines:latest $ACR_LOGIN_SERVER/prefect-pipelines:latest
docker push $ACR_LOGIN_SERVER/prefect-pipelines:latest
EOF

echo "💾 Credentials sauvegardés dans: $OUTPUT_FILE"
echo "⚠️  ATTENTION: Ce fichier contient des secrets sensibles!"
echo "   Ajouter à .gitignore et supprimer après configuration GitHub"
echo ""

# 9. Test de connexion
echo "🧪 Test de connexion au registry..."
if az acr login --name $ACR_NAME; then
    echo "✅ Connexion réussie!"
else
    echo "❌ Échec de connexion"
    exit 1
fi

# 10. Afficher les infos du registry
echo ""
echo "📊 Informations du registry:"
az acr show --name $ACR_NAME --query "{name:name, loginServer:loginServer, sku:sku.name, location:location}" -o table

echo ""
echo "🎉 Configuration terminée avec succès!"
echo ""
echo "Prochaines étapes:"
echo "  1. Copier les secrets dans GitHub (voir tableau ci-dessus)"
echo "  2. Commit et push .github/workflows/ci.yml"
echo "  3. L'image sera automatiquement poussée vers ACR"
echo ""
