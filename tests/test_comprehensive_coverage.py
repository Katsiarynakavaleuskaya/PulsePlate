"""
Comprehensive tests to improve coverage to 97%+.
"""

import os
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.types import ASGIApp
from typing import cast

import app as app_mod
from app import app
from tests.helpers.fast_update_stubs import (
    make_scheduler_stub,
    patch_app_get_update_scheduler,
)


class TestComprehensiveCoverage:
    """Comprehensive tests to improve coverage."""

    def setup_method(self) -> None:
        """Set up test environment."""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        self.client = TestClient(cast(ASGIApp, app))

    def teardown_method(self) -> None:
        """Clean up test environment."""
        # Explicitly close TestClient to clean up resources
        if hasattr(self, "client"):
            self.client.close()

        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]
        if "FEATURE_PREMIUM_NUTRITION" in os.environ:
            del os.environ["FEATURE_PREMIUM_NUTRITION"]

    def test_debug_env_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test debug_env endpoint with deterministic response."""
        # Mock environment variables to ensure consistent response
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("LLM_PROVIDER", "grok")
        monkeypatch.setenv("GROK_MODEL", "grok-1")
        monkeypatch.setenv("GROK_ENDPOINT", "https://api.x.ai/v1/chat/completions")

        response = self.client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        assert "FEATURE_INSIGHT" in data
        assert "LLM_PROVIDER" in data
        assert "GROK_MODEL" in data
        assert "GROK_ENDPOINT" in data
        assert "insight_enabled" in data

    def test_database_status_endpoint_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database status endpoint success case with deterministic assertions."""
        # Mock the update manager to return valid status
        with patch("app.get_update_scheduler", new_callable=AsyncMock) as mock_get_scheduler:
            mock_scheduler = AsyncMock()
            # get_status is SYNCHRONOUS, not async - use MagicMock not AsyncMock
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

            response = self.client.get("/api/v1/admin/db-status", headers={"X-API-Key": "test_key"})
            assert response.status_code == 200
            data = response.json()
            assert "scheduler" in data
            assert "databases" in data

    def test_database_status_endpoint_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test database status endpoint exception handling.

        This test is now deterministic by clearing the scheduler singleton and
        patching both the app module and scheduler module's get_update_scheduler.
        """
        # Clear the scheduler singleton to force fresh initialization
        from core.food_apis import scheduler

        monkeypatch.setattr(scheduler, "_scheduler_instance", None)

        # Clear any test scheduler override
        monkeypatch.setattr(app_mod, "_test_scheduler_override", None, raising=False)

        # Patch get_update_scheduler to raise an exception
        async def fake_get_scheduler_error():
            raise Exception("Test scheduler error")

        # Patch both the app module and scheduler module
        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_get_scheduler_error)
        monkeypatch.setattr(scheduler, "get_update_scheduler", fake_get_scheduler_error)

        response = self.client.get("/api/v1/admin/db-status", headers={"X-API-Key": "test_key"})

        # With cleared singleton and mocked function, should deterministically return 500
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_force_update_endpoint_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test force update endpoint success case with deterministic status."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.old_version = "1.0"
        mock_result.new_version = "1.1"
        mock_result.records_added = 10
        mock_result.records_updated = 5
        mock_result.records_removed = 0
        mock_result.duration_seconds = 1.0
        mock_result.errors = []
        scheduler = make_scheduler_stub(usda_result=mock_result)
        patch_app_get_update_scheduler(monkeypatch, app_mod, scheduler)

        response = self.client.post("/api/v1/admin/force-update", headers={"X-API-Key": "test_key"})
        # With successful mock, expect deterministic 200
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "results" in data

    def test_force_update_endpoint_with_source(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test force update endpoint with specific source - deterministic success."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.old_version = "1.0"
        mock_result.new_version = "1.1"
        mock_result.records_added = 5
        mock_result.records_updated = 3
        mock_result.records_removed = 1
        mock_result.duration_seconds = 0.5
        mock_result.errors = []
        scheduler = make_scheduler_stub(usda_result=mock_result)
        patch_app_get_update_scheduler(monkeypatch, app_mod, scheduler)

        response = self.client.post(
            "/api/v1/admin/force-update?source=usda",
            headers={"X-API-Key": "test_key"},
        )
        # With successful mock, expect deterministic 200
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "results" in data

    def test_force_update_endpoint_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test force update endpoint exception handling - deterministic.

        This test now clears the scheduler singleton to ensure the mock is invoked.
        """
        # Clear the scheduler singleton to force fresh initialization
        from core.food_apis import scheduler

        monkeypatch.setattr(scheduler, "_scheduler_instance", None)

        # Clear any test scheduler override
        monkeypatch.setattr(app_mod, "_test_scheduler_override", None, raising=False)

        # Patch using monkeypatch to ensure the endpoint sees the mock
        async def fake_get_scheduler_error():
            raise Exception("Test error")

        # Patch both the app module and scheduler module
        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_get_scheduler_error)
        monkeypatch.setattr(scheduler, "get_update_scheduler", fake_get_scheduler_error)

        response = self.client.post("/api/v1/admin/force-update", headers={"X-API-Key": "test_key"})
        # With cleared singleton and mocked function, should deterministically return 500
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_check_updates_endpoint_success(self) -> None:
        """Test check updates endpoint success case with deterministic status."""
        with patch("app.get_update_scheduler", new_callable=AsyncMock) as mock_get_scheduler:
            mock_scheduler = AsyncMock()
            mock_scheduler.update_manager.check_for_updates = AsyncMock(
                return_value={"usda": True, "openfoodfacts": False}
            )
            mock_get_scheduler.return_value = mock_scheduler

            response = self.client.get(
                "/api/v1/admin/check-updates", headers={"X-API-Key": "test_key"}
            )
            # With successful mock, expect deterministic 200
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "updates_available" in data

    def test_check_updates_endpoint_exception(self) -> None:
        """Test check updates endpoint exception handling - deterministic error."""
        with patch("app.get_update_scheduler", new_callable=AsyncMock) as mock_get_scheduler:
            mock_get_scheduler.side_effect = Exception("Test error")

            response = self.client.get(
                "/api/v1/admin/check-updates", headers={"X-API-Key": "test_key"}
            )
            # Endpoint should return 500 for scheduler errors
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    @pytest.mark.serial
    def test_rollback_endpoint_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test rollback endpoint success case."""
        # Use monkeypatch.setattr to patch module-level function for FastAPI endpoints

        async def fake_scheduler() -> SimpleNamespace:
            # Return a scheduler with update_manager.rollback_database that returns True
            mock_update_manager = SimpleNamespace(rollback_database=AsyncMock(return_value=True))
            return SimpleNamespace(update_manager=mock_update_manager)

        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_scheduler)
        response = self.client.post(
            "/api/v1/admin/rollback",
            params={"source": "usda", "target_version": "1.0"},
            headers={"X-API-Key": "test_key"},
        )
        # When rollback_database returns True, endpoint should return 200
        assert (
            response.status_code == 200
        ), f"Rollback success should return 200, got {response.status_code}"
        data = response.json()
        assert (
            "message" in data
        ), "API response must contain 'message' key per rollback endpoint contract"

    @pytest.mark.serial
    def test_rollback_endpoint_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test rollback endpoint exception handling with deterministic mock."""

        # Patch get_update_scheduler to raise an exception
        async def fake_scheduler_error():
            raise Exception("Test scheduler error")

        # Patch both the module attribute and globals to ensure the endpoint sees it
        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_scheduler_error)

        response = self.client.post(
            "/api/v1/admin/rollback",
            params={"source": "usda", "target_version": "1.0"},
            headers={"X-API-Key": "test_key"},
        )

        # Assert deterministic 500 error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Rollback operation failed" in data["detail"]
        assert "could not get scheduler" in data["detail"]

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_rollback_function_no_update_manager(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test rollback_database function when scheduler has no update_manager."""

        async def fake_scheduler():
            return SimpleNamespace(update_manager=None)

        # Rely on module-level patch; __globals__ mutation is unnecessary
        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_scheduler)

        # Since we fixed rollback_database to raise HTTPException,
        # this test now needs to expect HTTPException rather than generic Exception
        with pytest.raises(HTTPException) as exc_info:
            await app_mod.rollback_database("usda", "1.0")
        # The function should raise because update_manager is None
        assert "update manager" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    @pytest.mark.serial
    async def test_rollback_function_no_rollback_method(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test rollback_database function when update_manager lacks rollback method."""

        async def fake_scheduler():
            return SimpleNamespace(update_manager=SimpleNamespace())

        # Rely on module-level patch; __globals__ mutation is unnecessary
        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_scheduler)

        # Since we fixed rollback_database to raise HTTPException,
        # this test now needs to expect HTTPException rather than generic Exception
        with pytest.raises(HTTPException) as exc_info:
            await app_mod.rollback_database("usda", "1.0")
        # The function should raise because rollback_database method is missing
        assert "not supported" in str(exc_info.value.detail).lower()

    @pytest.mark.serial
    def test_rollback_endpoint_rollback_function_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test rollback when rollback_database raises exception."""

        # Patch get_update_scheduler to return a scheduler with failing rollback
        async def fake_scheduler():
            # Return a scheduler whose rollback_database raises an exception
            async def failing_rollback(source, target_version):
                raise Exception("Rollback failed")

            mock_update_manager = SimpleNamespace(rollback_database=failing_rollback)
            return SimpleNamespace(update_manager=mock_update_manager)

        # Patch both the module attribute and globals to ensure the endpoint sees it
        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_scheduler)

        response = self.client.post(
            "/api/v1/admin/rollback",
            params={"source": "usda", "target_version": "1.0"},
            headers={"X-API-Key": "test_key"},
        )

        # Assert deterministic 500 error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Rollback operation failed" in data["detail"]
        assert "Rollback failed" in data["detail"]

    @pytest.mark.serial
    def test_rollback_endpoint_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test rollback when rollback_database returns False."""

        # Patch get_update_scheduler to return a scheduler with rollback returning False
        async def fake_scheduler():
            # Return a scheduler whose rollback_database returns False
            mock_update_manager = SimpleNamespace(rollback_database=AsyncMock(return_value=False))
            return SimpleNamespace(update_manager=mock_update_manager)

        # Patch both the module attribute and globals to ensure the endpoint sees it
        monkeypatch.setattr(app_mod, "get_update_scheduler", fake_scheduler)

        response = self.client.post(
            "/api/v1/admin/rollback",
            params={"source": "usda", "target_version": "1.0"},
            headers={"X-API-Key": "test_key"},
        )

        # Assert deterministic 500 error response when rollback returns False
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Rollback operation failed" in data["detail"]
        assert "usda" in data["detail"]
        assert "1.0" in data["detail"]

    def test_premium_plate_endpoint_success(self) -> None:
        """Test premium plate endpoint success case."""
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        try:
            with (
                patch("app.make_plate") as mock_make_plate,
                patch("app.calculate_all_bmr") as mock_calc_bmr,
                patch("app.calculate_all_tdee") as mock_calc_tdee,
            ):
                self._assert_premium_plate_success(mock_calc_bmr, mock_calc_tdee, mock_make_plate)
        finally:
            if "FEATURE_PREMIUM_NUTRITION" in os.environ:
                del os.environ["FEATURE_PREMIUM_NUTRITION"]

    def _create_premium_plate_mock_data(self) -> Dict[str, Any]:
        """Create mock plate data for premium plate endpoint tests.

        Returns:
            Dictionary with complete plate data structure including kcal, macros, portions, layout, and meals.
        """
        return {
            "kcal": 2000,
            "macros": {
                "protein_g": 100,
                "fat_g": 70,
                "carbs_g": 250,
                "fiber_g": 30,
            },
            "portions": {
                "protein_palm": 4.0,
                "carb_cups": 3.0,
                "veg_cups": 2.0,
                "fat_thumbs": 2.5,
            },
            "layout": [
                {
                    "kind": "plate_sector",
                    "fraction": 0.4,
                    "label": "Carbs",
                    "tooltip": "Energy source",
                },
                {
                    "kind": "plate_sector",
                    "fraction": 0.3,
                    "label": "Protein",
                    "tooltip": "Muscle building",
                },
                {
                    "kind": "plate_sector",
                    "fraction": 0.2,
                    "label": "Vegetables",
                    "tooltip": "Vitamins & minerals",
                },
                {
                    "kind": "plate_sector",
                    "fraction": 0.1,
                    "label": "Fats",
                    "tooltip": "Essential fatty acids",
                },
            ],
            "meals": [
                {
                    "title": "Breakfast",
                    "kcal": 500,
                    "protein_g": 25,
                    "fat_g": 15,
                    "carbs_g": 60,
                },
                {
                    "title": "Lunch",
                    "kcal": 750,
                    "protein_g": 35,
                    "fat_g": 25,
                    "carbs_g": 90,
                },
            ],
        }

    def _create_premium_bmr_mocks(
        self, mock_calc_bmr: MagicMock, mock_calc_tdee: MagicMock
    ) -> None:
        """Configure BMR and TDEE mock return values.

        Args:
            mock_calc_bmr: MagicMock for calculate_all_bmr function
            mock_calc_tdee: MagicMock for calculate_all_tdee function
        """
        mock_calc_bmr.return_value = {"mifflin": 1500}
        mock_calc_tdee.return_value = {"mifflin": 2000}

    def _assert_premium_plate_success(
        self,
        mock_calc_bmr: MagicMock,
        mock_calc_tdee: MagicMock,
        mock_make_plate: MagicMock,
    ) -> None:
        """Test helper for premium plate endpoint success path.

        Args:
            mock_calc_bmr: MagicMock for calculate_all_bmr function
            mock_calc_tdee: MagicMock for calculate_all_tdee function
            mock_make_plate: MagicMock for make_plate function
        """
        # Configure mocks using helper functions
        self._create_premium_bmr_mocks(mock_calc_bmr, mock_calc_tdee)
        mock_make_plate.return_value = self._create_premium_plate_mock_data()

        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175,
            "weight_kg": 70,
            "activity": "moderate",
            "goal": "maintain",
        }

        response = self.client.post(
            "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
        )

        # Assertions stay in test body
        assert response.status_code == 200
        data = response.json()
        assert "kcal" in data
        assert "macros" in data
        assert "portions" in data

    def test_premium_plate_endpoint_value_error(self) -> None:
        """Test premium plate endpoint with ValueError."""
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        try:
            with patch("app.make_plate") as mock_make_plate:
                mock_make_plate.side_effect = ValueError("Invalid input")

                payload = {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "goal": "maintain",
                }

                response = self.client.post(
                    "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
                )
                # ValueError is caught and returns 400 (not 422 which is for schema validation)
                assert response.status_code == 400
        finally:
            if "FEATURE_PREMIUM_NUTRITION" in os.environ:
                del os.environ["FEATURE_PREMIUM_NUTRITION"]

    def test_premium_plate_endpoint_general_exception(self) -> None:
        """Test premium plate endpoint with general exception."""
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        with patch("app.make_plate") as mock_make_plate:
            mock_make_plate.side_effect = Exception("Test error")

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
                "goal": "maintain",
            }

            response = self.client.post(
                "/api/v1/premium/plate", json=payload, headers={"X-API-Key": "test_key"}
            )
            assert response.status_code == 500

    def test_premium_plate_missing_nh3_returns_424(self) -> None:
        """Test premium plate endpoint returns 424 when nh3 dependency is missing."""
        from core.data_sanitizer import MissingOptionalDependencyError

        with patch.dict(os.environ, {"FEATURE_PREMIUM_NUTRITION": "true"}, clear=False):
            import core.data_sanitizer as data_sanitizer

            with patch.object(data_sanitizer, "_require_nh3") as mock_require:
                mock_require.side_effect = MissingOptionalDependencyError(
                    "nh3",
                    (
                        "Optional dependency 'nh3' is required for plate data sanitization. "
                        "Install it with: python -m pip install nh3"
                    ),
                )

                payload = {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "moderate",
                    "goal": "maintain",
                }

                response = self.client.post(
                    "/api/v1/premium/plate",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )

        assert response.status_code == 424
        body = response.json()
        assert isinstance(body.get("detail"), dict)
        detail = body["detail"]
        assert detail.get("error") == "missing_dependency"
        assert detail.get("dependency") == "nh3"
        assert detail.get("message", "").startswith("HTML sanitization library (nh3)")
        assert "pip install nh3" in detail.get("action", "")

    def test_who_targets_endpoint_success(self) -> None:
        """Test WHO targets endpoint success case."""
        with patch("app.build_nutrition_targets") as mock_build_targets:
            mock_targets = MagicMock()
            mock_targets.kcal_daily = 2000
            mock_targets.macros.protein_g = 100
            mock_targets.macros.fat_g = 70
            mock_targets.macros.carbs_g = 250
            mock_targets.macros.fiber_g = 30
            mock_targets.water_ml_daily = 2500
            mock_targets.micros.get_priority_nutrients.return_value = {
                "iron_mg": 18.0,
                "calcium_mg": 1000.0,
            }
            mock_targets.activity.moderate_aerobic_min = 150
            mock_targets.activity.strength_sessions = 3
            mock_targets.activity.steps_daily = 8000
            mock_targets.calculation_date = "2023-01-01"

            mock_build_targets.return_value = mock_targets

            # Mock the validate_targets_safety function from core.recommendations
            with patch("core.recommendations.validate_targets_safety") as mock_validate:
                mock_validate.return_value = ["Warning: High sodium intake"]

                payload = {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "moderate",
                }

                response = self.client.post(
                    "/api/v1/premium/targets",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 200
                data = response.json()
                assert "kcal_daily" in data
                assert "macros" in data
                assert "water_ml" in data

    def test_who_targets_endpoint_value_error(self) -> None:
        """Test WHO targets endpoint with ValueError returns fallback (200)."""
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        with patch("app.build_nutrition_targets") as mock_build_targets:
            mock_build_targets.side_effect = ValueError("Invalid input")

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
            }

            response = self.client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            # Endpoint now returns 200 with fallback targets when build_nutrition_targets fails
            assert response.status_code == 200
            data = response.json()
            assert "macros" in data
            assert "kcal_daily" in data

    def test_who_targets_endpoint_general_exception(self) -> None:
        """Test WHO targets endpoint with general exception returns fallback (200)."""
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        with patch("app.build_nutrition_targets") as mock_build_targets:
            mock_build_targets.side_effect = Exception("Test error")

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
            }

            response = self.client.post(
                "/api/v1/premium/targets",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            # Endpoint now returns 200 with fallback targets when build_nutrition_targets fails
            assert response.status_code == 200
            data = response.json()
            assert "macros" in data
            assert "kcal_daily" in data

    def test_weekly_menu_endpoint_success(self) -> None:
        """Test weekly menu endpoint success case."""
        with patch("app.make_weekly_menu") as mock_make_menu:
            mock_week_menu = MagicMock()
            mock_week_menu.week_start = "2023-01-01"
            mock_week_menu.total_cost = 140.0

            mock_daily_menu = MagicMock()
            mock_daily_menu.date = "2023-01-01"
            mock_daily_menu.meals = [
                {"name": "Breakfast", "kcal": 500},
                {"name": "Lunch", "kcal": 750},
            ]
            mock_daily_menu.estimated_cost = 20.0

            mock_week_menu.daily_menus = [mock_daily_menu]
            mock_week_menu.weekly_coverage = {"protein_g": 95.0, "iron_mg": 85.0}
            mock_week_menu.shopping_list = {"chicken_breast_kg": 1.0, "rice_kg": 0.5}
            mock_week_menu.adherence_score = 92.0

            mock_make_menu.return_value = mock_week_menu

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
            }

            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "week_summary" in data
            assert "daily_menus" in data
            assert "weekly_coverage" in data

    def test_weekly_menu_endpoint_value_error(self) -> None:
        """Test weekly menu endpoint with ValueError."""
        with patch("app.make_weekly_menu") as mock_make_menu:
            mock_make_menu.side_effect = ValueError("Invalid input")

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
            }

            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            # ValueError is caught by the weekly menu endpoint and returns 400 (HTTPException)
            assert response.status_code == 400

    def test_weekly_menu_endpoint_general_exception(self) -> None:
        """Test weekly menu endpoint with general exception."""
        with patch("app.make_weekly_menu") as mock_make_menu:
            mock_make_menu.side_effect = Exception("Test error")

            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "moderate",
            }

            response = self.client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )
            assert response.status_code == 500

    def test_nutrient_gaps_endpoint_success(self) -> None:
        """Test nutrient gaps endpoint success case."""
        with (
            patch("app.analyze_nutrient_gaps") as mock_analyze,
            patch("app.build_nutrition_targets") as mock_build_targets,
        ):
            mock_targets = MagicMock()
            mock_targets.kcal_daily = 2000
            mock_targets.macros.protein_g = 100
            mock_targets.macros.fat_g = 70
            mock_targets.macros.carbs_g = 250
            mock_targets.macros.fiber_g = 30
            mock_targets.water_ml_daily = 2500
            mock_targets.micros.get_priority_nutrients.return_value = {
                "iron_mg": 18.0,
                "calcium_mg": 1000.0,
            }
            mock_targets.activity.moderate_aerobic_min = 150
            mock_targets.activity.strength_sessions = 3
            mock_targets.activity.steps_daily = 8000
            mock_targets.calculation_date = "2023-01-01"

            mock_build_targets.return_value = mock_targets
            mock_analyze.return_value = {"iron_mg": {"deficit": 5.0, "priority": "high"}}

            # Mock the functions from core.recommendations
            with (
                patch("core.recommendations.generate_deficiency_recommendations") as mock_recommend,
                patch("core.recommendations.score_nutrient_coverage") as mock_score,
            ):
                mock_recommend.return_value = ["Eat more red meat for iron"]
                mock_score.return_value = {"iron_mg": MagicMock(coverage_percent=75.0)}

                payload = {
                    "consumed_nutrients": {
                        "protein_g": 80,
                        "fat_g": 60,
                        "carbs_g": 200,
                    },
                    "user_profile": {
                        "sex": "male",
                        "age": 30,
                        "height_cm": 175,
                        "weight_kg": 70,
                        "activity": "sedentary",
                        "goal": "maintain",
                    },
                }

                response = self.client.post(
                    "/api/v1/premium/gaps",
                    json=payload,
                    headers={"X-API-Key": "test_key"},
                )
                assert response.status_code == 200
                data = response.json()
                assert "gaps" in data
                assert "food_recommendations" in data
                assert "adherence_score" in data

    def test_nutrient_gaps_endpoint_value_error(self) -> None:
        """Test nutrient gaps endpoint with ValueError."""
        payload = {
            "consumed_nutrients": {"protein_g": 80, "fat_g": 60, "carbs_g": 200},
            "user_profile": {
                "sex": "male",
                "age": -5,  # Invalid age
                "height_cm": 175,
                "weight_kg": 70,
                "activity": "sedentary",
                "goal": "maintain",
            },
        }

        response = self.client.post(
            "/api/v1/premium/gaps", json=payload, headers={"X-API-Key": "test_key"}
        )
        # With Pydantic validation, this will be a 422 (unprocessable entity) rather than 400
        assert response.status_code in [400, 422]

    def test_nutrient_gaps_endpoint_general_exception(self) -> None:
        """Test nutrient gaps endpoint with general exception.

        This test uses patch to deterministically trigger the exception path
        by making build_nutrition_targets raise an exception via score_nutrient_coverage.
        """
        # Patch score_nutrient_coverage to raise an exception
        # This function is called after build_targets succeeds, so it will trigger the exception handler
        with patch("core.recommendations.score_nutrient_coverage") as mock_score:
            mock_score.side_effect = Exception("Test error in score_nutrient_coverage")

            payload = {
                "consumed_nutrients": {"protein_g": 80, "fat_g": 60, "carbs_g": 200},
                "user_profile": {
                    "sex": "male",
                    "age": 30,
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity": "sedentary",
                    "goal": "maintain",
                },
            }

            response = self.client.post(
                "/api/v1/premium/gaps", json=payload, headers={"X-API-Key": "test_key"}
            )
            # With exception in score_nutrient_coverage, should return 500
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
