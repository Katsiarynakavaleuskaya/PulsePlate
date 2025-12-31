# -*- coding: utf-8 -*-
"""Tests for core.shoplist_engine.engine module.

RU: Тесты для модуля engine (orchestrator пайплайна).
EN: Tests for engine module (pipeline orchestrator).

This test suite ensures coverage for edge cases:
- packaging_rules=None (line 86)
"""

from __future__ import annotations

from decimal import Decimal

from core.shoplist_engine.engine import ShoplistEngine, generate_shoplist
from core.shoplist_engine.models import FoodForm, FoodRef, IngredientSpec, Quantity, Unit


def test_engine_generate_with_none_packaging_rules() -> None:
    """ShoplistEngine.generate handles packaging_rules=None (coverage for line 86)."""
    specs = [
        IngredientSpec(
            food=FoodRef(food_id="chicken"),
            qty=Quantity(Decimal("500"), Unit.G),
            form=FoodForm.RAW,
        ),
    ]
    result = ShoplistEngine.generate(specs, packaging_rules=None)
    # With None rules, all items should be unpacked
    assert len(result.packed) == 0
    assert len(result.unpacked) == 1
    assert result.unpacked[0].food.food_id == "chicken"


def test_generate_shoplist_with_none_packaging_rules() -> None:
    """generate_shoplist handles packaging_rules=None (coverage for line 86)."""
    specs = [
        IngredientSpec(
            food=FoodRef(food_id="rice"),
            qty=Quantity(Decimal("1000"), Unit.G),
            form=FoodForm.RAW,
        ),
    ]
    result = generate_shoplist(specs, packaging_rules=None)
    # With None rules, all items should be unpacked
    assert len(result.packed) == 0
    assert len(result.unpacked) == 1
    assert result.unpacked[0].food.food_id == "rice"
