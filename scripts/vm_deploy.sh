#!/usr/bin/env bash
# vm_deploy.sh — pull latest code and rebuild/restart containers on the VM
# Usage:
#   ./scripts/vm_deploy.sh          # deploy this folder (prod or dev)
#   ./scripts/vm_deploy.sh --clean  # also prune build cache after deploy
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CLEAN=false

for arg in "$@"; do
  [[ "$arg" == "--clean" ]] && CLEAN=true
done

cd "$APP_DIR"

echo "[deploy] Working directory: $APP_DIR"
echo "[deploy] Current branch: $(git rev-parse --abbrev-ref HEAD)"
echo "[deploy] Current commit: $(git rev-parse --short HEAD)"

# Pull latest code
echo ""
echo "[deploy] Pulling latest code..."
git pull --ff-only

echo "[deploy] Now at: $(git rev-parse --short HEAD) — $(git log -1 --pretty=%s)"

# Rebuild images and restart containers (zero-downtime for unchanged services)
echo ""
echo "[deploy] Building and restarting containers..."
docker compose up -d --build

# Wait a moment then confirm health
echo ""
echo "[deploy] Waiting for health checks..."
sleep 10

HEALTH=$(curl -sf http://localhost:5000/api/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null || echo "unreachable")
echo "[deploy] Backend health: $HEALTH"

# Remove dangling images from this build
echo ""
echo "[deploy] Removing dangling images..."
docker image prune -f

if $CLEAN; then
  echo "[deploy] Pruning build cache..."
  docker builder prune -f
fi

echo ""
echo "[deploy] Done."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
