#!/usr/bin/env python3
"""Tests for strict-preserve ethernet/L3 port mapping correctness."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

# Avoid heavy timezone loading during tests
os.environ["NOC_CONFIGMAKER_TESTS"] = "1"
# Force Ollama to be unavailable
os.environ["AI_PROVIDER"] = "ollama"
os.environ["OLLAMA_API_URL"] = "http://127.0.0.1:59999"

import api_server  # noqa: WPS433 - repo-local import (shim -> vm_deployment)

app = api_server.app
app.config["TESTING"] = True
client = app.test_client()


def test_ethernet_set_and_ip_address_preserved_and_mapped():
    src = (
        "# model =SOME-OLD-DEVICE-1\n"
        "/interface ethernet\n"
        "set [ find default-name=ether2 ] auto-negotiation=no comment=UPLINK l2mtu=9000 mtu=9000 speed=1G\n"
        "\n"
        "/ip address\n"
        "add address=203.0.113.10/29 interface=ether2 comment=UPLINK\n"
        "/system identity\n"
        "set name=RTR-OLD-2216-EXAMPLE\n"
    )

    r = client.post(
        "/api/translate-config",
        data=json.dumps({
            "source_config": src,
            "target_device": "ccr2004",
            "target_version": "7.19.4",
            "strict_preserve": True,
        }),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("success") is True
    translated = data.get("translated_config") or ""

    # The interface line should have been mapped to a target port and retain attributes
    assert re.search(r"\bset\s+\[\s*find\s+default-name=[A-Za-z0-9._-]+\b[^\n]*\bcomment=UPLINK\b", translated, re.IGNORECASE), "Mapped set line with comment UPLINK not preserved"
    assert "l2mtu=9000" in translated or "mtu=9000" in translated, "MTU/L2MTU attributes lost during mapping"
    # The IP address should reference the mapped interface
    assert re.search(r"add\s+address=203\.0\.113\.10/29\s+interface=\S+\s+comment=UPLINK", translated), "IP address add line lost or not updated to mapped interface"


if __name__ == "__main__":
    tests = [test_ethernet_set_and_ip_address_preserved_and_mapped]
    ok = True
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            ok = False
    raise SystemExit(0 if ok else 1)
