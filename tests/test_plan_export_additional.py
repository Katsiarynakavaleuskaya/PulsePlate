from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import plan_export
import settings


def test_slogan_default() -> None:
    assert plan_export._slogan(None) == plan_export.SLOGAN[plan_export.DEFAULT_LANG]


def test_require_valid_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    request = SimpleNamespace(query_params={}, url=SimpleNamespace(path="/api/demo"))
    monkeypatch.setattr(plan_export, "PRIVATE_EXPORTS_ENABLED", True, raising=False)
    with pytest.raises(HTTPException):
        plan_export._require_valid_token(request)


def test_require_valid_token_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    request = SimpleNamespace(query_params={}, url=SimpleNamespace(path="/api/demo"))
    monkeypatch.setattr(plan_export, "PRIVATE_EXPORTS_ENABLED", False, raising=False)
    plan_export._require_valid_token(request)


def test_require_valid_token_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    request = SimpleNamespace(
        query_params={"exp": "123", "sig": "abc"},
        url=SimpleNamespace(path="/api/demo"),
    )
    monkeypatch.setattr(plan_export, "PRIVATE_EXPORTS_ENABLED", True, raising=False)
    monkeypatch.setattr(plan_export, "verify", lambda *args, **kwargs: False)
    with pytest.raises(HTTPException):
        plan_export._require_valid_token(request)


def test_sign_export_link_invalid_path() -> None:
    payload = plan_export.SignRequest(path="/foo", ttl_seconds=10)
    with pytest.raises(HTTPException, match="path is not signable"):
        plan_export.sign_export_link(payload)


def test_sign_export_link_invalid_ttl() -> None:
    payload = plan_export.SignRequest(path=plan_export.WEEK_EXPORT_CSV_PATH, ttl_seconds=-1)
    with pytest.raises(HTTPException, match="ttl must be positive"):
        plan_export.sign_export_link(payload)


def test_sign_export_link_rejects_non_allowlisted_path() -> None:
    payload = plan_export.SignRequest(path="/api/v1/users", ttl_seconds=10)
    with pytest.raises(HTTPException, match="path is not signable"):
        plan_export.sign_export_link(payload)


def test_sign_export_link_rejects_ttl_above_configured_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(plan_export, "EXPORT_TOKEN_TTL_SECONDS", 900, raising=False)
    payload = plan_export.SignRequest(path=plan_export.WEEK_EXPORT_CSV_PATH, ttl_seconds=901)
    with pytest.raises(HTTPException, match="ttl exceeds configured max"):
        plan_export.sign_export_link(payload)


def test_sign_export_link_accepts_shoplist_path() -> None:
    payload = plan_export.SignRequest(path=plan_export.SHOPLIST_EXPORT_PDF_PATH, ttl_seconds=10)
    result = plan_export.sign_export_link(payload)
    assert result["url"].startswith(plan_export.SHOPLIST_EXPORT_PDF_PATH)


def test_export_token_secret_requires_non_default_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("PRIVATE_EXPORTS_ENABLED", "true")
    monkeypatch.delenv("EXPORT_TOKEN_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="EXPORT_TOKEN_SECRET"):
        settings.get_export_token_secret()


def test_export_token_secret_checks_environment_fallback_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("PRIVATE_EXPORTS_ENABLED", "true")
    monkeypatch.delenv("EXPORT_TOKEN_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="EXPORT_TOKEN_SECRET"):
        settings.get_export_token_secret()


def test_export_token_secret_rejects_documented_placeholder_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("PRIVATE_EXPORTS_ENABLED", "true")
    monkeypatch.setenv("EXPORT_TOKEN_SECRET", "replace_me_with_export_secret")

    with pytest.raises(RuntimeError, match="EXPORT_TOKEN_SECRET"):
        settings.get_export_token_secret()
