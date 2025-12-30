# -*- coding: utf-8 -*-
"""Tests for ShoplistEngine v1 normalizer.

RU: Тесты для нормализатора ShoplistEngine v1.
EN: Tests for ShoplistEngine v1 normalizer.

These are anchor tests to keep invariants. No env/time/random dependencies.
RU: Это якорные тесты для сохранения инвариантов. Нет зависимостей от env/time/random.
"""

from __future__ import annotations

from decimal import Decimal

from core.shoplist_engine.models import FoodForm, FoodRef, IngredientSpec, Quantity, Unit
from core.shoplist_engine.normalizer import (
    normalize_ingredient,
    normalize_quantity,
    normalize_specs,
)


class TestNormalizeQuantity:
    """Test normalize_quantity function."""

    def test_normalize_quantity_kg_to_g(self) -> None:
        """Test conversion from KG to G."""
        qty = Quantity(value=Decimal("1.5"), unit=Unit.KG)
        out = normalize_quantity(qty)
        assert out.unit == Unit.G
        assert out.value == Decimal("1500")

    def test_normalize_quantity_l_to_ml(self) -> None:
        """Test conversion from L to ML."""
        qty = Quantity(value=Decimal("2"), unit=Unit.L)
        out = normalize_quantity(qty)
        assert out.unit == Unit.ML
        assert out.value == Decimal("2000")

    def test_normalize_quantity_base_unit_noop(self) -> None:
        """Test that base units are returned unchanged."""
        qty = Quantity(value=Decimal("250"), unit=Unit.G)
        out = normalize_quantity(qty)
        assert out == qty
        assert out is qty  # Same instance for base units

    def test_normalize_quantity_pcs_noop(self) -> None:
        """Test that PCS unit is returned unchanged."""
        qty = Quantity(value=Decimal("10"), unit=Unit.PCS)
        out = normalize_quantity(qty)
        assert out == qty
        assert out is qty

    def test_normalize_quantity_zero_allowed(self) -> None:
        """Test that zero quantity is allowed and preserved."""
        qty = Quantity(value=Decimal("0"), unit=Unit.KG)
        out = normalize_quantity(qty)
        assert out.unit == Unit.G
        assert out.value == Decimal("0")

    def test_normalize_quantity_fractional_kg(self) -> None:
        """Test conversion of fractional KG values."""
        qty = Quantity(value=Decimal("0.5"), unit=Unit.KG)
        out = normalize_quantity(qty)
        assert out.unit == Unit.G
        assert out.value == Decimal("500")

    def test_normalize_quantity_fractional_l(self) -> None:
        """Test conversion of fractional L values."""
        qty = Quantity(value=Decimal("0.25"), unit=Unit.L)
        out = normalize_quantity(qty)
        assert out.unit == Unit.ML
        assert out.value == Decimal("250")


class TestNormalizeIngredient:
    """Test normalize_ingredient function."""

    def test_normalize_ingredient_returns_same_instance_if_no_change(self) -> None:
        """Test that unchanged spec returns same instance."""
        spec = IngredientSpec(
            food=FoodRef(food_id="food:banana"), qty=Quantity(Decimal("10"), Unit.G)
        )
        out = normalize_ingredient(spec)
        assert out is spec

    def test_normalize_ingredient_returns_new_instance_if_changed(self) -> None:
        """Test that changed spec returns new instance."""
        spec = IngredientSpec(
            food=FoodRef(food_id="food:banana"), qty=Quantity(Decimal("1"), Unit.KG)
        )
        out = normalize_ingredient(spec)
        assert out is not spec
        assert out.qty.unit == Unit.G
        assert out.qty.value == Decimal("1000")
        assert out.food == spec.food  # Other fields unchanged

    def test_normalize_ingredient_preserves_other_fields(self) -> None:
        """Test that other IngredientSpec fields are preserved."""
        spec = IngredientSpec(
            food=FoodRef(food_id="food:chicken"),
            qty=Quantity(Decimal("2"), Unit.KG),
            form=FoodForm.RAW,
            notes="boneless",
        )
        out = normalize_ingredient(spec)
        assert out.food == spec.food
        assert out.form == spec.form
        assert out.notes == spec.notes
        assert out.qty.unit == Unit.G
        assert out.qty.value == Decimal("2000")


class TestNormalizeSpecs:
    """Test normalize_specs function."""

    def test_normalize_specs_batch(self) -> None:
        """Test batch normalization of multiple specs."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="food:a"),
                qty=Quantity(Decimal("1"), Unit.KG),
            ),
            IngredientSpec(
                food=FoodRef(food_id="food:b"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
        ]
        out = normalize_specs(specs)
        assert out[0].qty.unit == Unit.G
        assert out[0].qty.value == Decimal("1000")
        assert out[1] is specs[1]  # Unchanged instance

    def test_normalize_specs_empty_list(self) -> None:
        """Test that empty list returns empty list."""
        out = normalize_specs([])
        assert out == []
        assert isinstance(out, list)

    def test_normalize_specs_mixed_units(self) -> None:
        """Test normalization of specs with mixed units."""
        specs = [
            IngredientSpec(
                food=FoodRef(food_id="food:water"),
                qty=Quantity(Decimal("1.5"), Unit.L),
            ),
            IngredientSpec(
                food=FoodRef(food_id="food:flour"),
                qty=Quantity(Decimal("2"), Unit.KG),
            ),
            IngredientSpec(
                food=FoodRef(food_id="food:eggs"),
                qty=Quantity(Decimal("6"), Unit.PCS),
            ),
        ]
        out = normalize_specs(specs)
        assert out[0].qty.unit == Unit.ML
        assert out[0].qty.value == Decimal("1500")
        assert out[1].qty.unit == Unit.G
        assert out[1].qty.value == Decimal("2000")
        assert out[2].qty.unit == Unit.PCS
        assert out[2].qty.value == Decimal("6")
        assert out[2] is specs[2]  # PCS unchanged
