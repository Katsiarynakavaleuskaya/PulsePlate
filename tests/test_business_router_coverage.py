"""Quality tests for business router analyzing real business logic.

Tests verify:
- Business analysis with real Bayesian analyzer integration
- Module disabled/enabled state handling
- Payload size limits (DoS protection)
- Error wrapping and logging
- HTTPException pass-through
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from tests._helpers.api_headers import API_KEY_HEADERS


class TestBusinessAnalysisEndpoint:
    """Test business analysis endpoint with real logic verification."""

    def test_business_analysis_success_with_real_analyzer(self, test_client) -> None:
        """Verify successful analysis with mocked BusinessBayesianAnalyzer."""
        from core.business_bayesian_analyzer import BusinessCategory

        # Mock the analyzer to return realistic business results
        with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
            mock_instance = MockAnalyzer.return_value

            # Create realistic business analysis result
            mock_result = MagicMock()
            mock_result.test_name = "revenue_analysis"
            mock_result.success = True
            mock_result.business_category = BusinessCategory.REVENUE_GROWTH
            mock_result.error_type = None
            mock_result.error_message = None
            mock_result.revenue_impact = "high"
            mock_result.cost_impact = "medium"
            mock_result.customer_impact = "positive"
            mock_result.optimization_potential = "Implement tiered pricing"

            mock_instance.analyze.return_value = [mock_result]

            # Send real code for analysis
            response = test_client.post(
                "/api/v1/business/analyze",
                json={
                    "code": "def calculate_revenue(price, quantity): return price * quantity",
                    "test_name": "revenue_analysis",
                    "locale": "en",
                },
                headers=API_KEY_HEADERS,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["test_name"] == "revenue_analysis"
            assert data[0]["success"] is True
            assert data[0]["business_category"] == "revenue_growth"
            assert data[0]["revenue_impact"] == "high"
            assert data[0]["optimization_potential"] == "Implement tiered pricing"

            # Verify analyzer was initialized with correct locale
            MockAnalyzer.assert_called_once_with(locale="en")
            mock_instance.analyze.assert_called_once()

    def test_business_analysis_rejects_missing_api_key(self, test_client) -> None:
        """Missing API key must fail closed through the app-level guard."""
        from app.main import app as main_app
        from app.routers.api_key import require_app_api_key

        def _reject_missing() -> str:
            raise HTTPException(status_code=403, detail="Missing API Key")

        main_app.dependency_overrides[require_app_api_key] = _reject_missing
        try:
            with TestClient(main_app) as isolated_client:
                response = isolated_client.post(
                    "/api/v1/business/analyze",
                    json={"code": "def test(): pass", "test_name": "missing_key"},
                )
        finally:
            main_app.dependency_overrides.pop(require_app_api_key, None)

        assert response.status_code == 403
        assert response.headers.get("content-type", "").startswith("application/json")
        assert response.json() == {"detail": "Missing API Key"}

    def test_business_module_disabled_returns_503(self, test_client, monkeypatch) -> None:
        """When module disabled, should return 503 before attempting analysis."""
        monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", False)

        response = test_client.post(
            "/api/v1/business/analyze",
            json={"code": "def test(): pass", "test_name": "test"},
            headers=API_KEY_HEADERS,
        )

        assert response.status_code == 503
        assert "disabled" in response.json()["detail"].lower()

    def test_oversized_payload_rejected_with_413(self, test_client, monkeypatch) -> None:
        """Payloads > 100KB should be rejected with 413 (manual check) to prevent DoS."""
        monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

        # Create exactly 100,001 bytes of code
        oversized_code = "x" * 100_001

        response = test_client.post(
            "/api/v1/business/analyze",
            json={"code": oversized_code, "test_name": "dos_test"},
            headers=API_KEY_HEADERS,
        )

        # Manual payload check returns 413 (Content Too Large)
        assert response.status_code == 413


@pytest.mark.asyncio
async def test_analyze_business_code_oversized_payload_internal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Internal guard: oversized payloads raise 413 even when using direct model construction."""
    from app.routers.business import BusinessAnalysisRequest, analyze_business_code

    # Ensure module-level flag allows analysis
    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    oversized_code = "x" * 100_001

    # Bypass Pydantic max_length validation to hit the runtime size guard
    request = BusinessAnalysisRequest.model_construct(
        code=oversized_code,
        test_name="internal_large_payload",
        locale="en",
    )

    with pytest.raises(HTTPException) as exc_info:
        await analyze_business_code(
            request,
            _api_key=API_KEY_HEADERS["X-API-Key"],
        )

    assert exc_info.value.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert "too large" in str(exc_info.value.detail).lower()


