#!/bin/bash
set -euo pipefail

# XP Hunt deployment to Hetzner (46.225.223.247)
SERVER="deploy@46.225.223.247"
REMOTE_DIR="/opt/xphunt"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== XP Hunt Deploy ==="
echo "Project: $PROJECT_DIR"
echo "Server:  $SERVER:$REMOTE_DIR"
echo ""

# 1. Sync project files
echo "[1/4] Syncing files..."
rsync -avz --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.env*' \
  --exclude 'mileshunt.db' \
  --exclude '.DS_Store' \
  "$PROJECT_DIR/" "$SERVER:$REMOTE_DIR/"

# 2. Build and start container
echo "[2/4] Building and starting container..."
ssh "$SERVER" "cd $REMOTE_DIR/deploy && docker compose up -d --build"

# 3. Wait for health check
echo "[3/4] Waiting for health check..."
sleep 3
ssh "$SERVER" "curl -sf http://127.0.0.1:8010/api/xp-table > /dev/null && echo 'Health check: OK' || echo 'Health check: FAIL'"

# 4. Check logs
echo "[4/4] Recent logs:"
ssh "$SERVER" "docker logs xphunt --tail 10"

echo ""
echo "=== Deploy complete ==="
echo "App: https://xphunt.pointiful.com"
echo "Admin: https://xphunt.pointiful.com/admin"
echo ""
echo "First time? Run:"
echo "  ssh $SERVER 'docker exec -it xphunt python -m mileshunt.admin_setup'"
