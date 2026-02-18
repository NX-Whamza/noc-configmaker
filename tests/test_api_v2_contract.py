import hashlib
import hmac
import importlib
import json
import sys
import time
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load_api_v2(monkeypatch, *, require_signature="true", require_idempotency="true"):
    repo_root = Path(__file__).resolve().parents[1]
    vm_dep = repo_root / "vm_deployment"
    for p in (str(repo_root), str(vm_dep)):
        if p not in sys.path:
            sys.path.insert(0, p)

    monkeypatch.setenv("NOC_API_KEYS_JSON", '{"test-key":["admin"]}')
    monkeypatch.setenv("NOC_API_SIGNING_KEYS_JSON", '{"sig-1":"secret123"}')
    monkeypatch.setenv("NOC_API_V2_REQUIRE_SIGNATURE", require_signature)
    monkeypatch.setenv("NOC_API_V2_REQUIRE_IDEMPOTENCY", require_idempotency)
    monkeypatch.setenv("NOC_API_V2_SIGNATURE_SKEW_SECONDS", "300")
    monkeypatch.setenv("NOC_API_V2_NONCE_TTL_SECONDS", "900")

    module_name = "vm_deployment.api_v2"
    if module_name in sys.modules:
        api_v2 = importlib.reload(sys.modules[module_name])
    else:
        api_v2 = importlib.import_module(module_name)

    app = FastAPI()
    app.include_router(api_v2.router)
    return api_v2, TestClient(app)


def _sign(method: str, path: str, body: str, *, secret: str = "secret123", key_id: str = "sig-1", api_key: str = "test-key", idem: str | None = None):
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    canonical = "\n".join([method.upper(), path, ts, nonce, body_hash])
    sig = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "X-API-Key": api_key,
        "X-Key-Id": key_id,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": sig,
        "Content-Type": "application/json",
    }
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def test_missing_api_key_returns_401(monkeypatch):
    _, client = _load_api_v2(monkeypatch, require_signature="false")
    r = client.get("/api/v2/omni/whoami")
    assert r.status_code == 401
    assert r.json()["detail"] == "Missing API key"


def test_signature_required_missing_signature_headers_returns_401(monkeypatch):
    _, client = _load_api_v2(monkeypatch, require_signature="true")
    r = client.get("/api/v2/omni/whoami", headers={"X-API-Key": "test-key"})
    assert r.status_code == 401
    assert "Missing signature headers" in r.json()["detail"]


def test_api_key_only_mode_works_when_signature_disabled(monkeypatch):
    _, client = _load_api_v2(monkeypatch, require_signature="false")
    r = client.get("/api/v2/omni/whoami", headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["api_key"] == "test-key"


def test_submit_requires_idempotency_key_when_enabled(monkeypatch):
    _, client = _load_api_v2(monkeypatch, require_signature="false", require_idempotency="true")
    payload = {"action": "health.get", "payload": {}}
    r = client.post("/api/v2/omni/jobs", headers={"X-API-Key": "test-key"}, json=payload)
    assert r.status_code == 400
    assert r.json()["detail"] == "Missing Idempotency-Key"


def test_submit_job_and_poll_detail_events_with_hmac(monkeypatch):
    _, client = _load_api_v2(monkeypatch, require_signature="true", require_idempotency="true")

    path_submit = "/api/v2/omni/jobs"
    submit_body = json.dumps({"action": "health.get", "payload": {}}, separators=(",", ":"))
    headers_submit = _sign("POST", path_submit, submit_body, idem="idem-1")
    r_submit = client.post(path_submit, headers=headers_submit, data=submit_body)
    assert r_submit.status_code == 202

    submit_json = r_submit.json()
    assert submit_json["status"] == "accepted"
    job_id = submit_json["data"]["job_id"]
    assert job_id

    path_job = f"/api/v2/omni/jobs/{job_id}"
    headers_job = _sign("GET", path_job, "")
    r_job = client.get(path_job, headers=headers_job)
    assert r_job.status_code == 200
    job_data = r_job.json()["data"]
    assert job_data["job_id"] == job_id
    assert "status" in job_data
    assert "payload" in job_data

    path_events = f"/api/v2/omni/jobs/{job_id}/events"
    headers_events = _sign("GET", path_events, "")
    r_events = client.get(path_events, headers=headers_events)
    assert r_events.status_code == 200
    events_data = r_events.json()["data"]
    assert events_data["job_id"] == job_id
    assert isinstance(events_data["events"], list)
    if events_data["events"]:
        evt = events_data["events"][0]
        assert set(evt.keys()) == {"ts", "level", "message"}
