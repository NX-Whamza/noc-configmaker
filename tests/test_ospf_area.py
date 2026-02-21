#!/usr/bin/env python3
"""Tests to ensure OSPF area and interface-template preservation/insertion."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

# Test-mode guard
os.environ["NOC_CONFIGMAKER_TESTS"] = "1"
os.environ["AI_PROVIDER"] = "none"

import api_server  # noqa: WPS433

app = api_server.app
app.config["TESTING"] = True
client = app.test_client()


def test_empty_ospf_area_gets_inserted():
    src = (
        "/routing ospf instance\n"
        "add disabled=no name=default-v2 router-id=10.4.1.161\n"
        "/routing ospf area\n"
        # area section intentionally left without add lines
        "\n"
        "/interface ethernet\n"
        "set [ find default-name=sfp-sfpplus7 ] comment=TEST l2mtu=9212 mtu=9198\n"
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

    # The OSPF area add line should exist after translation
    assert re.search(r"(?m)^/routing ospf area\s*$", translated), "OSPF area header missing"
    assert re.search(r"(?m)^add\s+disabled=no\s+instance=default-v2\s+name=backbone-v2", translated), "Missing inserted OSPF area add line"


if __name__ == "__main__":
    tests = [test_empty_ospf_area_gets_inserted]
    ok = True
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            ok = False
    raise SystemExit(0 if ok else 1)
