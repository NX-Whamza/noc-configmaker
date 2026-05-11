"""
SiteTracker client — fetches all Nextlink sites from the Codex Catalog MCP HTTP API.

Required env vars (add to .env):
  CODEX_CATALOG_URL  – API base URL (default: https://codex-catalog.nxlink.com/mcp)
  CODEX_CATALOG_AUTH – Full Authorization header value, e.g. "Basic <base64>"
"""
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

import requests

log = logging.getLogger(__name__)

_CODEX_URL = os.environ.get("CODEX_CATALOG_URL", "https://codex-catalog.nxlink.com/mcp")
_CODEX_AUTH = os.environ.get("CODEX_CATALOG_AUTH", "")

# All 50 US states + DC + territories + Nextlink special codes (TB, TBD).
# API calls for prefixes with 0 results return immediately — no overhead for unused codes.
_ALL_PREFIXES = [
    # Contiguous US + DC
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    # DC + territories
    "DC", "PR", "GU", "VI", "AS", "MP",
    # Nextlink special/placeholder codes seen in existing cache
    "TB", "TBD",
]

# Second-level characters used for sub-pagination when a prefix hits the 250-row cap
_SUB_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _call(name_contains: Optional[str] = None, limit: int = 250) -> list:
    """One JSON-RPC 2.0 call to sitetracker__list_sites_snapshot. Returns raw site list."""
    args: dict = {"limit": limit}
    if name_contains is not None:
        args["name_contains"] = name_contains

    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {"name": "sitetracker__list_sites_snapshot", "arguments": args},
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": _CODEX_AUTH,
    }

    for attempt in range(3):
        try:
            r = requests.post(_CODEX_URL, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            result = data.get("result", {})
            if result.get("isError"):
                raise RuntimeError(f"Tool error: {result}")
            text = result["content"][0]["text"]
            return json.loads(text).get("sites", [])
        except requests.RequestException as exc:
            if attempt == 2:
                raise
            log.warning("Codex API attempt %d failed: %s — retrying", attempt + 1, exc)
            time.sleep(1 + attempt)
    return []


def _normalize(s: dict) -> dict:
    """Map SiteTracker response fields to site_cache.json schema (backward-compatible)."""
    return {
        "name": s.get("name", ""),
        "lat": s.get("lat"),
        "lon": s.get("lon"),
        "status": s.get("site_status", ""),
        "city": s.get("city", ""),
        "state": s.get("state", ""),
        "site_id": s.get("site_id", ""),
        "pop_id": s.get("pop_id"),
        "record_type": s.get("record_type", ""),
        "network_type": s.get("network_type"),
        "county": s.get("county", ""),
        "zip": s.get("zip", ""),
    }


def fetch_all_sites() -> list:
    """
    Return all Nextlink SiteTracker sites, paginating around the 250-row API cap.

    Strategy:
      1. For each state/prefix code, query name_contains="{PREFIX}-".
      2. If the result hits 250 (cap), automatically sub-paginate:
         query name_contains="{PREFIX}-{A}", "{PREFIX}-{B}", ..., "{PREFIX}-{9}".
      3. Catch non-prefixed legacy sites (no XX- pattern) via an unfiltered call.

    All results are deduplicated by site_id.
    """
    seen: dict = {}  # site_id → normalized site dict

    def _add(raw: list) -> None:
        for s in raw:
            sid = s.get("site_id", "")
            if sid and sid not in seen:
                seen[sid] = _normalize(s)

    for prefix in _ALL_PREFIXES:
        query = f"{prefix}-"
        results = _call(name_contains=query)

        if not results:
            continue  # no sites for this state, skip

        _add(results)

        if len(results) >= 250:
            # Hit the cap — auto sub-paginate by the next character in the site name
            log.info("State '%s' hit 250-row cap, running letter sub-queries", prefix)
            for ch in _SUB_CHARS:
                sub = _call(name_contains=f"{query}{ch}")
                _add(sub)
                if len(sub) >= 250:
                    log.warning(
                        "Sub-query '%s%s' still hit 250-row cap — sites may be missing",
                        query, ch,
                    )

    # Catch non-state-prefixed sites (legacy names like MOUNTAINLAKE, 1708, etc.)
    _add(_call(name_contains=None))

    log.info("Fetched %d unique sites from SiteTracker", len(seen))
    return list(seen.values())


def build_cache_payload(sites: list) -> dict:
    """Wrap site list into site_cache.json format with metadata."""
    state_counts = dict(Counter(s.get("state", "?") for s in sites))
    return {
        "sites": sites,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(sites),
            "states": state_counts,
            "sources": ["SiteTracker (via Codex Catalog HTTP API)"],
            "note": "Auto sub-paginates any state prefix that hits the 250-row API cap",
        },
    }
