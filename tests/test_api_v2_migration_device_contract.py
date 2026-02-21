import importlib
import os
import sys
import time
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_api_v2_client(monkeypatch: object):
    repo_root = Path(__file__).resolve().parents[1]
    vm_dep = repo_root / "vm_deployment"
    for p in (str(repo_root), str(vm_dep)):
        if p not in sys.path:
            sys.path.insert(0, p)

    monkeypatch.setenv("NOC_API_KEYS_JSON", '{"test-key":["admin"]}')
    monkeypatch.setenv("NOC_API_V2_REQUIRE_SIGNATURE", "false")
    monkeypatch.setenv("NOC_API_V2_REQUIRE_IDEMPOTENCY", "true")
    monkeypatch.setenv("NOC_API_V2_JOB_WORKERS", "2")
    monkeypatch.setenv("AI_PROVIDER", "none")

    module_name = "vm_deployment.api_v2"
    if module_name in sys.modules:
        api_v2 = importlib.reload(sys.modules[module_name])
    else:
        api_v2 = importlib.import_module(module_name)

    app = FastAPI()
    app.include_router(api_v2.router)
    return api_v2, TestClient(app)


def _submit_job(client: TestClient, action: str, payload: dict, idem_suffix: str) -> str:
    r = client.post(
        "/api/v2/omni/jobs",
        headers={"X-API-Key": "test-key", "Idempotency-Key": f"idem-{idem_suffix}-{uuid.uuid4().hex}"},
        json={"action": action, "payload": payload},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "accepted"
    return body["data"]["job_id"]


def _wait_job_done(client: TestClient, job_id: str, timeout_s: int = 30) -> dict:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        r = client.get(f"/api/v2/omni/jobs/{job_id}", headers={"X-API-Key": "test-key"})
        assert r.status_code == 200, r.text
        last = r.json()["data"]
        if last["status"] in {"success", "error", "cancelled"}:
            return last
        time.sleep(0.25)
    raise AssertionError(f"Job {job_id} did not finish in {timeout_s}s. Last={last}")


def test_v2_migration_and_new_device_actions(monkeypatch: object) -> None:
    api_v2, client = _load_api_v2_client(monkeypatch)

    class _FakeResp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)
            self.headers = {"content-type": "application/json"}

        def json(self):
            return self._payload

    def _fake_request(method: str, url: str, timeout: int = 0, json=None, **kwargs):
        if url.endswith("/api/migrate-mikrotik-to-nokia"):
            return _FakeResp(200, {"success": True, "nokia_config": "/configure router interface"})
        if url.endswith("/api/migrate-config"):
            return _FakeResp(200, {"success": True, "target_device": "CCR2004-1G-12S+2XS"})
        if url.endswith("/api/generate-nokia7250"):
            return _FakeResp(
                200,
                {
                    "success": True,
                    "config": (
                        "/configure system name \"NOKIA-7250-TEST-1\"\n"
                        "/configure router interface \"system\" address 10.42.13.4/32"
                    ),
                },
            )
        return _FakeResp(404, {"error": f"unexpected url: {url}"})

    monkeypatch.setattr(api_v2.requests, "request", _fake_request)
    monkeypatch.setattr(api_v2.requests, "get", lambda url, **kwargs: _fake_request("GET", url, **kwargs))
    monkeypatch.setattr(api_v2.requests, "post", lambda url, **kwargs: _fake_request("POST", url, **kwargs))
    monkeypatch.setattr(api_v2.requests, "put", lambda url, **kwargs: _fake_request("PUT", url, **kwargs))
    monkeypatch.setattr(api_v2.requests, "patch", lambda url, **kwargs: _fake_request("PATCH", url, **kwargs))
    monkeypatch.setattr(api_v2.requests, "delete", lambda url, **kwargs: _fake_request("DELETE", url, **kwargs))

    migration_source = (
        "/ip address\n"
        "add address=192.168.88.1/24 interface=ether1 comment=LAN\n"
        "add address=10.1.0.245/32 interface=loop0 comment=loop\n"
        "/ip route\n"
        "add dst-address=0.0.0.0/0 gateway=192.168.88.254\n"
        "/system identity\n"
        "set name=RTR-MT2216-TEST\n"
    )
    job_mk_to_nokia = _submit_job(
        client,
        "migration.mikrotik_to_nokia",
        {"source_config": migration_source, "preserve_ips": True},
        "mk2nokia",
    )
    done_mk_to_nokia = _wait_job_done(client, job_mk_to_nokia)
    assert done_mk_to_nokia["status"] == "success", done_mk_to_nokia
    result = done_mk_to_nokia["result"] or {}
    assert result.get("ok") is True
    response = result.get("response") or {}
    assert response.get("success") is True
    assert "/configure router interface" in (response.get("nokia_config") or "")

    job_device_migration = _submit_job(
        client,
        "migration.config",
        {
            "config": "# model =CCR2216-1G-12XS-2XQ\n/interface ethernet\nset [ find default-name=sfp28-3 ] comment=BH",
            "target_device": "CCR2004-1G-12S+2XS",
            "target_version": "7",
        },
        "device-migration",
    )
    done_device_migration = _wait_job_done(client, job_device_migration)
    assert done_device_migration["status"] == "success", done_device_migration
    response = (done_device_migration["result"] or {}).get("response") or {}
    assert response.get("success") is True
    assert response.get("target_device") == "CCR2004-1G-12S+2XS"

    job_new_device = _submit_job(
        client,
        "nokia.generate_7250",
        {
            "system_name": "NOKIA-7250-TEST-1",
            "system_ip": "10.42.13.4/32",
            "location": "Lab",
            "port1_desc": "Switch",
            "backhauls": [{"name": "BH-1", "ip": "10.0.0.1/30"}],
        },
        "new-device",
    )
    done_new_device = _wait_job_done(client, job_new_device)
    assert done_new_device["status"] == "success", done_new_device
    response = (done_new_device["result"] or {}).get("response") or {}
    assert response.get("success") is True
    cfg = response.get("config") or ""
    assert "/configure system name" in cfg
    assert "/configure router interface \"system\" address 10.42.13.4/32" in cfg
