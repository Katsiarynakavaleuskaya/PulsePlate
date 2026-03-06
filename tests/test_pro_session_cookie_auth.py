"""Deterministic tests for PRO web-session cookie flow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from httpx import Response as HTTPXResponse
from starlette.requests import Request

import app.routers.pro_session as pro_session_mod
from app.main import app as main_app
from app.middleware.api_tiers import AuthSource, SubscriptionTier, TEST_KEY_PRO, TierAuthContext
from app.security.web_session import WEB_SESSION_COOKIE_NAME, issue_web_session


@pytest.fixture(autouse=True)
def _session_cookie_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set deterministic env for cookie signing and local cookie policy."""

    monkeypatch.setenv("SERVER_SALT", "test-server-salt")
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DEBUG", "true")


@pytest.fixture
def isolated_client() -> TestClient:
    """Isolated TestClient without shared fixture overrides."""

    with TestClient(main_app) as test_client:
        yield test_client


def _assert_json_response(response: HTTPXResponse) -> dict[str, Any]:
    """Assert JSON content type before parsing response body."""

    content_type = response.headers.get("content-type", "").lower()
    assert content_type.startswith("application/json")
    return response.json()


def test_exchange_success_sets_hardened_cookie(
    isolated_client: TestClient, pro_headers: dict[str, str]
) -> None:
    """Exchange should issue HttpOnly Lax cookie in local mode (Secure off)."""

    response = isolated_client.post(
        "/api/v1/pro/session/exchange",
        headers=pro_headers,
    )
    assert response.status_code == 200

    body = _assert_json_response(response)
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


def test_exchange_fail_invalid_key(isolated_client: TestClient) -> None:
    """Invalid header key should be rejected at exchange."""

    response = isolated_client.post(
        "/api/v1/pro/session/exchange",
        headers={"X-API-Key": "invalid_key"},
    )
    assert response.status_code == 403
    assert "PRO tier" in _assert_json_response(response)["detail"]


def test_status_uses_cookie_after_exchange(
    isolated_client: TestClient, pro_headers: dict[str, str]
) -> None:
    """Status should authenticate with cookie when header is absent."""

    exchange = isolated_client.post(
        "/api/v1/pro/session/exchange",
        headers=pro_headers,
    )
    assert exchange.status_code == 200

    response = isolated_client.get("/api/v1/pro/session")
    assert response.status_code == 200
    body = _assert_json_response(response)
    assert body["authenticated"] is True
    assert body["auth_source"] == "cookie"
    assert body["tier"] == "PRO"
    assert body["expires_at_epoch"] >= 1


def test_header_has_precedence_over_cookie(
    isolated_client: TestClient, pro_headers: dict[str, str]
) -> None:
    """Invalid header must not fall back to valid cookie (header-first precedence)."""

    exchange = isolated_client.post(
        "/api/v1/pro/session/exchange",
        headers=pro_headers,
    )
    assert exchange.status_code == 200

    response = isolated_client.get(
        "/api/v1/pro/session",
        headers={"X-API-Key": "invalid_key"},
    )
    assert response.status_code == 403
    assert "PRO tier" in _assert_json_response(response)["detail"]


def test_refresh_and_logout_flow(isolated_client: TestClient, pro_headers: dict[str, str]) -> None:
    """Refresh keeps auth valid; logout clears cookie and blocks cookie-only status."""

    exchange = isolated_client.post(
        "/api/v1/pro/session/exchange",
        headers=pro_headers,
    )
    assert exchange.status_code == 200

    refreshed = isolated_client.post("/api/v1/pro/session/refresh")
    assert refreshed.status_code == 200
    refreshed_body = _assert_json_response(refreshed)
    assert refreshed_body["status"] == "ok"
    assert refreshed_body["auth_source"] == "cookie"
    assert f"{WEB_SESSION_COOKIE_NAME}=" in refreshed.headers.get("set-cookie", "")

    logout = isolated_client.post("/api/v1/pro/session/logout")
    assert logout.status_code == 200
    assert _assert_json_response(logout) == {"status": "ok", "logged_out": True}
    clear_cookie = logout.headers.get("set-cookie", "").lower()
    assert f"{WEB_SESSION_COOKIE_NAME}=" in clear_cookie
    assert "max-age=0" in clear_cookie

    status_after_logout = isolated_client.get("/api/v1/pro/session")
    assert status_after_logout.status_code == 401


