from typing import cast

from starlette.types import ASGIApp
from app.middleware.api_tiers import TEST_KEY_VIP


def test_api_key_strict_production_requires_config(monkeypatch):
    import os

    from fastapi.testclient import TestClient

    import app

    # RU: BMI endpoint теперь публичный - работает без ключа даже в продакшене
    # EN: BMI endpoint is now public - works without key even in production
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")
    monkeypatch.delenv("API_KEY", raising=False)

    client = TestClient(cast(ASGIApp, app.app))
    r = client.post("/api/v1/bmi", json={"weight_kg": 70, "height_cm": 170, "group": "general"})
    assert r.status_code == 200  # BMI is public now

    # RU: BMI endpoint публичный - работает даже с неправильным ключом
    # EN: BMI endpoint is public - works even with wrong key
    r2 = client.post(
        "/api/v1/bmi",
        json={"weight_kg": 70, "height_cm": 170, "group": "general"},
        headers={"X-API-Key": "bad"},
    )
    assert r2.status_code == 200  # BMI is public now


def test_insight_feature_disabled_and_import_error(monkeypatch):
    import sys
    import types

    from fastapi.testclient import TestClient

    import app

    client = TestClient(cast(ASGIApp, app.app))

    # RU: FEATURE_INSIGHT выключен → 503 (legacy path)
    # EN: FEATURE_INSIGHT disabled → 503 (legacy path)
    monkeypatch.delenv("FEATURE_INSIGHT", raising=False)
    r = client.post("/insight", json={"text": "hello"}, headers={"X-API-Key": TEST_KEY_VIP})
    assert r.status_code == 503

    # RU: Включаем флаг и ломаем импорт llm → 503 (v1 path)
    # EN: Enable flag and break llm import → 503 (v1 path)
    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    mod = types.ModuleType("llm")  # no get_provider → ImportError on from llm import get_provider
    monkeypatch.setitem(sys.modules, "llm", mod)
    r2 = client.post(
        "/api/v1/insight",
        json={"text": "hello"},
        headers={"X-API-Key": TEST_KEY_VIP},
    )
    # Feature enabled but llm import broken → 503
    assert r2.status_code == 503


def test_admin_status_scheduler_error_paths(monkeypatch, api_key):
    from fastapi.testclient import TestClient

    import app

    client = TestClient(cast(ASGIApp, app.app))

    # RU: Планировщик отсутствует → 503
    # EN: Scheduler None → 503
    async def _none_sched():
        return None

    monkeypatch.setattr(app, "get_update_scheduler", _none_sched, raising=True)
    r = client.get("/api/v1/admin/status", headers={"X-API-Key": api_key})
    assert r.status_code == 503

    # RU: Исключение от геттера → 503
    # EN: Getter raises → 503
    async def _boom():
        raise RuntimeError("x")

    monkeypatch.setattr(app, "get_update_scheduler", _boom, raising=True)
    r2 = client.get("/api/v1/admin/status", headers={"X-API-Key": api_key})
    assert r2.status_code == 503


def test_export_pdf_generic_error_branches(monkeypatch):
    from fastapi.testclient import TestClient

    import app

    client = TestClient(cast(ASGIApp, app.app))
    headers = {"X-API-Key": "test_key"}

    # RU: Пустой пейлоад → 400
    # EN: Empty payload → 400
    r = client.post("/api/v1/export/pdf", json={}, headers=headers)
    assert r.status_code == 400

    # RU: Отсутствует to_pdf_day → 503
    # EN: Missing to_pdf_day → 503
    monkeypatch.setattr(app, "to_pdf_day", None, raising=False)
    r2 = client.post("/api/v1/export/pdf", json={"meals": []}, headers=headers)
    assert r2.status_code == 503
