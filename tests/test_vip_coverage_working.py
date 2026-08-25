# -*- coding: utf-8 -*-
"""
VIP Coverage Tests - Real endpoints working

RU: Тесты для VIP модуля с реальными эндпоинтами (echo mode)
EN: VIP module tests with real endpoints (echo mode)
"""

import pytest
from fastapi.testclient import TestClient

from tests._helpers.vip_contracts import (
    assert_json_response_payload,
    build_auto_repair_weekly_request_payload,
)


@pytest.mark.smoke
class TestVIPCoverageWorking:
    """VIP coverage tests for echo mode endpoints."""

    def test_vip_weekly_plan_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP weekly plan endpoint в echo режиме"""
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
                "user_id": "test",
                "preferences": {"diet": "balanced"},
                "calories": 2000,
            },
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data
        assert "menu" in data

    def test_vip_shoplist_endpoint(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP shoplist endpoint"""
        # Enable VIP module
        monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

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

    def test_vip_regions_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP regions endpoint"""
        response = client.get(
            "/api/v1/vip/regions",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "regions" in data
        assert "echo" in data

    def test_vip_recipe_synthesis_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP recipe synthesis endpoint в echo режиме"""
        response = client.post(
            "/api/v1/vip/recipes/synthesize",
            json={"ingredients": ["chicken", "rice", "vegetables"]},
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data

    def test_vip_auto_repair_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP auto repair endpoint с canonical strict request."""
        request_payload = build_auto_repair_weekly_request_payload()
        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json=request_payload,
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = assert_json_response_payload(response)
        assert data["status"] == "success"
        assert data["repair_result"]["status"] == "success"
        assert data["echo"] == request_payload

    def test_vip_daily_shoplist_endpoint(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP daily shoplist endpoint"""
        # Enable VIP module
        monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

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
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "packed" in data
        assert "unpacked" in data

    def test_vip_shoplist_formats_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP shoplist formats endpoint"""
        response = client.get(
            "/api/v1/vip/shoplist/formats",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "formats" in data

    def test_vip_region_search_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP region search endpoint"""
        response = client.get(
            "/api/v1/vip/regions/BY/search?query=milk",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "products" in data

    def test_vip_region_categories_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP region categories endpoint"""
        response = client.get(
            "/api/v1/vip/regions/BY/categories",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "categories" in data

    def test_vip_region_stores_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP region stores endpoint"""
        response = client.get(
            "/api/v1/vip/regions/BY/stores",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "stores" in data

    def test_vip_price_comparison_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP price comparison endpoint"""
        response = client.get(
            "/api/v1/vip/regions/compare/milk",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "comparison" in data

    def test_vip_weekly_recipes_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP weekly recipes endpoint"""
        response = client.post(
            "/api/v1/vip/recipes/weekly",
            json={
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
                        },
                        {
                            "day": "Tuesday",
                            "meals": [
                                {
                                    "ingredients": [
                                        {"name": "salmon", "amount": 250, "unit": "g"},
                                        {"name": "vegetables", "amount": 200, "unit": "g"},
                                    ]
                                }
                            ],
                        },
                    ]
                },
                "recipes_per_day": 1,
            },
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"

    def test_vip_recipe_templates_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP recipe templates endpoint"""
        response = client.get(
            "/api/v1/vip/recipes/templates",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "templates" in data

    def test_vip_repair_suggestions_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP repair suggestions endpoint"""
        response = client.post(
            "/api/v1/vip/auto-repair/suggestions",
            json={"gaps": ["vitamin_d"], "preferences": {"vegetarian": True}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"

    def test_vip_repair_strategies_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP repair strategies endpoint"""
        response = client.get(
            "/api/v1/vip/auto-repair/strategies",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert "strategies" in data

    def test_vip_health_endpoint(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP health endpoint"""
        response = client.get(
            "/api/v1/vip/health",
            headers=vip_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["status"] == "success"

    def test_vip_endpoints_no_api_key(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Тест VIP endpoints без API ключа"""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("ALLOW_DEV_API_KEY", "false")

        # Должен возвращать 403 без API ключа
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={"user_id": "test"},
        )
        assert response.status_code == 403

    def test_vip_endpoints_invalid_json(
        self,
        client: TestClient,
        vip_headers: dict[str, str],
    ) -> None:
        """Тест VIP endpoints с невалидным JSON"""
        # Тест с невалидными данными
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={"invalid": None, "calories": 2000},
            headers=vip_headers,
        )
        assert response.status_code == 422
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Invalid weekly plan request payload"}