def test_expired_cookie_is_rejected(isolated_client: TestClient) -> None:
    """Expired cookie must be rejected fail-closed."""

    issued = issue_web_session(
        api_key=TEST_KEY_PRO,
        tier="PRO",
        now=datetime(2020, 1, 1, tzinfo=timezone.utc),
        ttl_seconds=1,
    )
    isolated_client.cookies.set(WEB_SESSION_COOKIE_NAME, issued.token, path="/")

    response = isolated_client.get("/api/v1/pro/session")
    assert response.status_code == 401
    assert "API key required" in _assert_json_response(response)["detail"]


def test_invalid_cookie_is_rejected(isolated_client: TestClient) -> None:
    """Malformed/invalid signature cookie must be rejected fail-closed."""

    isolated_client.cookies.set(WEB_SESSION_COOKIE_NAME, "bad-token-value", path="/")
    response = isolated_client.get("/api/v1/pro/session")
    assert response.status_code == 401
    assert "API key required" in _assert_json_response(response)["detail"]


def test_vip_endpoint_rejects_pro_cookie(
    isolated_client: TestClient, pro_headers: dict[str, str]
) -> None:
    """VIP endpoint must reject PRO-tier cookie (no privilege escalation)."""

    exchange = isolated_client.post(
        "/api/v1/pro/session/exchange",
        headers=pro_headers,
    )
    assert exchange.status_code == 200

    response = isolated_client.get("/api/v1/vip/health")
    assert response.status_code == 403
    assert "VIP access required" in _assert_json_response(response)["detail"]


def test_get_cached_context_missing_returns_500() -> None:
    """Internal helper should fail closed when dependency did not cache auth context."""

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "scheme": "http",
            "method": "GET",
            "path": "/api/v1/pro/session",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1111),
            "server": ("testserver", 80),
        }
    )
    with pytest.raises(HTTPException) as exc_info:
        pro_session_mod._get_cached_pro_context(request)
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Missing authentication context"


def test_issue_and_set_cookie_rejects_unexpected_tier() -> None:
    """Unexpected tier should fail closed (no silent upgrade)."""

    response = Response()
    context = TierAuthContext(
        api_key=TEST_KEY_PRO,
        tier=SubscriptionTier.FREE,
        source=AuthSource.HEADER,
    )
    with pytest.raises(RuntimeError):
        pro_session_mod._issue_and_set_cookie(response=response, context=context)


def test_exchange_returns_503_when_cookie_issue_fails(
    isolated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
) -> None:
    """Exchange endpoint must return deterministic 503 on cookie issuance runtime errors."""

    monkeypatch.setattr(
        pro_session_mod,
        "_issue_and_set_cookie",
        lambda **_: (_ for _ in ()).throw(RuntimeError("session unavailable")),
    )
    response = isolated_client.post(
        "/api/v1/pro/session/exchange",
        headers=pro_headers,
    )
    assert response.status_code == 503
    assert _assert_json_response(response)["detail"] == "Web session is unavailable"


def test_refresh_returns_503_when_cookie_issue_fails(
    isolated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    pro_headers: dict[str, str],
) -> None:
    """Refresh endpoint must return deterministic 503 on cookie issuance runtime errors."""

    monkeypatch.setattr(
        pro_session_mod,
        "_issue_and_set_cookie",
        lambda **_: (_ for _ in ()).throw(RuntimeError("session unavailable")),
    )
    response = isolated_client.post(
        "/api/v1/pro/session/refresh",
        headers=pro_headers,
    )
    assert response.status_code == 503
    assert _assert_json_response(response)["detail"] == "Web session is unavailable"
