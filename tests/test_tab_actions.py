#!/usr/bin/env python3
"""Explicit backend action tests for tabs that previously had only structure coverage."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

os.environ.setdefault("AI_PROVIDER", "none")
os.environ.setdefault("DEFAULT_PASSWORD", "TestOnlyNocPass123!")

import api_server  # noqa: E402


app = api_server.app
app.config["TESTING"] = True
client = app.test_client()
_ADMIN_HEADERS: dict[str, str] | None = None
_TEST_ADMIN_EMAIL = "whamza@team.nxlink.com"
_TEST_DEFAULT_PASSWORD = "TestOnlyNocPass123!"


def _admin_auth_header() -> dict[str, str]:
    global _ADMIN_HEADERS
    if _ADMIN_HEADERS:
        return _ADMIN_HEADERS
    # Use platform admin email; fall back to env var for flexibility
    admin_email = os.getenv("PLATFORM_ADMIN_EMAILS", _TEST_ADMIN_EMAIL).split(",")[0].strip() or _TEST_ADMIN_EMAIL
    api_server.DEFAULT_PASSWORD = _TEST_DEFAULT_PASSWORD
    api_server.init_users_db()
    conn = sqlite3.connect(os.path.join("secure_data", "users.db"))
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
        password_hash = api_server.hash_password(_TEST_DEFAULT_PASSWORD)
        if row:
            conn.execute(
                """
                UPDATE users
                SET password_hash = ?, is_active = 1, first_login = 1
                WHERE id = ?
                """,
                (password_hash, row["id"]),
            )
            user_id = row["id"]
        else:
            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, display_name, is_active, first_login)
                VALUES (?, ?, ?, 1, 1)
                """,
                (admin_email, password_hash, admin_email.split("@")[0]),
            )
            user_id = cursor.lastrowid
        api_server._sync_user_platform_access(conn, user_id, admin_email)
        api_server._ensure_user_default_membership(conn, user_id)
        conn.commit()
    finally:
        conn.close()
    login = client.post(
        "/api/auth/login",
        json={
            "email": admin_email,
            # Reuse the single source of truth from api_server — no duplicate secrets in tests
            "password": _TEST_DEFAULT_PASSWORD,
        },
    )
    assert login.status_code == 200, login.get_data(as_text=True)
    token = (login.get_json() or {}).get("token")
    assert token
    _ADMIN_HEADERS = {"Authorization": f"Bearer {token}"}
    return _ADMIN_HEADERS


def test_completed_configs_tab_actions_round_trip():
    headers = _admin_auth_header()
    config_content = (
        '/system identity\n'
        'set name="RTR-TEST"\n'
        '/interface ethernet\n'
        'set [ find default-name=sfp-sfpplus1 ] comment="BH-1"\n'
        '/ip address\n'
        'add address=10.1.1.1/30 interface=sfp-sfpplus1 comment="BH-1"\n'
    )

    save = client.post(
        "/api/save-completed-config",
        headers=headers,
        json={
            "config_type": "tower",
            "device_name": "RTR-TEST",
            "device_type": "CCR2004",
            "customer_code": "TEST",
            "loopback_ip": "10.1.1.1/32",
            "routeros_version": "7.19.4",
            "config_content": config_content,
            "created_by": "netops@team.nxlink.com",
            "site_name": "TEST-SITE",
        },
    )
    assert save.status_code == 200, save.get_data(as_text=True)
    save_payload = save.get_json() or {}
    assert save_payload.get("success") is True
    config_id = save_payload.get("config_id")
    assert isinstance(config_id, int)

    listing = client.get("/api/get-completed-configs?search=RTR-TEST", headers=headers)
    assert listing.status_code == 200
    listing_payload = listing.get_json() or {}
    assert any(row.get("id") == config_id for row in listing_payload.get("configs", []))

    one = client.get(f"/api/get-completed-config/{config_id}", headers=headers)
    assert one.status_code == 200
    one_payload = one.get_json() or {}
    assert one_payload.get("id") == config_id
    assert "port_mapping_text" in one_payload

    portmap = client.post(
        "/api/extract-port-map",
        json={"config_content": config_content, "device_name": "RTR-TEST", "customer_code": "TEST"},
    )
    assert portmap.status_code == 200
    portmap_payload = portmap.get_json() or {}
    assert "port_map_text" in portmap_payload


