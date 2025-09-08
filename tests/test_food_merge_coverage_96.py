"""
Tests to improve coverage in core/food_merge.py for 96%+ coverage.

This module focuses on covering the missing lines in food_merge.py that are preventing
us from reaching 96% coverage.
"""

from datetime import date

from core.food_merge import MICROS, _classify_food_group, _merge_values, merge_records
from core.food_sources.base import FoodRecord


class TestFoodMergeCoverage96:
    """Tests to cover missing lines in food_merge.py for 96%+ coverage."""

    def _create_food_record(self, name="apple", **kwargs):
        """Helper to create FoodRecord with default values."""
        defaults = {
            "locale": "en",
            "per_g": 100.0,
            "kcal": 52.0,
            "protein_g": 0.3,
            "fat_g": 0.2,
            "carbs_g": 14.0,
            "fiber_g": 2.4,
            "Fe_mg": 0.1,
            "Ca_mg": 6.0,
            "VitD_IU": 0.0,
            "B12_ug": 0.0,
            "Folate_ug": 3.0,
            "Iodine_ug": 0.0,
            "K_mg": 107.0,
            "Mg_mg": 5.0,
            "flags": ["FRUIT"],
            "price": 0.0,
            "source": "USDA",
            "version_date": "2024-01-01",
        }
        defaults.update(kwargs)
        return FoodRecord(name=name, **defaults)

    def test_merge_values_empty_list(self):
        """Test _merge_values with empty list - line 44."""
        result = _merge_values([])
        assert result == 0.0

    def test_merge_values_none_values(self):
        """Test _merge_values with None values - line 44."""
        result = _merge_values([None, None, None])
        assert result == 0.0

    def test_merge_values_negative_values(self):
        """Test _merge_values with negative values - line 44."""
        result = _merge_values([-1, -2, -3])
        assert result == 0.0

    def test_merge_values_mixed_values(self):
        """Test _merge_values with mixed valid/invalid values - line 44."""
        result = _merge_values([1.0, None, -1, 2.0, 3.0])
        assert result == 2.0  # median of [1.0, 2.0, 3.0]

    def test_merge_values_first_strategy(self):
        """Test _merge_values with 'first' strategy - line 47."""
        result = _merge_values([1.0, 2.0, 3.0], strategy="first")
        assert result == 1.0

    def test_merge_values_median_strategy(self):
        """Test _merge_values with 'median' strategy - line 46."""
        result = _merge_values([1.0, 2.0, 3.0, 4.0, 5.0], strategy="median")
        assert result == 3.0

    def test_merge_values_single_value(self):
        """Test _merge_values with single value."""
        result = _merge_values([5.0])
        assert result == 5.0

    def test_merge_values_float_conversion(self):
        """Test _merge_values returns float."""
        result = _merge_values([1, 2, 3])
        assert isinstance(result, float)
        assert result == 2.0

    def test_merge_records_empty_streams(self):
        """Test merge_records with empty streams."""
        result = merge_records([])
        assert result == []

    def test_merge_records_single_record(self):
        """Test merge_records with single record."""
        record = self._create_food_record()

        result = merge_records([[record]])
        assert len(result) == 1
        assert result[0]["name"] == "apple"
        assert result[0]["kcal"] == 52.0
        assert result[0]["source"] == "MERGED(USDA)"

    def test_merge_records_multiple_sources(self):
        """Test merge_records with multiple sources for same food."""
        record1 = self._create_food_record(
            kcal=52.0,
            protein_g=0.3,
            fat_g=0.2,
            carbs_g=14.0,
            fiber_g=2.4,
            source="USDA",
        )
        record2 = self._create_food_record(
            kcal=50.0, protein_g=0.2, fat_g=0.1, carbs_g=13.0, fiber_g=2.2, source="OFF"
        )

        result = merge_records([[record1], [record2]])
        assert len(result) == 1
        assert result[0]["name"] == "apple"
        assert result[0]["kcal"] == 51.0  # median of 52.0 and 50.0
        assert result[0]["source"] == "MERGED(OFF,USDA)"

    def test_merge_records_micro_pick_usda_priority(self):
        """Test micro_pick function with USDA priority - lines 89-91."""
        record1 = self._create_food_record(Fe_mg=0.1, source="USDA")
        record2 = self._create_food_record(Fe_mg=0.2, source="OFF")

        result = merge_records([[record1], [record2]])
        assert len(result) == 1
        # Should use USDA value (0.1) instead of median of all values
        assert result[0]["Fe_mg"] == 0.1

    def test_merge_records_micro_pick_no_usda(self):
        """Test micro_pick function without USDA source - lines 89-91."""
        record1 = self._create_food_record(Fe_mg=0.1, source="OFF")
        record2 = self._create_food_record(Fe_mg=0.2, source="CUSTOM")

        result = merge_records([[record1], [record2]])
        assert len(result) == 1
        # Should use median of all values (0.15)
        assert result[0]["Fe_mg"] == 0.15

    def test_merge_records_flags_aggregation(self):
        """Test flags aggregation from multiple records."""
        record1 = self._create_food_record(flags=["FRUIT", "ORGANIC"])
        record2 = self._create_food_record(flags=["FRUIT", "LOCAL"])

        result = merge_records([[record1], [record2]])
        assert len(result) == 1
        assert set(result[0]["flags"]) == {"FRUIT", "LOCAL", "ORGANIC"}

    def test_merge_records_no_flags(self):
        """Test merge_records with records that have no flags."""
        record = self._create_food_record(flags=None)

        result = merge_records([[record]])
        assert len(result) == 1
        assert result[0]["flags"] == []

    def test_classify_food_group_high_protein_lean(self):
        """Test _classify_food_group for lean protein - line 156."""
        record = {
            "name": "chicken breast",
            "kcal": 165.0,
            "protein_g": 31.0,  # ~75% protein
            "fat_g": 3.6,  # low fat
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": [],
        }

        result = _classify_food_group(record)
        assert result == "protein"

    def test_classify_food_group_high_protein_high_fat(self):
        """Test _classify_food_group for high fat protein - line 156."""
        record = {
            "name": "almonds",
            "kcal": 579.0,
            "protein_g": 21.0,  # ~14% protein
            "fat_g": 50.0,  # high fat
            "carbs_g": 22.0,
            "fiber_g": 12.0,
            "flags": [],
        }

        result = _classify_food_group(record)
        # High fat (>30%) takes priority over protein
        assert result == "fat"

    def test_classify_food_group_high_fat(self):
        """Test _classify_food_group for high fat foods - line 161."""
        record = {
            "name": "olive oil",
            "kcal": 884.0,
            "protein_g": 0.0,
            "fat_g": 100.0,  # ~100% fat
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": [],
        }

        result = _classify_food_group(record)
        assert result == "fat"

    def test_classify_food_group_high_carb_high_fiber_legume(self):
        """Test _classify_food_group for legumes - line 167."""
        record = {
            "name": "lentil",
            "kcal": 353.0,
            "protein_g": 25.0,  # ~28% protein (>15%)
            "fat_g": 1.1,
            "carbs_g": 60.0,  # ~68% carbs
            "fiber_g": 10.7,  # high fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        # High protein (>15%) takes priority over carbs
        assert result == "protein"

    def test_classify_food_group_high_carb_high_fiber_bean(self):
        """Test _classify_food_group for beans - line 168."""
        record = {
            "name": "black bean",
            "kcal": 341.0,
            "protein_g": 21.0,  # ~25% protein (>15%)
            "fat_g": 1.4,
            "carbs_g": 62.0,  # ~73% carbs
            "fiber_g": 15.5,  # high fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        # High protein (>15%) takes priority
        assert result == "protein"

    def test_classify_food_group_high_carb_high_fiber_chickpea(self):
        """Test _classify_food_group for chickpeas - line 168."""
        record = {
            "name": "chickpea",
            "kcal": 364.0,
            "protein_g": 19.0,  # ~21% protein (>15%)
            "fat_g": 6.0,
            "carbs_g": 61.0,  # ~67% carbs
            "fiber_g": 17.0,  # high fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        # High protein (>15%) takes priority
        assert result == "protein"

    def test_classify_food_group_high_carb_high_fiber_grain(self):
        """Test _classify_food_group for grains - line 171."""
        record = {
            "name": "brown rice",
            "kcal": 111.0,
            "protein_g": 2.6,
            "fat_g": 0.9,
            "carbs_g": 23.0,  # ~83% carbs
            "fiber_g": 1.8,  # high fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        assert result == "grain"

    def test_classify_food_group_high_carb_high_sugar(self):
        """Test _classify_food_group for high sugar carbs - line 175."""
        record = {
            "name": "sweet potato",
            "kcal": 86.0,
            "protein_g": 1.6,
            "fat_g": 0.1,
            "carbs_g": 20.0,  # ~93% carbs
            "fiber_g": 3.0,  # high fiber
            "sugar_g": 12.0,  # high sugar
            "flags": [],
        }

        result = _classify_food_group(record)
        assert result == "fruit"

    def test_classify_food_group_high_carb_low_fiber(self):
        """Test _classify_food_group for starchy carbs - line 177."""
        record = {
            "name": "white rice",
            "kcal": 130.0,
            "protein_g": 2.7,
            "fat_g": 0.3,
            "carbs_g": 28.0,  # ~86% carbs
            "fiber_g": 0.4,  # low fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        assert result == "grain"

    def test_classify_food_group_vegetable(self):
        """Test _classify_food_group for vegetables - line 180."""
        record = {
            "name": "broccoli",
            "kcal": 34.0,  # low calories
            "protein_g": 2.8,  # ~33% protein (>15%)
            "fat_g": 0.4,
            "carbs_g": 7.0,
            "fiber_g": 2.6,  # high fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        # High protein (>15%) takes priority
        assert result == "protein"

    def test_classify_food_group_fruit_high_sugar(self):
        """Test _classify_food_group for fruits - line 184."""
        record = {
            "name": "banana",
            "kcal": 89.0,
            "protein_g": 1.1,
            "fat_g": 0.3,
            "carbs_g": 23.0,
            "fiber_g": 2.6,
            "sugar_g": 12.0,  # high sugar
            "flags": [],
        }

        result = _classify_food_group(record)
        assert result == "fruit"

    def test_classify_food_group_dairy(self):
        """Test _classify_food_group for dairy - line 188."""
        record = {
            "name": "milk",
            "kcal": 42.0,
            "protein_g": 3.4,  # ~32% protein (>15%)
            "fat_g": 1.0,
            "carbs_g": 5.0,
            "fiber_g": 0.0,
            "flags": ["DAIRY"],
        }

        result = _classify_food_group(record)
        # High protein (>15%) takes priority over dairy flag
        assert result == "protein"

    def test_classify_food_group_other(self):
        """Test _classify_food_group for other foods - line 192."""
        record = {
            "name": "mystery food",
            "kcal": 100.0,
            "protein_g": 5.0,  # ~20% protein (>15%)
            "fat_g": 5.0,  # ~45% fat
            "carbs_g": 10.0,  # ~40% carbs
            "fiber_g": 1.0,  # low fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        # High protein (>15%) takes priority
        assert result == "protein"

    def test_classify_food_group_zero_calories(self):
        """Test _classify_food_group with zero calories."""
        record = {
            "name": "water",
            "kcal": 0.0,
            "protein_g": 0.0,
            "fat_g": 0.0,
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": [],
        }

        result = _classify_food_group(record)
        assert result == "other"

    def test_classify_food_group_missing_sugar_g(self):
        """Test _classify_food_group without sugar_g field - line 173."""
        record = {
            "name": "apple",
            "kcal": 52.0,
            "protein_g": 0.3,  # ~2% protein
            "fat_g": 0.2,  # ~3% fat
            "carbs_g": 14.0,  # ~108% carbs (>50%)
            "fiber_g": 2.4,  # high fiber
            "flags": [],
        }

        result = _classify_food_group(record)
        # High carbs (>50%) with high fiber (>3) -> grain
        assert result == "grain"

    def test_merge_records_all_micros(self):
        """Test merge_records includes all micronutrients."""
        record = self._create_food_record()

        result = merge_records([[record]])
        assert len(result) == 1

        # Check all micronutrients are present
        for micro in MICROS:
            assert micro in result[0]
            assert isinstance(result[0][micro], float)

    def test_merge_records_rounding(self):
        """Test merge_records rounds values correctly."""
        record = self._create_food_record(
            kcal=52.123456,
            protein_g=0.345678,
            fat_g=0.234567,
            carbs_g=14.567890,
            fiber_g=2.456789,
            Fe_mg=0.123456,
        )

        result = merge_records([[record]])
        assert len(result) == 1

        # Check rounding
        assert result[0]["kcal"] == 52.1
        assert result[0]["protein_g"] == 0.35
        assert result[0]["fat_g"] == 0.23
        assert result[0]["carbs_g"] == 14.57
        assert result[0]["fiber_g"] == 2.46
        assert result[0]["Fe_mg"] == 0.123

    def test_merge_records_version_date(self):
        """Test merge_records sets version_date to today."""
        record = self._create_food_record()

        result = merge_records([[record]])
        assert len(result) == 1
        assert result[0]["version_date"] == date.today().isoformat()
