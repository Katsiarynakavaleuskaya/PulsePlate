"""
Combined tests for core/food_db_new.py
Includes basic tests and coverage tests for food database functionality.
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.food_db_new import FoodDB


class TestFoodDbNewCombined:
    """Combined tests for food_db_new.py functionality and coverage."""

    def setup_method(self) -> None:
        """Setup test environment."""
        # Create a minimal CSV for testing
        self.test_csv_content = (
            "name,group,per_g,protein_g,fat_g,carbs_g,fiber_g,Fe_mg,Ca_mg,"
            "VitD_IU,B12_ug,Folate_ug,Iodine_ug,K_mg,Mg_mg,flags,price\n"
            "test_food,test,1.0,10.0,5.0,15.0,3.0,2.0,50.0,0.0,0.0,100.0,"
            "0.0,200.0,30.0,VEG,5.00\n"
            "omni_food,test,1.0,5.0,2.0,10.0,1.0,1.0,25.0,0.0,0.0,50.0,"
            "0.0,100.0,15.0,OMNI,3.00"
        )

        self.temp_csv = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.temp_csv.write(self.test_csv_content)
        self.temp_csv.close()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        if os.path.exists(self.temp_csv.name):
            os.unlink(self.temp_csv.name)

    def test_parse_food_db(self) -> None:
        """Test that food database is parsed correctly."""
        csv_path = str(Path(__file__).resolve().parents[1] / "data" / "food_db_new.csv")

        # Parse the food database
        food_db = FoodDB(csv_path)

        # Check that we have foods
        assert isinstance(food_db.items, dict)
        assert len(food_db.items) > 0

        # Optional: avoid relying on specific item names which may change
        # Just sample one arbitrary element to ensure objects are parseable
        sample = next(iter(food_db.items.values()))
        assert hasattr(sample, "name")

    def test_get_food_returns_existing_item(self) -> None:
        """Test get_food returns existing item."""
        food_db = FoodDB(self.temp_csv.name)

        # Test getting existing food
        food_item = food_db.get_food("test_food")
        assert food_item.name == "test_food"
        assert food_item.protein_g == 10.0

    def test_get_food_not_found(self) -> None:
        """Test get_food method when food is not found."""
        food_db = FoodDB(self.temp_csv.name)

        # Test getting non-existing food - should raise KeyError
        with pytest.raises(KeyError):
            food_db.get_food("nonexistent_food")

    def test_food_item_attributes(self) -> None:
        """Test FoodItem object attributes."""
        food_db = FoodDB(self.temp_csv.name)

        # Test getting existing food and checking attributes
        food_item = food_db.get_food("test_food")
        assert hasattr(food_item, "name")
        assert hasattr(food_item, "protein_g")
        assert hasattr(food_item, "fat_g")
        assert hasattr(food_item, "carbs_g")
        assert hasattr(food_item, "fiber_g")
        assert hasattr(food_item, "group")
        assert hasattr(food_item, "flags")

    def test_food_db_items_dict(self) -> None:
        """Test that items is a dictionary."""
        food_db = FoodDB(self.temp_csv.name)

        # Test that items is a dictionary
        assert isinstance(food_db.items, dict)
        assert len(food_db.items) > 0

    def test_food_db_contains_items(self) -> None:
        """Test that food database contains expected items."""
        food_db = FoodDB(self.temp_csv.name)

        # Test that our test items are in the database
        assert "test_food" in food_db.items
        assert "omni_food" in food_db.items

    def test_food_db_initialization_error(self) -> None:
        """Test FoodDB initialization with invalid file."""
        with pytest.raises(FileNotFoundError):
            FoodDB("nonexistent_file.csv")

    def test_food_db_empty_file(self) -> None:
        """Test FoodDB with empty CSV file."""
        # Create empty CSV
        empty_csv = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        empty_csv.write(
            "name,group,per_g,protein_g,fat_g,carbs_g,fiber_g,Fe_mg,Ca_mg,"
            "VitD_IU,B12_ug,Folate_ug,Iodine_ug,K_mg,Mg_mg,flags,price\n"
        )
        empty_csv.close()

        try:
            food_db = FoodDB(empty_csv.name)
            assert len(food_db.items) == 0
        finally:
            os.unlink(empty_csv.name)


# __main__ guard intentionally omitted; run via `pytest`.
