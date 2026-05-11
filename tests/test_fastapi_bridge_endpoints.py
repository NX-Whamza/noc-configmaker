#!/usr/bin/env python3
"""Regression tests for UI bridge endpoints exposed by FastAPI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "vm_deployment"))

from fastapi_server import app  # noqa: E402
import api_server as _api_server  # noqa: E402


client = TestClient(app)


def _admin_email() -> str:
    return os.getenv("PLATFORM_ADMIN_EMAILS", "whamza@team.nxlink.com").split(",")[0].strip()


def _fastapi_auth_headers() -> dict[str, str]:
    token = _api_server.generate_token(999001, _admin_email())
    return {"Authorization": f"Bearer {token}"}


def test_maintenance_bridge_requires_auth():
    response = client.get("/api/maintenance/windows")
    assert response.status_code == 401


def test_command_vault_bridge_requires_auth():
    response = client.post("/api/command-vault/catalog", json={"family": "cisco"})
    assert response.status_code == 401


def test_maintenance_bridge_crud_round_trip():
    headers = _fastapi_auth_headers()
    payload = {
        "name": "Tenant Maintenance Window",
        "scheduled_at": "2026-04-01T07:00:00Z",
        "duration_minutes": 90,
        "priority": "normal",
        "devices": ["10.0.0.1", "10.0.0.2"],
        "tasks": ["backup", "config"],
        "notes": "Regression test window",
        "ticket_number": "NOC-1234",
        "ticket_url": "https://example.invalid/browse/NOC-1234",
        "status": "scheduled",
        "created_by": "test@example.com",
    }
    create_resp = client.post("/api/maintenance/windows", json=payload, headers=headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    window_id = created["window_id"]
    assert created["name"] == payload["name"]
    assert created["created_by"] == f"session:{_admin_email()}"

    list_resp = client.get("/api/maintenance/windows", params={"status": "all", "limit": 50}, headers=headers)
    assert list_resp.status_code == 200
    windows = list_resp.json()["windows"]
    assert any(window["window_id"] == window_id for window in windows)

    get_resp = client.get(f"/api/maintenance/windows/{window_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["ticket_number"] == "NOC-1234"

    update_resp = client.put(
        f"/api/maintenance/windows/{window_id}",
        json={**payload, "status": "running", "notes": "Updated note"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "running"
    assert updated["notes"] == "Updated note"

    delete_resp = client.delete(f"/api/maintenance/windows/{window_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"


def test_command_vault_bridge_returns_catalog_results():
    response = client.post(
        "/api/command-vault/catalog",
        json={"family": "cisco", "query": "ospf"},
        headers=_fastapi_auth_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert any(item["family"] == "cisco" for item in data["results"])
