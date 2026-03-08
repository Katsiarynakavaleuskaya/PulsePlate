from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
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


def test_export_csv_route_uses_runtime_secret_accessor(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_verify(secret: str, path: str, exp_ts: int, sig: str) -> bool:
        captured["signing_value"] = secret
        captured["path"] = path
        captured["exp_ts"] = exp_ts
        captured["sig"] = sig
        return True

    monkeypatch.setattr(plan_export, "PRIVATE_EXPORTS_ENABLED", True, raising=False)
    monkeypatch.setattr(plan_export, "get_export_token_secret", lambda: "runtime-token")
    monkeypatch.setattr(plan_export, "verify", _fake_verify)

    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("API_KEY_REQUIRED", "true")

    response = client.get(
        f"{plan_export.WEEK_EXPORT_CSV_PATH}?exp=123&sig=abc",
        headers={"X-API-Key": "test_key"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    assert captured == {
        "signing_value": "runtime-token",
        "path": plan_export.WEEK_EXPORT_CSV_PATH,
        "exp_ts": 123,
        "sig": "abc",
    }


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


def test_sign_export_link_uses_runtime_secret_accessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_sign(secret: str, path: str, exp_ts: int) -> str:
        captured["signing_value"] = secret
        captured["path"] = path
        captured["exp_ts"] = exp_ts
        return "signed-value"

    monkeypatch.setattr(plan_export, "get_export_token_secret", lambda: "runtime-token")
    monkeypatch.setattr(plan_export, "sign", _fake_sign)

    payload = plan_export.SignRequest(path=plan_export.WEEK_EXPORT_CSV_PATH, ttl_seconds=10)
    result = plan_export.sign_export_link(payload)

    assert captured["signing_value"] == "runtime-token"
    assert captured["path"] == plan_export.WEEK_EXPORT_CSV_PATH
    assert isinstance(captured["exp_ts"], int)
    assert result["url"].startswith(f"{plan_export.WEEK_EXPORT_CSV_PATH}?")
    assert "sig=signed-value" in result["url"]


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


def test_export_token_ttl_rejects_non_positive_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXPORT_TOKEN_TTL_SECONDS", "0")

    with pytest.raises(RuntimeError, match="EXPORT_TOKEN_TTL_SECONDS"):
        settings.get_export_token_ttl_seconds()


def test_export_routes_are_registered_but_hidden_from_public_openapi() -> None:
    runtime_paths = {
        getattr(route, "path", None)
        for route in app.routes
        if getattr(route, "path", None)
        in {
            "/api/v1/export/sign",
            plan_export.WEEK_EXPORT_CSV_PATH,
            plan_export.WEEK_EXPORT_PDF_PATH,
        }
    }
    public_paths = app.openapi()["paths"]

    assert runtime_paths == {
        "/api/v1/export/sign",
        plan_export.WEEK_EXPORT_CSV_PATH,
        plan_export.WEEK_EXPORT_PDF_PATH,
    }
    assert "/api/v1/export/sign" not in public_paths
    assert plan_export.WEEK_EXPORT_CSV_PATH not in public_paths
    assert plan_export.WEEK_EXPORT_PDF_PATH not in public_paths
