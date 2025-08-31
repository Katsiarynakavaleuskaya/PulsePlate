# -*- coding: utf-8 -*-
"""
RU: Насильно подменяем get_provider() на заглушку,
   чтобы пройти ветку /api/v1/insight.
EN: Monkeypatch get_provider() to a stub to exercise the insight endpoint.
"""

import pytest
from fastapi.testclient import TestClient

try:
    from app import app as fastapi_app  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

try:
    import llm  # type: ignore
except Exception as exc:  # pragma: no cover
    pytest.skip(f"llm import failed: {exc}", allow_module_level=True)

app_mod = pytest.importorskip("app")
client = TestClient(fastapi_app)


class _StubProvider:
    name = "stub-test"

    def generate(self, text: str) -> str:  # noqa: D401
        # Simple deterministic response
        return f"insight::{text[::-1]}"


class _StubProviderException:
    name = "stub-exception"

    def generate(self, text: str) -> str:
        raise RuntimeError("Simulated provider error")


def test_insight_with_monkeypatched_provider(monkeypatch):
    # Подменяем фабрику провайдера на нашу заглушку
    monkeypatch.setattr(llm, "get_provider", lambda: _StubProvider())

    r = client.post("/api/v1/insight", json={"text": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("insight", "").startswith("insight::")
    assert "hello"[::-1] in data["insight"]


def test_insight_with_provider_exception(monkeypatch):
    # Подменяем фабрику провайдера на заглушку, которая вызывает исключение
    monkeypatch.setattr(llm, "get_provider", lambda: _StubProviderException())

    r = client.post("/api/v1/insight", json={"text": "error"})
    assert r.status_code == 503
    data = r.json()
    assert "unavailable" in data.get("detail", "")


def test_insight_no_provider(monkeypatch):
    # Подменяем фабрику провайдера на None
    monkeypatch.setattr(llm, "get_provider", lambda: None)

    r = client.post("/api/v1/insight", json={"text": "test"})
    assert r.status_code == 503
    data = r.json()
    assert "not configured" in data.get("detail", "")


def test_health_smoke():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d, dict)
    assert d.get("status", "").lower() in {"ok", "healthy", "up"}
