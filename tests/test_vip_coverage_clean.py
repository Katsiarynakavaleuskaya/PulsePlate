"""
Clean VIP coverage tests with proper isolation.
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from app.middleware import api_tiers


class TestVIPCoverageClean:
    """Test class with proper isolation for VIP coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures with proper isolation."""
        # Store original state
        self.original_api_key = os.environ.get("API_KEY")
        # Set test environment
        os.environ["API_KEY"] = "test-key"

    def teardown_method(self) -> None:
        """Clean up test fixtures with proper isolation."""
        # Restore original environment
        if self.original_api_key is None:
            os.environ.pop("API_KEY", None)
        else:
            os.environ["API_KEY"] = self.original_api_key

    def test_vip_import_fallback_coverage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VIP import fallback coverage with proper isolation."""
        import app.routers.vip as vip

        from core import auto_repair

        try:
            monkeypatch.delattr(auto_repair, "RepairStatus", raising=False)
            vip_module = sys.modules.get("app.routers.vip", vip)
            importlib.reload(vip_module)

            assert vip_module.make_weekly_menu is None
            assert vip_module.analyze_nutrient_gaps is None
            assert vip_module.ShoplistGenerator is None
            assert vip_module.aggregate_ingredients is None
            assert vip_module.round_to_packages is None
            assert vip_module.format_export is None
            assert vip_module.get_region_catalog is None
            assert vip_module.search_products is None
            assert vip_module.get_available_regions is None
            assert vip_module.get_price_comparison is None
            assert vip_module.get_recipe_synthesizer is None
            assert vip_module.synthesize_recipe_from_ingredients is None
            assert vip_module.synthesize_recipes_for_week is None
            assert vip_module.get_auto_repair_engine is None
            assert vip_module.auto_repair_week_plan is None
            assert vip_module.suggest_manual_fixes is None
            assert vip_module.RepairStrategy is None
            assert vip_module.RepairStatus is None
        finally:
            monkeypatch.undo()
            vip_module = sys.modules.get("app.routers.vip", vip)
            importlib.reload(vip_module)

    def test_vip_safe_call_with_adapter_error(self) -> None:
        """Test VIP _safe_call_with_adapter structured error when adapter missing."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown", {})
        assert isinstance(result, dict) and result.get("status") == "error"

    def test_vip_weekly_menu_plan_coverage(self, vip_headers: dict[str, str]) -> None:
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
    ) -> None:
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
            )
            assert response.status_code == 200
            data = response.json()
            assert "days" in data
            assert isinstance(data["days"], list)
        finally:
            app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)

    def test_vip_regions_coverage(self, vip_headers: dict[str, str]) -> None:
        """Test VIP regions coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_recipe_templates_coverage(self, vip_headers: dict[str, str]) -> None:
        """Test VIP recipe templates coverage with proper isolation."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_strategies_coverage(self, vip_headers: dict[str, str]) -> None:
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

    def test_vip_weekly_recipes_coverage(self, vip_headers: dict[str, str]) -> None:
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

    def test_vip_weekly_plan_coverage(self, vip_headers: dict[str, str]) -> None:
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