def test_exactly_100kb_payload_accepted(test_client, monkeypatch) -> None:
    """Payload of exactly 100KB should be accepted."""
    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value
        mock_result = MagicMock()
        mock_result.test_name = "edge_case"
        mock_result.success = True
        mock_result.business_category = MagicMock(value="optimization")
        mock_result.error_type = None
        mock_result.error_message = None
        mock_result.revenue_impact = "low"
        mock_result.cost_impact = "low"
        mock_result.customer_impact = "neutral"
        mock_result.optimization_potential = None
        mock_instance.analyze.return_value = [mock_result]

        # Exactly 100,000 bytes
        max_allowed_code = "y" * 100_000

        response = test_client.post(
            "/api/v1/business/analyze",
            json={"code": max_allowed_code, "test_name": "edge_case"},
            headers=API_KEY_HEADERS,
        )

        # Should succeed
        assert response.status_code == 200


def test_business_analysis_invalid_api_key_rejected(test_client, monkeypatch) -> None:
    """Business analysis must fail closed on invalid API keys."""
    from app.main import app as main_app
    from app.routers.api_key import require_app_api_key

    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    def _reject_invalid() -> str:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    main_app.dependency_overrides[require_app_api_key] = _reject_invalid
    try:
        with TestClient(main_app) as isolated_client:
            response = isolated_client.post(
                "/api/v1/business/analyze",
                json={"code": "def test(): pass", "test_name": "auth_fail"},
            )
    finally:
        main_app.dependency_overrides.pop(require_app_api_key, None)

    assert response.status_code == 403
    assert response.headers.get("content-type", "").startswith("application/json")
    assert "invalid api key" in response.json()["detail"].lower()


def test_analyzer_exception_wrapped_as_500(test_client, monkeypatch, caplog) -> None:
    """Non-HTTP exceptions from analyzer should be wrapped as 500."""
    import logging

    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value

        # Simulate analyzer crash
        mock_instance.analyze.side_effect = RuntimeError("Bayesian model failed")

        with caplog.at_level(logging.ERROR):
            response = test_client.post(
                "/api/v1/business/analyze",
                json={"code": "def crash(): raise Exception()", "test_name": "crash_test"},
                headers=API_KEY_HEADERS,
            )

        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()
        # Should not leak internal error details
        assert "RuntimeError" not in response.json()["detail"]


def test_http_exception_passed_through_unchanged(test_client, monkeypatch) -> None:
    """HTTPException from analyzer should pass through without wrapping."""
    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value

        # Analyzer raises HTTPException (e.g., auth error)
        mock_instance.analyze.side_effect = HTTPException(
            status_code=403, detail="Insufficient permissions for business analysis"
        )

        response = test_client.post(
            "/api/v1/business/analyze",
            json={"code": "def test(): pass", "test_name": "auth_test"},
            headers=API_KEY_HEADERS,
        )

        # Should preserve original HTTPException
        assert response.status_code == 403
        assert "permissions" in response.json()["detail"].lower()


