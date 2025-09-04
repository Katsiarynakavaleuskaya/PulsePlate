"""
Basic Merge Tests

RU: Базовые тесты мерджа.
EN: Basic merge tests.
"""

import os

import pytest

from core.food_merge import merge_records
from core.food_sources.base import FoodRecord


def test_merge_same_canonical_no_duplicates():
    """Test that same canonical name from 2 sources produces 1 merged record."""
    # Create test records with same canonical name from different sources
    records1 = [
        FoodRecord(
            name="spinach_raw",
            locale="en",
            per_g=100.0,
            kcal=23,
            protein_g=2.9,
            fat_g=0.4,
            carbs_g=3.6,
            fiber_g=2.2,
            Fe_mg=2.7,
            Ca_mg=99,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=194,
            Iodine_ug=20,
            K_mg=558,
            Mg_mg=79,
            flags=[],
            price=0.0,
            source="USDA",
            version_date="2025-01-01"
        )
    ]

    records2 = [
        FoodRecord(
            name="spinach_raw",
            locale="en",
            per_g=100.0,
            kcal=25,
            protein_g=3.0,
            fat_g=0.5,
            carbs_g=3.5,
            fiber_g=2.0,
            Fe_mg=2.5,
            Ca_mg=100,
            VitD_IU=0,
            B12_ug=0,
            Folate_ug=200,
            Iodine_ug=25,
            K_mg=550,
            Mg_mg=80,
            flags=["GF", "VEG"],
            price=0.0,
            source="OFF",
            version_date="2025-01-01"
        )
    ]

    # Merge records
    merged = merge_records([records1, records2])

    # Should have exactly one record
    assert len(merged) == 1

    # Check that it's the merged record
    record = merged[0]
    assert record["name"] == "spinach_raw"
    assert "USDA" in record["source"]
    assert "OFF" in record["source"]

    # Check that values are merged (median of the two values)
    # For kcal: median of [23, 25] = 24
    assert record["kcal"] == 24.0

    # For protein: median of [2.9, 3.0] = 2.95
    assert record["protein_g"] == 2.95


def test_micro_prioritization_usda():
    """Test that micronutrients are taken from USDA when available."""
    # Create USDA record with specific micro values
    usda_record = FoodRecord(
        name="chicken_breast",
        locale="en",
        per_g=100.0,
        kcal=165,
        protein_g=31,
        fat_g=3.6,
        carbs_g=0,
        fiber_g=0,
        Fe_mg=0.7,      # USDA value
        Ca_mg=15,       # USDA value
        VitD_IU=0.7,    # USDA value
        B12_ug=0.3,     # USDA value
        Folate_ug=6,    # USDA value
        Iodine_ug=7,    # USDA value
        K_mg=256,       # USDA value
        Mg_mg=27,       # USDA value
        flags=[],
        price=0.0,
        source="USDA",
        version_date="2025-01-01"
    )

    # Create OFF record with different micro values
    off_record = FoodRecord(
        name="chicken_breast",
        locale="en",
        per_g=100.0,
        kcal=165,
        protein_g=31,
        fat_g=3.6,
        carbs_g=0,
        fiber_g=0,
        Fe_mg=1.0,      # Different OFF value
        Ca_mg=20,       # Different OFF value
        VitD_IU=1.0,    # Different OFF value
        B12_ug=0.5,     # Different OFF value
        Folate_ug=10,   # Different OFF value
        Iodine_ug=10,   # Different OFF value
        K_mg=300,       # Different OFF value
        Mg_mg=30,       # Different OFF value
        flags=[],
        price=0.0,
        source="OFF",
        version_date="2025-01-01"
    )

    # Merge records
    merged = merge_records([[usda_record], [off_record]])

    # Should have exactly one record
    assert len(merged) == 1

    # Check that micro values come from USDA (when USDA is present)
    record = merged[0]
    assert record["Fe_mg"] == 0.7    # USDA value
    assert record["Ca_mg"] == 15.0   # USDA value
    assert record["VitD_IU"] == 0.7  # USDA value
    assert record["B12_ug"] == 0.3   # USDA value
    assert record["Folate_ug"] == 6.0 # USDA value
    assert record["Iodine_ug"] == 7.0 # USDA value
    assert record["K_mg"] == 256.0   # USDA value
    assert record["Mg_mg"] == 27.0   # USDA value


def test_macro_median_merge():
    """Test that macronutrients are merged using median when values are close."""
    # Create records with close values
    record1 = FoodRecord(
        name="tofu",
        locale="en",
        per_g=100.0,
        kcal=76,
        protein_g=8,
        fat_g=4.8,
        carbs_g=1.9,
        fiber_g=0.3,
        Fe_mg=2.7,
        Ca_mg=350,
        VitD_IU=0,
        B12_ug=0,
        Folate_ug=25,
        Iodine_ug=0,
        K_mg=121,
        Mg_mg=35,
        flags=["VEG"],
        price=0.0,
        source="USDA",
        version_date="2025-01-01"
    )

    record2 = FoodRecord(
        name="tofu",
        locale="en",
        per_g=100.0,
        kcal=78,
        protein_g=8.2,
        fat_g=5.0,
        carbs_g=2.0,
        fiber_g=0.4,
        Fe_mg=2.5,
        Ca_mg=340,
        VitD_IU=0,
        B12_ug=0,
        Folate_ug=24,
        Iodine_ug=0,
        K_mg=125,
        Mg_mg=36,
        flags=["GF"],
        price=0.0,
        source="OFF",
        version_date="2025-01-01"
    )

    # Merge records
    merged = merge_records([[record1], [record2]])

    # Should have exactly one record
    assert len(merged) == 1

    # Check that macro values are merged using median
    record = merged[0]
    # For kcal: median of [76, 78] = 77
    assert record["kcal"] == 77.0

    # For protein: median of [8, 8.2] = 8.1
    assert record["protein_g"] == 8.1


if __name__ == "__main__":
    pytest.main([__file__])
