from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import plan_export


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
    with pytest.raises(HTTPException):
        plan_export.sign_export_link(payload)


def test_sign_export_link_invalid_ttl() -> None:
    payload = plan_export.SignRequest(path="/api/demo", ttl_seconds=-1)
    with pytest.raises(HTTPException):
        plan_export.sign_export_link(payload)
