#!/bin/bash
set -e

echo "⬆️ Updating Archon to latest stable version"

# Navigate to archon directory
cd ../archon

# Pull latest changes
echo "Pulling latest changes..."
git pull origin stable

# Rebuild services
echo "Rebuilding Archon services..."
docker compose down
docker compose up -d --build

# Wait for health
echo "Waiting for services to be healthy..."
sleep 15

# Health checks
until curl -f http://localhost:8181/health > /dev/null 2>&1; do
    echo "Waiting for Archon server..."
    sleep 5
done

until curl -f http://localhost:8051/health > /dev/null 2>&1; do
    echo "Waiting for Archon MCP..."
    sleep 5
done

echo "✅ Archon updated successfully"