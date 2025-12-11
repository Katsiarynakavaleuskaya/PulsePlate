"""
Final diff coverage boost tests to reach 97%+ coverage.

Targets specific missing lines identified in CI diff coverage report.
"""

import os
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.applications import ASGIApp

# Import app
import app as app_module

app = app_module.app


@pytest.fixture(autouse=True)
def _business_env_and_client(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Autouse fixture to set env vars and attach a TestClient to test instances."""
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("BUSINESS_MODULE_ENABLED", "true")

    client = TestClient(cast(ASGIApp, app))

    # Attach client to test class instances that expect self.client
    if getattr(request.node, "instance", None) is not None:
        setattr(request.node.instance, "client", client)

    try:
        yield
    finally:
        client.close()


class TestBusinessRouterMissingLines:
    """Tests for missing lines in app/routers/business.py"""

    def test_safe_error_summary_function(self) -> None:
        """Test _safe_error_summary returns class name (line 26)."""
        from app.routers.business import _safe_error_summary

        # Test with various exception types
        value_err = ValueError("sensitive user data")
        assert _safe_error_summary(value_err) == "ValueError"

        runtime_err = RuntimeError("database connection failed")
        assert _safe_error_summary(runtime_err) == "RuntimeError"

    def test_analyze_http_exception_re_raise(self) -> None:
        """Test HTTPException is re-raised untouched (lines 104-106)."""
        # Patch analyzer to raise HTTPException
        with patch("app.routers.business.BusinessBayesianAnalyzer") as mock_analyzer_cls:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.side_effect = HTTPException(status_code=403, detail="Forbidden")
            mock_analyzer_cls.return_value = mock_analyzer

            response = self.client.post(
                "/api/v1/business/analyze",
                json={"code": "test code", "test_name": "test"},
                headers={"X-API-Key": "test_key"},
            )

            # HTTPException should be re-raised with original status
            assert response.status_code == 403
            assert "Forbidden" in response.json()["detail"]

    def test_analyze_generic_exception_wrapped(self) -> None:
        """Test generic Exception is wrapped as 500 (lines 107-118)."""
        # Patch analyzer to raise generic exception
        with patch("app.routers.business.BusinessBayesianAnalyzer") as mock_analyzer_cls:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.side_effect = RuntimeError("Database connection failed")
            mock_analyzer_cls.return_value = mock_analyzer

            response = self.client.post(
                "/api/v1/business/analyze",
                json={"code": "test code", "test_name": "test_generic_error"},
                headers={"X-API-Key": "test_key"},
            )

            # Generic exception should be wrapped as 500
            assert response.status_code == 500
            assert "Business analysis failed" in response.json()["detail"]

    def test_business_status_endpoint(self) -> None:
        """Test /status endpoint returns module status (line 124)."""
        response = self.client.get("/api/v1/business/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert data["module"] == "business_analysis"


class TestMCPServerMissingLines:
    """Tests for missing lines in mcp_pulseplate_server.py (lines 39-40)"""

    def test_reset_model_cache_function(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _reset_model_cache clears cached models (lines 39-40)."""
        from mcp_pulseplate_server import PulsePlateMCPServer

        # Set some cache values using monkeypatch to avoid cross-test pollution
        monkeypatch.setattr(
            PulsePlateMCPServer,
            "_cached_models",
            {"gpt-4o", "gpt-4"},
        )
        monkeypatch.setattr(PulsePlateMCPServer, "_model_cache_failed", True)

        # Reset cache
        PulsePlateMCPServer._reset_model_cache()

        # Verify cache is cleared
        assert PulsePlateMCPServer._cached_models is None
        assert PulsePlateMCPServer._model_cache_failed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
