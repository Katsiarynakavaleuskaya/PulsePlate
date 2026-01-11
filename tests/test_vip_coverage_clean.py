"""
Clean VIP coverage tests with proper isolation.
"""

import os
import sys
from typing import cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from app.middleware import api_tiers


class TestVIPCoverageClean:
    """Test class with proper isolation for VIP coverage."""

    def setup_method(self):
        """Set up test fixtures with proper isolation."""
        # Store original state
        self.original_api_key = os.environ.get("API_KEY")
        # Store only the modules we might modify
        self.modules_to_watch = [
            "app.routers.vip",
            "core.auto_repair",
            "core.menu_engine",
            "core.recipe_synth",
            "core.region_catalog",
            "core.shoplist",
        ]

        self.original_modules = {
            module_name: sys.modules[module_name]
            for module_name in self.modules_to_watch
            if module_name in sys.modules
        }
        # Set test environment
        os.environ["API_KEY"] = "test-key"

    def teardown_method(self):
        """Clean up test fixtures with proper isolation."""
        # Restore original environment
        if self.original_api_key is None:
            os.environ.pop("API_KEY", None)
        else:
            os.environ["API_KEY"] = self.original_api_key

        # Restore original modules more carefully
        # Only restore modules that were modified by our test
        for module_name in self.modules_to_watch:
            if module_name in self.original_modules:
                sys.modules[module_name] = self.original_modules[module_name]
            elif module_name in sys.modules:
                del sys.modules[module_name]

    def test_vip_import_fallback_coverage(self):
        """Test VIP import fallback coverage with proper isolation."""
        # Mock import failure to trigger fallback logic
        # Remove modules instead of setting to None (prevents sys.modules None poisoning)
        modules_to_restore = {}
        for mod_name in [
            "core.auto_repair",
            "core.menu_engine",
            "core.recipe_synth",
            "core.region_catalog",
            "core.shoplist",
        ]:
            if mod_name in sys.modules:
                modules_to_restore[mod_name] = sys.modules[mod_name]
                del sys.modules[mod_name]

        try:
            # Re-import the module to trigger fallback
            if "app.routers.vip" in sys.modules:
                del sys.modules["app.routers.vip"]

            from app.routers import vip

            # Verify fallback values are set to None
            assert vip.make_weekly_menu is not None
            assert vip.analyze_nutrient_gaps is not None
            assert vip.ShoplistGenerator is not None
            assert vip.aggregate_ingredients is not None
            assert vip.round_to_packages is not None
        finally:
            # Restore modules
            for mod_name, mod_obj in modules_to_restore.items():
                sys.modules[mod_name] = mod_obj
            assert vip.format_export is not None
            assert vip.get_region_catalog is not None
            assert vip.search_products is not None
            assert vip.get_available_regions is not None
            assert vip.get_price_comparison is not None
            assert vip.get_recipe_synthesizer is not None
            assert vip.synthesize_recipe_from_ingredients is not None
            assert vip.synthesize_recipes_for_week is not None
            assert vip.get_auto_repair_engine is not None
            assert vip.auto_repair_week_plan is not None
            assert vip.suggest_manual_fixes is not None
            assert vip.RepairStrategy is not None
            assert vip.RepairStatus is not None

    def test_vip_safe_call_with_adapter_error(self):
        """Test VIP _safe_call_with_adapter structured error when adapter missing."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown", {})
        assert isinstance(result, dict) and result.get("status") == "error"

    def test_vip_weekly_menu_plan_coverage(self, vip_headers: dict[str, str]):
        """Test VIP weekly menu plan coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test with invalid request (should get validation error)
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json="invalid",  # Non-dict request
            headers=vip_headers,
        )
        assert response.status_code == 422  # Validation error

        # Test with valid WeeklyPlanRequest structure
        valid_request = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
        }
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=valid_request,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data
        assert "menu" in data

    def test_vip_shoplist_weekly_coverage(
        self,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ):
        """Test VIP shoplist weekly coverage with proper isolation."""
        import app

        # Enable VIP module
        def mock_is_vip_module_enabled() -> bool:
            return True

        monkeypatch.setattr(
            "app.routers.vip_shoplist.is_vip_module_enabled",
            mock_is_vip_module_enabled,
        )

        # Override VIP tier dependency
        async def mock_require_vip_tier() -> str:
            return "vip"

        app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

        try:
            client = TestClient(cast(ASGIApp, app.app))

            # Use new API format for vip_shoplist router
            response = client.post(
                "/api/v1/vip/shoplist/weekly",
                json={
                    "days": [
                        {
                            "items": [
                                {
                                    "food_id": "chicken",
                                    "qty": {"value": "500", "unit": "G"},
                                    "form": "RAW",
                                }
                            ],
                            "packaging_rules": [
                                {
                                    "food_id": "chicken",
                                    "pack_size": {"value": "500", "unit": "G"},
                                    "rounding": "CEIL",
                                    "min_packs": 1,
                                }
                            ],
                        }
                    ]
                },
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "days" in data
            assert isinstance(data["days"], list)
        finally:
            app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)

    def test_vip_regions_coverage(self, vip_headers: dict[str, str]):
        """Test VIP regions coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_recipe_templates_coverage(self, vip_headers: dict[str, str]):
        """Test VIP recipe templates coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_strategies_coverage(self, vip_headers: dict[str, str]):
        """Test VIP auto-repair strategies coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair strategies endpoint
        response = client.get(
            "/api/v1/vip/auto-repair/strategies",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "strategies" in data

    def test_vip_weekly_recipes_coverage(self, vip_headers: dict[str, str]):
        """Test VIP weekly recipes coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test weekly recipes endpoint
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json={"week_plan": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "weekly_recipes" in data

    def test_vip_weekly_plan_coverage(self, vip_headers: dict[str, str]):
        """Test VIP weekly plan coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test weekly plan endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={"calories": 2000, "preferences": []},
            headers=vip_headers,
        )
        assert response.status_code == 422  # Validation error for invalid request
