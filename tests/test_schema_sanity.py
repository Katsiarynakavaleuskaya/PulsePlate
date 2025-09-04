"""
Schema Sanity Tests

RU: Тесты валидности схемы.
EN: Schema sanity tests.
"""

import os

import pytest

from core.food_merge import merge_records
from core.food_sources.base import FoodRecord


def test_non_negative_nutrients():
    """Test that all nutrient values are non-negative."""
    record = FoodRecord(
        name="test_food",
        locale="en",
        per_g=100.0,
        kcal=100,
        protein_g=10,
        fat_g=5,
        carbs_g=20,
        fiber_g=3,
        Fe_mg=1.0,
        Ca_mg=50,
        VitD_IU=100,
        B12_ug=0.5,
        Folate_ug=50,
        Iodine_ug=10,
        K_mg=200,
        Mg_mg=30,
        flags=[],
        price=1.5,
        source="TEST",
        version_date="2025-01-01"
    )

    # All values should be non-negative
    assert record.kcal >= 0
    assert record.protein_g >= 0
    assert record.fat_g >= 0
    assert record.carbs_g >= 0
    assert record.fiber_g >= 0
    assert record.Fe_mg >= 0
    assert record.Ca_mg >= 0
    assert record.VitD_IU >= 0
    assert record.B12_ug >= 0
    assert record.Folate_ug >= 0
    assert record.Iodine_ug >= 0
    assert record.K_mg >= 0
    assert record.Mg_mg >= 0
    assert record.price >= 0


def test_kcal_calculation_approximation():
    """Test that kcal is approximately 4p + 4c + 9f (±15%)."""
    record = FoodRecord(
        name="test_food",
        locale="en",
        per_g=100.0,
        kcal=165,  # Actual value
        protein_g=31,
        fat_g=3.6,
        carbs_g=0,
        fiber_g=0,
        Fe_mg=0.7,
        Ca_mg=15,
        VitD_IU=0.7,
        B12_ug=0.3,
        Folate_ug=6,
        Iodine_ug=7,
        K_mg=256,
        Mg_mg=27,
        flags=[],
        price=0.0,
        source="TEST",
        version_date="2025-01-01"
    )

    # Calculate expected kcal from macronutrients
    expected_kcal = (record.protein_g * 4) + (record.carbs_g * 4) + (record.fat_g * 9)

    # Allow ±15% tolerance
    tolerance = 0.15
    lower_bound = expected_kcal * (1 - tolerance)
    upper_bound = expected_kcal * (1 + tolerance)

    assert lower_bound <= record.kcal <= upper_bound


def test_per_g_consistency():
    """Test that per_g is 100.0 for all records."""
    record = FoodRecord(
        name="test_food",
        locale="en",
        per_g=100.0,
        kcal=100,
        protein_g=10,
        fat_g=5,
        carbs_g=20,
        fiber_g=3,
        Fe_mg=1.0,
        Ca_mg=50,
        VitD_IU=100,
        B12_ug=0.5,
        Folate_ug=50,
        Iodine_ug=10,
        K_mg=200,
        Mg_mg=30,
        flags=[],
        price=1.5,
        source="TEST",
        version_date="2025-01-01"
    )

    assert record.per_g == 100.0


def test_merged_schema_sanity():
    """Test that merged records follow schema requirements."""
    # Create test records
    records = [
        FoodRecord(
            name="chicken_breast",
            locale="en",
            per_g=100.0,
            kcal=165,
            protein_g=31,
            fat_g=3.6,
            carbs_g=0,
            fiber_g=0,
            Fe_mg=0.7,
            Ca_mg=15,
            VitD_IU=0.7,
            B12_ug=0.3,
            Folate_ug=6,
            Iodine_ug=7,
            K_mg=256,
            Mg_mg=27,
            flags=[],
            price=0.0,
            source="USDA",
            version_date="2025-01-01"
        )
    ]

    # Merge records
    merged = merge_records([records])

    # Should have exactly one record
    assert len(merged) == 1

    record = merged[0]

    # Check schema requirements
    assert "name" in record
    assert "group" in record
    assert "per_g" in record
    assert "kcal" in record
    assert "protein_g" in record
    assert "fat_g" in record
    assert "carbs_g" in record
    assert "fiber_g" in record
    assert "Fe_mg" in record
    assert "Ca_mg" in record
    assert "VitD_IU" in record
    assert "B12_ug" in record
    assert "Folate_ug" in record
    assert "Iodine_ug" in record
    assert "K_mg" in record
    assert "Mg_mg" in record
    assert "flags" in record
    assert "price" in record
    assert "source" in record
    assert "version_date" in record

    # Check data types
    assert isinstance(record["name"], str)
    assert isinstance(record["group"], str)
    assert isinstance(record["per_g"], float)
    assert isinstance(record["kcal"], float)
    assert isinstance(record["protein_g"], float)
    assert isinstance(record["fat_g"], float)
    assert isinstance(record["carbs_g"], float)
    assert isinstance(record["fiber_g"], float)
    assert isinstance(record["Fe_mg"], float)
    assert isinstance(record["Ca_mg"], float)
    assert isinstance(record["VitD_IU"], float)
    assert isinstance(record["B12_ug"], float)
    assert isinstance(record["Folate_ug"], float)
    assert isinstance(record["Iodine_ug"], float)
    assert isinstance(record["K_mg"], float)
    assert isinstance(record["Mg_mg"], float)
    assert isinstance(record["flags"], list)
    assert isinstance(record["price"], float)
    assert isinstance(record["source"], str)
    assert isinstance(record["version_date"], str)

    # Check non-negative values
    assert record["per_g"] >= 0
    assert record["kcal"] >= 0
    assert record["protein_g"] >= 0
    assert record["fat_g"] >= 0
    assert record["carbs_g"] >= 0
    assert record["fiber_g"] >= 0
    assert record["Fe_mg"] >= 0
    assert record["Ca_mg"] >= 0
    assert record["VitD_IU"] >= 0
    assert record["B12_ug"] >= 0
    assert record["Folate_ug"] >= 0
    assert record["Iodine_ug"] >= 0
    assert record["K_mg"] >= 0
    assert record["Mg_mg"] >= 0
    assert record["price"] >= 0


if __name__ == "__main__":
    pytest.main([__file__])
