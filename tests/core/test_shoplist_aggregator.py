# -*- coding: utf-8 -*-
"""Tests for ShoplistEngine v1 aggregator.

RU: Тесты для агрегатора ShoplistEngine v1.
EN: Tests for ShoplistEngine v1 aggregator.

These are anchor tests to keep invariants. No env/time/random dependencies.
RU: Это якорные тесты для сохранения инвариантов. Нет зависимостей от env/time/random.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.shoplist_engine.aggregator import aggregate_specs
from core.shoplist_engine.models import FoodRef, IngredientSpec, Quantity, ShoplistLine, Unit


class TestAggregateSpecsBasic:
    """Test basic aggregation behavior."""

    def test_same_food_id_sums_quantities(self) -> None:
        """Test that specs with same food_id are summed."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("300"), Unit.G),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 1
        assert lines[0].food.food_id == "chicken"
        assert lines[0].qty.value == Decimal("800")
        assert lines[0].qty.unit == Unit.G

    def test_different_food_id_separate_lines(self) -> None:
        """Test that different food_id produce separate lines."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="rice"),
                qty=Quantity(Decimal("200"), Unit.G),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 2
        food_ids = {line.food.food_id for line in lines}
        assert food_ids == {"chicken", "rice"}

    def test_multiple_same_food_aggregates(self) -> None:
        """Test aggregation of multiple occurrences of same food."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("100"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("200"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("50"), Unit.G),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 1
        assert lines[0].qty.value == Decimal("350")  # 100 + 200 + 50

    def test_empty_list_returns_empty(self) -> None:
        """Test that empty input returns empty list."""
        lines = aggregate_specs([])
        assert lines == []
        assert isinstance(lines, list)

    def test_zero_quantity_allowed(self) -> None:
        """Test that zero quantity is allowed and preserved."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="salt"),
                qty=Quantity(Decimal("0"), Unit.G),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 1
        assert lines[0].qty.value == Decimal("0")
        assert lines[0].qty.unit == Unit.G


class TestAggregateSpecsUnits:
    """Test aggregation with different base units."""

    def test_ml_aggregation(self) -> None:
        """Test aggregation of ML units."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="water"),
                qty=Quantity(Decimal("500"), Unit.ML),
            ),
            IngredientSpec(
                food=FoodRef(food_id="water"),
                qty=Quantity(Decimal("300"), Unit.ML),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 1
        assert lines[0].qty.value == Decimal("800")
        assert lines[0].qty.unit == Unit.ML

    def test_pcs_aggregation(self) -> None:
        """Test aggregation of PCS units."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="eggs"),
                qty=Quantity(Decimal("6"), Unit.PCS),
            ),
            IngredientSpec(
                food=FoodRef(food_id="eggs"),
                qty=Quantity(Decimal("4"), Unit.PCS),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 1
        assert lines[0].qty.value == Decimal("10")
        assert lines[0].qty.unit == Unit.PCS

    def test_mixed_base_units_different_foods(self) -> None:
        """Test that different foods can have different base units."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="milk"),
                qty=Quantity(Decimal("1000"), Unit.ML),
            ),
        ]
        # Should work: different foods can have different base units
        lines = aggregate_specs(specs)
        assert len(lines) == 2
        food_units = {line.food.food_id: line.qty.unit for line in lines}
        assert food_units["flour"] == Unit.G
        assert food_units["milk"] == Unit.ML


class TestAggregateSpecsValidation:
    """Test validation and error cases."""

    def test_non_base_unit_raises_value_error(self) -> None:
        """Test that non-base units (KG, L) raise ValueError."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("1"), Unit.KG),
            ),
        ]

        with pytest.raises(ValueError, match=r"base units only"):
            aggregate_specs(specs)

    def test_unit_mismatch_same_food_raises(self) -> None:
        """Test that same food_id with different units raises ValueError."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("1"), Unit.ML),  # Different unit
            ),
        ]

        with pytest.raises(ValueError, match=r"Unit mismatch"):
            aggregate_specs(specs)


class TestAggregateSpecsDeterminism:
    """Test deterministic behavior."""

    def test_order_independent(self) -> None:
        """Test that input order does not affect result."""
        specs1 = [
            IngredientSpec(
                food=FoodRef(food_id="a"),
                qty=Quantity(Decimal("100"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="b"),
                qty=Quantity(Decimal("200"), Unit.G),
            ),
        ]
        specs2 = [
            IngredientSpec(
                food=FoodRef(food_id="b"),
                qty=Quantity(Decimal("200"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="a"),
                qty=Quantity(Decimal("100"), Unit.G),
            ),
        ]
        lines1 = aggregate_specs(specs1)
        lines2 = aggregate_specs(specs2)

        # Results should be identical (sorted by food_id)
        assert len(lines1) == len(lines2) == 2
        assert lines1[0].food.food_id == lines2[0].food.food_id == "a"
        assert lines1[1].food.food_id == lines2[1].food.food_id == "b"
        assert lines1[0].qty.value == lines2[0].qty.value == Decimal("100")
        assert lines1[1].qty.value == lines2[1].qty.value == Decimal("200")

    def test_output_sorted_by_food_id(self) -> None:
        """Test that output is sorted by food_id for determinism."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="zebra"),
                qty=Quantity(Decimal("100"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="apple"),
                qty=Quantity(Decimal("200"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="banana"),
                qty=Quantity(Decimal("300"), Unit.G),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 3
        # Should be sorted alphabetically
        assert lines[0].food.food_id == "apple"
        assert lines[1].food.food_id == "banana"
        assert lines[2].food.food_id == "zebra"


class TestAggregateSpecsEdgeCases:
    """Test edge cases and fractional values."""

    def test_fractional_decimal_values(self) -> None:
        """Test aggregation with fractional Decimal values."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="sugar"),
                qty=Quantity(Decimal("1.5"), Unit.G),
            ),
            IngredientSpec(
                food=FoodRef(food_id="sugar"),
                qty=Quantity(Decimal("2.25"), Unit.G),
            ),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 1
        assert lines[0].qty.value == Decimal("3.75")

    def test_preserves_first_food_ref(self) -> None:
        """Test that first FoodRef is preserved for each food_id."""
        food1 = FoodRef(food_id="chicken")
        food2 = FoodRef(food_id="chicken")  # Same food_id, different instance
        specs = [
            IngredientSpec(food=food1, qty=Quantity(Decimal("100"), Unit.G)),
            IngredientSpec(food=food2, qty=Quantity(Decimal("200"), Unit.G)),
        ]
        lines = aggregate_specs(specs)
        assert len(lines) == 1
        # Should preserve first FoodRef instance
        assert lines[0].food is food1
