"""RBAC Phase 1 — Nextlink role permission gating tests.

Covers @require_tab decorator, /api/admin/nextlink-role-permissions endpoints,
bootstrap tabPermissions, super_admin/platform_admin bypass, platform_support
NOT bypassed, NULL nextlink_role behavior, and stale localStorage compatibility.
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


def _load_api_server():
    repo_root = Path(__file__).resolve().parents[1]
    vm_dep = repo_root / "vm_deployment"
    for p in (str(repo_root), str(vm_dep)):
        if p not in sys.path:
            sys.path.insert(0, p)
    return importlib.import_module("vm_deployment.api_server")


def _patch_dbs(monkeypatch, api_server):
    db_uris = {
        "users.db": "file:rbac_nl_users?mode=memory&cache=shared",
        "feedback.db": "file:rbac_nl_feedback?mode=memory&cache=shared",
    }
    anchors = {name: sqlite3.connect(uri, uri=True) for name, uri in db_uris.items()}
    original_connect = sqlite3.connect
    original_exists = os.path.exists

    def connect_override(path, *args, **kwargs):
        target = str(path)
        for suffix, uri in db_uris.items():
            if target.endswith(suffix):
                return original_connect(uri, uri=True, *args, **kwargs)
        return original_connect(path, *args, **kwargs)

    monkeypatch.setattr(api_server.os.path, "exists", lambda p: True if str(p) == "secure_data" else original_exists(p))
    monkeypatch.setattr(api_server.os, "makedirs", lambda *args, **kwargs: None)
    monkeypatch.setattr(api_server.sqlite3, "connect", connect_override)
    monkeypatch.setattr(api_server, "DEFAULT_PASSWORD", uuid.uuid4().hex)
    return db_uris, anchors


def _login(client, api_server, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": api_server.DEFAULT_PASSWORD},
    )
    assert response.status_code == 200
    payload = response.get_json() or {}
    token = payload.get("token")
    assert token
    return token


def _set_nextlink_role(db_uri, email, nextlink_role):
    """Set nextlink_role for a user by email."""
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("UPDATE users SET nextlink_role = ? WHERE email = ?", (nextlink_role, email))
    conn.commit()
    conn.close()


def _insert_role_permission(db_uri, role, perm_type, perm_value):
    """Insert a role permission (tab or feature)."""
    conn = sqlite3.connect(db_uri, uri=True)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO nextlink_role_permissions (role, perm_type, perm_value) VALUES (?, ?, ?)",
        (role, perm_type, perm_value)
    )
    conn.commit()
    conn.close()


def test_super_admin_nextlink_role_bypasses_require_tab(monkeypatch):
    """super_admin nextlink_role bypasses @require_tab checks."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        email = "super@team.nxlink.com"
        _login(client, api_server, email)
        _set_nextlink_role(db_uris["users.db"], email, "super_admin")

        # POST to a tab-gated endpoint (enterprise)
        response = client.post(
            "/api/gen-enterprise-non-mpls",
            json={"device": "RB5009", "config": "basic"},
            headers={"Authorization": f"Bearer {_login(client, api_server, email)}"}
        )
        # Should NOT be 403 (allowed by super_admin)
        assert response.status_code != 403, f"Expected non-403, got {response.status_code}"
    finally:
        for conn in anchors.values():
            conn.close()


