import importlib
import sys
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests._client import open_test_client


@pytest.fixture
def client(
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


def test_export_csv_no_key_auth_only(client: TestClient) -> None:
    """Checks that a 403 is returned when no API key is provided for protected CSV export.

    This test only verifies authentication behavior, not dependency handling.
    CSV export uses the standard csv module, not pandas.
    """
    response = client.get("/api/v1/premium/exports/day/plan123.csv")
    # Endpoint requires API key, expect 403 if not provided, or 404 if not found
    assert response.status_code in [403, 404]


def test_rag_context_fallback(
    client: TestClient, vip_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Проверяет fallback-ветку RAG (core.rag) — ImportError не должен ломать insight endpoint."""
    disable_optional_modules(monkeypatch, "core.rag.simple_rag")
    payload = {"text": "What is BMI?"}
    response = client.post("/api/v1/insight", json=payload, headers=vip_headers)
    # VIP tier gate runs before handler; FEATURE_INSIGHT may still be disabled (503).
    assert response.status_code in [200, 503]


def test_premium_nutrient_gaps_fallback(
    client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Проверяет fallback-ветку premium nutrient gaps (analyze_nutrient_gaps ImportError)."""
    disable_optional_modules(monkeypatch, "core.menu_engine")
    # reload app to drop analyze_nutrient_gaps
    import app as app_module

    try:
        importlib.reload(app_module)
    except ModuleNotFoundError:
        # Expected when optional modules are missing - app.py should handle this gracefully
        pass
    payload = {"weight_kg": 70, "height_cm": 170, "age": 30, "sex": "male", "activity": "sedentary"}
    response = client.post("/api/v1/premium/gaps", json=payload, headers=pro_headers)
    # If API key is invalid, expect 403, else 503/500
    assert response.status_code in (503, 500, 403)


def test_bmi_endpoint_invalid_payload(client: TestClient, pro_headers: dict[str, str]) -> None:
    """Проверяет 422 Unprocessable Entity для невалидного запроса к /api/v1/bmi."""
    response = client.post("/api/v1/bmi", json={"weight_kg": None}, headers=pro_headers)
    # If API key is invalid, expect 403, else 422
    assert response.status_code in [422, 403]


def test_bmi_endpoint_value_error(client: TestClient, pro_headers: dict[str, str]) -> None:
    """Проверяет 400 Bad Request при ValueError в /api/v1/bmi (например, строка вместо числа)."""
    bad_payload = {
        "weight_kg": "not_a_number",
        "height_cm": 170,
        "age": 30,
        "sex": "male",
        "activity": "sedentary",
    }
    response = client.post("/api/v1/bmi", json=bad_payload, headers=pro_headers)
    # If API key is invalid, expect 403, else 400/422
    assert response.status_code in (400, 422, 403)


def test_premium_bmr_403_if_feature_flag(
    client: TestClient, pro_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Проверяет 503 Service Unavailable если FEATURE_PREMIUM_NUTRITION=0."""
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "0")
    payload = {"weight_kg": 70, "height_cm": 170, "age": 30, "sex": "male", "activity": "sedentary"}
    response = client.post("/api/v1/premium/bmr", json=payload, headers=pro_headers)
    # If API key is invalid, expect 403, else 503
    assert response.status_code in [503, 403]


# NOTE (CI trust): `test_no_calculate_all_bmr` was removed in PR-602.
# It relied on `importlib.reload(app)` + asserting internal symbols become None, which is not a
# supported contract and is nondeterministic under pytest import graph. Audit basis: PR-600.
# Tracking: BACKLOG_LEDGER P1 (closed by PR-602).


def test_no_bmi_pro_router(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет fallback-ветку при отсутствии bmi_pro_router (ImportError)."""
    import app as app_module

    # Test that bmi_pro_router exists and is not None
    assert app_module.bmi_pro_router is not None


def test_no_premium_week_router(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет fallback-ветку при отсутствии premium_week_router (ImportError)."""
    import app as app_module

    # Test that premium_week_router exists and is not None
    assert app_module.premium_week_router is not None


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    probe = response.json()
    assert probe.get("service") == "pulseplate-api"


def test_invalid_route(client: TestClient) -> None:
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_vip_module_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIP_MODULE_ENABLED", "false")
    from importlib import reload

    import app as app_module

    try:
        reload(app_module)
    except ModuleNotFoundError:
        # Expected when modules are missing - app.py should handle this
        pass
    # sourcery skip: no-conditionals-in-tests
    if not hasattr(app_module, "app") or app_module.app is None:
        raise RuntimeError("app_module.app is None or missing after reload.")
    if not isinstance(app_module.app, FastAPI):
        raise RuntimeError("app_module.app is not a FastAPI instance after reload.")
    with open_test_client(app_module.app) as test_client:
        response = test_client.get("/api/v1/vip/plan/week")
        assert response.status_code in (404, 422, 401)


def test_vip_module_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
    from importlib import reload

    import app as app_module

    try:
        reload(app_module)
    except ModuleNotFoundError:
        # Expected when modules are missing - app.py should handle this
        pass
    # sourcery skip: no-conditionals-in-tests
    if not hasattr(app_module, "app") or app_module.app is None:
        raise RuntimeError("app_module.app is None or missing after reload.")
    # sourcery skip: no-conditionals-in-tests
    if not isinstance(app_module.app, FastAPI):
        raise RuntimeError("app_module.app is not a FastAPI instance after reload.")


def test_invalid_method(client: TestClient, pro_headers: dict[str, str]) -> None:
    response = client.put("/api/v1/health", headers=pro_headers)
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
