# -*- coding: utf-8 -*-
"""Unit normalizer for ShoplistEngine v1.

RU: Нормализатор единиц для ShoplistEngine v1.
EN: Unit normalizer for ShoplistEngine v1.

This module normalizes quantities to base units (G, ML, PCS) for consistent
aggregation. Convenience units (KG, L) are converted to base units.

RU: Этот модуль нормализует количества к базовым единицам (G, ML, PCS) для
согласованного агрегирования. Удобные единицы (KG, L) конвертируются в базовые.

All functions are pure (no I/O, env, time, random dependencies).
RU: Все функции чистые (нет зависимостей от I/O, env, time, random).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List

from .models import IngredientSpec, Quantity


def normalize_quantity(qty: Quantity) -> Quantity:
    """Normalize Quantity to base units when possible.

    RU: Нормализует Quantity к базовым единицам (g/ml/pcs), если возможно.

    Converts KG → G and L → ML. Base units (G, ML, PCS) are returned unchanged.
    Zero values are allowed and preserved.

    RU: Конвертирует KG → G и L → ML. Базовые единицы (G, ML, PCS) возвращаются
    без изменений. Нулевые значения разрешены и сохраняются.

    Args:
        qty: Quantity to normalize

    Returns:
        Quantity in base units (G, ML, or PCS)

    Examples:
        normalize_quantity(Quantity(Decimal("1.5"), Unit.KG))  # Quantity(1500, G)
        normalize_quantity(Quantity(Decimal("2"), Unit.L))  # Quantity(2000, ML)
        normalize_quantity(Quantity(Decimal("500"), Unit.G))  # Quantity(500, G) (unchanged)

    RU: Примеры:
        normalize_quantity(Quantity(Decimal("1.5"), Unit.KG))  # Quantity(1500, G)
        normalize_quantity(Quantity(Decimal("2"), Unit.L))  # Quantity(2000, ML)
        normalize_quantity(Quantity(Decimal("500"), Unit.G))  # Quantity(500, G) (без изменений)
    """
    # Quantity already enforces value >= 0; we intentionally keep zero allowed.
    return qty.to_base_unit()


def normalize_ingredient(spec: IngredientSpec) -> IngredientSpec:
    """Normalize IngredientSpec.qty to base units.

    RU: Нормализует qty в IngredientSpec к базовым единицам.

    Returns the same instance if no conversion is needed, otherwise returns
    a new instance with normalized quantity.

    RU: Возвращает тот же экземпляр, если конверсия не нужна, иначе возвращает
    новый экземпляр с нормализованным количеством.

    Args:
        spec: IngredientSpec to normalize

    Returns:
        IngredientSpec with normalized quantity (same instance if unchanged)

    Examples:
        spec = IngredientSpec(food=FoodRef("chicken"), qty=Quantity(Decimal("1"), Unit.KG))
        normalized = normalize_ingredient(spec)
        # normalized.qty == Quantity(Decimal("1000"), Unit.G)

    RU: Примеры:
        spec = IngredientSpec(food=FoodRef("chicken"), qty=Quantity(Decimal("1"), Unit.KG))
        normalized = normalize_ingredient(spec)
        # normalized.qty == Quantity(Decimal("1000"), Unit.G)
    """
    normalized = normalize_quantity(spec.qty)
    return spec if normalized == spec.qty else replace(spec, qty=normalized)


def normalize_specs(specs: Iterable[IngredientSpec]) -> List[IngredientSpec]:
    """Normalize a batch of IngredientSpec items.

    RU: Нормализует набор IngredientSpec.

    Args:
        specs: Iterable of IngredientSpec to normalize

    Returns:
        List of normalized IngredientSpec (same instances if unchanged)

    Examples:
        specs = [
            IngredientSpec(food=FoodRef("a"), qty=Quantity(Decimal("1"), Unit.KG)),
            IngredientSpec(food=FoodRef("b"), qty=Quantity(Decimal("500"), Unit.G)),
        ]
        normalized = normalize_specs(specs)
        # normalized[0].qty == Quantity(Decimal("1000"), Unit.G)
        # normalized[1] is specs[1] (unchanged)

    RU: Примеры:
        specs = [
            IngredientSpec(food=FoodRef("a"), qty=Quantity(Decimal("1"), Unit.KG)),
            IngredientSpec(food=FoodRef("b"), qty=Quantity(Decimal("500"), Unit.G)),
        ]
        normalized = normalize_specs(specs)
        # normalized[0].qty == Quantity(Decimal("1000"), Unit.G)
        # normalized[1] is specs[1] (без изменений)
    """
    return [normalize_ingredient(s) for s in specs]
