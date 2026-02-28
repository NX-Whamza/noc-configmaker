#!/usr/bin/env bash
# =============================================================================
# setup_dev.sh — One-time DEV environment bootstrap on the VM
# =============================================================================
# Run this ONCE on the VM (after production is already set up).
# It creates the dev data dir, copies the env template, configures nginx,
# and brings up the dev docker stack.
#
# USAGE (on the VM):
#   cd ~/noc-configmaker
#   bash vm_deployment/setup_dev.sh
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${YELLOW}[INFO] $*${NC}"; }
ok()   { echo -e "${GREEN}[OK]   $*${NC}"; }
err()  { echo -e "${RED}[ERR]  $*${NC}"; }

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "=========================================="
echo "NOC Config Maker – DEV Setup"
echo "Repo: ${REPO_DIR}"
echo "=========================================="
echo ""

# ── 1. Create dev data directory ──
if [ ! -d "secure_data_dev" ]; then
  mkdir -p secure_data_dev
  chmod 700 secure_data_dev
  ok "Created secure_data_dev/"
else
  ok "secure_data_dev/ already exists"
fi

# ── 2. Create .env.dev from template if missing ──
if [ ! -f ".env.dev" ]; then
  if [ -f "ENV_DEV_TEMPLATE.txt" ]; then
    cp ENV_DEV_TEMPLATE.txt .env.dev
    chmod 600 .env.dev
    ok "Created .env.dev from template — edit it now if needed"
    info "  nano .env.dev"
  else
    err "ENV_DEV_TEMPLATE.txt not found!"
    exit 1
  fi
else
  ok ".env.dev already exists"
fi

# ── 3. Configure host nginx for dev domain ──
info "Setting up nginx for dev-noc-configmaker.nxlink.com..."
bash vm_deployment/configure_nginx_dev_domain.sh

# ── 4. Build and start dev stack ──
info "Building and starting the dev Docker stack..."
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --build

echo ""
echo "=========================================="
ok "DEV environment is live!"
echo "=========================================="
echo ""
echo "  URL:    https://dev-noc-configmaker.nxlink.com"
echo "  Data:   ./secure_data_dev/  (isolated from production)"
echo "  Logs:   docker compose -f docker-compose.dev.yml logs -f"
echo "  Stop:   docker compose -f docker-compose.dev.yml down"
echo "  Update: bash vm_deployment/update_dev.sh"
echo ""
