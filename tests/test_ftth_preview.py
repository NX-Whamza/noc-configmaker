#!/usr/bin/env python3
"""Tests for FTTH preview API endpoint."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

os.environ["NOC_CONFIGMAKER_TESTS"] = "1"

import api_server  # noqa: WPS433

app = api_server.app
app.config["TESTING"] = True
client = app.test_client()


def test_preview_ftth_bng_basic():
    payload = {
        "loopback_ip": "10.13.100.5/32",
        "cpe_cidr": "192.0.2.0/22",
        "cgnat_cidr": "100.64.0.0/22",
        "olt_cidr": "198.51.100.8/29",
    }

    r = client.post("/api/preview-ftth-bng", data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("success") is True
    p = data.get("preview") or {}
    assert "loopback" in p
    assert "olt" in p and "network" in p["olt"]
    assert "cpe" in p and "network" in p["cpe"]
    assert "cgnat" in p and "network" in p["cgnat"]


def test_generate_ftth_fiber_customer_with_compliance():
    payload = {
        "routerboard": "ccr2004",
        "routeros": "7.19.4",
        "provider": "ATT",
        "port": "sfp-sfpplus1",
        "address": "10.42.10.2/30",
        "network": "10.42.10.0/30",
        "loopback_ip": "10.26.0.7/32",
        "vlan_mode": "tagged",
        "vlan_id": "300",
        "apply_compliance": True,
    }

    r = client.post("/api/generate-ftth-fiber-customer", data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("success") is True
    assert data.get("selected_port") == "sfp-sfpplus1"
    assert data.get("compliance_source") in {"gitlab", "bundled-local"}
    text = data.get("config", "")
    assert '/routing ospf area' in text
    assert 'comment="ATT VLAN 300"' in text
    assert 'add interface="sfp-sfpplus1" name="VLAN 300" vlan-id="300"' in text
    assert "142.147.112.3" in text


def test_generate_ftth_fiber_customer_requires_loopback_when_compliance_enabled():
    payload = {
        "routerboard": "ccr2004",
        "routeros": "7.19.4",
        "provider": "ATT",
        "address": "10.42.10.2/30",
        "network": "10.42.10.0/30",
        "vlan_mode": "none",
        "apply_compliance": True,
    }

    r = client.post("/api/generate-ftth-fiber-customer", data=json.dumps(payload), content_type="application/json")
    assert r.status_code == 400
    data = r.get_json() or {}
    assert "loopback_ip" in (data.get("error") or "")


if __name__ == "__main__":
    tests = [
        test_preview_ftth_bng_basic,
        test_generate_ftth_fiber_customer_with_compliance,
        test_generate_ftth_fiber_customer_requires_loopback_when_compliance_enabled,
    ]
    ok = True
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            ok = False
    raise SystemExit(0 if ok else 1)
