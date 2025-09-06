"""
Additional tests to improve coverage for app.py to reach 97%+.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app


class TestAppCoverageImprovement:
    """Additional tests to improve coverage for app.py."""

    def setup_method(self):
        """Set up test environment."""
        # Set a test API key for testing
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

        # Reset the global scheduler instance
        import core.food_apis.scheduler

        core.food_apis.scheduler._scheduler_instance = None

    def teardown_method(self):
        """Clean up test environment."""
        # Remove the test API key
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_debug_env_endpoint(self):
        """Test the debug_env endpoint."""
        response = self.client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        assert "FEATURE_INSIGHT" in data
        assert "LLM_PROVIDER" in data
        assert "GROK_MODEL" in data
        assert "GROK_ENDPOINT" in data
        assert "insight_enabled" in data

    def test_database_status_endpoint_success(self):
        """Test database status endpoint success case."""
        # Mock the scheduler and its methods
        with patch(
            "app.get_update_scheduler", new_callable=AsyncMock
        ) as mock_get_scheduler:
            mock_scheduler = AsyncMock()
            mock_scheduler.get_status = MagicMock(
                return_value={
                    "scheduler": {
                        "is_running": True,
                        "last_update_check": None,
                        "update_interval_hours": 24.0,
                        "retry_counts": {},
                    },
                    "databases": {},
                }
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = self.client.get(
                "/api/v1/admin/db-status", headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200

    def test_database_status_endpoint_exception(self):
        """Test database status endpoint exception handling."""
        # Mock the scheduler to raise an exception
        with patch(
            "app.get_update_scheduler", new_callable=AsyncMock
        ) as mock_get_scheduler:
            mock_get_scheduler.side_effect = Exception("Test error")

            response = self.client.get(
                "/api/v1/admin/db-status", headers={"X-API-Key": "test_key"}
            )
            # The app catches the exception and raises HTTPException with status code 500
            assert response.status_code == 500

    def test_force_update_endpoint_success(self):
        """Test force update endpoint success case."""
        # Mock the scheduler and its methods
        with patch(
            "app.get_update_scheduler", new_callable=AsyncMock
        ) as mock_get_scheduler:
            mock_scheduler = AsyncMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.old_version = "1.0"
            mock_result.new_version = "1.1"
            mock_result.records_added = 10
            mock_result.records_updated = 5
            mock_result.records_removed = 0
            mock_result.duration_seconds = 1.0
            mock_result.errors = []
            mock_scheduler.force_update = AsyncMock(return_value={"usda": mock_result})
            mock_get_scheduler.return_value = mock_scheduler

            response = self.client.post(
                "/api/v1/admin/force-update", headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200

    def test_force_update_endpoint_exception(self):
        """Test force update endpoint exception handling."""
        # Mock the scheduler to raise an exception
        with patch(
            "app.get_update_scheduler", new_callable=AsyncMock
        ) as mock_get_scheduler:
            mock_get_scheduler.side_effect = Exception("Test error")

            response = self.client.post(
                "/api/v1/admin/force-update", headers={"X-API-Key": "test_key"}
            )
            # The app catches the exception and raises HTTPException with status code 500
            assert response.status_code == 500

    def test_check_updates_endpoint_success(self):
        """Test check updates endpoint success case."""
        # Mock the scheduler and its methods
        with patch(
            "app.get_update_scheduler", new_callable=AsyncMock
        ) as mock_get_scheduler:
            mock_scheduler = AsyncMock()
            mock_scheduler.update_manager.check_for_updates = AsyncMock(
                return_value={"usda": True, "openfoodfacts": False}
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = self.client.post(
                "/api/v1/admin/check-updates", headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 200

    def test_check_updates_endpoint_exception(self):
        """Test check updates endpoint exception handling."""
        # Mock the scheduler to raise an exception
        with patch(
            "app.get_update_scheduler", new_callable=AsyncMock
        ) as mock_get_scheduler:
            mock_get_scheduler.side_effect = Exception("Test error")

            response = self.client.post(
                "/api/v1/admin/check-updates", headers={"X-API-Key": "test_key"}
            )
            # The app catches the exception and raises HTTPException with status code 500
            assert response.status_code == 500

    def test_rollback_endpoint_success(self):
        """Test rollback endpoint success case."""
        # Mock the scheduler and its methods to simulate a successful rollback
        with patch(
            "app.get_update_scheduler", new_callable=AsyncMock
        ) as mock_get_scheduler:
            mock_scheduler = AsyncMock()
            mock_scheduler.update_manager.rollback_database = AsyncMock(
                return_value=True
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = self.client.post(
                "/api/v1/admin/rollback",
                params={"source": "usda", "target_version": "1.0"},
                headers={"X-API-Key": "test_key"},
            )
            # The app returns a 200 status code on successful rollback
            assert response.status_code == 200

    def test_nutrient_gaps_endpoint_with_none_targets(self):
        """Test nutrient gaps endpoint when build_nutrition_targets is None."""
        # Mock build_nutrition_targets to be None
        with patch("app.build_nutrition_targets", None):
            payload = {
                "consumed_nutrients": {"protein_g": 50, "fat_g": 70, "carbs_g": 250},
                "user_profile": {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "sedentary",
                    "goal": "maintain",
                    "deficit_pct": 20,
                    "surplus_pct": 10,
                    "bodyfat": None,
                    "diet_flags": [],
                    "life_stage": "adult",
                },
            }

            response = self.client.post(
                "/api/v1/premium/gaps", json=payload, headers={"X-API-Key": "test_key"}
            )
            # The app raises an HTTPException(503) directly when build_nutrition_targets is None
            assert response.status_code == 503

    def test_nutrient_gaps_endpoint_general_exception(self):
        """Test nutrient gaps endpoint with general exception."""

        # Mock analyze_nutrient_gaps to raise an exception
        def mock_analyze_nutrient_gaps_func(*args, **kwargs):
            raise Exception("Test error")

        with patch(
            "app.analyze_nutrient_gaps", side_effect=mock_analyze_nutrient_gaps_func
        ):
            payload = {
                "consumed_nutrients": {"protein_g": 50, "fat_g": 70, "carbs_g": 250},
                "user_profile": {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "sedentary",
                    "goal": "maintain",
                    "deficit_pct": 20,
                    "surplus_pct": 10,
                    "bodyfat": None,
                    "diet_flags": [],
                    "life_stage": "adult",
                },
            }

            response = self.client.post(
                "/api/v1/premium/gaps", json=payload, headers={"X-API-Key": "test_key"}
            )
            print(f"DEBUG: Status code: {response.status_code}")
            print(f"DEBUG: Response body: {response.json()}")
            # The app catches the exception and raises HTTPException with status code 500
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
