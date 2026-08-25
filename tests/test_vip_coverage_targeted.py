"""Targeted tests to improve app/routers/vip.py coverage to 97%."""

import pytest
from fastapi.testclient import TestClient

from tests._helpers.vip_contracts import (
    assert_json_response_payload,
    build_auto_repair_weekly_request_payload,
)


@pytest.fixture(autouse=True)
def _vip_test_environment(
    test_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep targeted VIP tests on their historical API-key value."""
    del test_environment
    monkeypatch.setenv("API_KEY", "test_key")


class TestVipCoverageTargeted:
    """Targeted tests for VIP router coverage."""

    def test_vip_health_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP health endpoint."""
        response = client.get("/api/v1/vip/health", headers=vip_headers)
        assert response.status_code == 200

    def test_vip_regions_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP regions endpoint."""
        response = client.get("/api/v1/vip/regions", headers=vip_headers)
        assert response.status_code == 200

    def test_vip_region_search_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region search endpoint."""
        response = client.get(
            "/api/v1/vip/regions/US/search?query=test",
            headers=vip_headers,
        )
        assert response.status_code == 200

    def test_vip_region_categories_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region categories endpoint."""
        response = client.get(
            "/api/v1/vip/regions/US/categories",
            headers=vip_headers,
        )
        assert response.status_code == 200

    def test_vip_region_stores_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP region stores endpoint."""
        response = client.get("/api/v1/vip/regions/US/stores", headers=vip_headers)
        assert response.status_code == 200

    def test_vip_price_comparison_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP price comparison endpoint."""
        response = client.get("/api/v1/vip/regions/compare/test", headers=vip_headers)
        assert response.status_code == 200

    def test_vip_shoplist_formats_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist formats endpoint."""
        response = client.get("/api/v1/vip/shoplist/formats", headers=vip_headers)
        assert response.status_code == 200

    def test_vip_recipe_templates_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP recipe templates endpoint."""
        response = client.get("/api/v1/vip/recipes/templates", headers=vip_headers)
        assert response.status_code == 200

    def test_vip_auto_repair_strategies_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto repair strategies endpoint."""
        response = client.get("/api/v1/vip/auto-repair/strategies", headers=vip_headers)
        assert response.status_code == 200

    def test_vip_menu_weekly_plan_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP menu weekly plan endpoint."""
        payload = {
            "sex": "male",
            "age": 30,
            "height_cm": 175.0,
            "weight_kg": 70.0,
            "activity": "moderate",
            "goal": "maintain",
            "user_id": "test_user",
            "preferences": {"diet": "balanced"},
            "calories": 2000,
        }
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200

    def test_vip_shoplist_weekly_endpoint(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP shoplist weekly endpoint."""
        # Enable VIP module
        monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

        payload = {
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
        }
        response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "days" in data

    def test_vip_recipes_weekly_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP recipes weekly endpoint."""
        payload = {
            "week_plan": {
                "days": [
                    {
                        "day": "Monday",
                        "meals": [
                            {
                                "ingredients": [
                                    {"name": "chicken", "amount": 200, "unit": "g"},
                                    {"name": "rice", "amount": 150, "unit": "g"},
                                ]
                            }
                        ],
                    }
                ]
            },
            "recipes_per_day": 1,
        }
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200

    def test_vip_recipes_synthesize_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP recipes synthesize endpoint."""
        payload = {"ingredients": ["chicken", "rice", "vegetables"]}
        response = client.post(
            "/api/v1/vip/recipes/synthesize",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200

    def test_vip_auto_repair_weekly_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto repair weekly endpoint."""
        payload = build_auto_repair_weekly_request_payload()
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        response_payload = assert_json_response_payload(response)
        assert response_payload["status"] == "success"
        assert response_payload["repair_result"]["status"] == "success"
        assert response_payload["echo"] == payload

    def test_vip_auto_repair_suggestions_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Test VIP auto repair suggestions endpoint."""
        payload = {"gaps": ["vitamin_d"], "preferences": {"vegetarian": True}}
        response = client.post(
            "/api/v1/vip/auto-repair/suggestions",
            json=payload,
            headers=vip_headers,
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
