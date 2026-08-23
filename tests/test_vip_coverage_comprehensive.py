"""
Comprehensive VIP coverage tests to achieve 97% coverage for all missing lines.
"""

import os
from typing import cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp

from app.middleware import api_tiers
from tests._helpers.vip_contracts import assert_json_response_payload


class TestVIPCoverageComprehensive:
    """Test class to achieve 97% coverage for VIP router covering all missing lines."""

    def setup_method(self):
        """Set up test fixtures with proper isolation."""
        # Store original state
        self.original_api_key = os.environ.get("API_KEY")
        # Set test environment
        os.environ["API_KEY"] = "test-key"

    def teardown_method(self):
        """Clean up test fixtures with proper isolation."""
        # Restore original environment
        if self.original_api_key is None:
            os.environ.pop("API_KEY", None)
        else:
            os.environ["API_KEY"] = self.original_api_key

    def test_vip_api_key_validation_coverage_lines_98_105_110(self):
        """Test VIP API key validation coverage for lines 98, 105-110."""
        from app.routers.vip import _require_api_key

        # Test with None function (line 98)
        with patch("app.routers.vip.resolve_attr", return_value=None):
            result = _require_api_key("test-key")
            assert result == "test-key"  # Returns key as-is when API_KEY is not set

        # Test with function that returns non-string (lines 105-110)
        with patch("app.routers.vip.resolve_attr", return_value=123):
            result = _require_api_key("test-key")
            assert result == "test-key"  # Returns key as-is when API_KEY is not set

    def test_vip_safe_call_with_adapter_error(self):
        """Test VIP _safe_call_with_adapter structured error when adapter missing."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown", {})
        assert isinstance(result, dict) and result.get("status") == "error"

    def test_vip_weekly_menu_plan_coverage_lines_173_180(self, vip_headers: dict[str, str]):
        """Test VIP weekly menu plan coverage for lines 173, 180."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test with invalid request (line 173)
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json="invalid",  # Non-dict request
            headers=vip_headers,
        )
        assert response.status_code == 422  # Validation error

        # Test with valid WeeklyPlanRequest structure
        valid_request = {
            "sex": "female",
            "age": 25,
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity": "light",
            "goal": "loss",
        }
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=valid_request,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_vip_weekly_menu_plan_error_coverage_lines_189_191(self, vip_headers: dict[str, str]):
        """Test VIP weekly menu plan error coverage for lines 189-191."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test with valid WeeklyPlanRequest that should work
        valid_request = {
            "sex": "male",
            "age": 35,
            "height_cm": 180.0,
            "weight_kg": 80.0,
            "activity": "active",
            "goal": "gain",
        }
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=valid_request,
            headers=vip_headers,
        )
        assert response.status_code == 200  # Should work with valid request
        data = response.json()
        assert data["status"] == "success"

    def test_vip_shoplist_weekly_coverage_lines_219_259(
        self, monkeypatch, vip_headers: dict[str, str]
    ):
        """Test VIP shoplist weekly coverage for lines 219-259."""
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

    def test_vip_shoplist_daily_coverage_lines_315_316(
        self, monkeypatch, vip_headers: dict[str, str]
    ):
        """Test VIP shoplist daily coverage for lines 315-316."""
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

    def test_vip_shoplist_formats_coverage_lines_350_361_362(self, vip_headers: dict[str, str]):
        """Test VIP shoplist formats coverage for lines 350, 361-362."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test shoplist formats
        response = client.get("/api/v1/vip/shoplist/formats", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "formats" in data

    def test_vip_regions_coverage_lines_421_422_449(self, vip_headers: dict[str, str]):
        """Test VIP regions coverage for lines 421-422, 449."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_region_search_coverage_lines_485_486(self, vip_headers: dict[str, str]):
        """Test VIP region search coverage for lines 485-486."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test region search endpoint
        response = client.get("/api/v1/vip/regions/ES/search?query=test", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "products" in data

    def test_vip_region_categories_coverage_line_508(self, vip_headers: dict[str, str]):
        """Test VIP region categories coverage for line 508."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test region categories endpoint
        response = client.get("/api/v1/vip/regions/ES/categories", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "categories" in data

    def test_vip_region_stores_coverage_lines_525_526(self, vip_headers: dict[str, str]):
        """Test VIP region stores coverage for lines 525-526."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test region stores endpoint
        response = client.get("/api/v1/vip/regions/ES/stores", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "stores" in data

    def test_vip_price_comparison_coverage_line_547(self, vip_headers: dict[str, str]):
        """Test VIP price comparison coverage for line 547."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test price comparison endpoint
        response = client.get("/api/v1/vip/regions/compare/test-product", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "comparison" in data

    def test_vip_recipe_templates_coverage_lines_564_565_587(self, vip_headers: dict[str, str]):
        """Test VIP recipe templates coverage for lines 564-565, 587."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_coverage_lines_623_624_681(
        self,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto-repair coverage for lines 623-624, 681."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair weekly endpoint
        with patch("app.routers.vip.auto_repair_week_plan", None):
            response = client.post(
                "/api/v1/vip/auto-repair/weekly",
                json={"menu": {"days": []}},
                headers=vip_headers,
            )
        assert response.status_code == 200
        assert assert_json_response_payload(response) == {
            "status": "error",
            "code": "auto_repair_unavailable",
            "message": "Auto-repair module not available",
            "detail": "Auto-repair module not available",
            "error": "auto_repair_unavailable",
            "repair_result": {},
        }

    def test_vip_auto_repair_strategies_coverage_lines_695_702_716(
        self, vip_headers: dict[str, str]
    ):
        """Test VIP auto-repair strategies coverage for lines 695, 702, 716."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test auto-repair strategies endpoint
        response = client.get("/api/v1/vip/auto-repair/strategies", headers=vip_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "strategies" in data

    def test_vip_weekly_recipes_coverage_lines_721_725_738_739_758(
        self, vip_headers: dict[str, str]
    ) -> None:
        """Test VIP weekly recipes coverage for lines 721-725, 738-739, 758."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        payload = {
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [{"ingredients": [{"name": "rice", "amount": 100, "unit": "g"}]}],
                    }
                ]
            },
            "recipes_per_day": 1,
        }

        # Test weekly recipes endpoint
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert isinstance(data["weekly_recipes"], dict)
        assert data["weekly_recipes"]
        assert data["total_recipes"] == 1
        assert data["echo"] == payload

    def test_vip_recipe_synthesis_coverage_lines_788_789_809(self, vip_headers: dict[str, str]):
        """Test VIP recipe synthesis coverage for lines 788-789, 809."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test recipe synthesis endpoint
        response = client.post(
            "/api/v1/vip/recipes/synthesize",
            json={"week_plan": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "recipe" in data

    def test_vip_weekly_plan_coverage_lines_829_832_835(self, vip_headers: dict[str, str]):
        """Test VIP weekly plan coverage for lines 829-832, 835."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test weekly plan endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={"calories": 2000, "preferences": []},
            headers=vip_headers,
        )
        assert response.status_code == 422  # Validation error for invalid request

    def test_vip_menu_repair_coverage_lines_907_941_942(self, vip_headers: dict[str, str]):
        """Test VIP menu repair coverage for lines 907, 941-942."""
        import app

        client = TestClient(cast(ASGIApp, app.app))

        # Test menu repair endpoint
        response = client.post(
            "/api/v1/vip/menu/weekly/repair",
            json={"menu": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "repairs" in data