def test_platform_admin_bypasses_require_tab(monkeypatch):
    """platform_admin (whamza@team.nxlink.com) bypasses @require_tab checks."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        token = _login(client, api_server, "whamza@team.nxlink.com")

        # POST to a tab-gated endpoint (enterprise)
        response = client.post(
            "/api/gen-enterprise-non-mpls",
            json={"device": "RB5009", "config": "basic"},
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should NOT be 403 (allowed by platform_admin)
        assert response.status_code != 403, f"Expected non-403, got {response.status_code}"
    finally:
        for conn in anchors.values():
            conn.close()


def test_platform_support_NOT_bypassed(monkeypatch):
    """platform_support with NULL nextlink_role is blocked by @require_tab."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        email = "support@team.nxlink.com"
        _login(client, api_server, email)
        # User has platform_support role but no nextlink_role
        # Manually set platform_role to platform_support
        conn = sqlite3.connect(db_uris["users.db"], uri=True)
        c = conn.cursor()
        c.execute("UPDATE users SET platform_role = ? WHERE email = ?", ("platform_support", email))
        conn.commit()
        conn.close()

        # POST to a tab-gated endpoint (enterprise)
        response = client.post(
            "/api/gen-enterprise-non-mpls",
            json={"device": "RB5009", "config": "basic"},
            headers={"Authorization": f"Bearer {_login(client, api_server, email)}"}
        )
        # Should be 403 because no nextlink_role assigned
        assert response.status_code == 403
        assert "does not have access" in (response.get_json().get("error") or "").lower()
    finally:
        for conn in anchors.values():
            conn.close()


def test_platform_support_subject_to_nextlink_role(monkeypatch):
    """platform_support with nextlink_role is gated by that role's permissions."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        email = "support2@team.nxlink.com"
        _login(client, api_server, email)
        conn = sqlite3.connect(db_uris["users.db"], uri=True)
        c = conn.cursor()
        c.execute("UPDATE users SET platform_role = ? WHERE email = ?", ("platform_support", email))
        conn.commit()
        conn.close()

        # Assign nextlink_role = 'noc'
        _set_nextlink_role(db_uris["users.db"], email, "noc")
        # Grant 'noc' access to 'enterprise' tab
        _insert_role_permission(db_uris["users.db"], "noc", "tab", "enterprise")

        # POST to enterprise endpoint
        response = client.post(
            "/api/gen-enterprise-non-mpls",
            json={"device": "RB5009", "config": "basic"},
            headers={"Authorization": f"Bearer {_login(client, api_server, email)}"}
        )
        # Should NOT be 403 (noc role has enterprise permission)
        assert response.status_code != 403, f"Expected non-403, got {response.status_code}"
    finally:
        for conn in anchors.values():
            conn.close()


def test_noc_role_allows_configured_tabs_bootstrap(monkeypatch):
    """Bootstrap reflects allowed tabs for noc role with specific permissions."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        email = "noc@team.nxlink.com"
        _login(client, api_server, email)
        _set_nextlink_role(db_uris["users.db"], email, "noc")
        _insert_role_permission(db_uris["users.db"], "noc", "tab", "tower")
        _insert_role_permission(db_uris["users.db"], "noc", "tab", "enterprise")

        response = client.get(
            "/api/session/bootstrap",
            headers={"Authorization": f"Bearer {_login(client, api_server, email)}"}
        )
        assert response.status_code == 200
        payload = response.get_json() or {}
        tp = payload.get("tabPermissions")
        assert tp is not None, "tabPermissions should be present in bootstrap"
        assert tp.get("restricted") is True
        allowed_tabs = tp.get("allowed_tabs") or []
        # Order-insensitive check
        assert set(allowed_tabs) == {"tower", "enterprise"}, f"Got {allowed_tabs}"
    finally:
        for conn in anchors.values():
            conn.close()


