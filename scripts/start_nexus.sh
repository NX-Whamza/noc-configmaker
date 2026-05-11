#!/usr/bin/env bash
# Starts ido_local_backend on loopback (18081), waits for it, then execs the main backend.
set -euo pipefail

echo "[start] Starting ido-backend on 127.0.0.1:18081..."
uvicorn --app-dir . vm_deployment.ido_local_backend:app \
  --host 127.0.0.1 --port 18081 &
IDO_PID=$!

# Wait up to 30s for ido-backend to be ready
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18081/health/full >/dev/null 2>&1; then
    echo "[start] ido-backend ready (${i}s)"
    break
  fi
  if ! kill -0 "$IDO_PID" 2>/dev/null; then
    echo "[start] ERROR: ido-backend process died" >&2
    exit 1
  fi
  sleep 1
done

echo "[start] Starting main backend on 0.0.0.0:5000..."
exec uvicorn --app-dir vm_deployment fastapi_server:app \
  --host 0.0.0.0 --port 5000 \
  --workers "${NEXUS_UVICORN_WORKERS:-1}"
