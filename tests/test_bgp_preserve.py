#!/usr/bin/env python3
"""Tests to ensure BGP connections and filters are preserved in strict-preserve mode."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

os.environ["NOC_CONFIGMAKER_TESTS"] = "1"
os.environ["AI_PROVIDER"] = "ollama"
os.environ["OLLAMA_API_URL"] = "http://127.0.0.1:59999"

import api_server  # noqa: WPS433

app = api_server.app
app.config["TESTING"] = True
client = app.test_client()


def test_bgp_connection_and_filters_preserved():
    src = (
        "/routing bgp connection\n"
        "add as=65001 remote.address=203.0.113.2 remote.as=65002 tcp-md5-key=SECRET templates=core\n"
        "/routing filter rule\n"
        "add chain=bgr-a-bgp-in-filter action=accept comment=TEST\n"
    )

    r = client.post(
        "/api/translate-config",
        data=json.dumps({"source_config": src, "target_device": "ccr2216", "target_version": "7.19.4", "strict_preserve": True}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("success") is True
    translated = data.get("translated_config") or ""

    assert "/routing bgp connection" in translated
    assert "tcp-md5-key=SECRET" in translated
    assert "/routing filter rule" in translated and "chain=bgr-a-bgp-in-filter" in translated


if __name__ == "__main__":
    tests = [test_bgp_connection_and_filters_preserved]
    ok = True
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            ok = False
    raise SystemExit(0 if ok else 1)
