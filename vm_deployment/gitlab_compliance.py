"""
vm_deployment/gitlab_compliance.py

Pull-on-demand GitLab compliance loader with TTL cache.

Fetches compliance rules and RouterOS script blocks from the
netforge/compliance GitLab repository on demand.  Results are cached
so repeat calls within the TTL window make zero network requests.
When GitLab is unreachable (no token, network down, etc.) every method
returns None and callers fall back to the hardcoded reference modules.

Required env vars
-----------------
GITLAB_COMPLIANCE_TOKEN      Personal access token with read_repository + read_api
GITLAB_COMPLIANCE_PROJECT_ID Numeric GitLab project ID (e.g. "75")

Optional env vars
-----------------
GITLAB_COMPLIANCE_HOST       defaults to "tested.nxlink.com"
GITLAB_COMPLIANCE_REF        git ref to read from, defaults to "main"
GITLAB_COMPLIANCE_TTL        cache TTL in seconds, defaults to 900 (15 min)
GITLAB_COMPLIANCE_SCRIPT_PATH defaults to "TX-ARv2.rsc"
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Module-level defaults (overridden via env vars at runtime)
# ---------------------------------------------------------------------------

_DEFAULT_HOST = "tested.nxlink.com"
_DEFAULT_REF  = "main"
_DEFAULT_TTL  = 900  # 15 minutes
_DEFAULT_SCRIPT_PATH = "TX-ARv2.rsc"
_DEFAULT_REPO_PATH = "netforge/compliance"


# ---------------------------------------------------------------------------
# Simple TTL cache  (no external dependencies)
# ---------------------------------------------------------------------------

class _TTLCache:
    """
    Minimal dict-backed TTL cache.
    Thread safety: CPython GIL makes individual dict reads/writes atomic;
    sufficient for low-frequency config-generation access patterns.
    """

    def __init__(self, ttl_seconds: int = 900) -> None:
        self._ttl        = ttl_seconds
        self._store:      Dict[str, Any]   = {}
        self._timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        ts = self._timestamps.get(key)
        if ts is None:
            return None
        if (time.monotonic() - ts) > self._ttl:
            self._store.pop(key, None)
            self._timestamps.pop(key, None)
            return None
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        self._store[key]      = value
        self._timestamps[key] = time.monotonic()

    def clear(self) -> None:
        self._store.clear()
        self._timestamps.clear()

    def age_seconds(self, key: str) -> Optional[float]:
        ts = self._timestamps.get(key)
        if ts is None:
            return None
        age = time.monotonic() - ts
        return None if age > self._ttl else round(age, 1)

    def info(self) -> dict:
        keys = list(self._store.keys())
        return {
            "cached_keys":  keys,
            "ages_seconds": {k: self.age_seconds(k) for k in keys},
            "ttl_seconds":  self._ttl,
        }


# ---------------------------------------------------------------------------
# GitLabComplianceLoader
# ---------------------------------------------------------------------------

class GitLabComplianceLoader:
    """
    Fetches compliance artifacts from a GitLab repository on demand.

    All public methods return None on failure so callers can fall back
    to the hardcoded Python compliance reference modules.
    """

    # ------------------------------------------------------------------ init

    def __init__(self) -> None:
        self._cache = _TTLCache(ttl_seconds=self._ttl())

    # ------------------------------------------------------------------ config helpers

    @staticmethod
    def _host() -> str:
        return os.getenv("GITLAB_COMPLIANCE_HOST", _DEFAULT_HOST).rstrip("/")

    @staticmethod
    def _token() -> Optional[str]:
        return os.getenv("GITLAB_COMPLIANCE_TOKEN") or None

    @staticmethod
    def _project_id() -> Optional[str]:
        return os.getenv("GITLAB_COMPLIANCE_PROJECT_ID") or None

    @staticmethod
    def _ref() -> str:
        return os.getenv("GITLAB_COMPLIANCE_REF", _DEFAULT_REF)

    @staticmethod
    def _ttl() -> int:
        try:
            return int(os.getenv("GITLAB_COMPLIANCE_TTL", str(_DEFAULT_TTL)))
        except (ValueError, TypeError):
            return _DEFAULT_TTL

    @staticmethod
    def _script_path() -> str:
        value = os.getenv("GITLAB_COMPLIANCE_SCRIPT_PATH", _DEFAULT_SCRIPT_PATH)
        value = (value or "").strip()
        if not value:
            value = _DEFAULT_SCRIPT_PATH
        return GitLabComplianceLoader._normalize_repo_path(value)

    @staticmethod
    def _repo_path() -> str:
        value = os.getenv("GITLAB_COMPLIANCE_REPO_PATH", _DEFAULT_REPO_PATH)
        value = (value or "").strip().strip("/")
        return value or _DEFAULT_REPO_PATH

    @staticmethod
    def _normalize_repo_path(value: str) -> str:
        """
        Accept either a repo-relative file path (preferred) OR a full GitLab blob URL
        and normalize to repo-relative path used by /repository/files/:path/raw.
        """
        raw = (value or "").strip()
        if not raw:
            return _DEFAULT_SCRIPT_PATH
        # Already a relative path
        if not raw.startswith(("http://", "https://")):
            return raw.lstrip("/")
        try:
            parsed = urllib.parse.urlparse(raw)
            # Expected shapes:
            #   /group/project/-/blob/main/TX-ARv2.rsc
            #   /group/project/-/blob/<sha>/path/to/file.rsc
            marker = "/-/blob/"
            if marker not in parsed.path:
                return _DEFAULT_SCRIPT_PATH
            tail = parsed.path.split(marker, 1)[1]
            # tail => "<ref>/path/to/file"
            parts = tail.split("/", 1)
            if len(parts) != 2:
                return _DEFAULT_SCRIPT_PATH
            return parts[1].lstrip("/")
        except Exception:
            return _DEFAULT_SCRIPT_PATH

    def _url(self, path: str) -> str:
        """Build GitLab raw-file API URL for a repository path."""
        host       = self._host()
        project_id = self._project_id()
        ref        = self._ref()
        encoded    = urllib.parse.quote(path, safe="")
        return (
            f"https://{host}/api/v4/projects/{project_id}"
            f"/repository/files/{encoded}/raw?ref={ref}"
        )

    def _raw_url(self, path: str) -> str:
        """
        Build GitLab web raw URL fallback:
          https://<host>/<group>/<project>/-/raw/<ref>/<path>
        """
        host = self._host()
        repo_path = self._repo_path()
        ref = self._ref()
        encoded_path = urllib.parse.quote(path.lstrip("/"), safe="/")
        return f"https://{host}/{repo_path}/-/raw/{urllib.parse.quote(ref, safe='')}/{encoded_path}"

    # ------------------------------------------------------------------ low-level fetch

    def fetch_file(self, path: str) -> str:
        """
        Fetch a raw file from the GitLab repository.

        Returns the decoded UTF-8 text.
        Raises RuntimeError / urllib.error.URLError on any failure.
        Timeout: 5 seconds.
        """
        token      = self._token()
        project_id = self._project_id()

        if not token or not project_id:
            raise RuntimeError(
                "GITLAB_COMPLIANCE_TOKEN and GITLAB_COMPLIANCE_PROJECT_ID "
                "must both be set to fetch from GitLab."
            )

        api_url = self._url(path)
        req = urllib.request.Request(api_url, headers={"PRIVATE-TOKEN": token})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"GitLab returned HTTP {resp.status} for path '{path}'"
                    )
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # Some GitLab deployments return 404 for repository/files raw endpoint
            # while the file is accessible via web raw URL. Try that path next.
            if exc.code not in (400, 404):
                raise
        # Fallback: web raw URL by repo path.
        raw_url = self._raw_url(path)
        raw_req = urllib.request.Request(raw_url, headers={"PRIVATE-TOKEN": token})
        with urllib.request.urlopen(raw_req, timeout=5) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"GitLab raw URL returned HTTP {resp.status} for path '{path}'"
                )
            return resp.read().decode("utf-8")

    # ------------------------------------------------------------------ cached fetch helpers

    def load_file_cached(self, path: str) -> str:
        """Fetch with cache.  Raises on failure (caller decides fallback)."""
        cached = self._cache.get(path)
        if cached is not None:
            return cached
        text = self.fetch_file(path)
        self._cache.set(path, text)
        return text

    def load_json_cached(self, path: str) -> dict:
        """Fetch and JSON-parse with cache.  Raises on failure."""
        # We cache the raw text so we can parse it on every call cheaply
        # (avoids caching the mutable dict reference).
        raw = self.load_file_cached(path)
        return json.loads(raw)

    # ------------------------------------------------------------------ public API

    def is_available(self) -> bool:
        """
        True if GitLab token + project ID are configured AND a quick probe
        succeeds.  Uses a 3-second timeout to keep the health check snappy.
        Does NOT populate the main cache.
        """
        if not self._token() or not self._project_id():
            return False
        try:
            host       = self._host()
            project_id = self._project_id()
            token      = self._token()
            url = f"https://{host}/api/v4/projects/{project_id}"
            req = urllib.request.Request(url, headers={"PRIVATE-TOKEN": token})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def is_configured(self) -> bool:
        """True if the required env vars are present (does not test connectivity)."""
        return bool(self._token() and self._project_id())

    def list_repository_tree(self, path: str = "", ref: Optional[str] = None) -> Optional[List[dict]]:
        """
        List files/directories in the repository.
        Returns a list of {name, path, type} dicts, or None on failure.
        """
        try:
            token      = self._token()
            project_id = self._project_id()
            if not token or not project_id:
                return None
            host = self._host()
            ref  = ref or self._ref()
            params = urllib.parse.urlencode({"ref": ref, "path": path, "per_page": 100})
            url = f"https://{host}/api/v4/projects/{project_id}/repository/tree?{params}"
            req = urllib.request.Request(url, headers={"PRIVATE-TOKEN": token})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status != 200:
                    return None
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"[GITLAB-COMPLIANCE] list_repository_tree failed: {exc}")
            return None

    def get_raw_compliance_script(self, path: Optional[str] = None) -> Optional[str]:
        """
        Fetch the raw compliance commands text file from the repository.
        Returns the text content, or None on failure.

        Default path:
            TX-ARv2.rsc
        """
        effective_path = path or self._script_path()
        try:
            return self.load_file_cached(effective_path)
        except Exception as exc:
            print(f"[GITLAB-COMPLIANCE] get_raw_compliance_script('{effective_path}') failed: {exc}")
            return None

    def get_compliance_blocks_from_script(
        self,
        loopback_ip: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Fetch the compliance script and parse it into a compliance blocks dict
        that matches the signature of get_all_compliance_blocks() in
        nextlink_compliance_reference.py.

        The file is expected to be a RouterOS script with clearly delimited
        sections.  Each section becomes one block in the returned dict.

        Section detection:
          Lines starting with  # ---  or  # ===  or  ## <SECTION>  are treated
          as section headers.  The section name is lowercased + underscored to
          form the dict key.  Lines before the first header go into "preamble"
          (discarded unless they are RouterOS commands).

        Returns None on any failure so callers fall back to hardcoded.
        """
        effective_path = path or self._script_path()
        lp = loopback_ip or "10.0.0.1/32"
        try:
            raw = self.load_file_cached(effective_path)
        except Exception as exc:
            print(f"[GITLAB-COMPLIANCE] fetch failed for '{effective_path}': {exc}")
            return None

        try:
            blocks = _parse_compliance_script(raw, loopback_ip=lp)
            if not blocks:
                print(f"[GITLAB-COMPLIANCE] parsed 0 blocks from '{effective_path}' - falling back")
                return None
            return blocks
        except Exception as exc:
            print(f"[GITLAB-COMPLIANCE] parse error for '{effective_path}': {exc}")
            return None

    def get_compliance_rsc_template(
        self,
        path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Fetch the engineering compliance RSC template from GitLab.
        Returns raw text or None on failure.
        """
        effective_path = self._normalize_repo_path(path or self._script_path())
        try:
            return self.load_file_cached(effective_path)
        except Exception as exc:
            print(f"[GITLAB-COMPLIANCE] RSC template fetch failed for '{effective_path}': {exc}")
            return None

    def refresh(self) -> None:
        """Clear the TTL cache — next access will re-fetch from GitLab."""
        self._cache.clear()
        print("[GITLAB-COMPLIANCE] Cache cleared — next request will re-fetch from GitLab")

    def cache_info(self) -> dict:
        """Diagnostic information about the current cache state."""
        return self._cache.info()


# ---------------------------------------------------------------------------
# Compliance script parser
# ---------------------------------------------------------------------------

def _normalise_section_name(header_line: str) -> str:
    """
    Convert a comment header line to a snake_case block key.

    Examples:
        # DNS SERVERS          -> dns_servers
        ## Firewall Filter     -> firewall_filter
        # --- RADIUS ---       -> radius
        # =========== NTP ==== -> ntp
    """
    text = header_line.lstrip("# =-\t").strip()
    # strip trailing decoration
    text = text.rstrip("# =-\t").strip()
    key  = text.lower().replace(" ", "_").replace("-", "_")
    # collapse repeated underscores
    import re as _re
    key = _re.sub(r"[^a-z0-9_]+", "_", key)
    key = _re.sub(r"_+", "_", key).strip("_")
    return key or "unknown"


import re as _section_re

_DECORATED_HEADER_RE = _section_re.compile(r"^#[-=\s]{2,}|^##\s")
_ALLCAPS_HEADER_RE = _section_re.compile(r"^#\s*([A-Z][A-Z0-9 _/\-()]{2,})\s*$")


def _is_section_header(stripped: str) -> bool:
    """
    Detect comment headers that start a new compliance section.

    We intentionally support:
      - # --- SECTION ---
      - ## SECTION
      - # FIREWALL - INPUT CHAIN
      - # FIREALL - FORWARD (legacy typo in source script)
    """
    if not stripped.startswith("#"):
        return False
    if _DECORATED_HEADER_RE.match(stripped):
        return True
    if _ALLCAPS_HEADER_RE.match(stripped):
        return True

    body = stripped.lstrip("#").strip()
    if not body:
        return False
    if body[0] in ("/", ":", "."):
        # Commented command, not a section header.
        return False
    if len(body) > 100:
        return False
    if not any(ch.isalpha() for ch in body):
        return False
    # Fallback for mixed-case headings like:
    #   # ENGINEERING COMPLIANCE (dynamic — GitLab-first)
    upper_body = body.upper()
    if upper_body.startswith("ENGINEERING COMPLIANCE"):
        return True
    if upper_body.startswith((
        "VARIABLES",
        "IP SERVICES",
        "DNS",
        "FIREWALL",
        "FIREALL",
        "SIP ALG",
        "CLOCK",
        "SNMP",
        "WATCHDOG",
        "AUTO UPGRADE",
        "UDP CONNECTION TRACKING",
        "WEB PROXY",
        "VPLS EDGE",
        "LOGGING",
        "USER AAA",
        "USER PROFILES",
        "USER GROUP",
        "USERS",
        "AAA",
        "DHCP",
        "RADIUS",
        "LDP",
        "MPLS LDP",
        "SCRIPTS",
        "SCHEDULER",
        "SYS NOTE",
        "SYSTEM NOTE",
    )):
        return True
    # Generic mixed-case header fallback (e.g. "FIREWALL ACLs", "LDP Filters")
    # Treat short, command-free comment lines as section headers.
    if "/" in body or "=" in body or ":" in body:
        return False
    words = [w for w in body.replace("-", " ").replace("_", " ").split() if w]
    if not words or len(words) > 8:
        return False
    alpha_chars = [c for c in body if c.isalpha()]
    if not alpha_chars:
        return False
    upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
    return upper_ratio >= 0.55


def _parse_compliance_script(
    text: str,
    loopback_ip: str = "10.0.0.1/32",
) -> dict:
    """
    Parse a RouterOS compliance script into named blocks.

    Strategy:
    1. Split on lines that look like section headers.
    2. Within each section, substitute {{LOOP_IP}} with the actual loopback.
    3. Map canonical section names to the compliance block keys expected by
       engineering_compliance.py's COMPLIANCE_ORDER list.
    """
    # Build a mapping from whatever section names appear in the file to the
    # canonical keys used by COMPLIANCE_ORDER.
    CANONICAL_MAP = {
        # Variables
        "variables":              "variables",
        # IP services
        "ip_services":            "ip_services",
        # DNS
        "dns": "dns",
        "dns_servers": "dns",
        # Firewall
        "firewall_acls":          "firewall_address_lists",
        "firewall_acls_s":        "firewall_address_lists",
        "firewall_address_lists": "firewall_address_lists",
        "firewall_address_list":  "firewall_address_lists",
        "address_lists":          "firewall_address_lists",
        "firewall_filter":        "firewall_filter_input",
        "firewall_filter_input":  "firewall_filter_input",
        "firewall_input_chain":   "firewall_filter_input",
        "firewall_input":         "firewall_filter_input",
        "firewall_raw":           "firewall_raw",
        "raw":                    "firewall_raw",
        "firewall_forward":       "firewall_forward",
        "fireall_forward":        "firewall_forward",
        "forward":                "firewall_forward",
        "firewall_nat":           "firewall_nat",
        "nat":                    "firewall_nat",
        "firewall_mangle":        "firewall_mangle",
        "mangle":                 "firewall_mangle",
        # Service-port / proxy / conntrack / edge settings
        "sip_alg_off":            "sip_alg_off",
        "udp_connection_tracking_timeout": "system_settings",
        "web_proxy_off":          "web_proxy_off",
        "vpls_edge_ports":        "vpls_edge_ports",
        # Clock / NTP
        "clock_ntp":              "clock_ntp",
        "ntp":                    "clock_ntp",
        "clock":                  "clock_ntp",
        "system_clock":           "clock_ntp",
        # SNMP
        "snmp":                   "snmp",
        # System
        "watchdog_timer":         "watchdog_timer",
        "auto_upgrade":           "auto_upgrade",
        "system_settings":        "system_settings",
        "system":                 "system_settings",
        # VPLS
        "vpls_edge":              "vpls_edge",
        "vpls":                   "vpls_edge",
        # Logging
        "logging":                "logging",
        "system_logging":         "logging",
        # Users / AAA
        "user_aaa":               "user_aaa",
        "aaa":                    "user_aaa",
        "users":                  "users",
        "aaa_users":              "user_aaa",
        "users_1":                "users",
        "user_groups":            "user_groups",
        "user_profiles":          "user_profiles",
        "groups":                 "user_groups",
        # DHCP
        "dhcp_options":           "dhcp_options",
        "dhcp":                   "dhcp_options",
        # RADIUS
        "radius":                 "radius",
        # LDP
        "ldp_filters":            "ldp_filters",
        "ldp_filter":             "ldp_filters",
        "ldp":                    "ldp_filters",
        "mpls_ldp":               "ldp_filters",
        # Script/scheduler/note blocks
        "scripts":                "scripts",
        "scheduler":              "scheduler",
        "sys_note":               "sys_note",
        "system_note":            "sys_note",
    }

    blocks: dict = {}
    current_key:   Optional[str] = None
    current_lines: list          = []

    def _flush(key: Optional[str], lines: list) -> None:
        if not key:
            return
        content = "\n".join(lines).strip()
        content = content.replace("{{LOOP_IP}}", loopback_ip)
        if content:
            canonical = CANONICAL_MAP.get(key, key)
            if canonical in blocks:
                # Append to existing block (multiple sections can map to same key)
                blocks[canonical] = blocks[canonical].rstrip() + "\n" + content
            else:
                blocks[canonical] = content

    for line in text.splitlines():
        stripped = line.strip()
        is_header = False

        if _is_section_header(stripped):
            is_header = True
            _flush(current_key, current_lines)
            current_key   = _normalise_section_name(stripped)
            current_lines = []

        if not is_header:
            current_lines.append(line)

    _flush(current_key, current_lines)
    return blocks


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_loader_instance: Optional[GitLabComplianceLoader] = None


def get_loader() -> GitLabComplianceLoader:
    """Return the process-wide singleton loader, creating it on first call."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = GitLabComplianceLoader()
    return _loader_instance

