"""
Final VIP coverage tests to achieve 97% coverage with proper isolation.
"""

import runpy

import pytest
from fastapi.testclient import TestClient

from tests._helpers.vip_contracts import assert_json_response_payload


class TestVIPCoverage97Final:
    """Test class to achieve 97% coverage for VIP router with proper isolation."""

    def test_vip_import_fallback_coverage_lines_54_73(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test VIP import fallback coverage for lines 54-73."""
        import core.auto_repair as auto_repair
        from app.routers import vip

        assert vip.__file__ is not None
        monkeypatch.delattr(auto_repair, "RepairStatus")

        fallback_namespace = runpy.run_path(
            vip.__file__,
            run_name="test_vip_optional_core_fallback",
        )

        assert fallback_namespace["RepairStatus"] is None
        assert fallback_namespace["make_weekly_menu"] is None

    def test_vip_safe_call_with_adapter_missing(self) -> None:
        """Test VIP _safe_call_with_adapter with unknown function name returns error dict."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown", {})
        assert isinstance(result, dict) and result.get("status") == "error"

    def test_vip_weekly_menu_plan_coverage_lines_188_190(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly menu plan coverage for lines 188-190."""
        # Test with invalid request (should get validation error)
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json="invalid",  # Non-dict request
            headers=vip_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_vip_shoplist_weekly_coverage_lines_217_254(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist weekly coverage for lines 217-254."""

        # Enable VIP module
        def mock_is_vip_module_enabled() -> bool:
            return True

        monkeypatch.setattr(
            "app.routers.vip_shoplist.is_vip_module_enabled",
            mock_is_vip_module_enabled,
        )

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
        data = assert_json_response_payload(response)
        assert "days" in data
        assert isinstance(data["days"], list)

    def test_vip_shoplist_daily_coverage_lines_293_300(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist daily coverage for lines 293-300."""

        # Enable VIP module
        def mock_is_vip_module_enabled() -> bool:
            return True

        monkeypatch.setattr(
            "app.routers.vip_shoplist.is_vip_module_enabled",
            mock_is_vip_module_enabled,
        )

        # Use new API format for vip_shoplist router
        response = client.post(
            "/api/v1/vip/shoplist/daily",
            json={
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
            },
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert "packed" in data
        assert "unpacked" in data

    def test_vip_shoplist_formats_coverage_lines_304_348(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist formats coverage for lines 304-348."""
        # Test shoplist formats
        response = client.get("/api/v1/vip/shoplist/formats", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "formats" in data

    def test_vip_regions_coverage_lines_355_365(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP regions coverage for lines 355-365."""
        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_region_search_coverage_lines_391_429(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region search coverage for lines 391-429."""
        # Test region search endpoint
        response = client.get(
            "/api/v1/vip/regions/ES/search?query=test",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "products" in data

    def test_vip_region_categories_coverage_lines_457_469(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region categories coverage for lines 457-469."""
        # Test region categories endpoint
        response = client.get(
            "/api/v1/vip/regions/ES/categories",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "categories" in data

    def test_vip_region_stores_coverage_lines_471_483(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region stores coverage for lines 471-483."""
        # Test region stores endpoint
        response = client.get("/api/v1/vip/regions/ES/stores", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "stores" in data

    def test_vip_price_comparison_coverage_lines_489_508(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP price comparison coverage for lines 489-508."""
        # Test price comparison endpoint
        response = client.get(
            "/api/v1/vip/regions/compare/test-product",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "comparison" in data

    def test_vip_recipe_templates_coverage_lines_507_508(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP recipe templates coverage for lines 507-508."""
        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_weekly_coverage_lines_530(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto-repair weekly coverage for lines 530."""
        monkeypatch.setattr("app.routers.vip.auto_repair_week_plan", None)

        # Test auto-repair weekly endpoint
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json={"menu": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "error"  # Fallback when auto_repair_week_plan is unavailable
        assert "repair_result" in data

    def test_vip_auto_repair_suggestions_coverage_lines_589(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto-repair suggestions coverage for lines 589."""
        # Test auto-repair suggestions endpoint
        response = client.post(
            "/api/v1/vip/auto-repair/suggestions",
            json={"menu": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "suggestions" in data

    def test_vip_auto_repair_strategies_coverage_lines_607(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto-repair strategies coverage for lines 607."""
        # Test auto-repair strategies endpoint
        response = client.get(
            "/api/v1/vip/auto-repair/strategies",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "strategies" in data

    def test_vip_weekly_recipes_coverage_lines_656_660(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly recipes coverage for lines 656-660."""
        # Test weekly recipes endpoint
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json={"week_plan": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "weekly_recipes" in data

    def test_vip_weekly_plan_coverage_lines_873_905(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly plan coverage for lines 873-905."""
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
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
