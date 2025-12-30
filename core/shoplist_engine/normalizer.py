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
from typing import Iterable

from .models import IngredientSpec, Quantity

__all__ = ["normalize_quantity", "normalize_ingredient", "normalize_specs"]


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
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import Quantity, Unit
        >>> normalize_quantity(Quantity(Decimal("1.5"), Unit.KG))  # Quantity(1500, G)
        >>> normalize_quantity(Quantity(Decimal("2"), Unit.L))  # Quantity(2000, ML)
        >>> normalize_quantity(Quantity(Decimal("500"), Unit.G))  # Quantity(500, G) (unchanged)

    RU: Примеры:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import Quantity, Unit
        >>> normalize_quantity(Quantity(Decimal("1.5"), Unit.KG))  # Quantity(1500, G)
        >>> normalize_quantity(Quantity(Decimal("2"), Unit.L))  # Quantity(2000, ML)
        >>> normalize_quantity(Quantity(Decimal("500"), Unit.G))  # Quantity(500, G) (без изменений)
    """
    # Zero values are allowed by Quantity validation and are preserved during normalization.
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
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, IngredientSpec, Quantity, Unit
        >>> spec = IngredientSpec(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("1"), Unit.KG))
        >>> normalized = normalize_ingredient(spec)
        >>> normalized.qty.unit == Unit.G  # True
        >>> normalized.qty.value == Decimal("1000")  # True

    RU: Примеры:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, IngredientSpec, Quantity, Unit
        >>> spec = IngredientSpec(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("1"), Unit.KG))
        >>> normalized = normalize_ingredient(spec)
        >>> normalized.qty.unit == Unit.G  # True
        >>> normalized.qty.value == Decimal("1000")  # True
    """
    normalized = normalize_quantity(spec.qty)
    if normalized == spec.qty:
        return spec
    return replace(spec, qty=normalized)


def normalize_specs(specs: Iterable[IngredientSpec]) -> list[IngredientSpec]:
    """Normalize a batch of IngredientSpec items.

    RU: Нормализует набор IngredientSpec.

    Args:
        specs: Iterable of IngredientSpec to normalize

    Returns:
        list[IngredientSpec]: Normalized IngredientSpec (same instances if unchanged)

    Examples:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, IngredientSpec, Quantity, Unit
        >>> specs = [
        ...     IngredientSpec(food=FoodRef(food_id="a"), qty=Quantity(Decimal("1"), Unit.KG)),
        ...     IngredientSpec(food=FoodRef(food_id="b"), qty=Quantity(Decimal("500"), Unit.G)),
        ... ]
        >>> normalized = normalize_specs(specs)
        >>> normalized[0].qty.unit == Unit.G  # True
        >>> normalized[0].qty.value == Decimal("1000")  # True
        >>> normalized[1] is specs[1]  # True (unchanged)

    RU: Примеры:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, IngredientSpec, Quantity, Unit
        >>> specs = [
        ...     IngredientSpec(food=FoodRef(food_id="a"), qty=Quantity(Decimal("1"), Unit.KG)),
        ...     IngredientSpec(food=FoodRef(food_id="b"), qty=Quantity(Decimal("500"), Unit.G)),
        ... ]
        >>> normalized = normalize_specs(specs)
        >>> normalized[0].qty.unit == Unit.G  # True
        >>> normalized[0].qty.value == Decimal("1000")  # True
        >>> normalized[1] is specs[1]  # True (без изменений)
    """
    return [normalize_ingredient(s) for s in specs]
