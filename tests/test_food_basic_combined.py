"""
Combined basic food tests.
Includes API smoke tests and basic food database tests.
"""

from fastapi.testclient import TestClient

import pytest

import app as app_module

from core.food_db import aggregate_shopping, parse_food_db, pick_booster_for


class TestFoodAPIBasic:
    """Basic food API tests."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app_module.app)

    def test_search_foods_smoke(self):
        """Test basic food search functionality."""
        r = self.client.get("/api/v1/foods", params={"limit": 5})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_food_card_404(self):
        """Test food card 404 error handling."""
        r = self.client.get("/api/v1/foods/__nope__")
        assert r.status_code == 404


class TestFoodDatabaseBasic:
    """Basic food database tests."""

    def test_parse_food_db(self):
        """Test that food database is parsed correctly."""
        # Parse the food database
        food_db = parse_food_db()

        # Check that we have foods
        assert isinstance(food_db, dict)
        assert len(food_db) > 0

        # Optionally sample one item without depending on a specific name
        sample_item = next(iter(food_db.values()))

        # Check that all required fields are present
        assert hasattr(sample_item, "name")
        assert hasattr(sample_item, "protein_g")
        assert hasattr(sample_item, "fat_g")
        assert hasattr(sample_item, "carbs_g")
        assert hasattr(sample_item, "fiber_g")
        assert hasattr(sample_item, "Fe_mg")
        assert hasattr(sample_item, "Ca_mg")
        assert hasattr(sample_item, "VitD_IU")
        assert hasattr(sample_item, "B12_ug")
        assert hasattr(sample_item, "Folate_ug")
        assert hasattr(sample_item, "Iodine_ug")
        assert hasattr(sample_item, "K_mg")
        assert hasattr(sample_item, "Mg_mg")
        assert hasattr(sample_item, "price_per_unit")
        assert hasattr(sample_item, "flags")

    def test_pick_booster_for(self):
        """Test booster food selection."""
        # Parse the food database
        food_db = parse_food_db()

        # Test picking a booster for iron
        booster_name = pick_booster_for("iron_mg", set(), food_db)
        # Should return a food that's high in iron
        assert booster_name is not None

        # Verify the booster actually contains iron
        booster = food_db[booster_name]
        assert hasattr(booster, "Fe_mg")
        assert booster.Fe_mg > 0

        # Test with vegetarian flag
        veg_booster_name = pick_booster_for("iron_mg", {"VEG"}, food_db)
        assert veg_booster_name is not None

        # Verify the vegetarian booster respects dietary constraints
        veg_booster = food_db[veg_booster_name]
        assert hasattr(veg_booster, "flags")
        assert "VEG" in veg_booster.flags
        assert hasattr(veg_booster, "Fe_mg")
        assert veg_booster.Fe_mg > 0

    def test_aggregate_shopping(self):
        """Test shopping list aggregation."""
        # Create mock daily plans
        days = [
            {"meals": [{"ingredients": {"Овсяные хлопья": 60, "Орехи": 20}}]},
            {"meals": [{"ingredients": {"Гречка": 70, "Тофу": 120}}]},
        ]

        # Aggregate shopping list
        shopping_list = aggregate_shopping(days)

        # Check that ingredients are aggregated correctly
        assert "Овсяные хлопья" in shopping_list
        assert shopping_list["Овсяные хлопья"] == 60
        assert "Тофу" in shopping_list
        assert shopping_list["Тофу"] == 120


# __main__ guard intentionally omitted; run via `pytest`.
