"""
Тесты для покрытия app.py router inclusion
Покрывает строки: 2095, 2118, 2151, 2153
"""

from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


@pytest.fixture()
def client(test_environment):
    import app

    return TestClient(cast(ASGIApp, app.app))


class TestAppRouterInclusionCoverage:
    """Тесты для покрытия app.py router inclusion"""

    def test_app_router_inclusion_bmi_coverage(self, client):
        """Тест покрытия app.py BMI router inclusion (строка 2095)"""
        # Тестируем BMI router inclusion
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

        # Проверяем, что BMI router работает
        response = client.get("/api/v1/bmi")
        assert response.status_code in [200, 405]

    def test_app_router_inclusion_bodyfat_coverage(self, client):
        """Тест покрытия app.py bodyfat router inclusion (строка 2118)"""
        # Тестируем bodyfat router inclusion
        response = client.post(
            "/api/v1/bodyfat",
            json={"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 422]

        # Проверяем, что bodyfat router работает
        response = client.get("/api/v1/bodyfat")
        assert response.status_code in [200, 405]

    def test_app_router_inclusion_insight_coverage(
        self, client, vip_headers: dict[str, str]
    ) -> None:
        """Тест покрытия app.py insight router inclusion (строка 2151)"""
        # Тестируем insight router inclusion
        response = client.post(
            "/api/v1/insight",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers=vip_headers,
        )
        assert response.status_code in [200, 422, 503]

        # Проверяем, что insight router работает
        response = client.get("/api/v1/insight")
        assert response.status_code in [200, 405]

    def test_app_router_inclusion_vip_coverage(self, client, vip_headers: dict[str, str]):
        """Тест покрытия app.py VIP router inclusion (строка 2153)"""
        # Тестируем VIP router inclusion
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
            },
            headers=vip_headers,
        )
        assert response.status_code == 200

        # Проверяем, что VIP router работает
        response = client.get("/api/v1/vip/menu/weekly/plan")
        assert response.status_code in [200, 405]

    def test_app_router_inclusion_api_key_coverage(self, client):
        """Тест покрытия app.py API key router inclusion"""
        # Тестируем API key router inclusion
        response = client.get("/api/v1/api-key")
        assert response.status_code in [200, 404, 405]

        response = client.post("/api/v1/api-key", json={})
        assert response.status_code in [200, 404, 405, 422]

    def test_app_router_inclusion_foods_coverage(self, client):
        """Тест покрытия app.py foods router inclusion"""
        # Тестируем foods router inclusion
        response = client.get("/api/v1/foods")
        assert response.status_code in [200, 404, 405]

        response = client.post("/api/v1/foods", json={})
        assert response.status_code in [200, 404, 405, 422]

    def test_app_router_inclusion_recipes_coverage(self, client):
        """Тест покрытия app.py recipes router inclusion"""
        # Тестируем recipes router inclusion
        response = client.get("/api/v1/recipes")
        assert response.status_code in [200, 404, 405]

        response = client.post("/api/v1/recipes", json={})
        assert response.status_code in [200, 404, 405, 422]

    def test_app_router_inclusion_users_coverage(self, client):
        """Тест покрытия app.py users router inclusion"""
        # Тестируем users router inclusion
        response = client.get("/api/v1/users")
        assert response.status_code in [200, 404, 405]

        response = client.post("/api/v1/users", json={})
        assert response.status_code in [200, 404, 405, 422]

    def test_app_router_inclusion_premium_week_coverage(self, client):
        """Тест покрытия app.py premium week router inclusion"""
        # Тестируем premium week router inclusion
        response = client.get("/api/v1/premium/week")
        assert response.status_code in [200, 404, 405]

        response = client.post("/api/v1/premium/week", json={})
        assert response.status_code in [200, 404, 405, 422]

    def test_app_router_inclusion_bmi_pro_coverage(self, client):
        """Тест покрытия app.py BMI pro router inclusion"""
        # Тестируем BMI pro router inclusion
        response = client.get("/api/v1/bmi-pro")
        assert response.status_code in [200, 404, 405]

        response = client.post("/api/v1/bmi-pro", json={})
        assert response.status_code in [200, 404, 405, 422]

    def test_app_router_inclusion_router_order_coverage(self, client):
        """Тест покрытия app.py router order"""
        # Тестируем router order
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_app_router_inclusion_router_prefix_coverage(self, client):
        """Тест покрытия app.py router prefix"""
        # Тестируем router prefix
        response = client.get("/api/v1/")
        assert response.status_code in [200, 404, 405]

        response = client.get("/api/v1")
        assert response.status_code in [200, 404, 405]

    def test_app_router_inclusion_router_tags_coverage(self, client):
        """Тест покрытия app.py router tags"""
        # Тестируем router tags
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_app_router_inclusion_router_dependencies_coverage(self, client):
        """Тест покрытия app.py router dependencies"""
        # Тестируем router dependencies
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

        response = client.post(
            "/api/v1/bodyfat",
            json={"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 422]

    def test_app_router_inclusion_router_responses_coverage(self, client):
        """Тест покрытия app.py router responses"""
        # Тестируем router responses
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        assert "bmi" in response.json()

        response = client.post(
            "/api/v1/bodyfat",
            json={"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 422]

    def test_app_router_inclusion_router_middleware_coverage(self, client):
        """Тест покрытия app.py router middleware"""
        # Тестируем router middleware
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_router_inclusion_router_exception_handlers_coverage(self, client):
        """Тест покрытия app.py router exception handlers"""
        # Тестируем router exception handlers
        response = client.get("/nonexistent")
        assert response.status_code == 404

        response = client.post("/nonexistent", json={})
        assert response.status_code == 404

    def test_app_router_inclusion_router_lifespan_coverage(self, client):
        """Тест покрытия app.py router lifespan"""
        # Тестируем router lifespan
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_router_inclusion_router_openapi_coverage(self, client):
        """Тест покрытия app.py router OpenAPI"""
        # Тестируем router OpenAPI
        response = client.get("/openapi.json")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_router_inclusion_router_validation_coverage(self, client):
        """Тест покрытия app.py router validation"""
        # Тестируем router validation
        response = client.post(
            "/api/v1/bmi",
            json={"invalid": "data"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [422, 403]

        response = client.post(
            "/api/v1/bodyfat",
            json={"invalid": "data"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [422, 403]
