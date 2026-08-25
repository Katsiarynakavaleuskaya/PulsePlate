"""
Clean VIP coverage tests with proper isolation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests._helpers.vip_contracts import (
    assert_json_response_payload,
    build_weekly_recipes_request_payload,
)


@pytest.fixture(autouse=True)
def _vip_test_environment(
    test_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep clean VIP tests on their historical API-key value."""
    del test_environment
    monkeypatch.setenv("API_KEY", "test-key")


class TestVIPCoverageClean:
    """Test class with proper isolation for VIP coverage."""

    def test_vip_router_does_not_expose_legacy_shoplist_aliases(self) -> None:
        """VIP shoplist generation/export ownership stays outside app.routers.vip."""
        import app.routers.vip as vip

        legacy_shoplist_aliases = {
            "ShoplistGenerator",
            "aggregate_ingredients",
            "round_to_packages",
            "format_export",
        }
        assert not legacy_shoplist_aliases & set(dir(vip))

    def test_vip_safe_call_with_adapter_error(self) -> None:
        """Test VIP _safe_call_with_adapter structured error when adapter missing."""
        from app.routers.vip import _safe_call_with_adapter

        result = _safe_call_with_adapter("unknown", {})
        assert isinstance(result, dict) and result.get("status") == "error"

    def test_vip_weekly_menu_plan_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly menu plan coverage with proper isolation."""
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
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data
        assert "menu" in data

    def test_vip_shoplist_weekly_coverage(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist weekly coverage with proper isolation."""

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
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "days" in data
        assert isinstance(data["days"], list)

    def test_vip_regions_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP regions coverage with proper isolation."""
        # Test regions endpoint
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"
        assert "regions" in data

    def test_vip_recipe_templates_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP recipe templates coverage with proper isolation."""
        # Test recipe templates endpoint
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data

    def test_vip_auto_repair_strategies_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto-repair strategies coverage with proper isolation."""
        # Test auto-repair strategies endpoint
        response = client.get(
            "/api/v1/vip/auto-repair/strategies",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"
        assert "strategies" in data

    def test_vip_weekly_recipes_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly recipes coverage with proper isolation."""
        # Test weekly recipes endpoint
        request_payload = build_weekly_recipes_request_payload()
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=request_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert data["total_recipes"] > 0
        assert data["weekly_recipes"]
        assert data["echo"] == request_payload

    def test_vip_weekly_plan_coverage(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP weekly plan coverage with proper isolation."""
        # Test weekly plan endpoint
        response = client.post(
            "/api/v1/vip/weekly-plan",
            json={"calories": 2000, "preferences": []},
            headers=vip_headers,
        )
        assert response.status_code == 422  # Validation error for invalid request
