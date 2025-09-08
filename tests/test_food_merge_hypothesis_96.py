"""
Hypothesis property-based tests for core/food_merge.py to maximize coverage and optimization.

This module uses Hypothesis to generate diverse test cases and find edge cases
that might be missed by traditional unit tests.
"""

import pytest
from hypothesis import given, strategies as st
from datetime import date
from collections import defaultdict

from core.food_merge import (
    _merge_values,
    merge_records,
    _classify_food_group,
    MICROS
)
from core.food_sources.base import FoodRecord


class TestFoodMergeHypothesis96:
    """Hypothesis property-based tests for food_merge.py."""

    def _create_food_record(self, name="test_food", **kwargs):
        """Helper to create FoodRecord with default values."""
        defaults = {
            "locale": "en",
            "per_g": 100.0,
            "kcal": 100.0,
            "protein_g": 10.0,
            "fat_g": 5.0,
            "carbs_g": 15.0,
            "fiber_g": 2.0,
            "Fe_mg": 1.0,
            "Ca_mg": 50.0,
            "VitD_IU": 10.0,
            "B12_ug": 1.0,
            "Folate_ug": 20.0,
            "Iodine_ug": 5.0,
            "K_mg": 200.0,
            "Mg_mg": 25.0,
            "flags": [],
            "price": 1.0,
            "source": "TEST",
            "version_date": "2024-01-01"
        }
        defaults.update(kwargs)
        return FoodRecord(name=name, **defaults)

    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=0, max_size=10))
    def test_merge_values_property_based(self, values):
        """Property-based test for _merge_values function."""
        result = _merge_values(values)
        
        # Properties that should always hold
        assert isinstance(result, float)
        assert result >= 0.0
        
        # If all values are valid, result should be in range
        valid_values = [v for v in values if v is not None and v >= 0]
        if valid_values:
            assert min(valid_values) <= result <= max(valid_values)
        else:
            assert result == 0.0

    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=1, max_size=5))
    def test_merge_values_median_property(self, values):
        """Test median strategy property."""
        result = _merge_values(values, strategy="median")
        
        # For odd number of values, median should be exact
        if len(values) % 2 == 1:
            sorted_values = sorted(values)
            expected_median = sorted_values[len(values) // 2]
            assert result == expected_median

    @given(st.lists(st.floats(min_value=0, max_value=1000), min_size=1, max_size=5))
    def test_merge_values_first_property(self, values):
        """Test first strategy property."""
        result = _merge_values(values, strategy="first")
        
        # Should return the first valid value
        valid_values = [v for v in values if v is not None and v >= 0]
        if valid_values:
            assert result == valid_values[0]

    @given(
        st.lists(st.floats(min_value=0, max_value=1000), min_size=0, max_size=5),
        st.lists(st.floats(min_value=0, max_value=1000), min_size=0, max_size=5)
    )
    def test_merge_values_consistency(self, values1, values2):
        """Test consistency of merge_values function."""
        result1 = _merge_values(values1)
        result2 = _merge_values(values2)
        
        # If inputs are the same, results should be the same
        if values1 == values2:
            assert result1 == result2

    @given(
        st.text(min_size=1, max_size=20),
        st.floats(min_value=0, max_value=1000),
        st.floats(min_value=0, max_value=1000),
        st.floats(min_value=0, max_value=1000),
        st.floats(min_value=0, max_value=1000),
        st.floats(min_value=0, max_value=1000)
    )
    def test_classify_food_group_property_based(self, name, kcal, protein_g, fat_g, carbs_g, fiber_g):
        """Property-based test for _classify_food_group function."""
        record = {
            "name": name,
            "kcal": kcal,
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carbs_g": carbs_g,
            "fiber_g": fiber_g,
            "flags": []
        }
        
        result = _classify_food_group(record)
        
        # Properties that should always hold
        assert isinstance(result, str)
        assert result in ["protein", "fat", "grain", "legume", "fruit", "veg", "dairy", "other"]
        
        # If kcal is 0, should return "other" (unless high fiber makes it "veg")
        if kcal == 0:
            if fiber_g > 2:
                assert result == "veg"  # High fiber with 0 calories -> veg
            else:
                assert result == "other"

    @given(
        st.floats(min_value=10, max_value=1000),  # Avoid very low kcal values
        st.floats(min_value=5, max_value=100),    # Ensure meaningful protein
        st.floats(min_value=0, max_value=20),     # Low fat to avoid conflicts
        st.floats(min_value=0, max_value=50)      # Low carbs to avoid conflicts
    )
    def test_classify_food_group_high_protein(self, kcal, protein_g, fat_g, carbs_g):
        """Test high protein classification property."""
        if kcal > 0 and protein_g > 0:
            protein_pct = (protein_g * 4 / kcal) * 100
            
            record = {
                "name": "test_protein",
                "kcal": kcal,
                "protein_g": protein_g,
                "fat_g": fat_g,
                "carbs_g": carbs_g,
                "fiber_g": 0.0,
                "flags": []
            }
            
            result = _classify_food_group(record)
            
            # If protein percentage > 15%, should be classified as protein
            if protein_pct > 15:
                assert result == "protein"

    def test_classify_food_group_high_fat_simple(self):
        """Test high fat classification with simple case."""
        record = {
            "name": "olive oil",
            "kcal": 884.0,
            "protein_g": 0.0,
            "fat_g": 100.0,     # ~100% fat
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": []
        }
        
        result = _classify_food_group(record)
        assert result == "fat"

    def test_classify_food_group_high_carbs_simple(self):
        """Test high carbs classification with simple case."""
        record = {
            "name": "white rice",
            "kcal": 130.0,
            "protein_g": 2.7,
            "fat_g": 0.3,
            "carbs_g": 28.0,    # ~86% carbs
            "fiber_g": 0.4,     # low fiber
            "flags": []
        }
        
        result = _classify_food_group(record)
        assert result == "grain"

    @given(st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=5))
    def test_classify_food_group_dairy_flags(self, flags):
        """Test dairy classification with various flags."""
        record = {
            "name": "test_dairy",
            "kcal": 100.0,
            "protein_g": 5.0,
            "fat_g": 5.0,
            "carbs_g": 10.0,
            "fiber_g": 0.0,
            "flags": flags
        }
        
        result = _classify_food_group(record)
        
        # If has DAIRY flag, should be classified as dairy (unless high protein)
        if any("DAIRY" in flag for flag in flags):
            protein_pct = (record["protein_g"] * 4 / record["kcal"]) * 100
            if protein_pct <= 15:  # Not high protein
                assert result == "dairy"

    @given(
        st.text(min_size=1, max_size=20),
        st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=3)
    )
    def test_classify_food_group_legume_names(self, name, flags):
        """Test legume classification with various names."""
        record = {
            "name": name,
            "kcal": 300.0,
            "protein_g": 20.0,  # High protein
            "fat_g": 2.0,
            "carbs_g": 50.0,    # High carbs
            "fiber_g": 10.0,    # High fiber
            "flags": flags
        }
        
        result = _classify_food_group(record)
        
        # If name contains legume keywords, should be classified as legume
        legume_keywords = ["lentil", "bean", "chickpea"]
        if any(keyword in name.lower() for keyword in legume_keywords):
            # But high protein takes priority
            protein_pct = (record["protein_g"] * 4 / record["kcal"]) * 100
            if protein_pct > 15:
                assert result == "protein"  # High protein takes priority
            else:
                assert result == "legume"

    @given(
        st.lists(
            st.builds(
                lambda name, kcal, protein_g, fat_g, carbs_g, fiber_g, source, flags: 
                FoodRecord(
                    name=name,
                    locale="en",
                    per_g=100.0,
                    kcal=kcal,
                    protein_g=protein_g,
                    fat_g=fat_g,
                    carbs_g=carbs_g,
                    fiber_g=fiber_g,
                    Fe_mg=1.0,
                    Ca_mg=50.0,
                    VitD_IU=10.0,
                    B12_ug=1.0,
                    Folate_ug=20.0,
                    Iodine_ug=5.0,
                    K_mg=200.0,
                    Mg_mg=25.0,
                    flags=flags,
                    price=1.0,
                    source=source,
                    version_date="2024-01-01"
                ),
                name=st.text(min_size=1, max_size=20),
                kcal=st.floats(min_value=0, max_value=1000),
                protein_g=st.floats(min_value=0, max_value=100),
                fat_g=st.floats(min_value=0, max_value=100),
                carbs_g=st.floats(min_value=0, max_value=100),
                fiber_g=st.floats(min_value=0, max_value=50),
                source=st.sampled_from(["USDA", "OFF", "CUSTOM"]),
                flags=st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=3)
            ),
            min_size=0,
            max_size=5
        )
    )
    def test_merge_records_property_based(self, records):
        """Property-based test for merge_records function."""
        if not records:
            result = merge_records([])
            assert result == []
            return
        
        # Group records by name
        streams = [[record] for record in records]
        result = merge_records(streams)
        
        # Properties that should always hold
        assert isinstance(result, list)
        assert len(result) <= len(records)  # Should merge records with same name
        
        for merged_record in result:
            assert isinstance(merged_record, dict)
            assert "name" in merged_record
            assert "kcal" in merged_record
            assert "protein_g" in merged_record
            assert "fat_g" in merged_record
            assert "carbs_g" in merged_record
            assert "fiber_g" in merged_record
            assert "group" in merged_record
            assert "source" in merged_record
            assert "version_date" in merged_record
            
            # All micronutrients should be present
            for micro in MICROS:
                assert micro in merged_record
                assert isinstance(merged_record[micro], float)
                assert merged_record[micro] >= 0
            
            # Values should be reasonable
            assert merged_record["kcal"] >= 0
            assert merged_record["protein_g"] >= 0
            assert merged_record["fat_g"] >= 0
            assert merged_record["carbs_g"] >= 0
            assert merged_record["fiber_g"] >= 0
            
            # Group should be valid
            assert merged_record["group"] in [
                "protein", "fat", "grain", "legume", "fruit", "veg", "dairy", "other"
            ]
            
            # Source should contain merged sources
            assert "MERGED(" in merged_record["source"]
            
            # Version date should be today
            assert merged_record["version_date"] == date.today().isoformat()

    @given(
        st.lists(
            st.builds(
                lambda name, source, flags: 
                FoodRecord(
                    name=name,
                    locale="en",
                    per_g=100.0,
                    kcal=100.0,
                    protein_g=10.0,
                    fat_g=5.0,
                    carbs_g=15.0,
                    fiber_g=2.0,
                    Fe_mg=1.0,
                    Ca_mg=50.0,
                    VitD_IU=10.0,
                    B12_ug=1.0,
                    Folate_ug=20.0,
                    Iodine_ug=5.0,
                    K_mg=200.0,
                    Mg_mg=25.0,
                    flags=flags,
                    price=1.0,
                    source=source,
                    version_date="2024-01-01"
                ),
                name=st.text(min_size=1, max_size=20),
                source=st.sampled_from(["USDA", "OFF", "CUSTOM"]),
                flags=st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=3)
            ),
            min_size=1,
            max_size=3
        )
    )
    def test_merge_records_usda_priority(self, records):
        """Test USDA priority in micronutrient selection."""
        # Set all records to have same name so they get merged
        for record in records:
            record.name = "test_food"
        
        streams = [[record] for record in records]
        result = merge_records(streams)
        
        assert len(result) == 1
        merged_record = result[0]
        
        # If any record has USDA source, micronutrients should prioritize USDA
        usda_records = [r for r in records if r.source == "USDA"]
        if usda_records:
            # Check that micronutrients match USDA values (or median of USDA values)
            for micro in MICROS:
                usda_values = [getattr(r, micro) for r in usda_records]
                usda_values = [v for v in usda_values if v is not None and v >= 0]
                if usda_values:
                    # Should use USDA values, not all values
                    assert merged_record[micro] in usda_values

    @given(
        st.lists(
            st.builds(
                lambda name, flags: 
                FoodRecord(
                    name=name,
                    locale="en",
                    per_g=100.0,
                    kcal=100.0,
                    protein_g=10.0,
                    fat_g=5.0,
                    carbs_g=15.0,
                    fiber_g=2.0,
                    Fe_mg=1.0,
                    Ca_mg=50.0,
                    VitD_IU=10.0,
                    B12_ug=1.0,
                    Folate_ug=20.0,
                    Iodine_ug=5.0,
                    K_mg=200.0,
                    Mg_mg=25.0,
                    flags=flags,
                    price=1.0,
                    source="TEST",
                    version_date="2024-01-01"
                ),
                name=st.text(min_size=1, max_size=20),
                flags=st.lists(st.text(min_size=1, max_size=10), min_size=0, max_size=5)
            ),
            min_size=1,
            max_size=3
        )
    )
    def test_merge_records_flags_aggregation(self, records):
        """Test flags aggregation property."""
        # Set all records to have same name so they get merged
        for record in records:
            record.name = "test_food"
        
        streams = [[record] for record in records]
        result = merge_records(streams)
        
        assert len(result) == 1
        merged_record = result[0]
        
        # All flags from all records should be present
        all_flags = set()
        for record in records:
            if record.flags:
                all_flags.update(record.flags)
        
        assert set(merged_record["flags"]) == all_flags

    def test_classify_food_group_edge_cases_simple(self):
        """Test edge cases in food group classification with simple cases."""
        # Test zero calories
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
        
        # Test high protein
        record = {
            "name": "chicken breast",
            "kcal": 165.0,
            "protein_g": 31.0,  # ~75% protein
            "fat_g": 3.6,       # low fat
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "flags": []
        }
        
        result = _classify_food_group(record)
        assert result == "protein"
