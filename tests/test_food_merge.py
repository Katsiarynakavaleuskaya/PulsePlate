"""
Tests for Food Merge Logic

RU: Тесты для логики мерджа данных о продуктах.
EN: Tests for food data merge logic.
"""

from datetime import date

from core.food_merge import (
    _merge_values,
    merge_records,
    _classify_food_group
)
from core.food_sources.base import FoodRecord


class TestMergeValues:
    """Test _merge_values function."""

    def test_merge_values_median_strategy(self):
        """Test median merge strategy."""
        values = [10.0, 20.0, 30.0, 40.0]
        result = _merge_values(values, "median")
        assert result == 25.0  # median of 10, 20, 30, 40

    def test_merge_values_first_strategy(self):
        """Test first merge strategy."""
        values = [10.0, 20.0, 30.0, 40.0]
        result = _merge_values(values, "first")
        assert result == 10.0

    def test_merge_values_with_none(self):
        """Test merge values with None values."""
        values = [10.0, None, 30.0, None]
        result = _merge_values(values, "median")
        assert result == 20.0  # median of 10, 30

    def test_merge_values_with_negative(self):
        """Test merge values with negative values."""
        values = [10.0, -5.0, 30.0, -10.0]
        result = _merge_values(values, "median")
        assert result == 20.0  # median of 10, 30 (negative values filtered out)

    def test_merge_values_empty_list(self):
        """Test merge values with empty list."""
        values = []
        result = _merge_values(values, "median")
        assert result == 0.0

    def test_merge_values_all_none(self):
        """Test merge values with all None values."""
        values = [None, None, None]
        result = _merge_values(values, "median")
        assert result == 0.0

    def test_merge_values_all_negative(self):
        """Test merge values with all negative values."""
        values = [-10.0, -20.0, -30.0]
        result = _merge_values(values, "median")
        assert result == 0.0

    def test_merge_values_single_value(self):
        """Test merge values with single value."""
        values = [15.0]
        result = _merge_values(values, "median")
        assert result == 15.0


