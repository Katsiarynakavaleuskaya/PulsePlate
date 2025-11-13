"""
Combined app error handling tests: critical lines coverage and exception handlers.

RU: Объединенные тесты для обработки ошибок app: критичные линии покрытия и exception handlers
EN: Combined tests for app error handling: critical lines coverage and exception handlers

These tests cover critical uncovered lines in main.py and exception handler coverage.
"""

import sys
from typing import Callable, NoReturn, Optional
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

import app
from tests.test_utils import FailingProvider, SlowProvider


def find_endpoint_dependency(
    app_instance, endpoint_name: str, dependency_name: str
) -> Optional[Callable]:
    """
    Find a dependency function for a specific endpoint.

    RU: Находит функцию зависимости для конкретного эндпоинта
    EN: Finds a dependency function for a specific endpoint

    Args:
        app_instance: FastAPI app instance
        endpoint_name: Name of the endpoint function (e.g., "insight_v1")
        dependency_name: Name of the dependency function (e.g., "_get_api_key_dynamic")

    Returns:
        The dependency callable if found, None otherwise
    """
    for route in app_instance.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is not None and endpoint.__name__ == endpoint_name:
            for dep in getattr(route, "dependant", object()).dependencies:  # type: ignore[arg-type]
                if getattr(dep.call, "__name__", "") == dependency_name:
                    return dep.call
    return None


class TestAppCriticalLines97:
    """Test the most critical uncovered lines in main.py"""

    def test_invalid_json_malformed_request(self, client: TestClient) -> None:
        """Test malformed JSON - error handling lines"""
        # Send invalid JSON to public BMI endpoint (without API key)
        # This string will fail json.loads because JSON requires double quotes and proper identifiers
        malformed_json = "{'invalid': json}"
        response = client.post(
            "/api/v1/bmi",
            content=malformed_json,
            headers={"Content-Type": "application/json"},  # No X-API-Key - BMI is public
        )
        assert response.status_code in [422, 400]

    def test_error_handling_edge_paths(self, client: TestClient) -> None:
        """Test various error handling paths"""
        # Test with empty request body on real endpoint
        response = client.post("/api/v1/bmi", headers={"Content-Type": "application/json"})
        assert response.status_code in [422, 400]  # BMI is public now, no 403

        # BMI endpoint is now public - works without API key
        response = client.post(
            "/api/v1/bmi", json={"sex": "male", "age": 30, "height_cm": 175, "weight_kg": 70}
        )
        assert response.status_code == 200  # BMI is public, valid payload returns 200

    def test_premium_endpoints_error_paths(self, client: TestClient) -> None:
        """Test error paths in premium endpoints"""
        # Test with invalid parameters on existing endpoint
        response = client.post("/premium_targets", json={"sex": "invalid", "age": -1})
        assert response.status_code in [422, 400, 403, 404]

    def test_health_endpoint_coverage(self, client: TestClient) -> None:
        """Test health endpoint for coverage"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_cors_and_middleware_paths(self, client: TestClient) -> None:
        """Test CORS and middleware paths"""
        # Options request for CORS
        response = client.options("/health")
        assert response.status_code in [200, 405]
        if response.status_code == 200:
            assert "access-control-allow-origin" in {
                k.lower(): v for k, v in response.headers.items()
            }

    def test_exception_handling_paths(self, client: TestClient) -> None:
        """Test exception handling paths"""
        # Test with very large JSON payload to reliably test size limits
        # Increased from 10k to 100k for more reliable testing
        large_data = {"data": "x" * 100000}
        response = client.post("/api/v1/bmi", json=large_data)
        assert response.status_code in [422, 400, 413]

    def test_various_endpoints_coverage(self, client: TestClient) -> None:
        """Test various endpoints for coverage"""
        # Test main endpoints
        endpoints = ["/", "/health", "/docs"]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404, 307]


class TestAppExceptionHandlersCoverage:
    """Tests for app.py exception handlers coverage"""

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
    def test_validation_error_handlers(
        self, client: TestClient, endpoint: str, payload: dict, expected_status: int
    ) -> None:
        """Test validation error handlers coverage"""
        # Build headers dict per test case based on endpoint parameter
        # (include API key for authenticated endpoints)
        headers = {}
        if "bodyfat" in endpoint:  # Bodyfat endpoint requires authentication
            headers["X-API-Key"] = "test_key"

        response = client.post(endpoint, json=payload, headers=headers)
        assert response.status_code == expected_status

    def test_http_exception_handlers(self, client: TestClient) -> None:
        """Test HTTP exception handlers coverage"""
        # Test with non-existent endpoint (404)
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # Test with wrong method (405)
        response = client.delete("/health")
        assert response.status_code == 405

    def test_runtime_error_handler(self, client: TestClient) -> None:
        """Test runtime error handler coverage: BMI endpoint is now public, test on another."""

        # BMI endpoint no longer uses get_api_key, use insight endpoint
        def _fail_api_key(_: str = "") -> NoReturn:
            raise RuntimeError("boom")

        if app.app is None:
            pytest.skip("app.app is None - cannot run integration test")

        dependency = find_endpoint_dependency(client.app, "insight_v1", "_get_api_key_dynamic")
        if dependency is None:
            dependency = app._get_api_key_dynamic

        client.app.dependency_overrides[dependency] = _fail_api_key
        try:
            with TestClient(client.app, raise_server_exceptions=False) as error_client:
                response = error_client.post(
                    "/api/v1/insight",
                    json={"text": "test"},
                    headers={"X-API-Key": "test_key"},
                )
        finally:
            client.app.dependency_overrides.pop(dependency, None)
        # Runtime error can result in either 500 (internal error) or 503 (service unavailable)
        assert response.status_code in [500, 503]

    def test_connection_error_handler(self, client: TestClient) -> None:
        """Test connection error handler coverage."""

        with patch("llm.get_provider", return_value=FailingProvider()):
            response = client.post(
                "/api/v1/insight",
                json={"text": "test"},
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code in [500, 503, 502]

    def test_timeout_error_handler(self, client: TestClient) -> None:
        """Test timeout error handler coverage."""

        with patch("llm.get_provider", return_value=SlowProvider()):
            response = client.post(
                "/api/v1/insight",
                json={"text": "test"},
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 503
