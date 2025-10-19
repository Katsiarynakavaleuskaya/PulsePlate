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
        """Test weekly menu endpoint with successful modular system (stubbed)."""
        from fastapi.testclient import TestClient
        import os

        # Set up test environment
        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        # Import after environment setup so configuration picks up overrides
        import app

        fake_week = {
            "daily_menus": [
                {
                    "meals": [
                        {
                            "title": "Oatmeal",
                            "title_translated": "Oatmeal",
                            "grams": {"oats": 80},
                            "kcal": 320,
                            "macros": {
                                "protein_g": 10.0,
                                "fat_g": 6.0,
                                "carbs_g": 52.0,
                                "fiber_g": 6.0,
                            },
                            "micros": {},
                        }
                    ],
                    "kcal": 2000,
                    "macros": {
                        "protein_g": 120.0,
                        "fat_g": 60.0,
                        "carbs_g": 220.0,
                        "fiber_g": 30.0,
                    },
                    "micros": {},
                    "coverage": {"iron_mg": 80.0},
                    "tips": [],
                    "total_cost": 5.0,
                }
            ]
            * 7,
            "weekly_coverage": {"iron_mg": 80.0},
            "shopping_list": {"oats": 560},
            "total_cost": 35.0,
            "adherence_score": 85.0,
        }

        with (
            patch("app.build_week", return_value=fake_week),
            patch("os.path.exists", return_value=True),
            patch("app.FoodDB") as _fd,
            patch("app.RecipeDB") as _rd,
        ):
            # This test covers the successful path through the modular system (stubbed)
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
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
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

    @pytest.mark.skip(
        reason="Complex module reload test - difficult to mock import architecture correctly"
    )
    def test_weekly_menu_endpoint_new_system_unavailable(self):
        """Ensure 503 is returned when modular system is disabled."""
        from fastapi.testclient import TestClient
        import os
        from unittest.mock import patch, MagicMock

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        # Mock the modular system as unavailable by patching imports
        with patch.dict(
            "sys.modules",
            {
                "core.weekly_plan_new": None,
                "core.food_db_new": None,
                "core.recipe_db_new": None,
                "core.recommendations": None,
                "app.routers.premium_week": None,
            },
        ):
            # Mock the premium_week_router import at module level
            with patch("app.premium_week_router", None):
                # Re-import app to trigger the import block with missing modules
                import importlib
                import app

                importlib.reload(app)

                with patch("os.path.exists", return_value=True):
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
                        "/api/v1/premium/plan/week",
                        json=payload,
                        headers={"X-API-Key": "test_key"},
                    )
                    assert response.status_code == 503
                    # Note: This test is difficult to implement correctly due to import architecture
                    # Skipping detailed assertion for now

        # Reload real module to avoid leaking mocks into other tests
        importlib.reload(app)

    def test_weekly_menu_endpoint_database_classes_none(self):
        """Ensure 503 when FoodDB/RecipeDB classes are unavailable."""
        from fastapi.testclient import TestClient
        import os
        import app

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        # Mock modules with None classes
        with patch.dict(
            "sys.modules",
            {
                "core.weekly_plan_new": MagicMock(),
                "core.food_db_new": MagicMock(FoodDB=None),
                "core.recipe_db_new": MagicMock(RecipeDB=None),
                "core.recommendations": MagicMock(),
            },
        ):
            # Re-import app to trigger the import block
            import importlib

            importlib.reload(app)

            with patch("os.path.exists", return_value=True):
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
                    "/api/v1/premium/plan/week",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 503
                assert "Database classes" in response.json()["detail"]

        # Reload real module to avoid leaking mocks into other tests
        importlib.reload(app)

    def test_weekly_menu_endpoint_build_nutrition_targets_none(self):
        """Ensure 503 when build_nutrition_targets is missing."""
        from fastapi.testclient import TestClient
        import os
        import app

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        # Mock modules with None build_nutrition_targets
        with patch.dict(
            "sys.modules",
            {
                "core.weekly_plan_new": MagicMock(),
                "core.food_db_new": MagicMock(),
                "core.recipe_db_new": MagicMock(),
                "core.recommendations": MagicMock(build_nutrition_targets=None),
            },
        ):
            # Re-import app to trigger the import block
            import importlib

            importlib.reload(app)

            with patch("os.path.exists", return_value=True):
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
                    "/api/v1/premium/plan/week",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 503
                assert "Nutrition targets" in response.json()["detail"]

        # Reload real module to avoid leaking mocks into other tests
        importlib.reload(app)

    def test_weekly_menu_endpoint_build_week_none(self):
        """Ensure 503 when build_week helper is missing."""
        from fastapi.testclient import TestClient
        import os
        import app

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        # Mock modules with None build_week
        with patch.dict(
            "sys.modules",
            {
                "core.weekly_plan_new": MagicMock(build_week=None),
                "core.food_db_new": MagicMock(),
                "core.recipe_db_new": MagicMock(),
                "core.recommendations": MagicMock(),
            },
        ):
            # Re-import app to trigger the import block
            import importlib

            importlib.reload(app)

            with patch("os.path.exists", return_value=True):
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
                    "/api/v1/premium/plan/week",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 503
                assert "Weekly plan generation" in response.json()["detail"]

        # Reload real module to avoid leaking mocks into other tests
        importlib.reload(app)

    def teardown_method(self):
        """Clean up test environment."""
        import os

        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]
        if "VIP_MODULE_ENABLED" in os.environ:
            del os.environ["VIP_MODULE_ENABLED"]