def test_log_history_tab_actions_record_and_read_activity():
    headers = _admin_auth_header()

    write_live = client.post(
        "/api/activity",
        headers=headers,
        json={
            "timestamp": "2026-03-17T00:00:00Z",
            "username": "netops@team.nxlink.com",
            "type": "tower-config",
            "siteName": "TEST-SITE",
        },
    )
    assert write_live.status_code == 200

    read_live = client.get("/api/activity", headers=headers)
    assert read_live.status_code == 200
    payload = read_live.get_json()
    # Endpoint returns either a plain list (legacy) or {activities: [...]} (multi-tenant)
    assert isinstance(payload, list) or isinstance((payload or {}).get("activities"), list)

    write_db = client.post(
        "/api/log-activity",
        headers=headers,
        json={
            "username": "netops@team.nxlink.com",
            "type": "tower-config",
            "device": "CCR2004",
            "siteName": "TEST-SITE",
            "routeros": "7.19.4",
            "success": True,
        },
    )
    assert write_db.status_code == 200
    assert (write_db.get_json() or {}).get("success") is True

    read_db = client.get("/api/get-activity?all=true&limit=5", headers=headers)
    assert read_db.status_code == 200
    read_db_payload = read_db.get_json() or {}
    assert isinstance(read_db_payload.get("activities"), list)


def test_feedback_and_admin_tab_actions_work():
    feedback = client.post(
        "/api/feedback",
        json={
            "type": "bug",
            "subject": "Tab action test",
            "category": "testing",
            "experience": "neutral",
            "details": "Explicit tab action coverage",
            "name": "Tab Tester",
            "email": "tab.tester@team.nxlink.com",
        },
    )
    assert feedback.status_code == 200, feedback.get_data(as_text=True)
    feedback_payload = feedback.get_json() or {}
    assert feedback_payload.get("success") is True
    feedback_id = feedback_payload.get("feedback_id")
    assert isinstance(feedback_id, int)

    my_status = client.get("/api/feedback/my-status?name=Tab%20Tester")
    assert my_status.status_code == 200
    my_rows = my_status.get_json() or []
    assert any(row.get("id") == feedback_id for row in my_rows)

    headers = _admin_auth_header()

    admin_list = client.get("/api/admin/feedback", headers=headers)
    assert admin_list.status_code == 200, admin_list.get_data(as_text=True)
    admin_payload = admin_list.get_json() or {}
    assert any(row.get("id") == feedback_id for row in admin_payload.get("feedback", []))

    update = client.put(
        f"/api/admin/feedback/{feedback_id}/status",
        headers=headers,
        json={"status": "reviewed", "admin_notes": "covered by explicit tab test"},
    )
    assert update.status_code == 200
    assert (update.get_json() or {}).get("success") is True

    reset = client.post(
        "/api/admin/users/reset-password",
        headers=headers,
        json={
            "email": "new.user@team.nxlink.com",
            "newPassword": _TEST_DEFAULT_PASSWORD,
            "requirePasswordChange": False,
        },
    )
    assert reset.status_code == 200, reset.get_data(as_text=True)
    reset_payload = reset.get_json() or {}
    assert reset_payload.get("success") is True


def test_compliance_scanner_tab_actions_report_status():
    status = client.get("/api/compliance-status")
    assert status.status_code == 200
    status_payload = status.get_json() or {}
    assert "gitlab_configured" in status_payload
    assert "active_source" in status_payload

    engineering = client.get("/api/compliance/engineering?loopback_ip=10.1.1.1")
    assert engineering.status_code == 200
    engineering_payload = engineering.get_json() or {}
    assert "compliance" in engineering_payload

    reload_resp = client.post("/api/reload-compliance", headers=_admin_auth_header())
    assert reload_resp.status_code in {200, 503}
