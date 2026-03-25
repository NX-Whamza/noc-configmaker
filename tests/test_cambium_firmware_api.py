#!/usr/bin/env python3
"""Regression tests for Cambium firmware updater backend APIs."""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "vm_deployment"))

os.environ.setdefault("NEXTLINK_RADIUS_SECRET", "TEST_RADIUS_SECRET")

from fastapi_server import app  # noqa: E402
import api_server  # noqa: E402
from cambium_firmware import list_firmware_catalog, resolve_firmware_image  # noqa: E402


client = TestClient(app)


def test_cambium_catalog_scans_images_and_picks_latest(monkeypatch):
    artifacts_root = repo_root / "tests_artifacts"
    artifacts_root.mkdir(exist_ok=True)
    firmware_root = artifacts_root / "cambium-firmware-catalog"
    if firmware_root.exists():
        shutil.rmtree(firmware_root)
    try:
        ep3k_dir = firmware_root / "Cambium" / "EP3K"
        ep3k_dir.mkdir(parents=True)
        (ep3k_dir / "ePMP-AC-v5.10.1.img").write_bytes(b"old")
        (ep3k_dir / "ePMP-AC-v5.10.4.img").write_bytes(b"new")

        monkeypatch.setenv("FIRMWARE_PATH", str(firmware_root))

        catalog = list_firmware_catalog()
        assert catalog["devices"]["CNEP3K"]["default_version"] == "5.10.4"
        assert catalog["devices"]["CNEP3K"]["available_versions"] == ["5.10.4", "5.10.1"]

        selected = resolve_firmware_image("CNEP3K")
        assert selected["version"] == "5.10.4"
        pinned = resolve_firmware_image("CNEP3K", "5.10.1")
        assert pinned["filename"] == "ePMP-AC-v5.10.1.img"
    finally:
        if firmware_root.exists():
            shutil.rmtree(firmware_root)


def test_cambium_device_info_updates_queue(monkeypatch):
    monkeypatch.setattr(api_server, "HAS_CAMBIUM", True)
    api_server.cambium_shared_queue.clear()

    def fake_device_info(ip, device_type, password=None, run_tests=True):
        return {
            "success": True,
            "test_results": [
                {"name": "Firmware Version", "actual": "5.10.4", "expected": "5.10.4", "pass": True}
            ],
            "running_config": "ok",
            "standard_config": "{}",
        }

    monkeypatch.setattr(api_server, "cambium_get_device_info", fake_device_info)
    monkeypatch.setattr(api_server, "cambium_resolve_device_type", lambda value: "CNEP3K")

    r = client.post(
        "/api/cambium/device-info",
        json={"ip": "10.10.10.10", "device_type": "CNEP3K", "password": "secret"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["firmware_version"] == "5.10.4"

    queue_body = client.get("/api/cambium/queue").json()
    assert queue_body["radios"][0]["firmwareVersion"] == "5.10.4"
    assert queue_body["radios"][0]["deviceType"] == "CNEP3K"


def test_cambium_run_completes_and_updates_status(monkeypatch):
    monkeypatch.setattr(api_server, "HAS_CAMBIUM", True)
    api_server.cambium_shared_queue.clear()
    api_server.cambium_tasks.clear()
    api_server.cambium_log_queues.clear()
    captured = {}

    def fake_device_info(ip, device_type, password=None, run_tests=True):
        return {
            "success": True,
            "test_results": [
                {"name": "Firmware Version", "actual": "5.10.1", "expected": "5.10.4", "pass": False}
            ],
        }

    def fake_update_device(ip, device_type, username=None, password=None, update_version=None, callback=None):
        captured["username"] = username
        captured["password"] = password
        if callback:
            callback(f"[{ip}] Firmware uploaded.")
            callback(f"[{ip}] Device updated.")
        return {
            "success": True,
            "ip": ip,
            "device_type": device_type,
            "target_version": update_version or "5.10.4",
            "selected_image": "ePMP-AC-v5.10.4.img",
        }

    monkeypatch.setattr(api_server, "cambium_get_device_info", fake_device_info)
    monkeypatch.setattr(api_server, "cambium_update_device", fake_update_device)
    monkeypatch.setattr(api_server, "cambium_resolve_device_type", lambda value: "CNEP3K")

    r = client.post(
        "/api/cambium/run",
        json={
            "ips": ["10.20.30.40"],
            "device_type": "CNEP3K",
            "update_version": "5.10.4",
            "password": "secret",
            "username": "tester",
            "requested_by": "frontend-user",
        },
    )
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    deadline = time.time() + 3
    final_status = None
    while time.time() < deadline:
        status_resp = client.get(f"/api/cambium/status/{task_id}")
        assert status_resp.status_code == 200
        final_status = status_resp.json()
        if final_status["status"] == "completed":
            break
        time.sleep(0.05)

    assert final_status is not None
    assert final_status["status"] == "completed"
    assert final_status["username"] == "frontend-user"
    assert final_status["results"][0]["status"] == "success"
    assert final_status["results"][0]["selected_image"] == "ePMP-AC-v5.10.4.img"
    assert captured == {"username": "tester", "password": "secret"}

    queue_body = client.get("/api/cambium/queue").json()
    assert queue_body["radios"][0]["status"] == "success"
    assert queue_body["radios"][0]["targetVersion"] == "5.10.4"
    assert queue_body["radios"][0]["username"] == "frontend-user"
