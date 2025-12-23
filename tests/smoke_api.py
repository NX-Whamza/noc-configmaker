#!/usr/bin/env python3
"""
Minimal smoke tests for NOC Config Maker backend.

Run:
  python tests/smoke_api.py

This uses Flask's test client (no network, no docker).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _fail(msg: str) -> None:
    raise SystemExit(f"[FAIL] {msg}")


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        _fail(msg)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    # Force Ollama to be "unavailable" so we can validate non-AI fallbacks deterministically.
    os.environ["AI_PROVIDER"] = "ollama"
    os.environ["OLLAMA_API_URL"] = "http://127.0.0.1:59999"

    import api_server  # noqa: WPS433 - repo-local import (shim -> vm_deployment)

    app = api_server.app
    app.config["TESTING"] = True

    client = app.test_client()

    # Health
    r = client.get("/api/health")
    _assert(r.status_code == 200, f"/api/health expected 200, got {r.status_code}")
    health = r.get_json() or {}
    _assert(health.get("status") == "online", f"/api/health status=online, got {health!r}")

    # App-config
    r = client.get("/api/app-config")
    _assert(r.status_code == 200, f"/api/app-config expected 200, got {r.status_code}")
    cfg = r.get_json() or {}
    _assert("bng_peers" in cfg, f"/api/app-config missing bng_peers: {cfg!r}")

    # Enterprise generator: ensure no SMTP remnants
    payload = {
        "device": "RB5009",
        "target_version": "7.19.4",
        "public_cidr": "67.219.124.128/29",
        "bh_cidr": "10.1.248.200/29",
        "loopback_ip": "10.13.0.84/32",
        "uplink_interface": "sfp-sfpplus1",
        "public_port": "ether7",
        "nat_port": "ether8",
        "snmp_community": "TEST",
        "identity": "RTR-RB5009.TEST",
        "uplink_comment": "TX-DELEON-NO-1",
    }
    r = client.post(
        "/api/gen-enterprise-non-mpls",
        data=json.dumps(payload),
        content_type="application/json",
    )
    _assert(r.status_code == 200, f"/api/gen-enterprise-non-mpls expected 200, got {r.status_code}")
    data = r.get_json() or {}
    _assert(data.get("success") is True, f"/api/gen-enterprise-non-mpls success=true, got {data!r}")
    generated = data.get("config") or ""
    _assert("SMTP" not in generated, "Enterprise config still contains SMTP rules")

    # Nokia migration: must return usable output even when AI is unavailable.
    source_config = (
        "/ip address\n"
        "add address=192.168.88.1/24 interface=ether1 comment=LAN\n"
        "add address=10.1.0.245/32 interface=loop0 comment=loop\n"
        "/ip route\n"
        "add dst-address=0.0.0.0/0 gateway=192.168.88.254\n"
        "/system identity\n"
        "set name=RTR-MT2216-TEST\n"
    )
    r = client.post(
        "/api/migrate-mikrotik-to-nokia",
        data=json.dumps({"source_config": source_config, "preserve_ips": True}),
        content_type="application/json",
    )
    _assert(r.status_code == 200, f"/api/migrate-mikrotik-to-nokia expected 200, got {r.status_code}")
    data = r.get_json() or {}
    _assert(data.get("success") is True, f"/api/migrate-mikrotik-to-nokia success=true, got {data!r}")
    nokia = data.get("nokia_config") or ""
    _assert("/configure router interface" in nokia, "Nokia migration output missing router interface config")

    # Translate: CCR2216 -> CCR2004 interface mapping must happen.
    export = (
        "# 2025-12-22 12:34:47 by RouterOS 7.19.4.2\n"
        "# model =CCR2216-1G-12XS-2XQ\n"
        "\n"
        "/interface ethernet\n"
        "set [ find default-name=qsfp28-1-1 ] disabled=yes\n"
        "set [ find default-name=sfp28-3 ] comment=TEST\n"
        "\n"
        "/ip address\n"
        "add address=10.42.2.57/29 interface=sfp28-3 network=10.42.2.56\n"
        "\n"
        "/system identity\n"
        "set name=RTR-MT2216-AR1.TEST\n"
    )
    r = client.post(
        "/api/translate-config",
        data=json.dumps({"source_config": export, "target_device": "ccr2004", "target_version": "7.19.4"}),
        content_type="application/json",
    )
    _assert(r.status_code == 200, f"/api/translate-config expected 200, got {r.status_code}")
    data = r.get_json() or {}
    _assert(data.get("success") is True, f"/api/translate-config success=true, got {data!r}")
    translated = data.get("translated_config") or ""
    _assert("qsfp28" not in translated, "Translated config still contains qsfp ports for CCR2004 target")
    _assert("sfp-sfpplus3" in translated, "Translated config did not map sfp28-3 -> sfp-sfpplus3")
    model = re.search(r"(?m)^#\s*model\s*=(.*)$", translated)
    _assert(model and "CCR2004" in model.group(1), "Translated config header model not updated to CCR2004")

    print("[OK] Smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
