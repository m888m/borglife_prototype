#!/bin/bash
set -e

echo "🚨 Emergency Recovery Procedure"

# 1. Stop all services
echo "Stopping all services..."
docker compose down
cd ../archon && docker compose down

# 2. Clean up networks
echo "Cleaning networks..."
docker network prune -f

# 3. Remove corrupted volumes (if needed)
# docker volume rm borglife_prototype_data

# 4. Restart from clean state
echo "Restarting from clean state..."
cd ../archon
docker compose up -d

# Wait for Archon
sleep 20

# 5. Restart Borglife
cd ../borglife_prototype
docker compose --profile organs up -d

# 6. Validate all services
echo "Validating services..."
python3 scripts/validate_prerequisites.py

echo "✅ Recovery complete"