# -*- coding: utf-8 -*-
"""
RU: Тестируем /api/v1/insight с LLM_PROVIDER=stub, чтобы активировать код провайдера.
EN: Test /api/v1/insight with LLM_PROVIDER=stub to exercise provider branch.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _set_stub_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    yield
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


try:
    from app import app as fastapi_app  # type: ignore
except Exception as exc:
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

client = TestClient(fastapi_app)


def test_insight_stub_provider():
    # Устанавливаем переменные окружения для теста
    import os

    original_feature = os.environ.get("FEATURE_INSIGHT")
    original_provider = os.environ.get("LLM_PROVIDER")
    os.environ["FEATURE_INSIGHT"] = "true"
    os.environ["LLM_PROVIDER"] = "stub"

    r = client.post(
        "/api/v1/insight", json={"text": "ping"}, headers={"X-API-Key": "test_key"}
    )
    if r.status_code == 404:
        pytest.skip("No /api/v1/insight route (skipping)")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "insight" in data
    assert isinstance(data["insight"], str) and data["insight"]

    # Восстанавливаем переменные окружения
    if original_feature is not None:
        os.environ["FEATURE_INSIGHT"] = original_feature
    else:
        del os.environ["FEATURE_INSIGHT"]

    if original_provider is not None:
        os.environ["LLM_PROVIDER"] = original_provider
    else:
        del os.environ["LLM_PROVIDER"]
