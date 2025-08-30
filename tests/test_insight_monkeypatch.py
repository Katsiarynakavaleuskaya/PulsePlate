# -*- coding: utf-8 -*-
"""
RU: Насильно подменяем get_provider() на заглушку, чтобы пройти ветку /api/v1/insight.
EN: Monkeypatch get_provider() to a stub to exercise the insight endpoint.
"""

import pytest
from fastapi.testclient import TestClient

try:
    import app as app_mod  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(app_mod.app)  # type: ignore


class _StubProvider:
    name = "stub-test"

    def generate(self, text: str) -> str:  # noqa: D401
        # Simple deterministic response
        return f"insight::{text[::-1]}"


def test_insight_with_monkeypatched_provider(monkeypatch):
    # Если маршрута нет — аккуратно скипаем
    r0 = client.post("/api/v1/insight", json={"text": "probe"})
    if r0.status_code == 404:
        pytest.skip("No /api/v1/insight route (skipping)")

    # Подменяем фабрику провайдера на нашу заглушку
    monkeypatch.setattr(app_mod, "get_provider", lambda: _StubProvider())

    r = client.post("/api/v1/insight", json={"text": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("insight", "").startswith("insight::")
    assert "hello"[::-1] in data["insight"]


def test_health_smoke():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d, dict)
    assert d.get("status", "").lower() in {"ok", "healthy", "up"}
