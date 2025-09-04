"""
Tests for Food Database Parser

RU: Тесты для парсера базы данных продуктов.
EN: Tests for the food database parser.
"""

import pytest

from core.food_db import aggregate_shopping, parse_food_db, pick_booster_for


def test_parse_food_db():
    """Test that food database is parsed correctly."""
    # Parse the food database
    food_db = parse_food_db()

    # Check that we have foods
    assert isinstance(food_db, dict)
    assert len(food_db) > 0

    # Check a specific food item
    assert "Овсяные хлопья" in food_db
    oatmeal = food_db["Овсяные хлопья"]

    # Check that all required fields are present
    assert hasattr(oatmeal, "name")
    assert hasattr(oatmeal, "protein_g")
    assert hasattr(oatmeal, "fat_g")
    assert hasattr(oatmeal, "carbs_g")
    assert hasattr(oatmeal, "fiber_g")
    assert hasattr(oatmeal, "Fe_mg")
    assert hasattr(oatmeal, "Ca_mg")
    assert hasattr(oatmeal, "VitD_IU")
    assert hasattr(oatmeal, "B12_ug")
    assert hasattr(oatmeal, "Folate_ug")
    assert hasattr(oatmeal, "Iodine_ug")
    assert hasattr(oatmeal, "K_mg")
    assert hasattr(oatmeal, "Mg_mg")
    assert hasattr(oatmeal, "price_per_unit")
    assert hasattr(oatmeal, "flags")


def test_pick_booster_for():
    """Test booster food selection."""
    # Parse the food database
    food_db = parse_food_db()

    # Test picking a booster for iron
    booster = pick_booster_for("iron_mg", set(), food_db)
    # Should return a food that's high in iron
    assert booster is not None

    # Test with vegetarian flag
    veg_booster = pick_booster_for("iron_mg", {"VEG"}, food_db)
    assert veg_booster is not None


def test_aggregate_shopping():
    """Test shopping list aggregation."""
    # Create mock daily plans
    days = [
        {
            "meals": [
                {
                    "ingredients": {
                        "Овсяные хлопья": 60,
                        "Орехи": 20
                    }
                }
            ]
        },
        {
            "meals": [
                {
                    "ingredients": {
                        "Гречка": 70,
                        "Тофу": 120
                    }
                }
            ]
        }
    ]

    # Aggregate shopping list
    shopping_list = aggregate_shopping(days)

    # Check that ingredients are aggregated correctly
    assert "Овсяные хлопья" in shopping_list
    assert shopping_list["Овсяные хлопья"] == 60
    assert "Тофу" in shopping_list
    assert shopping_list["Тофу"] == 120


if __name__ == "__main__":
    pytest.main([__file__])
