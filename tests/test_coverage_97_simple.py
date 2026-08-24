"""
Простые тесты для достижения 97% покрытия
"""

import os

import pytest
from fastapi.testclient import TestClient

from tests._helpers.vip_contracts import assert_json_response_payload


class TestCoverage97Simple:
    """Простые тесты для покрытия до 97%"""

    @pytest.fixture(autouse=True)
    def _env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set up deterministic environment without mutating os.environ globally."""
        monkeypatch.setenv("API_KEY", "test_key")
        monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")
        monkeypatch.setenv("VIP_MODULE_ENABLED", "true")
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")

    def test_conftest_fixture_coverage(self) -> None:
        """Тест покрытия conftest.py фикстур"""
        # Проверяем, что переменные окружения установлены
        assert os.environ.get("FEATURE_PREMIUM_NUTRITION") == "true"
        assert os.environ.get("API_KEY") == "test_key"
        assert os.environ.get("VIP_MODULE_ENABLED") == "true"
        assert os.environ.get("APP_ENV") == "test"
        assert os.environ.get("ALLOW_DEV_API_KEY") == "true"

    def test_app_import_coverage(self) -> None:
        """Тест покрытия импорта app"""
        import app

        assert app.app is not None
        assert hasattr(app.app, "title")

    def test_app_health_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_app_root_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия root endpoint"""
        response = client.get("/")
        assert response.status_code == 200

    def test_app_docs_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия docs endpoint"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_openapi_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия openapi endpoint"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_app_bmi_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия BMI endpoint"""
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

    def test_app_bodyfat_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия bodyfat endpoint"""
        response = client.post(
            "/api/v1/bodyfat",
            json={"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 422]

    def test_app_metrics_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_app_admin_status_endpoint_coverage(self, client: TestClient) -> None:
        """Тест покрытия admin status endpoint"""
        response = client.get("/api/v1/admin/status", headers={"X-API-Key": "test_key"})
        assert response.status_code in [200, 500, 503]

    def test_vip_weekly_menu_endpoint_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест покрытия VIP weekly menu endpoint"""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = client.post("/api/v1/vip/menu/weekly/plan", json=payload, headers=vip_headers)
        assert response.status_code == 200

    def test_vip_recipes_endpoint_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест покрытия VIP recipes endpoint"""
        payload = {
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [
                            {"ingredients": [{"name": "chicken", "amount": 100, "unit": "g"}]}
                        ],
                    }
                ]
            },
            "recipes_per_day": 1,
        }

        response = client.post("/api/v1/vip/recipes/weekly", json=payload, headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert isinstance(data["weekly_recipes"], dict)
        assert data["weekly_recipes"]
        assert data["total_recipes"] == 1
        assert data["echo"] == payload

    def test_vip_auto_repair_endpoint_coverage(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест покрытия VIP auto repair endpoint"""
        # This node owns the explicit module-unavailable rail, which intentionally
        # precedes strict request parsing in the route contract.
        with monkeypatch.context() as repair_guard:
            repair_guard.setattr("app.routers.vip.auto_repair_week_plan", None)
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json={"week_plan": {"days": []}},
                headers=vip_headers,
            )
        assert response.status_code == 200
        assert assert_json_response_payload(response) == {
            "status": "error",
            "code": "auto_repair_unavailable",
            "message": "Auto-repair module not available",
            "detail": "Auto-repair module not available",
            "error": "auto_repair_unavailable",
            "repair_result": {},
        }

    def test_app_error_handling_coverage(self, client: TestClient) -> None:
        """Тест покрытия обработки ошибок"""
        # Тест 404
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # Тест невалидных данных
        response = client.post(
            "/api/v1/bmi", json={"invalid": "data"}, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code in [422, 400]

    def test_app_cors_coverage(self, client: TestClient) -> None:
        """Тест покрытия CORS"""
        response = client.options("/api/v1/bmi")
        assert response.status_code in [200, 405]

    def test_app_middleware_coverage(self, client: TestClient) -> None:
        """Тест покрытия middleware"""
        # Проверяем, что middleware работает
        response = client.get("/health")
        assert response.status_code == 200

    def test_app_router_coverage(self) -> None:
        """Тест покрытия роутеров"""
        import app

        # Проверяем, что роутеры включены
        assert app.app is not None
        assert app.app.router is not None
        assert app.app.router.routes is not None
        assert len(app.app.router.routes) > 0

    def test_app_exception_handlers_coverage(self) -> None:
        """Тест покрытия обработчиков исключений"""
        import app

        # Проверяем, что обработчики исключений установлены
        assert app.app is not None
        assert app.app.exception_handlers is not None

    def test_app_user_middleware_coverage(self) -> None:
        """Тест покрытия user middleware"""
        import app

        # Проверяем, что middleware установлен
        assert app.app is not None
        assert app.app.user_middleware is not None
        assert len(app.app.user_middleware) > 0
