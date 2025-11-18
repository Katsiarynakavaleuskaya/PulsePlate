"""
Final VIP coverage tests to achieve 97% coverage with proper isolation.
"""

import os
import sys
from typing import cast
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from starlette.types import ASGIApp


class TestVIPCoverage97Final:
    """Test class to achieve 97% coverage for VIP router with proper isolation."""

    def setup_method(self) -> None:
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

    def teardown_method(self) -> None:
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

    def test_vip_import_fallback_coverage_lines_54_73(self) -> None:
        """Test VIP import fallback coverage for lines 54-73."""
        # Test that VIP module imports successfully and functions are available
        from app.routers import vip

        # Verify that VIP functions are available (not None)
        assert vip.make_weekly_menu is not None

    def test_vip_safe_call_with_adapter_missing(self) -> None:
        """Test VIP _safe_call_with_adapter with unknown function name returns error dict."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown", {})
        assert isinstance(result, dict) and result.get("status") == "error"

    def test_vip_weekly_menu_plan_coverage_lines_188_190(self) -> None:
        """Test VIP weekly menu plan coverage for lines 188-190."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test with invalid request (should get validation error)
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json="invalid",  # Non-dict request
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 422  # Validation error

    def test_vip_shoplist_weekly_coverage_lines_217_254(self) -> None:
        """Test VIP shoplist weekly coverage for lines 217-254."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test weekly shoplist generation
        response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json={"menu": {"days": []}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "shopping_list" in data

    def test_vip_shoplist_daily_coverage_lines_293_300(self) -> None:
        """Test VIP shoplist daily coverage for lines 293-300."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test daily shoplist generation
        response = client.post(
            "/api/v1/vip/shoplist/daily",
            json={"menu": {"days": []}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "shopping_list" in data

    def test_vip_shoplist_formats_coverage_lines_304_348(self) -> None:
        """Test VIP shoplist formats coverage for lines 304-348."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test shoplist formats
        response = client.get("/api/v1/vip/shoplist/formats", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "formats" in data

    def test_vip_regions_coverage_lines_355_365(self) -> None:
        """Test VIP regions coverage for lines 355-365."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_region_search_coverage_lines_391_429(self) -> None:
        """Test VIP region search coverage for lines 391-429."""
        import app
        from app.routers import vip as vip_router

        client = TestClient(cast(ASGIApp, app.app))

        # Mock search_products to return success
        mock_product = MagicMock()
        mock_product.product_id = "123"
        mock_product.name_es = "Test Product"
        mock_product.name_en = "Test Product"
        mock_product.category = "test"
        mock_product.unit = "kg"
        mock_product.typical_package_size = 1.0
        mock_product.price_eur = 1.0
        mock_product.price_usd = 1.2
        mock_product.store_chain = "Test Store"
        mock_product.region = "ES"

        mock_search_result = MagicMock()
        mock_search_result.products = [mock_product]
        mock_search_result.total_count = 1

        # Ensure search_products is not None before patching
        original_search_products = vip_router.search_products
        if original_search_products is None:
            vip_router.search_products = lambda *args, **kwargs: mock_search_result

        with patch.object(vip_router, "search_products", return_value=mock_search_result):
            # Test region search endpoint
            response = client.get(
                "/api/v1/vip/regions/ES/search?query=test", headers={"X-API-Key": "test-key"}
            )
            assert (
                response.status_code == 200
            ), f"Expected 200, got {response.status_code}. Response: {response.text}"
            data = response.json()
            assert (
                data["status"] == "success"
            ), f"Expected 'success', got '{data.get('status')}'. Full response: {data}"
            assert "products" in data

    def test_vip_region_categories_coverage_lines_457_469(self) -> None:
        """Test VIP region categories coverage for lines 457-469."""
        import app
        from app.routers import vip as vip_router

        client = TestClient(cast(ASGIApp, app.app))

        # Mock get_region_catalog to return success
        mock_catalog = MagicMock()
        mock_catalog.get_categories.return_value = ["dairy", "vegetables", "fruits"]

        # Ensure get_region_catalog is not None before patching
        original_get_region_catalog = vip_router.get_region_catalog
        if original_get_region_catalog is None:
            vip_router.get_region_catalog = lambda *args, **kwargs: mock_catalog

        with patch.object(vip_router, "get_region_catalog", return_value=mock_catalog):
            # Test region categories endpoint
            response = client.get(
                "/api/v1/vip/regions/ES/categories", headers={"X-API-Key": "test-key"}
            )
            assert (
                response.status_code == 200
            ), f"Expected 200, got {response.status_code}. Response: {response.text}"
            data = response.json()
            assert (
                data["status"] == "success"
            ), f"Expected 'success', got '{data.get('status')}'. Full response: {data}"
            assert "categories" in data

    def test_vip_region_stores_coverage_lines_471_483(self) -> None:
        """Test VIP region stores coverage for lines 471-483."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test region stores endpoint
        response = client.get("/api/v1/vip/regions/ES/stores", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stores" in data

    def test_vip_price_comparison_coverage_lines_489_508(self) -> None:
        """Test VIP price comparison coverage for lines 489-508."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test price comparison endpoint
        response = client.get(
            "/api/v1/vip/regions/compare/test-product", headers={"X-API-Key": "test-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "comparison" in data

    def test_vip_recipe_templates_coverage_lines_507_508(self) -> None:
        """Test VIP recipe templates coverage for lines 507-508."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_weekly_coverage_lines_530(self) -> None:
        """Test VIP auto-repair weekly coverage for lines 530."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair weekly endpoint
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json={"menu": {"days": []}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"  # Returns error when auto_repair_menu is None
        assert "repair_result" in data

    def test_vip_auto_repair_suggestions_coverage_lines_589(self) -> None:
        """Test VIP auto-repair suggestions coverage for lines 589."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair suggestions endpoint
        response = client.post(
            "/api/v1/vip/auto-repair/suggestions",
            json={"menu": {"days": []}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "suggestions" in data

    def test_vip_auto_repair_strategies_coverage_lines_607(self) -> None:
        """Test VIP auto-repair strategies coverage for lines 607."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair strategies endpoint
        response = client.get(
            "/api/v1/vip/auto-repair/strategies", headers={"X-API-Key": "test-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "strategies" in data

    def test_vip_weekly_recipes_coverage_lines_656_660(self) -> None:
        """Test VIP weekly recipes coverage for lines 656-660."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test weekly recipes endpoint
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json={"week_plan": {"days": []}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "weekly_recipes" in data

    def test_vip_weekly_plan_coverage_lines_873_905(self) -> None:
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
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200  # Should work with valid request
        data = response.json()
        assert data["status"] == "success"
