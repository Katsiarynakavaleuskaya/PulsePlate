"""Final coverage boost tests targeting remaining uncovered lines.

These tests target specific edge cases and error paths to achieve 97% coverage.
"""

import pytest
from typing import Any
from unittest.mock import patch, MagicMock
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

    def test_db_helper_functions(self) -> None:
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

    def test_business_router_edge_paths(
        self, test_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover business router edge cases."""
        monkeypatch.setattr("app.routers.business.BUSINESS_MODULE_ENABLED", True)

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
                headers={"X-API-Key": "test-key"},
            )

            assert response.status_code == 200
            data = response.json()[0]
            # When error_type is None, should default to "unknown"
            assert data["error_type"] == "unknown"

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
            raise OperationalError("fail", None, Exception("connection failed"))

        result = users._execute_with_retry(always_fails, fallback=[])
        assert result == []
        assert call_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_app_targets_disabled_edge_cases(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test targets_disabled edge cases."""
        import app

        # Test with package explicit None
        if not hasattr(app, "_APP_PACKAGE_REF"):
            pytest.skip("requires _APP_PACKAGE_REF")

        # Save original
        original = getattr(app, "build_nutrition_targets", None)
        try:
            # Set to None
            app.build_nutrition_targets = None
            result = app.targets_disabled()
            assert result is True
        finally:
            # Restore
            if original is not None:
                app.build_nutrition_targets = original

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
