"""
Clean VIP coverage tests to achieve 97% coverage with proper isolation.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests._helpers.vip_contracts import assert_json_response_payload


class TestVIPCoverage97Clean:
    """Test class to achieve 97% coverage for VIP router with proper isolation."""

    # setup_method removed - using conftest.py autouse fixture for environment setup

    def test_vip_import_fallback_coverage_lines_55_74(self) -> None:
        """Test VIP import fallback coverage for lines 55-74."""
        # Test that VIP module imports successfully and functions are available
        from app.routers import vip

        # Verify that VIP functions are available (not None)
        assert vip.make_weekly_menu is not None

    def test_vip_safe_call_with_adapter_errors(self) -> None:
        """Test VIP _safe_call_with_adapter error path when adapter missing."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown_function", {})
        assert isinstance(result, dict) and result.get("status") == "error"

        # Test helper functions for coverage
        from app.routers.vip import (
            _is_dev_mode,
            _is_production_environment,
            _log_api_key_event,
            _should_allow_anonymous_access,
            _validate_with_app_get_api_key,
        )

        # Test _is_production_environment
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "ENVIRONMENT": "", "DEBUG": "false"},
        ):
            is_production, app_env = _is_production_environment()
            assert is_production is True
            assert app_env == "production"

        # Test _should_allow_anonymous_access
        result = _should_allow_anonymous_access(True)
        assert result is False

        # Test _is_dev_mode
        result = _is_dev_mode("test")
        assert result is True

        # Test _validate_with_app_get_api_key with mock
        mock_get_api_key = MagicMock(return_value="valid_key")
        with patch("app.routers.vip.resolve_attr", return_value=mock_get_api_key):
            result = _validate_with_app_get_api_key("test_key")
            assert result == "valid_key"

        # Test _log_api_key_event with mock logging
        with patch("logging.error") as mock_error:
            _log_api_key_event(
                "VIP endpoint accessed without API key in production mode.", True, "production"
            )
            mock_error.assert_called_once()

    def test_vip_weekly_menu_plan_coverage_lines_173_180(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly menu plan coverage for lines 173, 180."""
        # Test with invalid request (line 173)
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json="invalid",  # Non-dict request
            headers=vip_headers,
        )
        assert response.status_code == 422

        # Test with valid request but None function (line 180)
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={"calories": 2000, "preferences": []},
            headers=vip_headers,
        )
        assert response.status_code == 422

    def test_vip_weekly_menu_plan_error_coverage_lines_189_191(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly menu plan error coverage for lines 189-191."""
        # Test with valid request that should work
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={"calories": 2000, "preferences": []},
            headers=vip_headers,
        )
        assert response.status_code == 422

    def test_vip_shoplist_weekly_coverage_lines_219_259(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist weekly coverage for lines 219-259."""
        # Test weekly shoplist generation
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

    def test_vip_shoplist_daily_coverage_lines_315_316(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist daily coverage for lines 315-316."""
        # Test daily shoplist generation
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

    def test_vip_shoplist_formats_coverage_lines_350_361_362(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist formats coverage for lines 350, 361-362."""
        # Test shoplist formats
        response = client.get("/api/v1/vip/shoplist/formats", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "formats" in data

    def test_vip_regions_coverage_lines_421_422_449(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP regions coverage for lines 421-422, 449."""
        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_region_search_coverage_lines_485_486(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region search coverage for lines 485-486."""
        # Test region search endpoint
        response = client.get(
            "/api/v1/vip/regions/ES/search?query=test",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "products" in data

    def test_vip_region_categories_coverage_line_508(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region categories coverage for line 508."""
        # Test region categories endpoint
        response = client.get(
            "/api/v1/vip/regions/ES/categories",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "categories" in data

    def test_vip_region_stores_coverage_lines_525_526(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region stores coverage for lines 525-526."""
        # Test region stores endpoint
        response = client.get("/api/v1/vip/regions/ES/stores", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "stores" in data

    def test_vip_price_comparison_coverage_line_547(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP price comparison coverage for line 547."""
        # Test price comparison endpoint
        response = client.get(
            "/api/v1/vip/regions/compare/test-product",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "comparison" in data

    def test_vip_recipe_templates_coverage_lines_564_565_587(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP recipe templates coverage for lines 564-565, 587."""
        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_coverage_lines_623_624_681(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto-repair coverage for lines 623-624, 681."""
        monkeypatch.setattr("app.routers.vip.auto_repair_week_plan", None)

        # Test auto-repair weekly endpoint
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json={"menu": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "error"
        assert "repair_result" in data

    def test_vip_auto_repair_strategies_coverage_lines_695_702_716(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto-repair strategies coverage for lines 695, 702, 716."""
        # Test auto-repair strategies endpoint
        response = client.get(
            "/api/v1/vip/auto-repair/strategies",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "strategies" in data

    def test_vip_weekly_recipes_coverage_lines_721_725_738_739_758(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly recipes coverage for lines 721-725, 738-739, 758."""
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

    def test_vip_recipe_synthesis_coverage_lines_788_789_809(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP recipe synthesis coverage for lines 788-789, 809."""
        # Test recipe synthesis endpoint
        response = client.post(
            "/api/v1/vip/recipes/synthesize",
            json={"week_plan": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "recipe" in data

    def test_vip_weekly_plan_coverage_lines_829_832_835(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly plan coverage for lines 829-832, 835."""
        # Test weekly plan endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={"calories": 2000, "preferences": []},
            headers=vip_headers,
        )
        assert response.status_code == 422

    def test_vip_menu_repair_coverage_lines_907_941_942(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP menu repair coverage for lines 907, 941-942."""
        # Test menu repair endpoint
        response = client.post(
            "/api/v1/vip/menu/weekly/repair",
            json={"menu": {"days": []}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert "repairs" in data