def test_noc_role_blocks_unconfigured_tab(monkeypatch):
    """User with noc role is blocked from tabs not in their permission matrix."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        email = "noc2@team.nxlink.com"
        _login(client, api_server, email)
        _set_nextlink_role(db_uris["users.db"], email, "noc")
        # Grant only 'tarana', NOT 'enterprise'
        _insert_role_permission(db_uris["users.db"], "noc", "tab", "tarana")

        # Try to access enterprise endpoint
        response = client.post(
            "/api/gen-enterprise-non-mpls",
            json={"device": "RB5009", "config": "basic"},
            headers={"Authorization": f"Bearer {_login(client, api_server, email)}"}
        )
        # Should be 403
        assert response.status_code == 403
    finally:
        for conn in anchors.values():
            conn.close()


def test_null_nextlink_role_blocks_all_tool_tabs(monkeypatch):
    """User with NULL nextlink_role is blocked and bootstrap shows restricted: true, allowed_tabs: []."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        email = "noassign@team.nxlink.com"
        _login(client, api_server, email)
        # Don't set nextlink_role (leave NULL)

        # Check bootstrap
        token = _login(client, api_server, email)
        response = client.get(
            "/api/session/bootstrap",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.get_json() or {}
        tp = payload.get("tabPermissions")
        assert tp is not None
        assert tp.get("restricted") is True
        assert tp.get("allowed_tabs") == []

        # Try to access enterprise endpoint
        response = client.post(
            "/api/gen-enterprise-non-mpls",
            json={"device": "RB5009", "config": "basic"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    finally:
        for conn in anchors.values():
            conn.close()


def test_stale_bootstrap_no_tabPermissions(monkeypatch):
    """_get_nextlink_tab_permissions always returns well-formed dict with 'restricted' key."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        # First, login to ensure user is in DB
        email = "stale@team.nxlink.com"
        _login(client, api_server, email)

        # Now get a user row and test _get_nextlink_tab_permissions
        conn = sqlite3.connect(db_uris["users.db"], uri=True)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Fetch the user we just created
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user_row = c.fetchone()
        assert user_row is not None, "User should exist after login"

        # Call _get_nextlink_tab_permissions
        result = api_server._get_nextlink_tab_permissions(user_row, conn)
        # Should always have 'restricted' key
        assert 'restricted' in result, f"Missing 'restricted' in {result}"
        # If no nextlink_role, should be restricted with empty lists
        assert isinstance(result['restricted'], bool)
        assert isinstance(result.get('allowed_tabs'), (list, type(None)))
        assert isinstance(result.get('allowed_features'), (list, type(None)))

        conn.close()
    finally:
        for conn in anchors.values():
            conn.close()


def test_admin_endpoint_returns_available_tabs_and_features(monkeypatch):
    """GET /api/admin/nextlink-role-permissions returns matrix, available_tabs, and available_features."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        token = _login(client, api_server, "whamza@team.nxlink.com")

        response = client.get(
            "/api/admin/nextlink-role-permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload.get("success") is True
        assert "matrix" in payload
        assert "available_tabs" in payload
        assert "available_features" in payload

        # Check structure of available_tabs
        tabs = payload["available_tabs"]
        assert isinstance(tabs, list)
        assert len(tabs) > 0
        # Each tab should have 'value' and 'label'
        for t in tabs:
            assert 'value' in t
            assert 'label' in t
        # Should include 'tower'
        tab_values = [t['value'] for t in tabs]
        assert 'tower' in tab_values

        # Check structure of available_features
        features = payload["available_features"]
        assert isinstance(features, list)
        assert len(features) > 0
        for f in features:
            assert 'value' in f
            assert 'label' in f
        feature_values = [f['value'] for f in features]
        assert 'nokia' in feature_values

        # matrix should be a dict (may be empty initially)
        assert isinstance(payload["matrix"], dict)
    finally:
        for conn in anchors.values():
            conn.close()


def test_unique_constraint_prevents_duplicate_permission_rows(monkeypatch):
    """Direct DB: inserting duplicate (role, perm_type, perm_value) raises IntegrityError."""
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        client = api_server.app.test_client()
        # First, login to initialize DB schema
        _login(client, api_server, "init@team.nxlink.com")

        db_uri = db_uris["users.db"]
        conn = sqlite3.connect(db_uri, uri=True)
        c = conn.cursor()

        # Insert first time
        c.execute(
            "INSERT INTO nextlink_role_permissions (role, perm_type, perm_value) VALUES (?, ?, ?)",
            ("test_role", "tab", "tower")
        )
        conn.commit()

        # Try to insert same row again — should raise IntegrityError
        try:
            c.execute(
                "INSERT INTO nextlink_role_permissions (role, perm_type, perm_value) VALUES (?, ?, ?)",
                ("test_role", "tab", "tower")
            )
            conn.commit()
            assert False, "Should have raised IntegrityError"
        except sqlite3.IntegrityError:
            # Expected
            pass
        finally:
            conn.close()
    finally:
        for conn in anchors.values():
            conn.close()


def test_v2_native_route_enforces_tab(monkeypatch):
    """FastAPI routes enforce require_tab_v2 decorator via nextlink_role (integration test).

    Tests:
    1. Bootstrap state reflects tab permissions (existing logic preserved)
    2. Direct HTTP calls to /api/v2/nexus/tools/config-diff are gated by require_tab_v2
       - Without permission: 403 Forbidden
       - With permission: != 403 (200 or 4xx from validation, but NOT 403)
    """
    api_server = _load_api_server()
    db_uris, anchors = _patch_dbs(monkeypatch, api_server)
    try:
        # Use Flask test client for bootstrap endpoint
        flask_client = api_server.app.test_client()
        email = "v2user@team.nxlink.com"
        _login(flask_client, api_server, email)
        _set_nextlink_role(db_uris["users.db"], email, "noc")
        # Verify the nextlink_role is set correctly
        token = _login(flask_client, api_server, email)

        # === PART 1: Verify bootstrap shows the user is restricted ===
        response = flask_client.get(
            "/api/session/bootstrap",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.get_json() or {}
        tp = payload.get("tabPermissions")
        assert tp is not None
        assert tp.get("restricted") is True
        # noc role has no permissions yet
        assert tp.get("allowed_tabs") == []

        # === PART 2: Direct HTTP call to /api/v2/... route WITHOUT permission ===
        # Import api_v2 and patch verify_token to accept our session tokens
        repo_root = Path(__file__).resolve().parents[1]
        vm_dep = repo_root / "vm_deployment"
        if str(vm_dep) not in sys.path:
            sys.path.insert(0, str(vm_dep))

        try:
            # Import api_v2 to access _verify_session_token patching
            import api_v2 as _api_v2_module  # noqa: E402
            from fastapi_server import app as fastapi_app  # noqa: E402
        except ImportError:
            fastapi_app = None
            _api_v2_module = None

        if fastapi_app is not None and _api_v2_module is not None:
            # Patch the verify_token function in api_v2 to use our monkeypatched db
            # We need to patch it after it's imported but before the TestClient is created
            original_verify_session_token = _api_v2_module._verify_session_token

            def mock_verify_session_token(token_str: str):
                """Use the Flask app's verify_token (which is patched with monkeypatch)."""
                return api_server.verify_token(token_str)

            monkeypatch.setattr(_api_v2_module, "_verify_session_token", mock_verify_session_token)

            fastapi_client = TestClient(fastapi_app)

            # Call /api/v2/nexus/tools/config-diff with minimal body
            # Pydantic expects config_a and config_b fields
            response = fastapi_client.post(
                "/api/v2/nexus/tools/config-diff",
                json={"config_a": "", "config_b": ""},
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should be 403 because noc role has no config-diff permission
            assert response.status_code == 403, (
                f"Expected 403 without config-diff permission, got {response.status_code}: {response.text}"
            )

        # === PART 3: Grant config-diff permission and test again ===
        _insert_role_permission(db_uris["users.db"], "noc", "tab", "config-diff")

        # Bootstrap should now show config-diff in allowed_tabs
        response = flask_client.get(
            "/api/session/bootstrap",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        payload = response.get_json() or {}
        tp = payload.get("tabPermissions")
        assert tp is not None
        assert "config-diff" in (tp.get("allowed_tabs") or [])

        # === PART 4: Direct HTTP call to /api/v2/... route WITH permission ===
        if fastapi_app is not None and _api_v2_module is not None:
            fastapi_client = TestClient(fastapi_app)

            # Call /api/v2/nexus/tools/config-diff again with same minimal body
            response = fastapi_client.post(
                "/api/v2/nexus/tools/config-diff",
                json={"config_a": "", "config_b": ""},
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should NOT be 403 (may be 500 or 400 from validation, but not 403)
            # The point is require_tab_v2 should not block anymore
            assert response.status_code != 403, (
                f"Expected non-403 WITH config-diff permission, got 403: {response.text}"
            )
    finally:
        for conn in anchors.values():
            conn.close()
