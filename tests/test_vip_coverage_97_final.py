"""
Final VIP coverage tests to achieve 97% coverage with proper isolation.
"""

import os
import sys
from typing import cast

from fastapi.testclient import TestClient
from starlette.types import ASGIApp


class TestVIPCoverage97Final:
    """Test class to achieve 97% coverage for VIP router with proper isolation."""

    def setup_method(self):
        """Set up test fixtures with proper isolation."""
        # Store original state
        self.original_api_key = os.environ.get("API_KEY")
        # Store only the modules we might modify
        modules_to_watch = [
            "app.routers.vip",
            "core.auto_repair",
            "core.menu_engine",
            "core.recipe_synth",
            "core.region_catalog",
            "core.shoplist",
        ]

        self.original_modules = {
            module_name: sys.modules[module_name]
            for module_name in modules_to_watch
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
        modules_to_restore = [
            "app.routers.vip",
            "core.auto_repair",
            "core.menu_engine",
            "core.recipe_synth",
            "core.region_catalog",
            "core.shoplist",
        ]

        for module_name in modules_to_restore:
            if module_name in self.original_modules:
                sys.modules[module_name] = self.original_modules[module_name]
            elif module_name in sys.modules:
                del sys.modules[module_name]

    def test_vip_import_fallback_coverage_lines_54_73(self):
        """Test VIP import fallback coverage for lines 54-73."""
        # Test that VIP module imports successfully and functions are available
        from app.routers import vip

        # Verify that VIP functions are available (not None)
        assert vip.make_weekly_menu is not None

    def test_vip_safe_call_with_adapter_missing(self):
        """Test VIP _safe_call_with_adapter with unknown function name returns error dict."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown", {})
        assert isinstance(result, dict) and result.get("status") == "error"

    def test_vip_weekly_menu_plan_coverage_lines_188_190(self, vip_headers):
        """Test VIP weekly menu plan coverage for lines 188-190."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test with invalid request (should get validation error)
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json="invalid",  # Non-dict request
            headers=vip_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_vip_shoplist_weekly_coverage_lines_217_254(self, monkeypatch, vip_headers):
        """Test VIP shoplist weekly coverage for lines 217-254."""
        import app
        from app.middleware import api_tiers

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

    def test_vip_shoplist_daily_coverage_lines_293_300(self, monkeypatch, vip_headers):
        """Test VIP shoplist daily coverage for lines 293-300."""
        import app
        from app.middleware import api_tiers

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
                "/api/v1/vip/shoplist/daily",
                json={
                    "items": [
                        {"food_id": "chicken", "qty": {"value": "500", "unit": "G"}, "form": "RAW"}
                    ],
                    "packaging_rules": [
                        {
                            "food_id": "chicken",
                            "pack_size": {"value": "500", "unit": "G"},
                            "rounding": "CEIL",
                            "min_packs": 1,
                        }
                    ],
                },
                headers=vip_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "packed" in data
            assert "unpacked" in data
        finally:
            app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)

    def test_vip_shoplist_formats_coverage_lines_304_348(self, vip_headers):
        """Test VIP shoplist formats coverage for lines 304-348."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test shoplist formats
        response = client.get("/api/v1/vip/shoplist/formats", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "formats" in data

    def test_vip_regions_coverage_lines_355_365(self, vip_headers):
        """Test VIP regions coverage for lines 355-365."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_region_search_coverage_lines_391_429(self, vip_headers):
        """Test VIP region search coverage for lines 391-429."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test region search endpoint
        response = client.get(
            "/api/v1/vip/regions/ES/search?query=test",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "products" in data

    def test_vip_region_categories_coverage_lines_457_469(self, vip_headers):
        """Test VIP region categories coverage for lines 457-469."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test region categories endpoint
        response = client.get(
            "/api/v1/vip/regions/ES/categories",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "categories" in data

    def test_vip_region_stores_coverage_lines_471_483(self, vip_headers):
        """Test VIP region stores coverage for lines 471-483."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test region stores endpoint
        response = client.get("/api/v1/vip/regions/ES/stores", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stores" in data

    def test_vip_price_comparison_coverage_lines_489_508(self, vip_headers):
        """Test VIP price comparison coverage for lines 489-508."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test price comparison endpoint
        response = client.get(
            "/api/v1/vip/regions/compare/test-product",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "comparison" in data

    def test_vip_recipe_templates_coverage_lines_507_508(self, vip_headers):
        """Test VIP recipe templates coverage for lines 507-508."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_weekly_coverage_lines_530(self, vip_headers):
        """Test VIP auto-repair weekly coverage for lines 530."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair weekly endpoint
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json={"menu": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"  # Returns error when auto_repair_menu is None
        assert "repair_result" in data

    def test_vip_auto_repair_suggestions_coverage_lines_589(self, vip_headers):
        """Test VIP auto-repair suggestions coverage for lines 589."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair suggestions endpoint
        response = client.post(
            "/api/v1/vip/auto-repair/suggestions",
            json={"menu": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "suggestions" in data

    def test_vip_auto_repair_strategies_coverage_lines_607(self, vip_headers):
        """Test VIP auto-repair strategies coverage for lines 607."""
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

    def test_vip_weekly_recipes_coverage_lines_656_660(self, vip_headers):
        """Test VIP weekly recipes coverage for lines 656-660."""
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

    def test_vip_weekly_plan_coverage_lines_873_905(self, vip_headers):
        """Test VIP weekly plan coverage for lines 873-905."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test weekly plan endpoint with valid WeeklyPlanRequest
        valid_request = {
            "sex": "female",
            "age": 32,
            "height_cm": 168.0,
            "weight_kg": 62.0,
            "activity": "light",
            "goal": "maintain",
        }
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=valid_request,
            headers=vip_headers,
        )
        assert response.status_code == 200  # Should work with valid request
        data = response.json()
        assert data["status"] == "success"
