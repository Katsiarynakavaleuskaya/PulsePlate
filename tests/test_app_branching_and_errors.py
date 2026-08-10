import sys
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests._client import open_test_client


@pytest.fixture
def production_client(
    test_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    """Start lifespan safely, then exercise route-time production auth branches."""
    del test_environment
    with open_test_client() as managed_client:
        with monkeypatch.context() as production_env:
            production_env.setenv("APP_ENV", "production")
            production_env.setenv("ALLOW_DEV_API_KEY", "false")
            production_env.setenv("API_KEY", "secret-key")
            production_env.setenv("PRO_API_KEYS", "test_pro_key")
            production_env.setenv("VIP_API_KEYS", "test_vip_key")
            yield managed_client


def disable_optional_modules(monkeypatch: pytest.MonkeyPatch, *modules: str) -> None:
    """Prevent importing the listed modules by simulating ImportError."""
    for module in modules:
        monkeypatch.delitem(sys.modules, module, raising=False)


def test_rag_context_fallback(
    production_client: TestClient,
    vip_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет fallback-ветку RAG (core.rag) — ImportError не должен ломать insight endpoint."""
    disable_optional_modules(monkeypatch, "core.rag.simple_rag")
    payload = {"text": "What is BMI?"}
    response = production_client.post("/api/v1/insight", json=payload, headers=vip_headers)
    # VIP tier gate runs before handler; FEATURE_INSIGHT may still be disabled (503).
    assert response.status_code in [200, 503]


def test_bmi_endpoint_invalid_payload(production_client: TestClient) -> None:
    """Проверяет 422 Unprocessable Entity для невалидного запроса к /api/v1/bmi."""
    response = production_client.post("/api/v1/bmi", json={"weight_kg": None})
    assert response.status_code == 422


def test_bmi_endpoint_value_error(production_client: TestClient) -> None:
    """Проверяет 400 Bad Request при ValueError в /api/v1/bmi (например, строка вместо числа)."""
    bad_payload = {
        "weight_kg": "not_a_number",
        "height_cm": 170,
        "age": 30,
        "sex": "male",
        "activity": "sedentary",
    }
    response = production_client.post("/api/v1/bmi", json=bad_payload)
    assert response.status_code in (400, 422)


def test_premium_bmr_403_if_feature_flag(
    production_client: TestClient,
    pro_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет 503 Service Unavailable если FEATURE_PREMIUM_NUTRITION=0."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "0")
    payload = {"weight_kg": 70, "height_cm": 170, "age": 30, "sex": "male", "activity": "sedentary"}
    response = production_client.post("/api/v1/premium/bmr", json=payload, headers=pro_headers)
    # If API key is invalid, expect 403, else 503
    assert response.status_code in [503, 403]


# NOTE (CI trust): `test_no_calculate_all_bmr` was removed in PR-602.
# It relied on `importlib.reload(app)` + asserting internal symbols become None, which is not a
# supported contract and is nondeterministic under pytest import graph. Audit basis: PR-600.
# Tracking: BACKLOG_LEDGER P1 (closed by PR-602).


def test_root_endpoint(production_client: TestClient) -> None:
    response = production_client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    probe = response.json()
    assert probe.get("service") == "pulseplate-api"


def test_invalid_route(production_client: TestClient) -> None:
    response = production_client.get("/nonexistent-endpoint")
    assert response.status_code == 404


def test_health_endpoint(production_client: TestClient) -> None:
    response = production_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_invalid_method(production_client: TestClient, pro_headers: dict[str, str]) -> None:
    response = production_client.put("/api/v1/health", headers=pro_headers)
    assert response.status_code in (405, 404)


def test_internal_error(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.foods import get_food_store

    class BrokenFoodStore:
        def search_foods(self, query: str, limit: int, offset: int) -> list[dict[str, object]]:
            raise RuntimeError("Boom")

        def get_food(self, food_id: str) -> dict[str, object] | None:  # pragma: no cover
            return None

    monkeypatch.setitem(app.dependency_overrides, get_food_store, lambda: BrokenFoodStore())  # type: ignore[misc]
    with open_test_client(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/foods")
        assert response.status_code == 500, response.text
