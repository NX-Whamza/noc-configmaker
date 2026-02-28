#!/usr/bin/env bash
# =============================================================================
# update_dev.sh — Pull latest code and rebuild the DEV stack ONLY
# =============================================================================
# Production containers are untouched.
#
# USAGE (on the VM):
#   cd ~/noc-configmaker && bash vm_deployment/update_dev.sh
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${YELLOW}[INFO] $*${NC}"; }
ok()   { echo -e "${GREEN}[OK]   $*${NC}"; }

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=========================================="
echo "NOC Config Maker – DEV Update"
echo "=========================================="
echo ""

# ── 1. Pull latest code ──
info "Pulling latest code from origin..."
git pull origin main --ff-only
ok "Code updated"

# ── 2. Rebuild and restart dev containers only ──
info "Rebuilding dev containers..."
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --build

ok "DEV stack rebuilt and restarted"
echo ""

# ── 3. Health check ──
info "Waiting 10s for containers to start..."
sleep 10

echo ""
info "Health check:"
if curl -fsS http://127.0.0.1:8100/api/health | head -c 200; then
  echo ""
  ok "DEV is healthy at https://dev-noc-configmaker.nxlink.com"
else
  echo ""
  echo -e "${RED}[WARN] Health check failed — check logs:${NC}"
  echo "  docker compose -f docker-compose.dev.yml logs -f"
fi

echo ""
echo "=========================================="
echo "Production status (untouched):"
docker compose ps --format 'table {{.Name}}\t{{.Status}}' 2>/dev/null || echo "(production stack not running via compose on this host)"
echo "=========================================="
