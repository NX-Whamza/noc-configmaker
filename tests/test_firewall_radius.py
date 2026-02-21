#!/usr/bin/env python3
"""Tests to ensure firewall/mangle and radius preservation in strict-preserve mode."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

os.environ["NOC_CONFIGMAKER_TESTS"] = "1"
os.environ["AI_PROVIDER"] = "none"

import api_server  # noqa: WPS433

app = api_server.app
app.config["TESTING"] = True
client = app.test_client()


def test_firewall_mangle_and_radius_preserved():
    src = (
        "/ip firewall mangle\n"
        "add action=return chain=CONN-MARK comment=\"BREAK CONN-MARK\"\n"
        "/radius\n"
        "add address=142.147.112.18 secret=RADIUS_SECRET service=login\n"
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

    assert "/ip firewall mangle" in translated and "action=return" in translated and "CONN-MARK" in translated
    assert "/radius" in translated and "RADIUS_SECRET" in translated


if __name__ == "__main__":
    tests = [test_firewall_mangle_and_radius_preserved]
    ok = True
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            ok = False
    raise SystemExit(0 if ok else 1)
