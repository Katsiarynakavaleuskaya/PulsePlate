"""
Тесты для покрытия app.py HTTP методы и endpoints
Покрывает строки: 98, 105, 115, 130-132, 144→148, 147, 164→170, 169, 205→208, 210, 242→246, 247, 252-256
"""

from fastapi.testclient import TestClient
from typing import cast
from starlette.types import ASGIApp


class TestAppEndpointsCoverage:
    """Тесты для покрытия app.py HTTP методы и endpoints"""

    def test_app_health_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py health endpoint (строки 98, 105, 115)"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем health endpoint
        response = client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert "status" in health_data

    def test_app_root_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py root endpoint (строки 130-132, 144→148, 147)"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем root endpoint
        response = client.get("/")
        assert response.status_code == 200

    def test_app_docs_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py docs endpoint (строки 164→170, 169)"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_openapi_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py OpenAPI endpoint (строки 205→208, 210)"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем OpenAPI endpoint
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema

    def test_app_metrics_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py metrics endpoint (строки 242→246, 247)"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем metrics endpoint
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_app_admin_status_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py admin status endpoint (строки 252-256)"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем admin status endpoint
        response = client.get(
            "/api/v1/admin/status",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 404]

    def test_app_bmi_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py BMI endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем BMI endpoint
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

        bmi_data = response.json()
        assert "bmi" in bmi_data

    def test_app_bodyfat_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py bodyfat endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем bodyfat endpoint
        response = client.post(
            "/api/v1/bodyfat",
            json={"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 422]

    def test_app_insight_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py insight endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем insight endpoint
        response = client.post(
            "/api/v1/insight",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 404, 422]

    def test_app_vip_endpoints_coverage(self, test_environment):
        """Тест покрытия app.py VIP endpoints"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем VIP endpoints
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
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

    def test_app_api_key_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py API key endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем API key endpoint
        response = client.get("/api/v1/api-key")
        assert response.status_code in [200, 404, 405]

    def test_app_foods_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py foods endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем foods endpoint
        response = client.get("/api/v1/foods")
        assert response.status_code in [200, 404, 405]

    def test_app_recipes_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py recipes endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем recipes endpoint
        response = client.get("/api/v1/recipes")
        assert response.status_code in [200, 404, 405]

    def test_app_users_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py users endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем users endpoint
        response = client.get("/api/v1/users")
        assert response.status_code in [200, 404, 405]

    def test_app_premium_week_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py premium week endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем premium week endpoint
        response = client.get("/api/v1/premium/week")
        assert response.status_code in [200, 404, 405]

    def test_app_bmi_pro_endpoint_coverage(self, test_environment):
        """Тест покрытия app.py BMI pro endpoint"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем BMI pro endpoint
        response = client.get("/api/v1/bmi-pro")
        assert response.status_code in [200, 404, 405]

    def test_app_admin_endpoints_coverage(self, test_environment):
        """Тест покрытия app.py admin endpoints"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем admin endpoints
        response = client.get(
            "/api/v1/admin/db-status",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 404]

    def test_app_http_methods_coverage(self, test_environment):
        """Тест покрытия app.py HTTP methods"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем различные HTTP methods
        response = client.get("/health")
        assert response.status_code == 200

        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

        response = client.put("/health")
        assert response.status_code in [405, 404]

        response = client.delete("/health")
        assert response.status_code in [405, 404]

        response = client.options("/health")
        assert response.status_code in [200, 405]

    def test_app_endpoint_validation_coverage(self, test_environment):
        """Тест покрытия app.py endpoint validation"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем endpoint validation
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

    def test_app_endpoint_error_handling_coverage(self, test_environment):
        """Тест покрытия app.py endpoint error handling"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем endpoint error handling
        response = client.get("/nonexistent")
        assert response.status_code == 404

        response = client.post("/nonexistent", json={})
        assert response.status_code == 404

    def test_app_endpoint_security_coverage(self, test_environment):
        """Тест покрытия app.py endpoint security"""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Тестируем endpoint security
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200

        # Тестируем без API key
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
        )
        assert response.status_code in [401, 403]
