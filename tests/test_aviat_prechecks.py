#!/usr/bin/env python3
"""Unit tests for Aviat precheck parsing used by queue status badges."""

from __future__ import annotations

import os
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from vm_deployment.aviat_config import check_license_bundles, check_subnet_mask  # noqa: E402


class _FakeClient:
    def __init__(self, output: str):
        self.output = output
        self.ip = "10.0.0.1"

    def send_command(self, _command: str):
        return self.output


def test_subnet_parser_accepts_cidr_29_output():
    os.environ["AVIAT_EXPECTED_MASK"] = "255.255.255.248"
    client = _FakeClient("IPv4 Addresses: 10.249.73.67/29\nEnabled: yes\n")
    ok, detail = check_subnet_mask(client)
    assert ok is True
    assert detail == "255.255.255.248"


def test_license_parser_accepts_paid_bundles_even_with_trial_present():
    output = "\n".join(
        [
            "Installed Bundles",
            "Trial",
            "WZF-CAP",
            "WZF-MLHC",
            "WZL-CE1",
            "WZL-ENTERPRISE2",
        ]
    )
    client = _FakeClient(output)
    ok, detail = check_license_bundles(client)
    assert ok is True
    assert "WZF-CAP" in detail
    assert "WZL-CE1" in detail


def test_license_parser_trial_only_is_not_licensed():
    client = _FakeClient("Installed Bundles\nTrial\n")
    ok, detail = check_license_bundles(client)
    assert ok is False
    assert detail == "trial"

