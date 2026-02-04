"""
Combined app error handling tests: critical lines coverage and exception handlers.

RU: Объединенные тесты для обработки ошибок app: критичные линии покрытия и exception handlers
EN: Combined tests for app error handling: critical lines coverage and exception handlers

These tests cover critical uncovered lines in main.py and exception handler coverage.
"""

import pytest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
import re
from typing import NoReturn, cast
from starlette.types import ASGIApp

import app

_UPSTREAM_PROVIDER_TOKENS = (
    "openai",
    "anthropic",
    "azure",
    "vertex",
    "claude",
    "groq",
    "ollama",
)

# Keep this intentionally loose to avoid brittle coupling to exact wording.
_GENERIC_DETAIL_RE = re.compile(r"(error|unavailable|timeout|failed|disabled)", re.IGNORECASE)


def _assert_json_error_hygiene(response) -> str:
    """Assert error response is JSON and does not leak upstream details."""
    assert response.headers["content-type"].startswith("application/json")

    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body

    detail = str(body["detail"])
    lowered = detail.lower()

    # No urls
    assert "http://" not in lowered
    assert "https://" not in lowered

    # No provider identifiers
    for token in _UPSTREAM_PROVIDER_TOKENS:
        assert token not in lowered

    # Keep message generic but meaningful (avoid blank/garbage)
    assert detail.strip() != ""
    assert _GENERIC_DETAIL_RE.search(detail) is not None

    return detail


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
        large_data = {"data": "x" * 100000}  # Increased from 10k to 100k for more reliable testing
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

    def test_runtime_error_handler(self, client: TestClient, vip_headers: dict[str, str]) -> None:
        """Test runtime error handler coverage: BMI endpoint is now public, test on another."""

        # BMI endpoint no longer uses get_api_key, use insight endpoint
        def _fail_vip_guard() -> NoReturn:
            raise RuntimeError("boom")

        if app.app is None:
            pytest.skip("app.app is None - cannot run integration test")

        from app.middleware.api_tiers import require_vip_tier

        with patch.dict(
            app.app.dependency_overrides, {require_vip_tier: _fail_vip_guard}, clear=False
        ):
            # Use a client that does not re-raise server exceptions so we can assert on HTTP status codes.
            local_client = TestClient(cast(ASGIApp, app.app), raise_server_exceptions=False)
            response = local_client.post(
                "/api/v1/insight", json={"text": "test"}, headers=vip_headers
            )
        # Runtime error can result in either 500 (internal error) or 503 (service unavailable)
        assert response.status_code in [500, 503]

    def test_connection_error_handler(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test connection error handler coverage"""
        # Test with insight endpoint that makes external LLM calls
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")

        with patch(
            "httpx.AsyncClient.post",
            side_effect=httpx.ConnectError("Connection failed"),
        ) as mocked_post:
            response = client.post(
                "/api/v1/insight",
                json={"text": "test"},
                headers=vip_headers,
            )
            assert mocked_post.called is True
            # Should handle connection error gracefully
            assert response.status_code in [500, 503, 502]
            detail = _assert_json_error_hygiene(response)
            assert "Connection failed" not in detail

    def test_timeout_error_handler(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test timeout error handler coverage"""
        # Test with insight endpoint that makes external LLM calls
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")

        with patch(
            "httpx.AsyncClient.post",
            side_effect=httpx.ReadTimeout("Request timeout"),
        ) as mocked_post:
            response = client.post(
                "/api/v1/insight",
                json={"text": "test"},
                headers=vip_headers,
            )
            assert mocked_post.called is True
            # Should handle timeout error gracefully - expect 503 Service Unavailable
            assert response.status_code == 503
            detail = _assert_json_error_hygiene(response)
            assert "Request timeout" not in detail
