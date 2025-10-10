"""
VIP Coverage Tests - Real endpoints working

RU: Тесты для VIP модуля с реальными эндпоинтами (echo mode)
EN: VIP module tests with real endpoints (echo mode)
"""

from fastapi.testclient import TestClient


def _get_app():
    """Safely get the FastAPI app instance."""
    import app

    if app.app is None:
        raise RuntimeError("FastAPI app is not initialized")
    return app.app


import pytest


@pytest.mark.smoke
class TestVIPCoverageWorking:
    """VIP coverage tests for echo mode endpoints."""

    def test_vip_weekly_plan_endpoint(self):
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
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data
        assert "menu" in data

    def test_vip_shoplist_endpoint(self):
        """Тест VIP shoplist endpoint в echo режиме"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/shoplist/weekly",
            json={"plan_id": "test123", "format": "grouped"},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data

    def test_vip_regions_endpoint(self):
        """Тест VIP regions endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert "echo" in data

    def test_vip_recipe_synthesis_endpoint(self):
        """Тест VIP recipe synthesis endpoint в echo режиме"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/recipes/synthesize",
            json={"ingredients": ["chicken", "rice", "vegetables"]},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "echo" in data

    def test_vip_auto_repair_endpoint(self):
        """Тест VIP auto repair endpoint в echo режиме"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/auto-repair/weekly",
            json={"plan_id": "test123", "gaps": ["vitamin_d", "iron"]},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in [
            "success",
            "error",
        ]  # Allow either status depending on module availability
        assert "echo" in data

    def test_vip_daily_shoplist_endpoint(self):
        """Тест VIP daily shoplist endpoint"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/shoplist/daily",
            json={"day_plan": {"breakfast": [], "lunch": [], "dinner": []}},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_vip_shoplist_formats_endpoint(self):
        """Тест VIP shoplist formats endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/shoplist/formats",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data

    def test_vip_region_search_endpoint(self):
        """Тест VIP region search endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/BY/search?query=milk",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data

    def test_vip_region_categories_endpoint(self):
        """Тест VIP region categories endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/BY/categories",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    def test_vip_region_stores_endpoint(self):
        """Тест VIP region stores endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/BY/stores",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "stores" in data

    def test_vip_price_comparison_endpoint(self):
        """Тест VIP price comparison endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/regions/compare/milk",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data

    def test_vip_weekly_recipes_endpoint(self):
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
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_vip_recipe_templates_endpoint(self):
        """Тест VIP recipe templates endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/recipes/templates",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data

    def test_vip_repair_suggestions_endpoint(self):
        """Тест VIP repair suggestions endpoint"""
        client = TestClient(_get_app())

        response = client.post(
            "/api/v1/vip/auto-repair/suggestions",
            json={"gaps": ["vitamin_d"], "preferences": {"vegetarian": True}},
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_vip_repair_strategies_endpoint(self):
        """Тест VIP repair strategies endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/auto-repair/strategies",
            headers={"X-API-Key": "test_key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data

    def test_vip_health_endpoint(self):
        """Тест VIP health endpoint"""
        client = TestClient(_get_app())

        response = client.get(
            "/api/v1/vip/health",
            headers={"X-API-Key": "test_key"},
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
            assert response.status_code == 403

    def test_vip_endpoints_invalid_json(self):
        """Тест VIP endpoints с невалидным JSON"""
        client = TestClient(_get_app())

        # Тест с невалидными данными
        response = client.post(
            "/api/v1/vip/menu/weekly/plan",
            json={"invalid": None, "calories": 2000},
            headers={"X-API-Key": "test_key"},
        )
        # Echo mode should still work
        assert response.status_code == 200