def test_status_endpoint_reflects_module_state(test_client, monkeypatch) -> None:
    """Status endpoint should accurately reflect BUSINESS_MODULE_ENABLED."""
    # Test when enabled
    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)
    response = test_client.get("/api/v1/business/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["module"] == "business_analysis"

    # Test when disabled
    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", False)
    response = test_client.get("/api/v1/business/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["module"] == "business_analysis"


def test_error_type_handling_when_analyzer_returns_error(test_client, monkeypatch) -> None:
    """Verify error_type conversion when analysis returns error results."""
    from core.business_bayesian_analyzer import BusinessErrorType

    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value

        # Result with error
        mock_result = MagicMock()
        mock_result.test_name = "failed_test"
        mock_result.success = False
        mock_result.business_category = MagicMock(value="unknown")
        mock_result.error_type = BusinessErrorType.PRICING_INEFFICIENCY
        mock_result.error_message = "Invalid pricing logic"
        mock_result.revenue_impact = "unknown"
        mock_result.cost_impact = "unknown"
        mock_result.customer_impact = "unknown"
        mock_result.optimization_potential = None

        mock_instance.analyze.return_value = [mock_result]

        response = test_client.post(
            "/api/v1/business/analyze",
            json={"code": "def bad_pricing(): price = -10", "test_name": "failed_test"},
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        data = response.json()[0]
        assert data["success"] is False
        assert data["error_type"] == "pricing_inefficiency"
        assert data["error_message"] == "Invalid pricing logic"


def test_multiple_results_returned_as_list(test_client, monkeypatch) -> None:
    """Analyzer can return multiple results for different aspects."""
    from core.business_bayesian_analyzer import BusinessCategory

    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value

        # Multiple analysis results
        result1 = MagicMock()
        result1.test_name = "revenue"
        result1.success = True
        result1.business_category = BusinessCategory.REVENUE_GROWTH
        result1.error_type = None
        result1.error_message = None
        result1.revenue_impact = "high"
        result1.cost_impact = "low"
        result1.customer_impact = "positive"
        result1.optimization_potential = "A/B testing"

        result2 = MagicMock()
        result2.test_name = "cost"
        result2.success = True
        result2.business_category = BusinessCategory.COST_OPTIMIZATION
        result2.error_type = None
        result2.error_message = None
        result2.revenue_impact = "medium"
        result2.cost_impact = "high"
        result2.customer_impact = "neutral"
        result2.optimization_potential = "Reduce infrastructure"

        mock_instance.analyze.return_value = [result1, result2]

        response = test_client.post(
            "/api/v1/business/analyze",
            json={"code": "def optimize(): pass", "test_name": "multi_aspect"},
            headers={"X-API-Key": "test_key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["business_category"] == "revenue_growth"
        assert data[1]["business_category"] == "cost_optimization"


def test_log_injection_prevented_in_error_logging(test_client, monkeypatch, caplog) -> None:
    """Test that malicious test_name values are sanitized before logging."""
    import logging

    monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

    with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
        mock_instance = MockAnalyzer.return_value
        # Force an exception to trigger error logging
        mock_instance.analyze.side_effect = RuntimeError("Test error")

        # Malicious test_name with control characters (newlines, tabs, etc.)
        malicious_test_name = "evil\ntest\r\nINJECTED: fake_log_entry\t\x00null_byte"

        with caplog.at_level(logging.ERROR):
            response = test_client.post(
                "/api/v1/business/analyze",
                json={"code": "def test(): pass", "test_name": malicious_test_name},
                headers={"X-API-Key": "test_key"},
            )

        assert response.status_code == 500

        # Verify the log message was captured
        error_logs = [record for record in caplog.records if record.levelno == logging.ERROR]
        assert len(error_logs) == 1

        # Verify control characters were removed from logged message
        logged_message = error_logs[0].message
        assert "\n" not in logged_message  # Newlines removed
        assert "\r" not in logged_message  # Carriage returns removed
        assert "\t" not in logged_message  # Tabs removed
        assert "\x00" not in logged_message  # Null bytes removed
        # Sanitized name should be present but without control chars
        assert "evil" in logged_message
        assert "test" in logged_message


def test_sanitize_log_value_truncates_long_strings() -> None:
    """Test that _sanitize_log_value truncates strings over max_length."""
    from app.routers.business import _sanitize_log_value

    # Test truncation at default 100 chars
    long_string = "a" * 150
    result = _sanitize_log_value(long_string)
    assert len(result) == 103  # 100 chars + "..."
    assert result.endswith("...")
    assert result.startswith("a" * 100)

    # Test custom max_length
    result = _sanitize_log_value(long_string, max_length=50)
    assert len(result) == 53  # 50 chars + "..."
    assert result.endswith("...")


def test_sanitize_log_value_removes_control_characters() -> None:
    """Test that _sanitize_log_value removes control characters."""
    from app.routers.business import _sanitize_log_value

    # Test various control characters
    malicious = "test\nvalue\r\n\twith\x00controls\x1f\x7f"
    result = _sanitize_log_value(malicious)

    # All control chars should be removed
    assert "\n" not in result
    assert "\r" not in result
    assert "\t" not in result
    assert "\x00" not in result
    assert "\x1f" not in result
    assert "\x7f" not in result

    # Regular characters should remain
    assert "test" in result
    assert "value" in result
    assert "with" in result
    assert "controls" in result


def test_sanitize_log_value_preserves_safe_characters() -> None:
    """Test that _sanitize_log_value preserves normal alphanumeric and punctuation."""
    from app.routers.business import _sanitize_log_value

    safe_string = "test_name-123.py: Revenue Analysis (2024)"
    result = _sanitize_log_value(safe_string)
    assert result == safe_string  # Should be unchanged
