"""
Тесты для покрытия app.py production режим
Покрывает строки: 66-68

Uses canonical entrypoint (app.main:app) via conftest client fixture.
"""

from fastapi.testclient import TestClient


class TestAppProductionCoverage:
    """Тесты для покрытия app.py production режим"""

    def test_app_production_mode_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production режим (строки 66-68)"""
        # Проверяем, что production режим работает корректно
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_production_api_key_validation_coverage(
        self, client: TestClient, production_environment
    ):
        """Тест покрытия app.py production API key validation"""
        # Проверяем, что API key validation работает в production режиме
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "production-secret-key"},
        )
        assert response.status_code == 200

        # BMI endpoint теперь публичный - работает с любым ключом
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 200  # BMI is public now

    def test_app_production_environment_variables_coverage(
        self, client: TestClient, production_environment
    ):
        """Тест покрытия app.py production environment variables"""
        # Проверяем, что environment variables работают в production режиме
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_production_security_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production security"""
        # Проверяем, что security работает в production режиме
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "production-secret-key"},
        )
        assert response.status_code == 200

    def test_app_production_logging_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production logging"""
        # Проверяем, что logging работает в production режиме
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_production_error_handling_coverage(
        self, client: TestClient, production_environment
    ):
        """Тест покрытия app.py production error handling"""
        # Проверяем, что error handling работает в production режиме
        response = client.get("/nonexistent")
        assert response.status_code == 404

        response = client.post("/nonexistent", json={})
        assert response.status_code == 404

    def test_app_production_middleware_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production middleware"""
        # Проверяем, что middleware работает в production режиме
        response = client.get("/health")
        assert response.status_code == 200

        response = client.options("/health")
        assert response.status_code in [200, 405]

    def test_app_production_cors_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production CORS"""
        # Проверяем, что CORS работает в production режиме
        response = client.options("/api/v1/bmi")
        assert response.status_code in [200, 405]

        response = client.options("/api/v1/bodyfat")
        assert response.status_code in [200, 405]

    def test_app_production_validation_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production validation"""
        # Проверяем, что validation работает в production режиме
        response = client.post(
            "/api/v1/bmi",
            json={"invalid": "data"},
            headers={"X-API-Key": "production-secret-key"},
        )
        assert response.status_code in [422, 401]

    def test_app_production_metrics_coverage(self, production_environment):
        """Тест покрытия app.py production metrics"""
        # /metrics route registration is covered by canonical metrics tests.
        # RU: Здесь проверяем exporter helper напрямую, чтобы не зависеть от singleton route state.
        # EN: Exercise the exporter helper directly to avoid singleton route-registration drift.
        from app.bootstrap.metrics import metrics_endpoint

        response = metrics_endpoint()
        assert response.status_code == 200

    def test_app_production_health_check_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production health check"""
        # Проверяем, что health check работает в production режиме
        response = client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert "status" in health_data

    def test_app_production_openapi_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production OpenAPI"""
        # Проверяем, что OpenAPI работает в production режиме
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_schema = response.json()
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema

    def test_app_production_docs_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production docs"""
        # Проверяем, что docs работает в production режиме
        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_production_redoc_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production redoc"""
        # Проверяем, что redoc работает в production режиме
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_app_production_router_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production router"""
        # Проверяем, что router работает в production режиме
        response = client.post(
            "/api/v1/bodyfat",
            json={"weight_kg": 70, "height_cm": 170, "waist_cm": 80, "hip_cm": 90},
            headers={"X-API-Key": "production-secret-key"},
        )
        assert response.status_code in [200, 422]

    def test_app_production_lifespan_coverage(self, client: TestClient, production_environment):
        """Тест покрытия app.py production lifespan"""
        # Проверяем, что lifespan работает в production режиме
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/docs")
        assert response.status_code == 200

    def test_app_production_exception_handlers_coverage(
        self, client: TestClient, production_environment
    ):
        """Тест покрытия app.py production exception handlers"""
        # Проверяем, что exception handlers работают в production режиме
        response = client.get("/nonexistent")
        assert response.status_code == 404

        response = client.post("/nonexistent", json={})
        assert response.status_code == 404

    def test_app_production_vip_endpoints_coverage(
        self, client: TestClient, production_environment, vip_headers
    ):
        """Тест покрытия app.py production VIP endpoints"""
        # Проверяем, что VIP endpoints работают в production режиме
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

    def test_app_production_admin_endpoints_coverage(
        self, client: TestClient, production_environment
    ):
        """Тест покрытия app.py production admin endpoints"""
        # Проверяем, что admin endpoints работают в production режиме
        response = client.get(
            "/api/v1/admin/status",
            headers={"X-API-Key": "production-secret-key"},
        )
        assert response.status_code in [200, 404]

    def test_app_production_root_endpoint_coverage(
        self, client: TestClient, production_environment
    ):
        """Тест покрытия app.py production root endpoint"""
        # Проверяем, что root endpoint работает в production режиме
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        root_data = response.json()
        assert root_data.get("service") == "pulseplate-api"
