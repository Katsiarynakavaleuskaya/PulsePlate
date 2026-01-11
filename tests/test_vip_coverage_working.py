# -*- coding: utf-8 -*-
"""
VIP Coverage Tests - Real endpoints working

RU: Тесты для VIP модуля с реальными эндпоинтами (echo mode)
EN: VIP module tests with real endpoints (echo mode)
"""

import pytest
from fastapi.testclient import TestClient


def _get_app():
    """Safely get the FastAPI app instance."""
    import app

    if app.app is None:
        raise RuntimeError("FastAPI app is not initialized")
    return app.app


@pytest.mark.smoke
class TestVIPCoverageWorking:
    """VIP coverage tests for echo mode endpoints."""

    def test_vip_weekly_plan_endpoint(self, vip_headers):
        """Тест VIP weekly plan endpoint в echo режиме"""
        client = TestClient(_get_app())

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
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data
        assert "menu" in data

    def test_vip_shoplist_endpoint(self, monkeypatch, vip_headers):
        """Тест VIP shoplist endpoint"""
        import app
        from app.middleware import api_tiers

        # Enable VIP module
        monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

        # Override VIP tier dependency
        async def mock_require_vip_tier() -> str:
            return "vip"

        app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

        try:
            client = TestClient(_get_app())

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
        finally:
            app.app.dependency_overrides.pop(api_tiers.require_vip_tier, None)

    def test_vip_regions_endpoint(self, vip_headers):
        """Тест VIP regions endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert "echo" in data

    def test_vip_recipe_synthesis_endpoint(self, vip_headers):
        """Тест VIP recipe synthesis endpoint в echo режиме"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/recipes/synthesize",
            json={"ingredients": ["chicken", "rice", "vegetables"]},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data

    def test_vip_auto_repair_endpoint(self, vip_headers):
        """Тест VIP auto repair endpoint в echo режиме"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json={"plan_id": "test123", "gaps": ["vitamin_d", "iron"]},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in [
            "success",
            "error",
        ]  # Allow either status depending on module availability
        assert "echo" in data

    def test_vip_daily_shoplist_endpoint(self, monkeypatch, vip_headers):
        """Тест VIP daily shoplist endpoint"""
        import app
        from app.middleware import api_tiers

        # Enable VIP module
        monkeypatch.setattr("app.routers.vip_shoplist.is_vip_module_enabled", lambda: True)

        # Override VIP tier dependency
        async def mock_require_vip_tier() -> str:
            return "vip"

        app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier

        try:
            client = TestClient(_get_app())

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

    def test_vip_shoplist_formats_endpoint(self, vip_headers):
        """Тест VIP shoplist formats endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/shoplist/formats",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data

    def test_vip_region_search_endpoint(self, vip_headers):
        """Тест VIP region search endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/BY/search?query=milk",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data

    def test_vip_region_categories_endpoint(self, vip_headers):
        """Тест VIP region categories endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/BY/categories",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    def test_vip_region_stores_endpoint(self, vip_headers):
        """Тест VIP region stores endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/BY/stores",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "stores" in data

    def test_vip_price_comparison_endpoint(self, vip_headers):
        """Тест VIP price comparison endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/compare/milk",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data

    def test_vip_weekly_recipes_endpoint(self, vip_headers):
        """Тест VIP weekly recipes endpoint"""
        client = TestClient(_get_app())

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
        data = response.json()
        assert data["status"] == "success"

    def test_vip_recipe_templates_endpoint(self, vip_headers):
        """Тест VIP recipe templates endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/recipes/templates",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data

    def test_vip_repair_suggestions_endpoint(self, vip_headers):
        """Тест VIP repair suggestions endpoint"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/auto-repair/suggestions",
            json={"gaps": ["vitamin_d"], "preferences": {"vegetarian": True}},
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_vip_repair_strategies_endpoint(self, vip_headers):
        """Тест VIP repair strategies endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/auto-repair/strategies",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data

    def test_vip_health_endpoint(self, vip_headers):
        """Тест VIP health endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/health",
            headers=vip_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_vip_endpoints_no_api_key(self):
        """Тест VIP endpoints без API ключа"""
        import os
        from unittest.mock import patch

        # Mock environment to force strict auth
        with patch.dict(
            os.environ, {"APP_ENV": "production", "ALLOW_DEV_API_KEY": "false"}, clear=False
        ):
            client = TestClient(_get_app())

            # Должен возвращать 403 без API ключа
            response = client.post(
                "/api/v1/vip/menu/weekly/plan",
                json={"user_id": "test"},
            )
            assert response.status_code in (401, 403)

    def test_vip_endpoints_invalid_json(self, vip_headers):
        """Тест VIP endpoints с невалидным JSON"""
        client = TestClient(_get_app())

        # Тест с невалидными данными
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={"invalid": None, "calories": 2000},
            headers=vip_headers,
        )
        # Echo mode should still work
        assert response.status_code == 200
