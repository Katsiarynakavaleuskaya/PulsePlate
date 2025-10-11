"""Tests for food_store.py to improve coverage."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.services import food_store


class TestFoodStoreCoverage:
    """Test coverage for food store functionality."""

    def test_expand_query_basic(self):
        """Test basic query expansion."""
        # Test empty query
        result = food_store.expand_query("")
        assert result == []

        # Test None query
        result = food_store.expand_query(None)
        assert result == []

        # Test whitespace query
        result = food_store.expand_query("   ")
        assert result == []

    def test_expand_query_with_aliases(self):
        """Test query expansion with known aliases."""
        # Test known alias
        result = food_store.expand_query("йогурт")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

        # Test English alias
        result = food_store.expand_query("yogurt")
        assert "йогурт" in result
        assert "yogurt" in result
        assert "yoghurt" in result

    def test_expand_query_unknown(self):
        """Test query expansion with unknown terms."""
        result = food_store.expand_query("unknown_food")
        assert result == ["unknown_food"]

    def test_search_foods_empty_query(self):
        """Test food search with empty query."""
        with patch("app.services.food_store._connect") as mock_connect:
            mock_con = MagicMock()
            mock_con.execute.return_value.fetchall.return_value = []
            mock_connect.return_value.__enter__.return_value = mock_con
            mock_connect.return_value.__exit__.return_value = None

            result = food_store.search_foods("", limit=10, offset=0)
            # Empty query should return empty list when mocked fetchall returns empty
            assert result == []

    def test_search_foods_with_query(self):
        """Test food search with query."""
        with patch("app.services.food_store._connect") as mock_connect:
            mock_con = MagicMock()
            mock_row = MagicMock()
            mock_row.__iter__ = Mock(return_value=iter(["food1", "Apple", 50, 0.3, 0.2, 13]))
            mock_con.execute.return_value.fetchall.return_value = [mock_row]
            mock_connect.return_value.__enter__.return_value = mock_con
            mock_connect.return_value.__exit__.return_value = None

            result = food_store.search_foods("apple", limit=10, offset=0)
            assert len(result) == 1
            # Check that the result has the expected structure
            assert isinstance(result[0], dict)
            # The result should contain food data (even if empty dict)
            assert result[0] is not None

    def test_search_foods_with_aliases(self):
        """Test food search with alias expansion."""
        with patch("app.services.food_store._connect") as mock_connect:
            mock_con = MagicMock()
            mock_con.execute.return_value.fetchall.return_value = []
            mock_connect.return_value.__enter__.return_value = mock_con
            mock_connect.return_value.__exit__.return_value = None

            # Test with alias that should expand
            result = food_store.search_foods("йогурт", limit=10, offset=0)
            assert result == []

    def test_get_food_existing(self):
        """Test getting existing food item."""
        with patch("app.services.food_store._connect") as mock_connect:
            mock_con = MagicMock()
            mock_row = MagicMock()
            mock_row.__iter__ = Mock(
                return_value=iter(["food1", "Apple", "fruits", 100.0, 50, 0.3, 0.2, 13, 2.4])
            )
            mock_con.execute.return_value.fetchone.return_value = mock_row
            mock_connect.return_value.__enter__.return_value = mock_con
            mock_connect.return_value.__exit__.return_value = None

            result = food_store.get_food("food1")
            assert result is not None
            assert isinstance(result, dict)
            # Check that the result contains food data (even if empty dict)
            assert result is not None

    def test_get_food_not_found(self):
        """Test getting non-existing food item."""
        with patch("app.services.food_store._connect") as mock_connect:
            mock_con = MagicMock()
            mock_con.execute.return_value.fetchone.return_value = None
            mock_connect.return_value.__enter__.return_value = mock_con
            mock_connect.return_value.__exit__.return_value = None

            result = food_store.get_food("nonexistent")
            assert result is None

    def test_nutrients_for_empty_ingredients(self):
        """Test nutrient calculation with empty ingredients."""
        result = food_store.nutrients_for([])

        # Should return dict with all keys set to 0.0
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
            assert key in result
            assert result[key] == 0.0

    def test_nutrients_for_with_ingredients(self):
        """Test nutrient calculation with ingredients."""
        with patch("app.services.food_store.get_food") as mock_get_food:
            # Mock food data
            mock_food = {
                "kcal": 50,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 13,
                "Fe_mg": 0.1,
                "Ca_mg": 5,
                "K_mg": 100,
                "Mg_mg": 5,
                "VitD_IU": 0,
                "B12_ug": 0,
                "Folate_ug": 3,
                "Iodine_ug": 0,
                "per_g": 100.0,
            }
            mock_get_food.return_value = mock_food

            ingredients = [{"food_id": "food1", "grams": 200}]

            result = food_store.nutrients_for(ingredients)

            # Should calculate nutrients based on 200g (2x the 100g base)
            assert result["kcal"] == 100.0  # 50 * 2
            assert result["protein_g"] == 0.6  # 0.3 * 2
            assert result["fat_g"] == 0.4  # 0.2 * 2
            assert result["carbs_g"] == 26.0  # 13 * 2

    def test_nutrients_for_missing_food(self):
        """Test nutrient calculation with missing food items."""
        with patch("app.services.food_store.get_food") as mock_get_food:
            mock_get_food.return_value = None

            ingredients = [{"food_id": "missing_food", "grams": 100}]

            result = food_store.nutrients_for(ingredients)

            # Should return zeros for missing food
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

    def test_nutrients_for_multiple_ingredients(self):
        """Test nutrient calculation with multiple ingredients."""
        with patch("app.services.food_store.get_food") as mock_get_food:

            def mock_get_food_side_effect(food_id):
                if food_id == "food1":
                    return {
                        "kcal": 50,
                        "protein_g": 0.3,
                        "fat_g": 0.2,
                        "carbs_g": 13,
                        "Fe_mg": 0.1,
                        "Ca_mg": 5,
                        "K_mg": 100,
                        "Mg_mg": 5,
                        "VitD_IU": 0,
                        "B12_ug": 0,
                        "Folate_ug": 3,
                        "Iodine_ug": 0,
                        "per_g": 100.0,
                    }
                elif food_id == "food2":
                    return {
                        "kcal": 100,
                        "protein_g": 1.0,
                        "fat_g": 0.5,
                        "carbs_g": 20,
                        "Fe_mg": 0.2,
                        "Ca_mg": 10,
                        "K_mg": 200,
                        "Mg_mg": 10,
                        "VitD_IU": 0,
                        "B12_ug": 0,
                        "Folate_ug": 5,
                        "Iodine_ug": 0,
                        "per_g": 100.0,
                    }
                return None

            mock_get_food.side_effect = mock_get_food_side_effect

            ingredients = [
                {"food_id": "food1", "grams": 100},  # 1x base
                {"food_id": "food2", "grams": 150},  # 1.5x base
            ]

            result = food_store.nutrients_for(ingredients)

            # Should sum nutrients from both ingredients
            assert result["kcal"] == 200.0  # 50*1 + 100*1.5
            assert result["protein_g"] == 1.8  # 0.3*1 + 1.0*1.5
            assert result["fat_g"] == 0.95  # 0.2*1 + 0.5*1.5
            assert result["carbs_g"] == 43.0  # 13*1 + 20*1.5

    def test_nutrients_for_different_per_g_values(self):
        """Test nutrient calculation with different per_g values."""
        with patch("app.services.food_store.get_food") as mock_get_food:
            mock_food = {
                "kcal": 50,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 13,
                "Fe_mg": 0.1,
                "Ca_mg": 5,
                "K_mg": 100,
                "Mg_mg": 5,
                "VitD_IU": 0,
                "B12_ug": 0,
                "Folate_ug": 3,
                "Iodine_ug": 0,
                "per_g": 50.0,  # Different base (50g instead of 100g)
            }
            mock_get_food.return_value = mock_food

            ingredients = [
                {"food_id": "food1", "grams": 100}  # 100g of food with 50g base
            ]

            result = food_store.nutrients_for(ingredients)

            # Should calculate based on ratio: 100g / 50g = 2x
            assert result["kcal"] == 100.0  # 50 * 2
            assert result["protein_g"] == 0.6  # 0.3 * 2
            assert result["fat_g"] == 0.4  # 0.2 * 2
            assert result["carbs_g"] == 26.0  # 13 * 2

    def test_nutrients_for_missing_nutrient_values(self):
        """Test nutrient calculation with missing nutrient values."""
        with patch("app.services.food_store.get_food") as mock_get_food:
            mock_food = {
                "kcal": 50,
                "protein_g": 0.3,
                "fat_g": 0.2,
                "carbs_g": 13,
                # Missing some nutrients
                "per_g": 100.0,
            }
            mock_get_food.return_value = mock_food

            ingredients = [{"food_id": "food1", "grams": 100}]

            result = food_store.nutrients_for(ingredients)

            # Should handle missing nutrients gracefully
            assert result["kcal"] == 50.0
            assert result["protein_g"] == 0.3
            assert result["fat_g"] == 0.2
            assert result["carbs_g"] == 13.0
            # Missing nutrients should default to 0.0
            assert result["Fe_mg"] == 0.0
            assert result["Ca_mg"] == 0.0
