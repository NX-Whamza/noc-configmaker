from __future__ import annotations

import os
import re
from pathlib import Path

try:
    from nextlink_compliance_reference import get_all_compliance_blocks
except Exception:  # pragma: no cover - import path fallback
    from vm_deployment.nextlink_compliance_reference import get_all_compliance_blocks

# GitLab dynamic compliance loader (optional — falls back gracefully when unavailable)
try:
    from gitlab_compliance import get_loader as _get_gitlab_loader
    _HAS_GITLAB = True
except ImportError:
    try:
        from vm_deployment.gitlab_compliance import get_loader as _get_gitlab_loader
        _HAS_GITLAB = True
    except ImportError:
        _HAS_GITLAB = False
        _get_gitlab_loader = None  # type: ignore[assignment]

COMPLIANCE_MARKER = "# ENGINEERING-COMPLIANCE-APPLIED"
TEMPLATE_TOKEN = "{{NEXTLINK_RFC_BLOCKS}}"

COMPLIANCE_ORDER = [
    # Keys from both GitLab parser and hardcoded fallback.
    # GitLab parser may combine blocks under different key names;
    # missing keys are silently skipped so listing both is safe.
    "variables",            # GitLab: LoopIP / curDate / curTime variables
    "ip_services",          # GitLab: ip service disable
    "dns",                  # GitLab: combined dns + all firewall blocks
    "firewall_address_lists",  # hardcoded fallback
    "firewall_filter_input",   # hardcoded fallback
    "firewall_raw",            # hardcoded fallback
    "firewall_forward",        # hardcoded fallback
    "firewall_nat",            # hardcoded fallback
    "firewall_mangle",         # hardcoded fallback
    "sip_alg_off",          # GitLab: service-port sip disable
    "clock_ntp",
    "snmp",
    "auto_upgrade",         # GitLab: routerboard auto-upgrade
    "system_settings",      # hardcoded fallback
    "web_proxy_off",        # GitLab: ip proxy disable
    "vpls_edge",            # hardcoded fallback
    "vpls_edge_ports",      # GitLab: combined vpls_edge + logging/syslog
    "logging",              # hardcoded fallback
    "user_aaa",
    "user_groups",          # hardcoded fallback
    "user_profiles",        # GitLab: combined user groups
    "users",                # GitLab: explicit /user block
    "dhcp_options",
    "radius",               # GitLab: combined radius + LDP filters
    "ldp_filters",          # hardcoded fallback
    "scripts",              # GitLab: compliance script section
    "scheduler",            # GitLab: compliance scheduler section
    "watchdog_timer",       # GitLab: watchdog timer
    "sys_note",             # GitLab: system note
]

SAFE_DEDUPE_PREFIXES = (
    "/ip service set ",
    "/ip dns set servers=",
    "/system ntp client set enabled=",
    "/system clock set time-zone-name=",
    "/ip proxy set enabled=",
    "/ip firewall service-port set sip disabled=",
    "/system routerboard settings set auto-upgrade=",
    "/system note set note=",
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
    """
    Render RFC-09-10-25 compliance blocks in COMPLIANCE_ORDER sequence.

    Source priority:
      1. GitLab compliance repo (dynamic, TTL-cached) — if configured + reachable
      2. Hardcoded nextlink_compliance_reference module (always available)
    """
    blocks: dict | None = None

    if _HAS_GITLAB and _get_gitlab_loader is not None:
        try:
            loader = _get_gitlab_loader()
            blocks = loader.get_compliance_blocks_from_script(loopback_ip=loopback_ip)
        except Exception as _exc:
            print(f"[COMPLIANCE] GitLab loader error in _render_rfc_blocks: {_exc}")
            blocks = None

    if not blocks:
        # Fall back to hardcoded Python reference module
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
    """
    Load the full engineering compliance script for the given loopback IP.

    Template source priority:
      1. GitLab compliance repo RSC template (dynamic, TTL-cached)
      2. Local disk RSC template (ENGINEERING_COMPLIANCE_FILE or default path)
      3. Inline minimal default template

    Block rendering inside the template uses _render_rfc_blocks() which
    applies the same GitLab-first / hardcoded-fallback logic.
    """
    template: str | None = None

    # 1. Try GitLab RSC template
    if _HAS_GITLAB and _get_gitlab_loader is not None:
        try:
            template = _get_gitlab_loader().get_compliance_rsc_template()
        except Exception as _exc:
            print(f"[COMPLIANCE] GitLab RSC template fetch failed: {_exc}")
            template = None

    # 2. Fall back to local disk template
    if not template:
        template_path = _resolve_template_path()
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")

    # 3. Inline minimal default
    if not template:
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
    def _compliance_source_note() -> str:
        if _HAS_GITLAB and _get_gitlab_loader is not None:
            try:
                loader = _get_gitlab_loader()
                if loader.is_configured():
                    ref = os.getenv("GITLAB_COMPLIANCE_REF", "main")
                    path = os.getenv("GITLAB_COMPLIANCE_SCRIPT_PATH", "TX-ARv2.rsc")
                    return f"# compliance_source=gitlab ref={ref} path={path}"
            except Exception:
                pass
        return "# compliance_source=fallback(local/reference)"

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
        + _compliance_source_note()
        + "\n"
        + compliance_text
        + "\n"
    )
    return _dedupe_safe_single_line_commands(merged)
