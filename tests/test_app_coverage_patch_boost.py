"""
Tests to boost patch coverage by 1.5% for app.py.

Focuses on uncovered lines and edge cases to improve overall coverage.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app


@pytest.fixture
def client() -> TestClient:
    """Test client fixture with API_KEY and FEATURE_PREMIUM_NUTRITION set."""
    original_api_key = os.environ.get("API_KEY")
    original_feature = os.environ.get("FEATURE_PREMIUM_NUTRITION")
    os.environ["API_KEY"] = "test_key"
    os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
    try:
        yield TestClient(app.app)
    finally:
        if original_api_key is None:
            os.environ.pop("API_KEY", None)
        else:
            os.environ["API_KEY"] = original_api_key
        if original_feature is None:
            os.environ.pop("FEATURE_PREMIUM_NUTRITION", None)
        else:
            os.environ["FEATURE_PREMIUM_NUTRITION"] = original_feature


class TestAppCoveragePatchBoost:
    """Tests to boost patch coverage for app.py."""

    @pytest.mark.asyncio
    async def test_start_background_updates_coverage(self, client: TestClient) -> None:
        """Test start_background_updates function coverage with scheduler interaction."""
        # Create a mock scheduler to spy on interactions
        mock_scheduler = MagicMock()
        mock_scheduler.is_running = False
        mock_scheduler.start = AsyncMock()

        # Patch get_update_scheduler to return our mock (async function)
        async def mock_get_scheduler() -> MagicMock:
            return mock_scheduler

        with patch("core.food_apis.scheduler.get_update_scheduler", side_effect=mock_get_scheduler):
            # Import the real implementation from scheduler module
            from core.food_apis.scheduler import start_background_updates

            # Call with a known interval
            await start_background_updates(update_interval_hours=12)

            # Assert scheduler.start() was called (interaction check)
            mock_scheduler.start.assert_called_once()

        # Verify the app.py wrapper function exists and is callable
        assert callable(app.start_background_updates)
        result = app.start_background_updates(update_interval_hours=12)
        assert result is None

    @pytest.mark.asyncio
    async def test_stop_background_updates_coverage(self, client: TestClient) -> None:
        """Test stop_background_updates function coverage with scheduler interaction."""
        # Create a mock scheduler to spy on interactions
        mock_scheduler = MagicMock()
        mock_scheduler.is_running = True
        mock_scheduler.stop = AsyncMock()

        # Patch the scheduler instance to use our mock
        original_instance = None
        try:
            from core.food_apis import scheduler as scheduler_module

            original_instance = getattr(scheduler_module, "_scheduler_instance", None)
            scheduler_module._scheduler_instance = mock_scheduler

            # Import the real implementation from scheduler module
            from core.food_apis.scheduler import stop_background_updates

            # Call stop function
            await stop_background_updates()

            # Assert scheduler.stop() was called (interaction check)
            mock_scheduler.stop.assert_called_once()
        finally:
            # Restore original instance
            if original_instance is not None:
                scheduler_module._scheduler_instance = original_instance
            elif hasattr(scheduler_module, "_scheduler_instance"):
                delattr(scheduler_module, "_scheduler_instance")

        # Verify the app.py wrapper function exists and is callable
        assert callable(app.stop_background_updates)
        result = app.stop_background_updates()
        assert result is None

    def test_calculate_all_bmr_wrapper_normal(self, client: TestClient) -> None:
        """Test _calculate_all_bmr_wrapper normal execution."""
        # Test normal execution path
        result = app._calculate_all_bmr_wrapper(70, 175, 30, "male", None)

        # Verify result structure and types
        assert result is not None
        assert isinstance(result, dict), "Result should be a dictionary"

        # Verify required fields exist
        assert "mifflin" in result, "Result should contain 'mifflin' BMR value"
        assert "harris" in result, "Result should contain 'harris' BMR value"

        # Verify field types and values
        assert isinstance(result["mifflin"], (int, float)), "'mifflin' should be numeric"
        assert isinstance(result["harris"], (int, float)), "'harris' should be numeric"
        assert result["mifflin"] > 0, "'mifflin' should be a positive value"
        assert result["harris"] > 0, "'harris' should be a positive value"

        # Verify katch is not present when bodyfat is None
        assert "katch" not in result, "'katch' should not be present when bodyfat is None"

    def test_calculate_all_tdee_wrapper_normal(self, client: TestClient) -> None:
        """Test _calculate_all_tdee_wrapper normal execution."""
        # Test normal execution path
        bmr_results = app._calculate_all_bmr_wrapper(70, 175, 30, "male", None)
        result = app._calculate_all_tdee_wrapper(bmr_results, "moderate")
        assert result is not None

    def test_get_update_scheduler_with_global_getter(self, client: TestClient) -> None:
        """Test get_update_scheduler with global _scheduler_getter set."""
        original_getter = app._scheduler_getter
        try:

            async def mock_getter() -> MagicMock:
                return MagicMock()

            app._scheduler_getter = mock_getter
            import asyncio

            scheduler = asyncio.run(app.get_update_scheduler())
            assert scheduler is not None
        finally:
            app._scheduler_getter = original_getter

    def test_get_update_scheduler_without_getter_returns_scheduler(
        self, client: TestClient
    ) -> None:
        """Test get_update_scheduler when _scheduler_getter is None and scheduler is available."""
        original_getter = app._scheduler_getter
        try:
            app._scheduler_getter = None
            import asyncio

            # Mock scheduler with required methods
            mock_scheduler = MagicMock()
            mock_scheduler.create_task = MagicMock()
            mock_scheduler.call_soon = MagicMock()

            # Patch the late import to return our mock scheduler
            async def mock_getter() -> MagicMock:
                return mock_scheduler

            with patch("core.food_apis.scheduler.get_update_scheduler", side_effect=mock_getter):
                scheduler = asyncio.run(app.get_update_scheduler())
                # Assert scheduler is returned and has required methods
                assert scheduler is not None
                assert hasattr(scheduler, "create_task")
                assert hasattr(scheduler, "call_soon")
        finally:
            app._scheduler_getter = original_getter

    def test_get_update_scheduler_without_getter_returns_none(self, client: TestClient) -> None:
        """Test get_update_scheduler when _scheduler_getter is None and scheduler is unavailable."""
        original_getter = app._scheduler_getter
        try:
            app._scheduler_getter = None
            import asyncio

            # Patch the late import to return None (simulating scheduler unavailability)
            async def mock_getter() -> None:
                return None

            with patch("core.food_apis.scheduler.get_update_scheduler", side_effect=mock_getter):
                scheduler = asyncio.run(app.get_update_scheduler())
                # Assert None is returned when scheduler is unavailable
                assert scheduler is None
        finally:
            app._scheduler_getter = original_getter

    def test_is_truthy_edge_cases(self, client: TestClient) -> None:
        """Test _is_truthy function with edge cases."""
        assert app._is_truthy("1") is True
        assert app._is_truthy("true") is True
        assert app._is_truthy("yes") is True
        assert app._is_truthy("on") is True
        assert app._is_truthy(" 1 ") is True  # With whitespace
        assert app._is_truthy("0") is False
        assert app._is_truthy("false") is False
        assert app._is_truthy("no") is False
        assert app._is_truthy("off") is False
        assert app._is_truthy("") is False
        assert app._is_truthy(None) is False

    def test_get_api_key_strict_mode_without_key(self, client: TestClient) -> None:
        """Test get_api_key in strict mode without configured key."""
        with patch.dict(os.environ, {"API_KEY_REQUIRED": "true"}, clear=True):
            from fastapi import HTTPException

            with pytest.raises(HTTPException, match="API key required"):
                app.get_api_key(api_key="")

    def test_get_api_key_dev_mode_trivial_token(self, client: TestClient) -> None:
        """Test get_api_key rejects trivial tokens in dev mode."""
        with patch.dict(os.environ, {"API_KEY": "", "APP_ENV": "dev"}):
            from fastapi import HTTPException

            with pytest.raises(HTTPException, match="Invalid API Key"):
                app.get_api_key(api_key="bad")

    def test_get_api_key_dev_mode_short_token(self, client: TestClient) -> None:
        """Test get_api_key rejects short tokens."""
        with patch.dict(os.environ, {"API_KEY": "", "APP_ENV": "dev"}):
            from fastapi import HTTPException

            with pytest.raises(HTTPException, match="Invalid API Key"):
                app.get_api_key(api_key="abc")  # Less than 4 chars

    def test_admin_status_scheduler_unavailable(self, client: TestClient) -> None:
        """Test admin_status when scheduler is unavailable."""

        async def mock_getter() -> None:
            return None

        with patch("app.get_update_scheduler", side_effect=mock_getter):
            response = client.get("/api/v1/admin/status", headers={"X-API-Key": "test_key"})
            # Should return 503 when scheduler is unavailable
            assert response.status_code == 503

    def test_database_health_success(self, client: TestClient) -> None:
        """Test database_health endpoint success path."""
        # Test normal execution path
        response = client.get("/health/db")
        # Should return 200 on success
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_legacy_category_label_edge_cases(self, client: TestClient) -> None:
        """Test legacy_category_label with explicit language values and fallback behavior."""
        # Test with explicit English language - should map "Normal weight" to "Healthy weight"
        result = app.legacy_category_label("Normal weight", "en")
        assert (
            result == "Healthy weight"
        ), f"Expected 'Healthy weight' for lang='en', got '{result}'"

        # Test with explicit Russian language - should map "Избыточная масса" to "Избыточный вес"
        result = app.legacy_category_label("Избыточная масса", "ru")
        assert (
            result == "Избыточный вес"
        ), f"Expected 'Избыточный вес' for lang='ru', got '{result}'"

        # Test with Spanish language (unsupported mapping) - should return category unchanged
        result = app.legacy_category_label("Normal weight", "es")
        assert result == "Normal weight", f"Expected 'Normal weight' for lang='es', got '{result}'"

        # Test with None language - defaults to "ru", so "Normal weight" stays unchanged
        # (no mapping exists for "Normal weight" in Russian context)
        result = app.legacy_category_label("Normal weight", None)
        assert (
            result == "Normal weight"
        ), f"Expected 'Normal weight' for lang=None (fallback to 'ru'), got '{result}'"

        # Test with invalid lang type (int) - exception caught, defaults to "ru"
        # Should return category unchanged as fallback behavior
        result = app.legacy_category_label("Normal weight", 123)  # type: ignore
        assert (
            result == "Normal weight"
        ), f"Expected 'Normal weight' for invalid lang (fallback to 'ru'), got '{result}'"

    def test_add_visualization_if_requested_not_requested(self, client: TestClient) -> None:
        """Test add_visualization_if_requested when not requested."""
        result = {"bmi": 25.0}
        req = MagicMock()
        req.include_chart = False
        app.add_visualization_if_requested(result, req)
        assert "visualization" not in result

    def test_add_visualization_if_requested_matplotlib_unavailable(
        self, client: TestClient
    ) -> None:
        """Test add_visualization_if_requested when matplotlib unavailable."""
        result = {"bmi": 25.0}
        req = MagicMock()
        req.include_chart = True
        req.age = 30
        req.gender = "male"
        req.pregnant = False
        req.athlete = False
        req.lang = "en"

        with patch("app.MATPLOTLIB_AVAILABLE", False):
            app.add_visualization_if_requested(result, req)
            assert "visualization" in result
            assert result["visualization"]["available"] is False

    def test_normalize_flags_boolean_values(self, client: TestClient) -> None:
        """Test normalize_flags with boolean values."""
        result = app.normalize_flags("male", True, False)
        assert result["gender_male"] is True
        assert result["is_pregnant"] is False
        assert result["is_athlete"] is False

        result = app.normalize_flags("female", True, True)
        assert result["gender_male"] is False
        assert result["is_pregnant"] is True
        assert result["is_athlete"] is True

    def test_waist_risk_edge_cases(self, client: TestClient) -> None:
        """Test waist_risk with edge cases."""
        # Test None waist
        result = app.waist_risk(None, True, "en")
        assert result == ""

        # Test high risk male
        result = app.waist_risk(105, True, "en")
        assert "High" in result or "risk" in result.lower()

        # Test high risk female
        result = app.waist_risk(90, False, "en")
        assert "High" in result or "risk" in result.lower()

    def test_root_endpoint_coverage(self, client: TestClient) -> None:
        """Test root endpoint coverage."""
        response = client.get("/")
        assert response.status_code == 200
        assert "BMI Calculator" in response.text or "Калькулятор" in response.text

    def test_favicon_endpoint_coverage(self, client: TestClient) -> None:
        """Test favicon endpoint coverage."""
        response = client.get("/favicon.ico")
        assert response.status_code == 204

    def test_health_endpoints_coverage(self, client: TestClient) -> None:
        """Test health endpoints coverage."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_metrics_endpoint_coverage(self, client: TestClient) -> None:
        """Test metrics endpoint coverage."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "error" in response.json() or "Prometheus" in str(response.json())

    def test_privacy_endpoint_coverage(self, client: TestClient) -> None:
        """Test privacy endpoint coverage."""
        response = client.get("/privacy")
        assert response.status_code == 200
        assert "privacy_policy" in response.json()
