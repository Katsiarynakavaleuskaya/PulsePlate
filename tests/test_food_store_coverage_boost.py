import os


# -*- coding: utf-8 -*-
"""
RU: Тесты для повышения покрытия app/services/food_store.py
EN: Coverage boost tests for app/services/food_store.py
"""

from unittest.mock import MagicMock, patch

import pytest


try:
    from app.services import food_store
except ImportError as exc:
    pytest.skip(f"Import failed: {exc}", allow_module_level=True)


class TestFoodStoreCoverage:
    """Test class for food_store coverage boost."""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    def test_expand_query_empty_string(self):
        """Test expand_query with empty string."""
        result = food_store.expand_query("")
        assert result == []

    def test_expand_query_none(self):
        """Test expand_query with None."""
        result = food_store.expand_query(None)
        assert result == []

    def test_expand_query_whitespace(self):
        """Test expand_query with whitespace only."""
        result = food_store.expand_query("   ")
        assert result == []

    def test_expand_query_basic_term(self):
        """Test expand_query with basic term."""
        result = food_store.expand_query("yogurt")
        assert "yogurt" in result

    def test_expand_query_with_aliases(self):
        """Test expand_query with aliases."""
        result = food_store.expand_query("йогурт")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

    def test_expand_query_alias_variant(self):
        """Test expand_query with alias variant."""
        result = food_store.expand_query("yoghurt")
        assert "yoghurt" in result
        assert "йогурт" in result
        assert "yogurt" in result

    def test_expand_query_olive_oil(self):
        """Test expand_query with olive oil."""
        result = food_store.expand_query("масло оливковое")
        assert "масло оливковое" in result
        assert "olive oil" in result
        assert "aceite de oliva" in result

    def test_expand_query_cottage_cheese(self):
        """Test expand_query with cottage cheese."""
        result = food_store.expand_query("творог")
        assert "творог" in result
        assert "cottage cheese" in result
        assert "queso cottage" in result

    @patch("app.services.food_store._connect")
    def test_search_foods_with_query(self, mock_connect):
        """Test search_foods with query."""
        # Mock database connection and cursor
        mock_con = MagicMock()
        mock_con.__enter__.return_value = mock_con
        mock_con.__exit__.return_value = None
        mock_con.execute.return_value.fetchall.return_value = [
            {
                "id": "1",
                "canonical_name": "apple",
                "kcal": 52,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
            }
        ]
        mock_connect.return_value = mock_con

        result = food_store.search_foods("apple", limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["canonical_name"] == "apple"
        mock_con.execute.assert_called_once()

    @patch("app.services.food_store._connect")
    def test_search_foods_without_query(self, mock_connect):
        """Test search_foods without query."""
        # Mock database connection and cursor
        mock_con = MagicMock()
        mock_con.__enter__.return_value = mock_con
        mock_con.__exit__.return_value = None
        mock_con.execute.return_value.fetchall.return_value = [
            {
                "id": "1",
                "canonical_name": "apple",
                "kcal": 52,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 14.0,
            }
        ]
        mock_connect.return_value = mock_con

        result = food_store.search_foods("", limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["canonical_name"] == "apple"
        mock_con.execute.assert_called_once()

    @patch("app.services.food_store._connect")
    def test_search_foods_none_query(self, mock_connect):
        """Test search_foods with None query."""
        # Mock database connection and cursor
        mock_con = MagicMock()
        mock_con.__enter__.return_value = mock_con
        mock_con.__exit__.return_value = None
        mock_con.execute.return_value.fetchall.return_value = []
        mock_connect.return_value = mock_con

        result = food_store.search_foods(None, limit=10, offset=0)

        assert result == []
        mock_con.execute.assert_called_once()

    @patch("app.services.food_store._connect")
    def test_get_food_found(self, mock_connect):
        """Test get_food when food is found."""
        # Mock database connection and cursor
        mock_con = MagicMock()
        mock_con.__enter__.return_value = mock_con
        mock_con.__exit__.return_value = None
        mock_con.execute.return_value.fetchone.return_value = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "per_g": 100.0,
        }
        mock_connect.return_value = mock_con

        result = food_store.get_food("1")

        assert result is not None
        assert result["canonical_name"] == "apple"
        assert result["kcal"] == 52

    @patch("app.services.food_store._connect")
    def test_get_food_not_found(self, mock_connect):
        """Test get_food when food is not found."""
        # Mock database connection and cursor
        mock_con = MagicMock()
        mock_con.__enter__.return_value = mock_con
        mock_con.__exit__.return_value = None
        mock_con.execute.return_value.fetchone.return_value = None
        mock_connect.return_value = mock_con

        result = food_store.get_food("999")

        assert result is None

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_empty_list(self, mock_get_food):
        """Test nutrients_for with empty ingredients list."""
        result = food_store.nutrients_for([])

        expected_keys = [
            "kcal",
            "protein_g",
            "fat_g",
            "carbs_g",
            "Fe_mg",
            "Ca_mg",
            "K_mg",
            "Mg_mg",
            "VitD_IU",
            "B12_ug",
            "Folate_ug",
            "Iodine_ug",
        ]

        for key in expected_keys:
            assert result[key] == 0.0

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_single_ingredient(self, mock_get_food):
        """Test nutrients_for with single ingredient."""
        mock_get_food.return_value = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "Fe_mg": 0.1,
            "Ca_mg": 6.0,
            "K_mg": 107.0,
            "Mg_mg": 5.0,
            "VitD_IU": 0,
            "B12_ug": 0,
            "Folate_ug": 3.0,
            "Iodine_ug": 0,
            "per_g": 100.0,
        }

        ingredients = [{"food_id": "1", "grams": 200.0}]
        result = food_store.nutrients_for(ingredients)

        # 200g of apple (per 100g) = 2x the values
        assert result["kcal"] == 104.0  # 52 * 2
        assert result["protein_g"] == 0.6  # 0.3 * 2
        assert result["fat_g"] == 0.4  # 0.2 * 2
        assert result["carbs_g"] == 28.0  # 14.0 * 2

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_multiple_ingredients(self, mock_get_food):
        """Test nutrients_for with multiple ingredients."""

        def mock_get_food_side_effect(food_id):
            if food_id == "1":
                return {
                    "id": "1",
                    "canonical_name": "apple",
                    "kcal": 52,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbs_g": 14.0,
                    "Fe_mg": 0.1,
                    "Ca_mg": 6.0,
                    "K_mg": 107.0,
                    "Mg_mg": 5.0,
                    "VitD_IU": 0,
                    "B12_ug": 0,
                    "Folate_ug": 3.0,
                    "Iodine_ug": 0,
                    "per_g": 100.0,
                }
            elif food_id == "2":
                return {
                    "id": "2",
                    "canonical_name": "banana",
                    "kcal": 89,
                    "protein_g": 1.1,
                    "fat_g": 0.3,
                    "carbs_g": 23.0,
                    "Fe_mg": 0.3,
                    "Ca_mg": 5.0,
                    "K_mg": 358.0,
                    "Mg_mg": 27.0,
                    "VitD_IU": 0,
                    "B12_ug": 0,
                    "Folate_ug": 20.0,
                    "Iodine_ug": 0,
                    "per_g": 100.0,
                }
            return None

        mock_get_food.side_effect = mock_get_food_side_effect

        ingredients = [
            {"food_id": "1", "grams": 100.0},  # 100g apple
            {"food_id": "2", "grams": 150.0},  # 150g banana
        ]
        result = food_store.nutrients_for(ingredients)

        # Apple: 100g = 1x values
        # Banana: 150g = 1.5x values
        assert result["kcal"] == 52 + (89 * 1.5)  # 52 + 133.5 = 185.5
        assert result["protein_g"] == 0.3 + (1.1 * 1.5)  # 0.3 + 1.65 = 1.95
        assert result["fat_g"] == 0.2 + (0.3 * 1.5)  # 0.2 + 0.45 = 0.65

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_missing_food(self, mock_get_food):
        """Test nutrients_for with missing food."""
        mock_get_food.return_value = None

        ingredients = [{"food_id": "999", "grams": 100.0}]
        result = food_store.nutrients_for(ingredients)

        # All values should be 0.0 since food was not found
        expected_keys = [
            "kcal",
            "protein_g",
            "fat_g",
            "carbs_g",
            "Fe_mg",
            "Ca_mg",
            "K_mg",
            "Mg_mg",
            "VitD_IU",
            "B12_ug",
            "Folate_ug",
            "Iodine_ug",
        ]

        for key in expected_keys:
            assert result[key] == 0.0

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_custom_per_g(self, mock_get_food):
        """Test nutrients_for with custom per_g value."""
        mock_get_food.return_value = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "Fe_mg": 0.1,
            "Ca_mg": 6.0,
            "K_mg": 107.0,
            "Mg_mg": 5.0,
            "VitD_IU": 0,
            "B12_ug": 0,
            "Folate_ug": 3.0,
            "Iodine_ug": 0,
            "per_g": 50.0,  # Custom per_g value
        }

        ingredients = [{"food_id": "1", "grams": 100.0}]
        result = food_store.nutrients_for(ingredients)

        # 100g of apple (per 50g) = 2x the values
        assert result["kcal"] == 104.0  # 52 * 2
        assert result["protein_g"] == 0.6  # 0.3 * 2

    @patch("app.services.food_store.get_food")
    def test_nutrients_for_missing_nutrient_values(self, mock_get_food):
        """Test nutrients_for with missing nutrient values."""
        mock_get_food.return_value = {
            "id": "1",
            "canonical_name": "apple",
            "kcal": 52,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            # Missing some nutrient values
            "per_g": 100.0,
        }

        ingredients = [{"food_id": "1", "grams": 100.0}]
        result = food_store.nutrients_for(ingredients)

        # Should handle missing values gracefully
        assert result["kcal"] == 52.0
        assert result["protein_g"] == 0.3
        assert result["Fe_mg"] == 0.0  # Missing value defaults to 0.0
        assert result["Ca_mg"] == 0.0  # Missing value defaults to 0.0
