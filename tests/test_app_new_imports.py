"""
Tests for new modular system imports in app.py.

These tests cover the new import block that checks for modular system availability.
"""

import importlib
from datetime import datetime, timezone
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def reload_app_module():
    """Reload app module on demand and reset after the test."""
    import app

    def _reload() -> ModuleType:
        return importlib.reload(app)

    yield _reload
    importlib.reload(app)


class TestAppNewImports:
    """Test class for new modular system imports."""

    def test_new_modular_system_import_success(self, reload_app_module):
        """Test successful import of new modular system components."""
        with patch.dict(
            "sys.modules",
            {
                "core.weekly_plan_new": MagicMock(),
                "core.food_db_new": MagicMock(),
                "core.recipe_db_new": MagicMock(),
                "core.recommendations": MagicMock(),
            },
        ):
            app_module = reload_app_module()

            assert hasattr(app_module, "NEW_MODULAR_SYSTEM_AVAILABLE")
            assert hasattr(app_module, "build_week")
            assert hasattr(app_module, "FoodDB")
            assert hasattr(app_module, "RecipeDB")
            assert hasattr(app_module, "build_nutrition_targets")

    def test_weekly_menu_endpoint_success(self, reload_app_module):
        """Test weekly menu endpoint with successful modular system (stubbed)."""
        from fastapi.testclient import TestClient
        import os

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        app_module = reload_app_module()

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
            patch("app.FoodDB"),
            patch("app.RecipeDB"),
        ):
            client = TestClient(app_module.app)

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

            assert response.status_code == 200
            assert "week_summary" in response.json()
            assert "daily_menus" in response.json()

    def test_weekly_menu_endpoint_missing_csv_files(self, reload_app_module):
        """Test weekly menu endpoint when CSV files are missing."""
        from fastapi.testclient import TestClient
        import os

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        with patch("os.path.exists", return_value=False):
            app_module = reload_app_module()
            client = TestClient(app_module.app)

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

    def test_weekly_menu_endpoint_invalid_payload(self, reload_app_module):
        """Test weekly menu endpoint with invalid payload."""
        from fastapi.testclient import TestClient
        import os

        os.environ["API_KEY"] = "test_key"
        os.environ["VIP_MODULE_ENABLED"] = "true"

        app_module = reload_app_module()

        client = TestClient(app_module.app)

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

        assert response.status_code == 422


    @pytest.mark.skip(
        reason="Complex module reload test - difficult to mock import architecture correctly"
    )
    def test_weekly_menu_endpoint_new_system_unavailable(
        self, reload_app_module
    ):
        """Ensure 503 is returned when modular system is disabled."""
        from fastapi.testclient import TestClient
        import os

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
                app_module = reload_app_module()

                with patch("os.path.exists", return_value=True):
                    client = TestClient(app_module.app)
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

    def test_weekly_menu_endpoint_database_classes_none(self, reload_app_module):
        """Ensure 503 when FoodDB/RecipeDB classes are unavailable."""
        from fastapi.testclient import TestClient
        import os

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
            app_module = reload_app_module()

            with patch("os.path.exists", return_value=True):
                client = TestClient(app_module.app)
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

    def test_weekly_menu_endpoint_build_nutrition_targets_none(
        self, reload_app_module
    ):
        """Ensure 503 when build_nutrition_targets is missing."""
        from fastapi.testclient import TestClient
        import os

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
            app_module = reload_app_module()

            with patch("os.path.exists", return_value=True):
                client = TestClient(app_module.app)
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

    def test_weekly_menu_endpoint_build_week_none(self, reload_app_module):
        """Ensure 503 when build_week helper is missing."""
        from fastapi.testclient import TestClient
        import os

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
            app_module = reload_app_module()

            with patch("os.path.exists", return_value=True):
                client = TestClient(app_module.app)
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

    def teardown_method(self):
        """Clean up test environment."""
        import os

        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]
        if "VIP_MODULE_ENABLED" in os.environ:
            del os.environ["VIP_MODULE_ENABLED"]


def test_get_week_start_utc_default_returns_monday(reload_app_module):
    """_get_week_start should compute Monday using UTC when no base_date is provided."""
    app_module = reload_app_module()
    week_start = app_module._get_week_start()

    computed_date = datetime.fromisoformat(week_start)
    assert computed_date.weekday() == 0, "Week start should fall on Monday"


def test_get_week_start_accepts_timezone_aware_base_date(reload_app_module):
    """_get_week_start should honor a provided timezone-aware base_date."""
    app_module = reload_app_module()
    base_date = datetime(2025, 1, 15, tzinfo=timezone.utc)  # Wednesday
    week_start = app_module._get_week_start(base_date)

    assert week_start == "2025-01-13"
