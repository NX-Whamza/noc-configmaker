from __future__ import annotations

import os
import re
from pathlib import Path

try:
    from nextlink_compliance_reference import get_all_compliance_blocks
except Exception:  # pragma: no cover - import path fallback
    from vm_deployment.nextlink_compliance_reference import get_all_compliance_blocks

COMPLIANCE_MARKER = "# ENGINEERING-COMPLIANCE-APPLIED"
TEMPLATE_TOKEN = "{{NEXTLINK_RFC_BLOCKS}}"

COMPLIANCE_ORDER = [
    "dns",
    "firewall_address_lists",
    "firewall_filter_input",
    "firewall_raw",
    "firewall_forward",
    "firewall_nat",
    "firewall_mangle",
    "clock_ntp",
    "snmp",
    "system_settings",
    "vpls_edge",
    "logging",
    "user_aaa",
    "user_groups",
    "dhcp_options",
    "radius",
    "ldp_filters",
]

SAFE_DEDUPE_PREFIXES = (
    "/ip dns set servers=",
    "/system ntp client set enabled=",
    "/system clock set time-zone-name=",
    "/ip proxy set enabled=",
    "/ip firewall service-port set sip disabled=",
    "/system routerboard settings set auto-upgrade=",
)


def _default_template_path() -> Path:
    return Path(__file__).resolve().parent / "config_policies" / "compliance" / "mikrotik_engineering_compliance.rsc"


def _resolve_template_path() -> Path:
    configured = os.getenv("ENGINEERING_COMPLIANCE_FILE")
    if configured:
        p = Path(configured)
        if p.exists():
            return p
    return _default_template_path()


def extract_loopback_ip(config_text: str) -> str | None:
    patterns = [
        r"/ip\s+address\s+add\s+address=(\d+\.\d+\.\d+\.\d+)(?:/\d+)?[^\n]*\binterface=loop0\b",
        r"/ip\s+address\s+add\s+address=(\d+\.\d+\.\d+\.\d+)/(?:\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, config_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _render_rfc_blocks(loopback_ip: str) -> str:
    blocks = get_all_compliance_blocks(loopback_ip)
    lines: list[str] = []
    for key in COMPLIANCE_ORDER:
        value = blocks.get(key)
        if not value:
            continue
        lines.append(f"# {key.upper().replace('_', ' ')}")
        lines.append(value.strip())
        lines.append("")
    return "\n".join(lines).strip()


def load_compliance_text(loopback_ip: str) -> str:
    template_path = _resolve_template_path()
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = (
            "# VARIABLES\n"
            f":global LoopIP \"{loopback_ip}\"\n\n"
            + TEMPLATE_TOKEN
            + "\n\n# SYS NOTE\n"
            "/system note set note=\"COMPLIANCE SCRIPT LAST RUN ON $[/system clock get date] $[/system clock get time]\"\n"
        )

    rendered = template.replace("__LOOP_IP__", loopback_ip)
    if TEMPLATE_TOKEN in rendered:
        rendered = rendered.replace(TEMPLATE_TOKEN, _render_rfc_blocks(loopback_ip))
    return rendered.strip()


def apply_engineering_compliance(config_text: str, loopback_ip: str | None = None) -> str:
    def _dedupe_safe_single_line_commands(text: str) -> str:
        seen: set[str] = set()
        out: list[str] = []
        for line in text.splitlines():
            normalized = line.strip()
            lower = normalized.lower()
            if normalized and any(lower.startswith(prefix) for prefix in SAFE_DEDUPE_PREFIXES):
                if normalized in seen:
                    continue
                seen.add(normalized)
            out.append(line)
        return "\n".join(out).rstrip() + "\n"

    if COMPLIANCE_MARKER in config_text:
        return _dedupe_safe_single_line_commands(config_text)

    loop_ip = loopback_ip or extract_loopback_ip(config_text) or "10.0.0.1"
    compliance_text = load_compliance_text(loop_ip)

    merged = (
        config_text.rstrip()
        + "\n\n"
        + COMPLIANCE_MARKER
        + "\n# Compliance baseline loaded from backend policy file\n"
        + compliance_text
        + "\n"
    )
    return _dedupe_safe_single_line_commands(merged)
