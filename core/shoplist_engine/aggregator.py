# -*- coding: utf-8 -*-
"""Aggregator for ShoplistEngine v1.

RU: Агрегатор для ShoplistEngine v1.
EN: Aggregator for ShoplistEngine v1.

This module aggregates IngredientSpec items by food_id, summing quantities
in base units (G, ML, PCS). Input must already be normalized to base units.

RU: Этот модуль агрегирует IngredientSpec по food_id, суммируя количества
в базовых единицах (G, ML, PCS). Входные данные должны быть уже нормализованы
к базовым единицам.

All functions are pure (no I/O, env, time, random dependencies).
RU: Все функции чистые (нет зависимостей от I/O, env, time, random).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .models import FoodRef, IngredientSpec, Quantity, ShoplistLine, Unit

__all__ = ["aggregate_specs"]

# Base units allowed for aggregation
BASE_UNITS = {Unit.G, Unit.ML, Unit.PCS}


def aggregate_specs(specs: Iterable[IngredientSpec]) -> list[ShoplistLine]:
    """Aggregate IngredientSpec items by food_id, summing quantities.

    RU: Агрегирует IngredientSpec по food_id, суммируя количества.

    Groups specs by food_id and sums their quantities. All quantities must
    be in base units (G, ML, PCS). Raises ValueError if non-base units are found.

    RU: Группирует спецификации по food_id и суммирует их количества.
    Все количества должны быть в базовых единицах (G, ML, PCS).
    Вызывает ValueError, если найдены небазовые единицы.

    Args:
        specs: Iterable of IngredientSpec to aggregate (must be normalized)

    Returns:
        list[ShoplistLine]: Aggregated lines, one per unique food_id

    Raises:
        ValueError: If any spec has non-base unit (KG, L)

    Examples:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, IngredientSpec, Quantity, Unit
        >>> specs = [
        ...     IngredientSpec(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("500"), Unit.G)),
        ...     IngredientSpec(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("300"), Unit.G)),
        ...     IngredientSpec(food=FoodRef(food_id="rice"), qty=Quantity(Decimal("200"), Unit.G)),
        ... ]
        >>> lines = aggregate_specs(specs)
        >>> len(lines) == 2  # True
        >>> lines[0].qty.value == Decimal("800")  # True (chicken: 500 + 300)
        >>> lines[1].qty.value == Decimal("200")  # True (rice)

    RU: Примеры:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, IngredientSpec, Quantity, Unit
        >>> specs = [
        ...     IngredientSpec(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("500"), Unit.G)),
        ...     IngredientSpec(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("300"), Unit.G)),
        ...     IngredientSpec(food=FoodRef(food_id="rice"), qty=Quantity(Decimal("200"), Unit.G)),
        ... ]
        >>> lines = aggregate_specs(specs)
        >>> len(lines) == 2  # True
        >>> lines[0].qty.value == Decimal("800")  # True (chicken: 500 + 300)
        >>> lines[1].qty.value == Decimal("200")  # True (rice)
    """
    # Dictionary: food_id -> (accumulated_value, unit, first_food_ref)
    # We keep first FoodRef to preserve original reference
    totals: dict[str, tuple[Decimal, Unit, FoodRef]] = {}

    for spec in specs:
        qty = spec.qty

        # Validate base unit
        if qty.unit not in BASE_UNITS:
            raise ValueError(
                f"aggregate_specs expects base units only (G, ML, PCS), "
                f"got {qty.unit} for food_id={spec.food.food_id}"
            )

        food_id = spec.food.food_id

        if food_id not in totals:
            # First occurrence: initialize
            totals[food_id] = (qty.value, qty.unit, spec.food)
        else:
            # Accumulate: add value, verify unit consistency
            acc_value, acc_unit, first_food = totals[food_id]

            if qty.unit != acc_unit:
                raise ValueError(
                    f"Unit mismatch for food_id={food_id}: "
                    f"found both {acc_unit} and {qty.unit}. "
                    f"All specs for same food_id must use same unit."
                )

            totals[food_id] = (acc_value + qty.value, acc_unit, first_food)

    # Convert to ShoplistLine list
    result = [
        ShoplistLine(
            food=food_ref,
            qty=Quantity(value=value, unit=unit),
        )
        for value, unit, food_ref in totals.values()
    ]

    # Sort by food_id for deterministic output (order-independent input)
    result.sort(key=lambda line: line.food.food_id)

    return result
