#!/usr/bin/env bash
# CI/CD deploy — pulls GHCR images and restarts containers via docker-compose.prod.yml
set -euo pipefail

VERSION="${1:-latest}"
APP_DIR="/home/whamza/nexus"
COMPOSE_FILE="$APP_DIR/docker-compose.prod.yml"

echo "[deploy] Version: $VERSION"
cd "$APP_DIR"

echo "[deploy] Pulling latest compose config..."
git pull origin main --ff-only || echo "[deploy] git pull skipped (non-fast-forward or offline)"

export NEXUS_VERSION="$VERSION"
export NEXUS_APP_VERSION="$VERSION"
export NEXUS_APP_RELEASE_DATE="$(date -u +%Y-%m-%d)"

echo "[deploy] Pulling images..."
docker compose -f "$COMPOSE_FILE" pull

echo "[deploy] Starting containers..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "[deploy] Waiting for health checks..."
sleep 15

HEALTH=$(curl -sf http://localhost:5000/api/health 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null \
  || echo "unreachable")
echo "[deploy] Health: $HEALTH"

echo "[deploy] Pruning old images..."
docker image prune -f

echo "[deploy] Done — $VERSION is live."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
