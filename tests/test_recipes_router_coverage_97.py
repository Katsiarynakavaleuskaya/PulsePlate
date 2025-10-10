"""
Тесты для покрытия missing lines в app/routers/recipes.py
Цель: повысить покрытие до 97%
"""

import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from app.py file
import importlib.util


spec = importlib.util.spec_from_file_location("app_module", "app.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load app.py")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app


class TestRecipesRouterCoverage97:
    """Тесты для покрытия missing lines в recipes router."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_list_recipes_limit_validation_line_17(self):
        """Test line 17: limit validation error path."""
        # Test limit > 50
        response = self.client.get("/api/v1/recipes?limit=51")
        assert response.status_code == 422
        assert "limit must be in [1,50]" in response.json()["detail"]

        # Test limit < 1
        response = self.client.get("/api/v1/recipes?limit=0")
        assert response.status_code == 422
        assert "limit must be in [1,50]" in response.json()["detail"]

    def test_get_recipe_not_found_line_44(self):
        """Test line 44: recipe not found error path."""
        with patch("app.services.recipe_store.get_recipe", return_value=None):
            response = self.client.get("/api/v1/recipes/nonexistent_recipe")
            assert response.status_code == 404
            assert "Recipe not found" in response.json()["detail"]

    def test_get_recipe_success_line_44(self):
        """Test line 44: successful recipe retrieval."""
        mock_recipe = {
            "recipe_id": "test_recipe",
            "title": "Test Recipe",
            "locale": "en",
            "servings": 4,
            "yield_total_g": 1000.0,
            "ingredients_json": '[{"food_id": "test_food", "grams": 100}]',
            "steps_json": '["Step 1", "Step 2"]',
            "tags_json": '["tag1", "tag2"]',
            "allergens_json": '["allergen1"]',
            "cost_total": 10.0,
            "cost_per_serv": 2.5,
            "nutrients_per_serv_json": '{"calories": 200}',
            "source": "test",
            "version_date": "2025-01-01",
        }
        with patch("app.services.recipe_store.get_recipe", return_value=mock_recipe):
            response = self.client.get("/api/v1/recipes/test_recipe")
            assert response.status_code == 200
            data = response.json()
            assert data["recipe_id"] == "test_recipe"
            assert data["title"] == "Test Recipe"

    def test_recipe_preview_servings_validation_line_65(self):
        """Test line 65: servings validation error path."""
        payload = {
            "title": "Test Recipe",
            "servings": 0,  # Invalid servings
            "ingredients": [{"food_id": "test_food", "grams": 100}],
        }
        response = self.client.post("/api/v1/recipes/preview", json=payload)
        assert response.status_code == 422
        assert "servings must be >= 1" in response.json()["detail"]