class TestClassifyFoodGroup:
    """Test _classify_food_group function."""

    def test_classify_high_protein_lean(self):
        """Test classification of lean protein foods."""
        record = {
            "name": "chicken breast",
            "kcal": 165.0,
            "protein_g": 31.0,  # ~75% of calories from protein
            "fat_g": 3.6,
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"

    def test_classify_high_protein_fatty(self):
        """Test classification of fatty protein foods."""
        record = {
            "name": "almonds",
            "kcal": 579.0,
            "protein_g": 21.2,  # ~15% of calories from protein
            "fat_g": 49.9,  # High fat
            "carbs_g": 21.6,
            "fiber_g": 12.5,
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "fat"  # High fat percentage takes priority

    def test_classify_high_fat_food(self):
        """Test classification of high fat foods."""
        record = {
            "name": "olive oil",
            "kcal": 884.0,
            "protein_g": 0.0,
            "fat_g": 100.0,  # ~100% of calories from fat
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "fat"

    def test_classify_high_carb_grain(self):
        """Test classification of high carb grain foods."""
        record = {
            "name": "brown rice",
            "kcal": 111.0,
            "protein_g": 2.6,
            "fat_g": 0.9,
            "carbs_g": 23.0,  # ~83% of calories from carbs
            "fiber_g": 1.8,
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "grain"

    def test_classify_high_fiber_grain(self):
        """Test classification of high fiber grain foods."""
        record = {
            "name": "whole wheat bread",
            "kcal": 247.0,
            "protein_g": 13.0,  # ~21% of calories from protein
            "fat_g": 4.2,
            "carbs_g": 41.0,  # ~66% of calories from carbs
            "fiber_g": 6.0,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume(self):
        """Test classification of legume foods."""
        record = {
            "name": "lentils",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume_by_name(self):
        """Test classification of legume foods by name."""
        record = {
            "name": "chickpea",
            "kcal": 164.0,
            "protein_g": 8.9,  # ~22% of calories from protein
            "fat_g": 2.6,
            "carbs_g": 27.4,  # ~67% of calories from carbs
            "fiber_g": 7.6,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_high_sugar_fruit(self):
        """Test classification of high sugar fruit foods."""
        record = {
            "name": "banana",
            "kcal": 89.0,
            "protein_g": 1.1,
            "fat_g": 0.3,
            "carbs_g": 22.8,  # ~102% of calories from carbs
            "fiber_g": 2.6,
            "sugar_g": 12.2,  # High sugar
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "fruit"

    def test_classify_vegetable(self):
        """Test classification of vegetable foods."""
        record = {
            "name": "broccoli",
            "kcal": 34.0,  # Low calories
            "protein_g": 2.8,  # ~33% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 6.6,
            "fiber_g": 2.6,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_dairy(self):
        """Test classification of dairy foods."""
        record = {
            "name": "milk",
            "kcal": 42.0,
            "protein_g": 3.4,  # ~32% of calories from protein
            "fat_g": 1.0,
            "carbs_g": 5.0,
            "fiber_g": 0.0,
            "flags": ["DAIRY"]
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_other_default(self):
        """Test default classification."""
        record = {
            "name": "unknown food",
            "kcal": 100.0,
            "protein_g": 5.0,  # ~20% of calories from protein
            "fat_g": 5.0,
            "carbs_g": 10.0,
            "fiber_g": 1.0,
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_zero_calories(self):
        """Test classification with zero calories."""
        record = {
            "name": "water",
            "kcal": 0.0,
            "protein_g": 0.0,
            "fat_g": 0.0,
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "other"

    def test_classify_legume_correct(self):
        """Test correct classification of legume foods."""
        record = {
            "name": "lentils",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_grain_correct(self):
        """Test correct classification of grain foods."""
        record = {
            "name": "rice",
            "kcal": 130.0,
            "protein_g": 2.7,  # ~8% of calories from protein
            "fat_g": 0.3,
            "carbs_g": 28.0,  # ~86% of calories from carbs
            "fiber_g": 0.4,  # Low fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "grain"

    def test_classify_vegetable_correct(self):
        """Test correct classification of vegetable foods."""
        record = {
            "name": "lettuce",
            "kcal": 15.0,  # Low calories
            "protein_g": 1.4,  # ~37% of calories from protein
            "fat_g": 0.2,
            "carbs_g": 2.9,
            "fiber_g": 1.3,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_dairy_correct(self):
        """Test correct classification of dairy foods."""
        record = {
            "name": "cheese",
            "kcal": 113.0,
            "protein_g": 7.0,  # ~25% of calories from protein
            "fat_g": 9.0,
            "carbs_g": 0.4,
            "fiber_g": 0.0,
            "flags": ["DAIRY"]
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume_by_name_match(self):
        """Test classification of legume foods by name matching."""
        record = {
            "name": "lentil soup",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume_by_name_bean(self):
        """Test classification of legume foods by name matching bean."""
        record = {
            "name": "black bean",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume_by_name_chickpea(self):
        """Test classification of legume foods by name matching chickpea."""
        record = {
            "name": "chickpea flour",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_high_sugar_carb(self):
        """Test classification of high sugar carb foods."""
        record = {
            "name": "sweet fruit",
            "kcal": 100.0,
            "protein_g": 1.0,  # ~4% of calories from protein
            "fat_g": 0.5,
            "carbs_g": 25.0,  # ~100% of calories from carbs
            "fiber_g": 2.0,  # Low fiber
            "sugar_g": 15.0,  # High sugar
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "fruit"

    def test_classify_vegetable_low_calorie(self):
        """Test classification of low calorie vegetable foods."""
        record = {
            "name": "cucumber",
            "kcal": 16.0,  # Low calories
            "protein_g": 0.7,  # ~18% of calories from protein
            "fat_g": 0.1,
            "carbs_g": 4.0,
            "fiber_g": 0.5,  # Low fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_fruit_by_sugar(self):
        """Test classification of fruit foods by sugar content."""
        record = {
            "name": "apple",
            "kcal": 52.0,
            "protein_g": 0.3,  # ~2% of calories from protein
            "fat_g": 0.2,
            "carbs_g": 14.0,  # ~108% of calories from carbs
            "fiber_g": 2.4,  # Low fiber
            "sugar_g": 10.0,  # High sugar
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "grain"  # Low fiber, high carb -> grain

    def test_classify_dairy_by_flags(self):
        """Test classification of dairy foods by flags."""
        record = {
            "name": "yogurt",
            "kcal": 59.0,
            "protein_g": 10.0,  # ~68% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 3.6,
            "fiber_g": 0.0,
            "flags": ["DAIRY", "PROBIOTIC"]
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume_by_name_lentil(self):
        """Test classification of legume foods by name matching lentil."""
        record = {
            "name": "lentil",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume_by_name_bean_match(self):
        """Test classification of legume foods by name matching bean."""
        record = {
            "name": "bean",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_legume_by_name_chickpea_match(self):
        """Test classification of legume foods by name matching chickpea."""
        record = {
            "name": "chickpea",
            "kcal": 116.0,
            "protein_g": 9.0,  # ~31% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 20.1,  # ~69% of calories from carbs
            "fiber_g": 7.9,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_vegetable_high_fiber_low_calorie(self):
        """Test classification of vegetable foods with high fiber and low calories."""
        record = {
            "name": "spinach",
            "kcal": 23.0,  # Low calories
            "protein_g": 2.9,  # ~50% of calories from protein
            "fat_g": 0.4,
            "carbs_g": 3.6,
            "fiber_g": 2.2,  # High fiber
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_fruit_by_sugar_low_protein(self):
        """Test classification of fruit foods by sugar content with low protein."""
        record = {
            "name": "orange",
            "kcal": 47.0,
            "protein_g": 0.9,  # ~8% of calories from protein
            "fat_g": 0.1,
            "carbs_g": 11.8,  # ~100% of calories from carbs
            "fiber_g": 2.4,  # Low fiber
            "sugar_g": 9.4,  # High sugar
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "grain"  # Low fiber, high carb -> grain

    def test_classify_dairy_by_flags_low_protein(self):
        """Test classification of dairy foods by flags with low protein."""
        record = {
            "name": "milk",
            "kcal": 42.0,
            "protein_g": 3.4,  # ~32% of calories from protein
            "fat_g": 1.0,
            "carbs_g": 5.0,
            "fiber_g": 0.0,
            "flags": ["DAIRY"]
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority


class TestMergeRecords:
    """Test merge_records function."""

    def create_food_record(self, name, source, **kwargs):
        """Helper to create FoodRecord objects."""
        defaults = {
            "locale": "en",
            "per_g": 100.0,
            "kcal": 100.0,
            "protein_g": 10.0,
            "fat_g": 5.0,
            "carbs_g": 15.0,
            "fiber_g": 2.0,
            "flags": [],
            "price": 0.0,
            "version_date": "2024-01-01",
            "Fe_mg": 1.0,
            "Ca_mg": 50.0,
            "VitD_IU": 10.0,
            "B12_ug": 0.5,
            "Folate_ug": 20.0,
            "Iodine_ug": 5.0,
            "K_mg": 200.0,
            "Mg_mg": 25.0
        }
        defaults.update(kwargs)
        return FoodRecord(name=name, source=source, **defaults)

    def test_merge_records_single_source(self):
        """Test merging records from single source."""
        records = [
            self.create_food_record("apple", "USDA", kcal=52.0, protein_g=0.3)
        ]
        streams = [records]

        result = merge_records(streams)

        assert len(result) == 1
        assert result[0]["name"] == "apple"
        assert result[0]["kcal"] == 52.0
        assert result[0]["protein_g"] == 0.3
        assert result[0]["source"] == "MERGED(USDA)"

    def test_merge_records_multiple_sources(self):
        """Test merging records from multiple sources."""
        records1 = [self.create_food_record("apple", "USDA", kcal=52.0, protein_g=0.3)]
        records2 = [self.create_food_record("apple", "OFF", kcal=50.0, protein_g=0.2)]
        streams = [records1, records2]

        result = merge_records(streams)

        assert len(result) == 1
        assert result[0]["name"] == "apple"
        assert result[0]["kcal"] == 51.0  # median of 52.0 and 50.0
        assert result[0]["protein_g"] == 0.25  # median of 0.3 and 0.2
        assert result[0]["source"] == "MERGED(OFF,USDA)"

    def test_merge_records_micro_nutrients_usda_priority(self):
        """Test that USDA micro nutrients take priority."""
        records1 = [self.create_food_record("apple", "USDA", Fe_mg=2.0, Ca_mg=100.0)]
        records2 = [self.create_food_record("apple", "OFF", Fe_mg=1.0, Ca_mg=50.0)]
        streams = [records1, records2]

        result = merge_records(streams)

        assert len(result) == 1
        assert result[0]["Fe_mg"] == 2.0  # USDA value
        assert result[0]["Ca_mg"] == 100.0  # USDA value

    def test_merge_records_micro_nutrients_fallback(self):
        """Test micro nutrients fallback when no USDA."""
        records1 = [self.create_food_record("apple", "OFF", Fe_mg=1.0, Ca_mg=50.0)]
        records2 = [self.create_food_record("apple", "CUSTOM", Fe_mg=3.0, Ca_mg=75.0)]
        streams = [records1, records2]

        result = merge_records(streams)

        assert len(result) == 1
        assert result[0]["Fe_mg"] == 2.0  # median of 1.0 and 3.0
        assert result[0]["Ca_mg"] == 62.5  # median of 50.0 and 75.0

    def test_merge_records_flags_aggregation(self):
        """Test that flags are aggregated from all sources."""
        records1 = [self.create_food_record("milk", "USDA", flags=["DAIRY", "ORGANIC"])]
        records2 = [self.create_food_record("milk", "OFF", flags=["DAIRY", "LOW_FAT"])]
        streams = [records1, records2]

        result = merge_records(streams)

        assert len(result) == 1
        assert set(result[0]["flags"]) == {"DAIRY", "ORGANIC", "LOW_FAT"}

    def test_merge_records_multiple_foods(self):
        """Test merging multiple different foods."""
        records1 = [
            self.create_food_record("apple", "USDA", kcal=52.0),
            self.create_food_record("banana", "USDA", kcal=89.0)
        ]
        records2 = [
            self.create_food_record("apple", "OFF", kcal=50.0),
            self.create_food_record("orange", "OFF", kcal=47.0)
        ]
        streams = [records1, records2]

        result = merge_records(streams)

        assert len(result) == 3  # apple, banana, orange
        names = [r["name"] for r in result]
        assert "apple" in names
        assert "banana" in names
        assert "orange" in names

    def test_merge_records_empty_streams(self):
        """Test merging empty streams."""
        streams = []
        result = merge_records(streams)
        assert result == []

    def test_merge_records_version_date(self):
        """Test that version_date is set to today."""
        records = [self.create_food_record("apple", "USDA")]
        streams = [records]

        result = merge_records(streams)

        assert len(result) == 1
        assert result[0]["version_date"] == date.today().isoformat()

    def test_merge_records_food_group_classification(self):
        """Test that food group classification is applied."""
        records = [self.create_food_record("chicken", "USDA",
                                           kcal=165.0, protein_g=31.0, fat_g=3.6, carbs_g=0.0)]
        streams = [records]

        result = merge_records(streams)

        assert len(result) == 1
        assert result[0]["group"] == "protein"  # Should be classified as protein

    def test_merge_records_rounding(self):
        """Test that values are properly rounded."""
        records = [self.create_food_record("apple", "USDA",
                                           kcal=52.123456, protein_g=0.256789, Fe_mg=1.234567)]
        streams = [records]

        result = merge_records(streams)

        assert len(result) == 1
        assert result[0]["kcal"] == 52.1  # rounded to 1 decimal
        assert result[0]["protein_g"] == 0.26  # rounded to 2 decimals
        assert result[0]["Fe_mg"] == 1.235  # rounded to 3 decimals

    def test_classify_high_carb_no_sugar_grain(self):
        """Test classification of high carb food without sugar field (line 162)."""
        record = {
            "name": "rice",
            "kcal": 130.0,
            "protein_g": 2.7,  # Low protein
            "fat_g": 0.3,
            "carbs_g": 28.0,  # High carbs > 50%
            "fiber_g": 0.4,  # Low fiber
            "flags": []
            # No sugar_g field
        }
        result = _classify_food_group(record)
        assert result == "grain"

    def test_classify_high_carb_high_sugar_fruit(self):
        """Test classification of high carb food with high sugar (line 162)."""
        record = {
            "name": "banana",
            "kcal": 89.0,
            "protein_g": 1.1,  # Low protein
            "fat_g": 0.3,
            "carbs_g": 22.8,  # High carbs > 50%
            "fiber_g": 2.6,  # Low fiber
            "sugar_g": 12.2,  # High sugar > 10
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "fruit"

    def test_classify_vegetable_high_fiber_low_calorie(self):
        """Test classification of vegetable with high fiber and low calories (line 168)."""
        record = {
            "name": "broccoli",
            "kcal": 34.0,  # Low calories < 100
            "protein_g": 2.8,  # High protein percentage
            "fat_g": 0.4,
            "carbs_g": 6.6,
            "fiber_g": 2.6,  # High fiber > 2
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_fruit_by_sugar_no_sugar_field(self):
        """Test classification of fruit by sugar without sugar field (line 172)."""
        record = {
            "name": "apple",
            "kcal": 52.0,
            "protein_g": 0.3,  # Low protein
            "fat_g": 0.2,
            "carbs_g": 13.8,  # High carbs > 50%
            "fiber_g": 2.4,
            "flags": []
            # No sugar_g field
        }
        result = _classify_food_group(record)
        assert result == "grain"  # High carbs without high fiber

    def test_classify_dairy_by_flags_no_dairy_flags(self):
        """Test classification without dairy flags (line 176)."""
        record = {
            "name": "milk",
            "kcal": 42.0,
            "protein_g": 3.4,  # High protein percentage
            "fat_g": 1.0,
            "carbs_g": 5.0,
            "fiber_g": 0.0,
            "flags": []  # No DAIRY flag
        }
        result = _classify_food_group(record)
        assert result == "protein"  # High protein percentage takes priority

    def test_classify_vegetable_low_protein_high_fiber(self):
        """Test classification of vegetable with low protein and high fiber (line 169)."""
        record = {
            "name": "lettuce",
            "kcal": 15.0,  # Low calories < 100
            "protein_g": 0.5,  # Very low protein percentage
            "fat_g": 0.2,
            "carbs_g": 2.9,
            "fiber_g": 2.5,  # High fiber > 2
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "grain"  # High carbs without high protein

    def test_classify_fruit_by_sugar_field(self):
        """Test classification of fruit by sugar field (line 173)."""
        record = {
            "name": "grape",
            "kcal": 67.0,
            "protein_g": 0.6,  # Low protein
            "fat_g": 0.4,
            "carbs_g": 17.0,
            "fiber_g": 0.9,
            "sugar_g": 16.0,  # High sugar > 5
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "fruit"

    def test_classify_dairy_by_flags_field(self):
        """Test classification of dairy by flags field (line 177)."""
        record = {
            "name": "yogurt",
            "kcal": 59.0,
            "protein_g": 0.5,  # Low protein
            "fat_g": 0.4,
            "carbs_g": 3.6,
            "fiber_g": 0.0,
            "flags": ["DAIRY"]  # Has DAIRY flag
        }
        result = _classify_food_group(record)
        assert result == "dairy"  # Dairy flags take priority when protein is low

    def test_classify_legume_by_name_high_fiber(self):
        """Test classification of legume by name with high fiber (lines 157-161)."""
        record = {
            "name": "lentil",
            "kcal": 116.0,
            "protein_g": 2.0,  # Very low protein percentage
            "fat_g": 0.4,
            "carbs_g": 20.1,  # High carbs > 50%
            "fiber_g": 7.9,  # High fiber > 3
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "legume"  # Should be classified as legume by name

    def test_classify_grain_high_fiber_not_legume(self):
        """Test classification of grain with high fiber but not legume name (line 161)."""
        record = {
            "name": "quinoa",  # Not a legume name
            "kcal": 120.0,
            "protein_g": 1.0,  # Very low protein percentage
            "fat_g": 0.4,
            "carbs_g": 22.0,  # High carbs > 50%
            "fiber_g": 5.0,  # High fiber > 3
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "grain"  # Should be classified as grain

    def test_classify_vegetable_very_low_protein(self):
        """Test classification of vegetable with very low protein (line 169)."""
        record = {
            "name": "spinach",
            "kcal": 23.0,  # Low calories < 100
            "protein_g": 0.5,  # Very low protein percentage
            "fat_g": 0.4,
            "carbs_g": 1.0,  # Low carbs < 50%
            "fiber_g": 2.2,  # High fiber > 2
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "veg"  # Should be classified as vegetable

    def test_classify_fruit_very_low_protein(self):
        """Test classification of fruit with very low protein (line 173)."""
        record = {
            "name": "strawberry",
            "kcal": 32.0,
            "protein_g": 0.7,  # Low protein
            "fat_g": 0.3,
            "carbs_g": 1.0,  # Low carbs < 50%
            "fiber_g": 2.0,
            "sugar_g": 4.9,  # High sugar > 5
            "flags": []
        }
        result = _classify_food_group(record)
        assert result == "other"  # Default classification when conditions don't match
