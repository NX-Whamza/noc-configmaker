from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from engineering_compliance import apply_engineering_compliance, load_compliance_text
from mt_config_gen.mt_bng2 import BNG2_PORT_POLICY
from mt_config_gen.mt_tower import PORT_POLICY


def _base_config_path() -> Path:
    env = os.getenv("BASE_CONFIG_PATH") or os.getenv("NEXTLINK_BASE_CONFIG_PATH")
    if env:
        p = Path(env)
        if (p / "Router").is_dir():
            return p
    return Path(__file__).resolve().parent / "base_configs"


def _dns_servers() -> str:
    primary = os.getenv("NEXTLINK_DNS_PRIMARY", "142.147.112.3").strip()
    secondary = os.getenv("NEXTLINK_DNS_SECONDARY", "142.147.112.19").strip()
    return f"{primary},{secondary}"


def get_defaults(config_type: str | None = None) -> Dict[str, Any]:
    common = {
        "routeros_min_version": "7.19.4",
        "dns_servers": _dns_servers(),
        "asn": "26077",
        "peer_1_name": os.getenv("NEXTLINK_BGP_PEER1_NAME", "CR7"),
        "peer_1_address": os.getenv("NEXTLINK_BGP_PEER1_ADDRESS", "10.2.0.107/32"),
        "peer_2_name": os.getenv("NEXTLINK_BGP_PEER2_NAME", "CR8"),
        "peer_2_address": os.getenv("NEXTLINK_BGP_PEER2_ADDRESS", "10.2.0.108/32"),
        "apply_compliance": True,
    }
    if not config_type:
        return common
    if config_type == "tower":
        return {
            **common,
            "state_code": os.getenv("NEXTLINK_DEFAULT_STATE_CODE", "TX"),
        }
    if config_type == "bng2":
        return {
            **common,
            "state_code": os.getenv("NEXTLINK_DEFAULT_STATE_CODE", "KS"),
            "ospf_area": os.getenv("NEXTLINK_DEFAULT_OSPF_AREA", "248"),
            "bng_1_ip": os.getenv("NEXTLINK_BNG1_IP", "10.249.0.200"),
            "bng_2_ip": os.getenv("NEXTLINK_BNG2_IP", "10.249.0.201"),
            "vlan_1000_cisco": os.getenv("NEXTLINK_VPLS_1000_ID", "1248"),
            "vlan_2000_cisco": os.getenv("NEXTLINK_VPLS_2000_ID", "2248"),
            "vlan_3000_cisco": os.getenv("NEXTLINK_VPLS_3000_ID", "3248"),
            "vlan_4000_cisco": os.getenv("NEXTLINK_VPLS_4000_ID", "4248"),
            "mpls_mtu": os.getenv("NEXTLINK_MPLS_MTU", "9000"),
            "vpls_l2_mtu": os.getenv("NEXTLINK_VPLS_L2_MTU", "1580"),
        }
    return common


def merge_defaults(config_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(payload or {})
    defaults = get_defaults(config_type)
    for key, value in defaults.items():
        merged.setdefault(key, value)
    return merged


def get_templates(config_type: str | None = None) -> Dict[str, Any]:
    base = _base_config_path()
    roots: Dict[str, Path] = {
        "tower": base / "Router" / "Tower" / "config",
        "bng2": base / "Router" / "BNG2" / "config",
    }
    if config_type:
        root = roots.get(config_type)
        if not root or not root.is_dir():
            return {"config_type": config_type, "templates": []}
        return {
            "config_type": config_type,
            "templates": sorted([p.name for p in root.iterdir() if p.is_file()]),
        }
    out = {}
    for key, root in roots.items():
        out[key] = sorted([p.name for p in root.iterdir() if root.is_dir() and p.is_file()])
    return out


def get_device_profiles() -> Dict[str, Any]:
    return {
        "routeros_min_version": "7.19.4",
        "tower": PORT_POLICY,
        "bng2": BNG2_PORT_POLICY,
    }


def get_compliance(loopback_ip: str) -> str:
    return load_compliance_text(loopback_ip)


def apply_compliance(config_text: str, loopback_ip: str | None) -> str:
    return apply_engineering_compliance(config_text, loopback_ip)

