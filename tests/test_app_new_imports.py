"""
Tests for new modular system imports in app.py.

These tests cover the new import block that checks for modular system availability.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAppNewImports:
    """Test class for new modular system imports."""

    def test_new_modular_system_import_success(self):
        """Test successful import of new modular system components."""
        # This test covers the try block in the new import section
        with patch.dict(
            "sys.modules",
            {
                "core.weekly_plan_new": MagicMock(),
                "core.food_db_new": MagicMock(),
                "core.recipe_db_new": MagicMock(),
                "core.recommendations": MagicMock(),
            },
        ):
            # Re-import app to trigger the import block
            import importlib
            import app

            importlib.reload(app)

            # Verify that the imports were successful
            assert hasattr(app, "NEW_MODULAR_SYSTEM_AVAILABLE")
            assert hasattr(app, "build_week")
            assert hasattr(app, "FoodDB")
            assert hasattr(app, "RecipeDB")
            assert hasattr(app, "build_nutrition_targets")

        # Reload real module to avoid leaking mocks into other tests
        importlib.reload(app)

    def test_weekly_menu_endpoint_success(self):
        """Test weekly menu endpoint with successful modular system."""
        from fastapi.testclient import TestClient
        import os

        # Set up test environment
        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        # Import after environment setup so configuration picks up overrides
        import app

        # This test covers the successful path through the modular system
        client = TestClient(app.app)

        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "lang": "en",
        }

        response = client.post(
            "/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Since modular system is available, we expect success
        assert response.status_code == 200
        assert "week_summary" in response.json()
        assert "daily_menus" in response.json()

    def test_weekly_menu_endpoint_missing_csv_files(self):
        """Test weekly menu endpoint when CSV files are missing."""
        from fastapi.testclient import TestClient
        import os

        # Set up test environment
        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        with patch("os.path.exists", return_value=False):
            import app

            client = TestClient(app.app)

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "lang": "en",
            }

            response = client.post(
                "/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": "test_key"}
            )

            assert response.status_code == 503
            assert "not found" in response.json()["detail"]

    def test_weekly_menu_endpoint_invalid_payload(self):
        """Test weekly menu endpoint with invalid payload."""
        from fastapi.testclient import TestClient
        import os

        # Set up test environment
        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        import app

        client = TestClient(app.app)

        # Test with invalid payload
        invalid_payload = {
            "sex": "invalid",
            "age": -5,
            "height_cm": 0,
            "weight_kg": -10,
            "activity": "invalid",
            "lang": "invalid",
        }

        response = client.post(
            "/api/v1/premium/plan/week", json=invalid_payload, headers={"X-API-Key": "test_key"}
        )

        # Should return validation error
        assert response.status_code == 422

    def test_weekly_menu_endpoint_new_system_unavailable(self):
        """Ensure 503 is returned when modular system is disabled."""
        from fastapi.testclient import TestClient
        import os
        import app

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        original_flag = app.app_module.NEW_MODULAR_SYSTEM_AVAILABLE
        app.app_module.NEW_MODULAR_SYSTEM_AVAILABLE = False
        try:
            client = TestClient(app.app)
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "lang": "en",
            }
            response = client.post(
                "/api/v1/premium/plan/week", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 503
            assert "New modular system" in response.json()["detail"]
        finally:
            app.app_module.NEW_MODULAR_SYSTEM_AVAILABLE = original_flag

    def test_weekly_menu_endpoint_database_classes_none(self):
        """Ensure 503 when FoodDB/RecipeDB classes are unavailable."""
        from fastapi.testclient import TestClient
        import os
        import app

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        original_fooddb = app.app_module.FoodDB
        original_recipedb = app.app_module.RecipeDB
        app.app_module.FoodDB = None
        app.app_module.RecipeDB = None
        try:
            client = TestClient(app.app)
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "lang": "en",
            }
            with patch("os.path.exists", return_value=True):
                response = client.post(
                    "/api/v1/premium/plan/week",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
            assert response.status_code == 503
            assert "Database classes" in response.json()["detail"]
        finally:
            app.app_module.FoodDB = original_fooddb
            app.app_module.RecipeDB = original_recipedb

    def test_weekly_menu_endpoint_build_nutrition_targets_none(self):
        """Ensure 503 when build_nutrition_targets is missing."""
        from fastapi.testclient import TestClient
        import os
        import app

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        original_builder = app.app_module.build_nutrition_targets
        app.app_module.build_nutrition_targets = None
        try:
            client = TestClient(app.app)
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "lang": "en",
            }
            with patch("os.path.exists", return_value=True):
                response = client.post(
                    "/api/v1/premium/plan/week",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
            assert response.status_code == 503
            assert "Nutrition targets" in response.json()["detail"]
        finally:
            app.app_module.build_nutrition_targets = original_builder

    def test_weekly_menu_endpoint_build_week_none(self):
        """Ensure 503 when build_week helper is missing."""
        from fastapi.testclient import TestClient
        import os
        import app

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        original_build_week = app.app_module.build_week
        app.app_module.build_week = None
        try:
            client = TestClient(app.app)
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "lang": "en",
            }
            with patch("os.path.exists", return_value=True):
                response = client.post(
                    "/api/v1/premium/plan/week",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
            assert response.status_code == 503
            assert "Weekly plan generation" in response.json()["detail"]
        finally:
            app.app_module.build_week = original_build_week

    def teardown_method(self):
        """Clean up test environment."""
        import os

        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]
        if "VIP_MODULE_ENABLED" in os.environ:
            del os.environ["VIP_MODULE_ENABLED"]
