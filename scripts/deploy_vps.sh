#!/bin/bash
set -e

echo "🚀 VPS Deployment Script"
echo "========================"

cd /home/prefect/prefect-production/youtube-snowflake-pipeline

# 1. Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# 2. Login to Azure ACR
echo "🔐 Logging in to Azure ACR..."
echo "$ACR_PASSWORD" | docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME --password-stdin

# 3. Pull latest image
echo "📦 Pulling latest Docker image..."
docker pull $ACR_LOGIN_SERVER/prefect-pipelines:latest

# 4. Tag as latest
echo "🏷️  Tagging image..."
docker tag $ACR_LOGIN_SERVER/prefect-pipelines:latest prefect-pipelines:latest

# 5. Restart worker
echo "🔄 Restarting worker..."
/usr/local/bin/docker-compose up -d --no-deps --force-recreate prefect-worker

# 6. Wait for worker to be ready
echo "⏳ Waiting for worker to start..."
sleep 15

# 7. Deploy flows
echo "📤 Deploying Prefect flows..."
echo "  → YouTube pipeline..."
/usr/local/bin/docker-compose exec -T prefect-worker python /app/pipelines/youtube/deploy.py
echo "  → GitHub pipeline..."
/usr/local/bin/docker-compose exec -T prefect-worker python /app/pipelines/github/deploy.py
echo "  → Test pipeline..."
/usr/local/bin/docker-compose exec -T prefect-worker python /app/pipelines/test/deploy.py

# 8. Verify deployments
echo "✅ Verifying deployments..."
/usr/local/bin/docker-compose exec -T prefect-worker prefect deployment ls

echo ""
echo "✅ Deployment completed successfully!"
