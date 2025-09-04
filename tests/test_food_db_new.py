"""
Tests for Food Database Parser

RU: Тесты для парсера базы данных продуктов.
EN: Tests for the food database parser.
"""

import os

import pytest

from core.food_db_new import MICRO_KEYS, FoodDB


def test_parse_food_db():
    """Test that food database is parsed correctly."""
    # Get the path to the test data file
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")

    # Parse the food database
    food_db = FoodDB(csv_path)

    # Check that we have foods
    assert isinstance(food_db.items, dict)
    assert len(food_db.items) > 0

    # Check a specific food item
    assert "chicken_breast" in food_db.items
    chicken = food_db.get_food("chicken_breast")

    # Check that all required fields are present
    assert hasattr(chicken, "name")
    assert hasattr(chicken, "group")
    assert hasattr(chicken, "protein_g")
    assert hasattr(chicken, "fat_g")
    assert hasattr(chicken, "carbs_g")
    assert hasattr(chicken, "fiber_g")
    assert hasattr(chicken, "micros")
    assert hasattr(chicken, "flags")
    assert hasattr(chicken, "price")

    # Check specific values
    assert chicken.protein_g == 31.0
    assert chicken.fat_g == 3.6
    assert chicken.micros["Fe_mg"] == 0.7
    assert "OMNI" in chicken.flags

def test_pick_booster_for():
    """Test booster food selection."""
    # Get the path to the test data file
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")

    # Parse the food database
    food_db = FoodDB(csv_path)

    # Test picking a booster for iron
    booster = food_db.pick_booster_for("Fe_mg", [])
    # Should return a food that's high in iron
    assert booster is not None
    assert booster in ["lentils", "spinach", "tofu", "chicken_breast"]

    # Test with vegetarian flag
    veg_booster = food_db.pick_booster_for("Fe_mg", ["VEG"])
    assert veg_booster is not None
    assert veg_booster in ["lentils", "spinach", "tofu"]
    assert veg_booster != "chicken_breast"  # Should not return non-veg items

def test_aggregate_shopping():
    """Test shopping list aggregation."""
    # Get the path to the test data file
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")

    # Parse the food database
    food_db = FoodDB(csv_path)

    # Create mock daily plans
    days = [
        {
            "meals": [
                {
                    "grams": {
                        "oats": 60,
                        "greek_yogurt": 150,
                        "banana": 100
                    }
                }
            ]
        },
        {
            "meals": [
                {
                    "grams": {
                        "lentils": 180,
                        "spinach": 120,
                        "olive_oil": 10
                    }
                }
            ]
        }
    ]

    # Aggregate shopping list
    shopping_list = food_db.aggregate_shopping(days)

    # Check that ingredients are aggregated correctly
    oats_item = next((item for item in shopping_list if item["name"] == "oats"), None)
    assert oats_item is not None
    assert oats_item["grams"] == 60

    spinach_item = next((item for item in shopping_list if item["name"] == "spinach"), None)
    assert spinach_item is not None
    assert spinach_item["grams"] == 120

def test_get_translated_food_name():
    """Test food name translation."""
    # Get the path to the test data file
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")

    # Parse the food database
    food_db = FoodDB(csv_path)

    # Test translation for different languages
    assert food_db.get_translated_food_name("chicken_breast", "en") == "Chicken breast"
    assert food_db.get_translated_food_name("chicken_breast", "ru") == "Куриная грудка"
    assert food_db.get_translated_food_name("chicken_breast", "es") == "Pechuga de pollo"

    # Test that unknown food returns original name
    assert food_db.get_translated_food_name("unknown_food", "en") == "unknown_food"

def test_aggregate_shopping_multilingual():
    """Test multilingual shopping list aggregation."""
    # Get the path to the test data file
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "food_db_new.csv")

    # Parse the food database
    food_db = FoodDB(csv_path)

    # Create mock daily plans
    days = [
        {
            "meals": [
                {
                    "grams": {
                        "oats": 60,
                        "greek_yogurt": 150,
                        "banana": 100
                    }
                }
            ]
        }
    ]

    # Test shopping list with different languages
    for lang in ["en", "ru", "es"]:
        shopping_list = food_db.aggregate_shopping(days, lang)

        # Check that we have translated names
        assert len(shopping_list) > 0
        for item in shopping_list:
            assert "name" in item
            assert "name_translated" in item
            assert "grams" in item
            assert "price_est" in item

if __name__ == "__main__":
    pytest.main([__file__])
