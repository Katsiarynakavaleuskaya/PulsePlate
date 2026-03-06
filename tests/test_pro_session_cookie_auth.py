"""Deterministic tests for PRO web-session cookie flow."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO
from app.security.web_session import WEB_SESSION_COOKIE_NAME, issue_web_session


@pytest.fixture(autouse=True)
def _session_cookie_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set deterministic env for cookie signing and local cookie policy."""

    monkeypatch.setenv("SERVER_SALT", "test-server-salt")
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DEBUG", "true")


def test_exchange_success_sets_hardened_cookie(client: TestClient) -> None:
    """Exchange should issue HttpOnly Lax cookie in local mode (Secure off)."""

    response = client.post(
        "/api/v1/pro/session/exchange",
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["tier"] == "PRO"
    assert body["auth_source"] == "header"
    assert body["ttl_seconds"] >= 1
    assert body["expires_at_epoch"] >= 1

    set_cookie = response.headers.get("set-cookie", "")
    assert f"{WEB_SESSION_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    assert "secure" not in set_cookie.lower()


def test_exchange_fail_invalid_key(client: TestClient) -> None:
    """Invalid header key should be rejected at exchange."""

    response = client.post(
        "/api/v1/pro/session/exchange",
        headers={"X-API-Key": "invalid_key"},
    )
    assert response.status_code == 403
    assert "PRO tier" in response.json()["detail"]


def test_status_uses_cookie_after_exchange(client: TestClient) -> None:
    """Status should authenticate with cookie when header is absent."""

    exchange = client.post(
        "/api/v1/pro/session/exchange",
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert exchange.status_code == 200

    response = client.get("/api/v1/pro/session")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["auth_source"] == "cookie"
    assert body["tier"] == "PRO"
    assert body["expires_at_epoch"] >= 1


def test_header_has_precedence_over_cookie(client: TestClient) -> None:
    """Invalid header must not fall back to valid cookie (header-first precedence)."""

    exchange = client.post(
        "/api/v1/pro/session/exchange",
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert exchange.status_code == 200

    response = client.get(
        "/api/v1/pro/session",
        headers={"X-API-Key": "invalid_key"},
    )
    assert response.status_code == 403
    assert "PRO tier" in response.json()["detail"]


def test_refresh_and_logout_flow(client: TestClient) -> None:
    """Refresh keeps auth valid; logout clears cookie and blocks cookie-only status."""

    exchange = client.post(
        "/api/v1/pro/session/exchange",
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert exchange.status_code == 200

    refreshed = client.post("/api/v1/pro/session/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "ok"
    assert refreshed.json()["auth_source"] == "cookie"
    assert f"{WEB_SESSION_COOKIE_NAME}=" in refreshed.headers.get("set-cookie", "")

    logout = client.post("/api/v1/pro/session/logout")
    assert logout.status_code == 200
    assert logout.json() == {"status": "ok", "logged_out": True}
    clear_cookie = logout.headers.get("set-cookie", "").lower()
    assert f"{WEB_SESSION_COOKIE_NAME}=" in clear_cookie
    assert "max-age=0" in clear_cookie

    status_after_logout = client.get("/api/v1/pro/session")
    assert status_after_logout.status_code == 401


def test_expired_cookie_is_rejected(client: TestClient) -> None:
    """Expired cookie must be rejected fail-closed."""

    issued = issue_web_session(
        api_key=TEST_KEY_PRO,
        tier="PRO",
        now=datetime(2020, 1, 1, tzinfo=timezone.utc),
        ttl_seconds=1,
    )
    client.cookies.set(WEB_SESSION_COOKIE_NAME, issued.token, path="/")

    response = client.get("/api/v1/pro/session")
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]


def test_invalid_cookie_is_rejected(client: TestClient) -> None:
    """Malformed/invalid signature cookie must be rejected fail-closed."""

    client.cookies.set(WEB_SESSION_COOKIE_NAME, "bad-token-value", path="/")
    response = client.get("/api/v1/pro/session")
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]


def test_vip_endpoint_rejects_pro_cookie(client: TestClient) -> None:
    """VIP endpoint must reject PRO-tier cookie (no privilege escalation)."""

    exchange = client.post(
        "/api/v1/pro/session/exchange",
        headers={"X-API-Key": TEST_KEY_PRO},
    )
    assert exchange.status_code == 200

    response = client.get("/api/v1/vip/health")
    assert response.status_code == 403
    assert "VIP access required" in response.json()["detail"]
