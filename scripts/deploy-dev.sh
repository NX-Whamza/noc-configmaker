#!/usr/bin/env bash
# Deploy to dev environment — pulls GHCR image, restarts nexus-dev stack on port 8100
# WARNING: This script is CI-controlled. Any uncommitted edits in /home/whamza/nexus-dev/
# will be discarded on every run by `git reset --hard origin/main`.
set -euo pipefail

VERSION="${1:-latest}"
APP_DIR="/home/whamza/nexus-dev"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"

echo "[deploy-dev] Version: $VERSION"
cd "$APP_DIR"

echo "[deploy-dev] Pulling latest compose config..."
git fetch origin main && git reset --hard origin/main

export NEXUS_VERSION="$VERSION"
export NEXUS_APP_VERSION="$VERSION"
export NEXUS_APP_RELEASE_DATE="$(date -u +%Y-%m-%d)"

echo "[deploy-dev] Building images..."
docker compose -f "$COMPOSE_FILE" -p nexus-dev build

echo "[deploy-dev] Starting containers..."
docker compose -f "$COMPOSE_FILE" -p nexus-dev up -d --remove-orphans

echo "[deploy-dev] Waiting for health checks..."
sleep 15

HEALTH=$(curl -sf http://localhost:8100/nexus.html 2>/dev/null && echo "ok" || echo "unreachable")
echo "[deploy-dev] Frontend health: $HEALTH"

echo "[deploy-dev] Pruning old images..."
docker image prune -f --filter "until=24h"

echo "[deploy-dev] Done — $VERSION is live on dev (port 8100)."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -i nexus-dev || true
