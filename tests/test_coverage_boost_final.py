"""Final coverage boost tests targeting remaining uncovered lines.

These tests target specific edge cases and error paths to achieve 97% coverage.
"""

import pytest
from typing import Any
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient


class TestCoverageFinalBoost:
    """Tests to cover final missing lines for 97% target."""

    def test_bayesian_analyzer_edge_cases(self) -> None:
        """Cover edge cases in bayesian analyzer."""
        from core.bayesian_test_analyzer import BayesianTestAnalyzer

        analyzer = BayesianTestAnalyzer()

        # Test with empty symptoms
        diagnosis = analyzer.diagnose_test_failure("test", "", {})
        assert diagnosis.most_likely_cause is not None

        # Test predict with no history
        prob = analyzer.predict_test_failure_probability("new_test")
        assert 0 <= prob <= 1

        # Test health score with no history
        health = analyzer.get_test_health_score("new_test")
        assert 0 <= health <= 1

    def test_db_helper_functions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database helper functions."""
        from core import db

        # Test get_session_factory
        factory = db.get_session_factory()
        assert factory is not None

        # Test _extract_sqlite_path edge cases
        assert db._extract_sqlite_path("postgresql://localhost/db") is None
        assert db._extract_sqlite_path("sqlite:///:memory:") is None
        assert db._extract_sqlite_path("sqlite:///test.db") == "test.db"
        assert (
            db._extract_sqlite_path("sqlite:////absolute/path/db.sqlite")
            == "/absolute/path/db.sqlite"
        )

        # Test _build_engine_url absolute/relative path handling
        # This covers lines 158-163 in core/db.py
        # Use monkeypatch to temporarily clear DATABASE_URL to test non-env path logic
        monkeypatch.delenv("DATABASE_URL", raising=False)

        # Call _build_engine_url without env var (triggers default path logic)
        result_url = db._build_engine_url()
        assert result_url.startswith("sqlite:///"), "Default path should produce sqlite:/// URL"
        # The default path is "cache/app.db" which is relative (tests line 162-163)
        assert (
            "cache/app.db" in result_url or "cache" in result_url
        ), "Default path should be included"

        # Verify the URL doesn't have absolute path markers (no leading // after sqlite:///)
        # This confirms the relative path logic was used (line 162: path_part = parsed.path.lstrip("/"))
        assert not result_url.startswith(
            "sqlite:////"
        ), "Relative path should not have double slashes"

    def test_business_router_edge_paths(
        self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover business router edge cases."""
        from app.routers.api_key import require_app_api_key

        monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)
        test_client.app.dependency_overrides[require_app_api_key] = lambda: "test-api-key"
        try:
            with patch("app.routers.business.BusinessBayesianAnalyzer") as MockAnalyzer:
                # Test with None error_type
                mock_instance = MockAnalyzer.return_value
                mock_result = MagicMock()
                mock_result.test_name = "test"
                mock_result.success = True
                mock_result.business_category = MagicMock(value="optimization")
                mock_result.error_type = None  # None case
                mock_result.error_message = None
                mock_result.revenue_impact = "low"
                mock_result.cost_impact = "low"
                mock_result.customer_impact = "neutral"
                mock_result.optimization_potential = None
                mock_instance.analyze.return_value = [mock_result]

                response = test_client.post(
                    "/api/v1/business/analyze",
                    json={"code": "def test(): pass", "test_name": "test"},
                    headers={"X-API-Key": "test-api-key"},
                )

                assert response.status_code == 200
                data = response.json()[0]
                # When error_type is None, should default to "unknown"
                assert data["error_type"] == "unknown"
        finally:
            test_client.app.dependency_overrides.pop(require_app_api_key, None)

    def test_users_retry_edge_cases(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test users router retry edge cases."""
        from app.routers import users
        from sqlalchemy.exc import OperationalError

        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.SessionLocal.return_value = mock_session
        monkeypatch.setattr("app.routers.users.db_module", mock_db)

        # Test with all retries failing but fallback provided
        call_count = 0

        def always_fails(session: Any) -> Any:
            nonlocal call_count
            call_count += 1
            raise OperationalError("test", {}, Exception("DB error"))

        # Call should raise HTTPException after retries (no fallback)
        with pytest.raises(HTTPException) as exc_info:
            users._execute_with_retry(always_fails)

        # Should be 503 (service unavailable) after exhausting retries
        assert exc_info.value.status_code == 503
        assert call_count == 4  # initial + 3 retries (hardcoded max_retries=3)

    def test_technical_utils_edge_cases(self) -> None:
        """Test bayesian technical utils edge cases."""
        from core.bayesian_technical_utils import analyze_technical_aspects_common

        # Test with syntax error (triggers regex fallback)
        code_with_error = "def broken syntax here"
        issues = analyze_technical_aspects_common(code_with_error)
        assert isinstance(issues, list)

        # Test with async without await
        code_async = "async def test(): return 1"
        issues = analyze_technical_aspects_common(code_async)
        assert "Async function without await usage" in issues
