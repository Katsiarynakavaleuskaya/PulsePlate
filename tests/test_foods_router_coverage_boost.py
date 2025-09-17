# -*- coding: utf-8 -*-
"""
RU: Тесты для повышения покрытия app/routers/foods.py
EN: Coverage boost tests for app/routers/foods.py
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
import os

try:
    from app import app as fastapi_app
    from app.routers.foods import router
    from app.schemas.food import FoodHit, FoodItem
except ImportError as exc:
    pytest.skip(f"Import failed: {exc}", allow_module_level=True)

client = TestClient(fastapi_app)


class TestFoodsRouterCoverage:
    """Test class for foods router coverage boost."""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_router_configuration(self):
        """Test router configuration."""
        assert "foods" in router.tags

    @patch("app.routers.foods.food_store.search_foods")
    def test_list_foods_success(self, mock_search_foods):
        """Test list_foods endpoint success."""
        mock_search_foods.return_value = [
            {
                "id": "1",
                "canonical_name": "apple",
                "kcal": 52,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
            },
            {
                "id": "2",
                "canonical_name": "banana",
                "kcal": 89,
                "protein_g": 1.1,
                "fat_g": 0.3,
                "carbs_g": 23.0,
            },
        ]

        response = client.get("/api/v1/foods?query=apple&limit=10&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "apple"
        assert data[0]["kcal"] == 52
        assert data[1]["name"] == "banana"
        assert data[1]["kcal"] == 89

    @patch("app.routers.foods.food_store.search_foods")
    def test_list_foods_empty_query(self, mock_search_foods):
        """Test list_foods with empty query."""
        mock_search_foods.return_value = []

        response = client.get("/api/v1/foods?query=&limit=10&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert data == []

    @patch("app.routers.foods.food_store.search_foods")
    def test_list_foods_no_query(self, mock_search_foods):
        """Test list_foods without query parameter."""
        mock_search_foods.return_value = [
            {
                "id": "1",
                "canonical_name": "apple",
                "kcal": 52,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
            }
        ]

        response = client.get("/api/v1/foods?limit=10&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "apple"

    def test_list_foods_limit_too_high(self):
        """Test list_foods with limit too high."""
        response = client.get("/api/v1/foods?limit=101")
        assert response.status_code == 422
        assert "limit must be in [1,100]" in response.json()["detail"]

    def test_list_foods_limit_too_low(self):
        """Test list_foods with limit too low."""
        response = client.get("/api/v1/foods?limit=0")
        assert response.status_code == 422
        assert "limit must be in [1,100]" in response.json()["detail"]

    def test_list_foods_limit_negative(self):
        """Test list_foods with negative limit."""
        response = client.get("/api/v1/foods?limit=-1")
        assert response.status_code == 422
        assert "limit must be in [1,100]" in response.json()["detail"]

    def test_list_foods_limit_maximum(self):
        """Test list_foods with maximum limit."""
        with patch("app.routers.foods.food_store.search_foods") as mock_search_foods:
            mock_search_foods.return_value = []

            response = client.get("/api/v1/foods?limit=100")
            assert response.status_code == 200

    def test_list_foods_limit_minimum(self):
        """Test list_foods with minimum limit."""
        with patch("app.routers.foods.food_store.search_foods") as mock_search_foods:
            mock_search_foods.return_value = []

            response = client.get("/api/v1/foods?limit=1")
            assert response.status_code == 200

    @patch("app.routers.foods.food_store.search_foods")
    def test_list_foods_with_offset(self, mock_search_foods):
        """Test list_foods with offset."""
        mock_search_foods.return_value = [
            {
                "id": "2",
                "canonical_name": "banana",
                "kcal": 89,
                "protein_g": 1.1,
                "fat_g": 0.3,
                "carbs_g": 23.0,
            }
        ]

        response = client.get("/api/v1/foods?query=fruit&limit=10&offset=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "banana"

    @patch("app.routers.foods.food_store.search_foods")
    def test_list_foods_long_query(self, mock_search_foods):
        """Test list_foods with long query."""
        long_query = "a" * 64  # Exactly 64 characters
        mock_search_foods.return_value = []

        response = client.get(f"/api/v1/foods?query={long_query}")
        assert response.status_code == 200

    def test_list_foods_query_too_long(self):
        """Test list_foods with query too long."""
        long_query = "a" * 65  # More than 64 characters
        response = client.get(f"/api/v1/foods?query={long_query}")
        assert response.status_code == 422

    @patch("app.routers.foods.food_store.get_food")
    def test_get_food_success(self, mock_get_food):
        """Test get_food endpoint success."""
        mock_get_food.return_value = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "fiber_g": 2.4,
            "Fe_mg": 0.1,
            "Ca_mg": 6.0,
            "K_mg": 107.0,
            "Mg_mg": 5.0,
            "VitD_IU": 0,
            "B12_ug": 0,
            "Folate_ug": 3.0,
            "Iodine_ug": 0,
            "per_g": 100.0,
            "price_per_100g": 0.5,
            "flags": ["organic"],
            "version_date": "2024-01-01",
        }

        response = client.get("/api/v1/foods/1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "1"
        assert data["canonical_name"] == "apple"
        assert data["kcal"] == 52
        assert data["protein_g"] == 0.3

    @patch("app.routers.foods.food_store.get_food")
    def test_get_food_not_found(self, mock_get_food):
        """Test get_food endpoint when food not found."""
        mock_get_food.return_value = None

        response = client.get("/api/v1/foods/999")
        assert response.status_code == 404
        assert "Food not found" in response.json()["detail"]

    @patch("app.routers.foods.food_store.get_food")
    def test_get_food_with_special_characters(self, mock_get_food):
        """Test get_food with special characters in ID."""
        mock_get_food.return_value = {
            "id": "food-123_abc",
            "canonical_name": "special food",
            "kcal": 100,
            "protein_g": 5.0,
            "fat_g": 2.0,
            "carbs_g": 15.0,
            "fiber_g": 3.0,
            "Fe_mg": 1.0,
            "Ca_mg": 50.0,
            "K_mg": 200.0,
            "Mg_mg": 20.0,
            "VitD_IU": 10.0,
            "B12_ug": 1.0,
            "Folate_ug": 25.0,
            "Iodine_ug": 5.0,
            "per_g": 100.0,
            "price_per_100g": 1.0,
            "flags": [],
            "version_date": "2024-01-01",
        }

        response = client.get("/api/v1/foods/food-123_abc")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "food-123_abc"
        assert data["canonical_name"] == "special food"

    @patch("app.routers.foods.food_store.get_food")
    def test_get_food_with_numeric_id(self, mock_get_food):
        """Test get_food with numeric ID."""
        mock_get_food.return_value = {
            "id": "123",
            "canonical_name": "numeric food",
            "kcal": 75,
            "protein_g": 3.0,
            "fat_g": 1.5,
            "carbs_g": 12.0,
            "fiber_g": 2.0,
            "Fe_mg": 0.5,
            "Ca_mg": 30.0,
            "K_mg": 150.0,
            "Mg_mg": 15.0,
            "VitD_IU": 5.0,
            "B12_ug": 0.5,
            "Folate_ug": 15.0,
            "Iodine_ug": 3.0,
            "per_g": 100.0,
            "price_per_100g": 0.8,
            "flags": ["local"],
            "version_date": "2024-01-01",
        }

        response = client.get("/api/v1/foods/123")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "123"
        assert data["canonical_name"] == "numeric food"

    def test_food_hit_schema(self):
        """Test FoodHit schema creation."""
        food_hit = FoodHit(id="1", name="apple", kcal=52, protein_g=0.3, fat_g=0.2, carbs_g=14.0)

        assert food_hit.id == "1"
        assert food_hit.name == "apple"
        assert food_hit.kcal == 52
        assert food_hit.protein_g == 0.3
        assert food_hit.fat_g == 0.2
        assert food_hit.carbs_g == 14.0

    def test_food_item_schema(self):
        """Test FoodItem schema creation."""
        food_item = FoodItem(
            id="1",
            canonical_name="apple",
            kcal=52,
            protein_g=0.3,
            fat_g=0.2,
            carbs_g=14.0,
            fiber_g=2.4,
            Fe_mg=0.1,
            Ca_mg=6.0,
            K_mg=107.0,
            Mg_mg=5.0,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=3.0,
            Iodine_ug=0,
            per_g=100.0,
            price_per_100g=0.5,
            flags=["organic"],
            version_date="2024-01-01",
        )

        assert food_item.id == "1"
        assert food_item.canonical_name == "apple"
        assert food_item.kcal == 52
        assert food_item.fiber_g == 2.4
        assert food_item.Fe_mg == 0.1
        assert food_item.price_per_100g == 0.5
        assert food_item.flags == ["organic"]
