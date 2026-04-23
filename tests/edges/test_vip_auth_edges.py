# -*- coding: utf-8 -*-
"""VIP/auth adapter edge tests for CI smoke diff coverage."""

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset auth env deterministically for each test.

    RU: Изолируем env через monkeypatch, без прямой мутации os.environ.
    EN: Isolate env through monkeypatch without direct os.environ mutation.
    """

    for key in (
        "APP_ENV",
        "ENVIRONMENT",
        "DEBUG",
        "ALLOW_ANONYMOUS_API_KEYS",
        "ALLOW_DEV_API_KEY",
        "API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_require_api_key_allow_anonymous_nonprod(monkeypatch: pytest.MonkeyPatch):
    from app.routers.vip import _require_api_key

    # Non-production, explicit allow
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")

    assert _require_api_key(None) == "anonymous"


def test_require_api_key_dev_fallback_returns_test_key(monkeypatch: pytest.MonkeyPatch):
    from app.routers.vip import _require_api_key

    # Non-production, no explicit allow/deny → fallback to dev test key
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DEBUG", "true")

    assert _require_api_key(None) == "test_key"


def test_require_vip_tier_missing_key_returns_403(client: TestClient):
    """Test that VIP endpoints return 403 when no API key is provided.

    RU: Тест, что VIP endpoints возвращают 403 при отсутствии API ключа.
    EN: Test that VIP endpoints return 403 when no API key is provided.

    This is a behavioral test through TestClient, not testing private router functions.
    VIP guard (require_vip_tier) is a feature-gate: missing key yields 403.
    """
    # Test without API key header
    response = client.get("/api/v1/vip/health", headers={})
    assert response.status_code == 403
    detail = str(response.json().get("detail", "")).lower()
    assert any(k in detail for k in ("vip", "access"))


def test_require_vip_tier_with_vip_key_returns_2xx(
    client: TestClient,
    vip_headers: dict[str, str],
):
    """Test that VIP endpoints return 2xx when valid VIP key is provided.

    RU: Тест, что VIP endpoints возвращают 2xx при валидном VIP ключе.
    EN: Test that VIP endpoints return 2xx when valid VIP key is provided.
    """
    response = client.get("/api/v1/vip/health", headers=vip_headers)
    assert response.status_code == 200


def test_require_valid_api_key_header_dependency_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.middleware.api_tiers import (
        TEST_KEY_PRO,
        TEST_KEY_VIP,
        SubscriptionTier,
        require_valid_api_key,
    )

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DEBUG", "true")

    free_dependency = require_valid_api_key()
    assert free_dependency(x_api_key=f" {TEST_KEY_PRO} ") == TEST_KEY_PRO

    with pytest.raises(HTTPException) as missing:
        free_dependency(x_api_key=None)
    assert missing.value.status_code == 401
    assert missing.value.detail == "API key required"

    with pytest.raises(HTTPException) as blank:
        free_dependency(x_api_key="   ")
    assert blank.value.status_code == 401
    assert blank.value.detail == "API key required"

    unknown_token = "not-configured-token"
    with pytest.raises(HTTPException) as invalid:
        free_dependency(x_api_key=unknown_token)
    assert invalid.value.status_code == 401
    assert invalid.value.detail == "Invalid API key"

    vip_dependency = require_valid_api_key(required_tier=SubscriptionTier.VIP)
    with pytest.raises(HTTPException) as insufficient:
        vip_dependency(x_api_key=TEST_KEY_PRO)
    assert insufficient.value.status_code == 401
    assert "VIP tier access" in insufficient.value.detail

    assert vip_dependency(x_api_key=TEST_KEY_VIP) == TEST_KEY_VIP


def test_get_feedback_user_derives_subject_from_validated_key() -> None:
    from app.middleware.api_tiers import TEST_KEY_PRO, derive_subject_id_from_api_key
    from app.routers.feedback import get_feedback_user

    user = asyncio.run(get_feedback_user(api_key=TEST_KEY_PRO))

    assert user.api_key == TEST_KEY_PRO
    assert user.user_id == derive_subject_id_from_api_key(TEST_KEY_PRO)


def test_require_api_key_dev_legacy_nonprod_and_prod_allow(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.routers.vip import _require_api_key_dev_legacy, TEST_KEY
    from fastapi import Request
    from unittest.mock import MagicMock

    # Dev/local: returns TEST_KEY (not anonymous) when no explicit flag
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("DEBUG", "true")
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = None
    assert _require_api_key_dev_legacy(mock_request) == TEST_KEY

    # Production with explicit anonymous allow - should raise 403 (no anonymous in prod)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ALLOW_ANONYMOUS_API_KEYS", "true")
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = None

    with pytest.raises(HTTPException) as ei:
        _require_api_key_dev_legacy(mock_request)
    assert ei.value.status_code == 403


def test_adapter_make_weekly_menu_no_profile_path():
    from app.routers.vip import _adapter_make_weekly_menu

    # Pass kwargs without any profile-like fields → expect None (echo path)
    out = _adapter_make_weekly_menu(dummy=1, data={"foo": "bar"})
    assert out is None
