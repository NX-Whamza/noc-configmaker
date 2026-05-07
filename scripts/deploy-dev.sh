#!/usr/bin/env bash
# Deploy to dev environment — pulls GHCR image, restarts nexus-dev stack on port 8100
set -euo pipefail

VERSION="${1:-latest}"
APP_DIR="/home/whamza/nexus-dev"
COMPOSE_FILE="$APP_DIR/docker-compose.dev.yml"

echo "[deploy-dev] Version: $VERSION"
cd "$APP_DIR"

echo "[deploy-dev] Pulling latest compose config..."
git pull origin main --ff-only || echo "[deploy-dev] git pull skipped (non-fast-forward or offline)"

export NEXUS_VERSION="$VERSION"
export NEXUS_APP_VERSION="$VERSION"
export NEXUS_APP_RELEASE_DATE="$(date -u +%Y-%m-%d)"

echo "[deploy-dev] Pulling images..."
docker compose -f "$COMPOSE_FILE" pull

echo "[deploy-dev] Starting containers..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "[deploy-dev] Waiting for health checks..."
sleep 15

HEALTH=$(curl -sf http://localhost:8100/nexus.html 2>/dev/null && echo "ok" || echo "unreachable")
echo "[deploy-dev] Frontend health: $HEALTH"

echo "[deploy-dev] Pruning old images..."
docker image prune -f

echo "[deploy-dev] Done — $VERSION is live on dev (port 8100)."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -i nexus-dev || true
