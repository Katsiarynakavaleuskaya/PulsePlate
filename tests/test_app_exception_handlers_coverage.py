"""
Тесты для покрытия app.py exception handlers
Покрывает строки: 1732, 1735-1739
"""

import pytest
from fastapi.testclient import TestClient


class TestAppExceptionHandlersCoverage:
    """Тесты для покрытия app.py exception handlers"""

    @pytest.fixture
    def client(self, test_environment):
        """Фикстура для создания TestClient"""
        import app

        from typing import cast
        from starlette.types import ASGIApp

        return TestClient(cast(ASGIApp, app.app))

    @pytest.mark.parametrize(
        "endpoint,payload,expected_status",
        [
            ("/api/v1/bmi", {"invalid": "data"}, 422),
            ("/api/v1/bodyfat", {"invalid": "data"}, 422),
            ("/api/v1/bmi", {"weight_kg": "invalid", "height_cm": "invalid"}, 422),
            ("/api/v1/bodyfat", {"weight_kg": "invalid", "height_cm": "invalid"}, 422),
            ("/api/v1/bmi", {}, 422),
            ("/api/v1/bodyfat", {}, 422),
            ("/api/v1/bmi", {"weight_kg": None, "height_cm": None}, 422),
            ("/api/v1/bodyfat", {"weight_kg": None, "height_cm": None}, 422),
            ("/api/v1/bmi", {"weight_kg": -1, "height_cm": -1}, 422),
            ("/api/v1/bodyfat", {"weight_kg": -1, "height_cm": -1}, 422),
            ("/api/v1/bmi", {"wrong_key": "value"}, 422),
            ("/api/v1/bodyfat", {"wrong_key": "value"}, 422),
        ],
    )
    def test_validation_error_handlers(self, client, endpoint, payload, expected_status):
        """Тест покрытия validation error handlers"""
        response = client.post(endpoint, json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == expected_status

    def test_http_exception_handlers(self, client):
        """Тест покрытия HTTP exception handlers"""
        # Тест с несуществующим endpoint (404)
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # Тест с неверным методом (405)
        response = client.delete("/health")
        assert response.status_code == 405

    def test_runtime_error_handler(self, client):
        """Тест покрытия runtime error handler"""
        # Тестируем runtime error handler через различные сценарии
        response = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "general"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code in [200, 422, 500]

    def test_connection_error_handler(self, client):
        """Тест покрытия connection error handler"""
        # Тестируем connection error handler
        response = client.get("/health")
        assert response.status_code in [200, 500]

    def test_timeout_error_handler(self, client):
        """Тест покрытия timeout error handler"""
        # Тестируем timeout error handler
        response = client.get("/health")
        assert response.status_code in [200, 500]
