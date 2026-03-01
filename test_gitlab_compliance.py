#!/usr/bin/env python3
"""
test_gitlab_compliance.py — Live GitLab Compliance Connectivity Test

Run this locally or on the VM to verify that the compliance system
can actually reach GitLab and pull TX-ARv2.rsc in real time.

Usage:
    python test_gitlab_compliance.py
    
    # Or with explicit env vars:
    GITLAB_COMPLIANCE_TOKEN=glpat-xxx GITLAB_COMPLIANCE_PROJECT_ID=75 python test_gitlab_compliance.py

Set these env vars (or put them in .env next to this script):
    GITLAB_COMPLIANCE_TOKEN       = your GitLab personal access token
    GITLAB_COMPLIANCE_PROJECT_ID  = 75  (netforge/compliance)
    GITLAB_COMPLIANCE_HOST        = tested.nxlink.com  (default)
"""

import os
import sys
import time
import datetime

# ── Try to load .env file if present ──────────────────────────────────────
def _load_dotenv():
    """Load .env file from same directory as this script."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vm_deployment", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and val and key not in os.environ:
                os.environ[key] = val

_load_dotenv()

# ── Add vm_deployment to path so we can import gitlab_compliance ──────────
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vm_deployment"))

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
WARN = "\033[93m⚠ WARN\033[0m"
INFO = "\033[94mℹ INFO\033[0m"

def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def main():
    header("GitLab Compliance Connectivity Test")
    print(f"  Time: {datetime.datetime.now().isoformat()}")
    print()

    # ── Step 1: Check env vars ────────────────────────────────────────────
    print("─── Step 1: Environment Variables ───")
    token = os.getenv("GITLAB_COMPLIANCE_TOKEN", "")
    project_id = os.getenv("GITLAB_COMPLIANCE_PROJECT_ID", "")
    host = os.getenv("GITLAB_COMPLIANCE_HOST", "tested.nxlink.com")
    ref = os.getenv("GITLAB_COMPLIANCE_REF", "main")
    script_path = os.getenv("GITLAB_COMPLIANCE_SCRIPT_PATH", "TX-ARv2.rsc")
    ttl = os.getenv("GITLAB_COMPLIANCE_TTL", "900")

    print(f"  GITLAB_COMPLIANCE_HOST        = {host}")
    print(f"  GITLAB_COMPLIANCE_PROJECT_ID  = {project_id or '(NOT SET)'}")
    print(f"  GITLAB_COMPLIANCE_TOKEN       = {'***' + token[-4:] if len(token) > 4 else '(NOT SET or too short)'}")
    print(f"  GITLAB_COMPLIANCE_REF         = {ref}")
    print(f"  GITLAB_COMPLIANCE_SCRIPT_PATH = {script_path}")
    print(f"  GITLAB_COMPLIANCE_TTL         = {ttl}")

    if not token or token == "CHANGE_ME":
        print(f"\n  {FAIL} GITLAB_COMPLIANCE_TOKEN is not set or is still 'CHANGE_ME'!")
        print(f"       This is why compliance falls back to hardcoded data.")
        print(f"       Fix: Set a real GitLab PAT in your .env file.")
        return 1

    if not project_id:
        print(f"\n  {FAIL} GITLAB_COMPLIANCE_PROJECT_ID is not set!")
        return 1

    print(f"\n  {PASS} Environment variables are set")

    # ── Step 2: Import the loader ─────────────────────────────────────────
    print("\n─── Step 2: Import gitlab_compliance ───")
    try:
        from gitlab_compliance import GitLabComplianceLoader, get_loader
        print(f"  {PASS} Module imported successfully")
    except ImportError as e:
        print(f"  {FAIL} Cannot import: {e}")
        return 1

    loader = get_loader()

    # ── Step 3: Check is_configured ───────────────────────────────────────
    print("\n─── Step 3: Configuration Check ───")
    configured = loader.is_configured()
    print(f"  is_configured() = {configured}")
    if configured:
        print(f"  {PASS} Loader sees token + project ID")
    else:
        print(f"  {FAIL} Loader does NOT see token + project ID")
        print(f"       Token value starts with: {repr(token[:8])}...")
        return 1

    # ── Step 4: Test connectivity (is_available) ──────────────────────────
    print("\n─── Step 4: GitLab Connectivity ───")
    print(f"  Testing connection to https://{host}/api/v4/projects/{project_id} ...")
    t0 = time.time()
    available = loader.is_available()
    elapsed = round((time.time() - t0) * 1000)
    print(f"  is_available() = {available}  ({elapsed}ms)")
    if available:
        print(f"  {PASS} GitLab is reachable and token is valid")
    else:
        print(f"  {FAIL} Cannot reach GitLab or token is invalid")
        print(f"       Check: is {host} reachable from this machine?")
        print(f"       Check: is the token expired or revoked?")
        return 1

    # ── Step 5: Fetch TX-ARv2.rsc (bypassing cache) ──────────────────────
    print("\n─── Step 5: Fetch TX-ARv2.rsc (fresh, no cache) ───")
    loader.refresh()  # Clear cache first
    print(f"  Cache cleared. Fetching {script_path} from GitLab...")
    t0 = time.time()
    try:
        raw = loader.fetch_file(script_path)
        elapsed = round((time.time() - t0) * 1000)
        print(f"  {PASS} Fetched {len(raw)} bytes in {elapsed}ms")
        # Show first 3 lines
        lines = raw.splitlines()
        print(f"  First 3 lines of {script_path}:")
        for i, line in enumerate(lines[:3]):
            print(f"    {i+1}: {line[:100]}")
        print(f"  Total lines: {len(lines)}")
    except Exception as e:
        elapsed = round((time.time() - t0) * 1000)
        print(f"  {FAIL} Fetch failed in {elapsed}ms: {e}")
        return 1

    # ── Step 6: Test get_raw_compliance_text (verbatim path) ──────────────
    print("\n─── Step 6: Test get_raw_compliance_text() (verbatim) ───")
    loader.refresh()  # Clear again to force real fetch
    t0 = time.time()
    text = loader.get_raw_compliance_text(loopback_ip="10.0.0.1")
    elapsed = round((time.time() - t0) * 1000)
    if text:
        print(f"  {PASS} Got verbatim text: {len(text)} bytes in {elapsed}ms")
        # Check for comment= attributes (sign of real GitLab data)
        comment_count = text.count('comment=')
        print(f"  Contains {comment_count} 'comment=' attributes")
        if comment_count > 5:
            print(f"  {PASS} Rich comment data present (real GitLab source)")
        else:
            print(f"  {WARN} Few comments — might be hardcoded fallback")
    else:
        print(f"  {FAIL} get_raw_compliance_text returned None (falling back to hardcoded)")
        return 1

    # ── Step 7: Test cache behavior ───────────────────────────────────────
    print("\n─── Step 7: Cache Behavior ───")
    # This call should be a CACHE_HIT since Step 6 just fetched it
    t0 = time.time()
    text2 = loader.get_raw_compliance_text(loopback_ip="10.0.0.1")
    elapsed = round((time.time() - t0) * 1000)
    print(f"  Second call: {len(text2 or '')} bytes in {elapsed}ms (should be <1ms = cache hit)")

    info = loader.cache_info()
    print(f"  Cache info: {info}")

    # ── Step 8: Show diagnostics ──────────────────────────────────────────
    print("\n─── Step 8: Full Diagnostics ───")
    diag = loader.diagnostics()
    print(f"  Stats:")
    for k, v in diag["stats"].items():
        print(f"    {k}: {v}")
    print(f"  Recent log:")
    for entry in diag["recent_log"]:
        print(f"    [{entry['time']}] {entry['type']}: {entry['path']} {entry.get('detail','')}")

    # ── Summary ───────────────────────────────────────────────────────────
    header("RESULT: ALL TESTS PASSED")
    print(f"  GitLab at {host} is reachable")
    print(f"  TX-ARv2.rsc fetched successfully ({len(raw)} bytes)")
    print(f"  Compliance is being pulled in REAL TIME from GitLab")
    print(f"  Cache TTL = {ttl}s — after this, next call re-fetches live")
    print(f"  Token last used: NOW (GitLab should show 'just now')")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
