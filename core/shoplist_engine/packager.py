# -*- coding: utf-8 -*-
"""Packager for ShoplistEngine v1.

RU: Упаковщик для ShoplistEngine v1.
EN: Packager for ShoplistEngine v1.

This module applies packaging rules to aggregated shoplist lines, converting
quantities into packs with rounding modes and calculating overage.

RU: Этот модуль применяет правила упаковки к агрегированным строкам списка покупок,
конвертируя количества в упаковки с режимами округления и вычисляя избыток.

All functions are pure (no I/O, env, time, random dependencies).
RU: Все функции чистые (нет зависимостей от I/O, env, time, random).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Iterable

from .models import PackPlan, PackageRule, Quantity, RoundingMode, ShoplistLine, Unit

__all__ = ["PackagingResult", "apply_packaging"]

# Base units allowed for packaging
BASE_UNITS: frozenset[Unit] = frozenset({Unit.G, Unit.ML, Unit.PCS})


@dataclass(frozen=True)
class PackagingResult:
    """Result of applying packaging rules to shoplist lines.

    RU: Результат применения правил упаковки к строкам списка покупок.

    Contains two lists:
    - packed: lines that had matching rules and were packaged
    - unpacked: lines without matching rules (no packaging applied)

    RU: Содержит два списка:
    - packed: строки, для которых были правила и которые были упакованы
    - unpacked: строки без правил (упаковка не применялась)

    Examples:
        result = PackagingResult(
            packed=[PackPlan(...), PackPlan(...)],
            unpacked=[ShoplistLine(...)]
        )

    RU: Примеры:
        result = PackagingResult(
            packed=[PackPlan(...), PackPlan(...)],
            unpacked=[ShoplistLine(...)]
        )
    """

    packed: list[PackPlan]
    unpacked: list[ShoplistLine]


def build_rules_index(rules: Iterable[PackageRule]) -> dict[str, PackageRule]:
    """Build index of rules by food_id.

    RU: Строит индекс правил по food_id.

    Args:
        rules: Iterable of PackageRule

    Returns:
        dict[str, PackageRule]: Rules indexed by food_id

    Raises:
        ValueError: If duplicate rules found for same food_id

    Examples:
        >>> rules = [
        ...     PackageRule(food_id="chicken", pack_size=Quantity(Decimal("500"), Unit.G)),
        ...     PackageRule(food_id="rice", pack_size=Quantity(Decimal("1000"), Unit.G)),
        ... ]
        >>> index = build_rules_index(rules)
        >>> index["chicken"].pack_size.value == Decimal("500")  # True

    RU: Примеры:
        >>> rules = [
        ...     PackageRule(food_id="chicken", pack_size=Quantity(Decimal("500"), Unit.G)),
        ...     PackageRule(food_id="rice", pack_size=Quantity(Decimal("1000"), Unit.G)),
        ... ]
        >>> index = build_rules_index(rules)
        >>> index["chicken"].pack_size.value == Decimal("500")  # True
    """
    index: dict[str, PackageRule] = {}
    for rule in rules:
        if rule.food_id in index:
            raise ValueError(
                f"Duplicate PackageRule for food_id={rule.food_id}. "
                f"Only one rule per food_id is allowed."
            )
        index[rule.food_id] = rule
    return index


def compute_packs(
    requested: Decimal,
    pack_size: Decimal,
    mode: RoundingMode,
    min_packs: int,
) -> int:
    """Compute number of packs needed.

    RU: Вычисляет необходимое количество упаковок.

    Args:
        requested: Requested quantity value (must be >= 0)
        pack_size: Size of one pack (must be > 0)
        mode: Rounding mode (CEIL, NEAREST, NONE)
        min_packs: Minimum number of packs required (must be >= 0)

    Returns:
        int: Number of packs (always >= min_packs, or 0 if requested=0 and min_packs=0)

    Raises:
        ValueError: If requested < 0, pack_size <= 0, or min_packs < 0

    Examples:
        >>> compute_packs(Decimal("1200"), Decimal("500"), RoundingMode.CEIL, 1)
        3
        >>> compute_packs(Decimal("900"), Decimal("500"), RoundingMode.NEAREST, 1)
        2
        >>> compute_packs(Decimal("0"), Decimal("500"), RoundingMode.CEIL, 0)
        0

    RU: Примеры:
        >>> compute_packs(Decimal("1200"), Decimal("500"), RoundingMode.CEIL, 1)
        3
        >>> compute_packs(Decimal("900"), Decimal("500"), RoundingMode.NEAREST, 1)
        2
        >>> compute_packs(Decimal("0"), Decimal("500"), RoundingMode.CEIL, 0)
        0
    """
    # Validate inputs
    if requested < 0:
        raise ValueError(f"requested must be >= 0, got {requested}")
    if pack_size <= 0:
        raise ValueError(f"pack_size must be > 0, got {pack_size}")
    if min_packs < 0:
        raise ValueError(f"min_packs must be >= 0, got {min_packs}")

    if requested == 0:
        return max(0, min_packs)

    ratio = requested / pack_size

    if mode == RoundingMode.CEIL:
        # CEIL: always round up using Decimal rounding
        packs = int(ratio.to_integral_value(rounding=ROUND_CEILING))
        packs = max(packs, min_packs)
    elif mode == RoundingMode.NEAREST:
        # NEAREST: round to nearest, but never under-supply
        floor_packs = int(ratio.to_integral_value(rounding=ROUND_FLOOR))
        ceil_packs = int(ratio.to_integral_value(rounding=ROUND_CEILING))

        # Calculate distances
        floor_value = floor_packs * pack_size
        ceil_value = ceil_packs * pack_size
        floor_dist = abs(requested - floor_value)
        ceil_dist = abs(requested - ceil_value)

        if floor_dist < ceil_dist:
            packs = floor_packs
        else:
            # ceil on tie or if ceil is closer
            packs = ceil_packs

        # Never under-supply: if chosen packs don't cover requested, use ceil
        if requested > 0 and packs * pack_size < requested:
            packs = ceil_packs

        # Ensure at least min_packs, and at least 1 if requested > 0
        packs = max(packs, min_packs, 1 if requested > 0 else 0)
    elif mode == RoundingMode.NONE:
        # NONE: natural/floor rounding with coverage guarantee.
        # Uses floor as default but will add one pack if floor count does not
        # cover the requested quantity (ensures we never under-supply).
        packs = int(ratio.to_integral_value(rounding=ROUND_FLOOR))
        packs = max(packs, min_packs, 1 if requested > 0 else 0)

        # If floor doesn't cover requested, add one pack
        if requested > 0 and packs * pack_size < requested:
            packs += 1
    else:
        raise ValueError(f"Unknown rounding mode: {mode}")

    return packs


def apply_packaging(
    lines: Iterable[ShoplistLine],
    rules: Iterable[PackageRule],
) -> PackagingResult:
    """Apply packaging rules to shoplist lines.

    RU: Применяет правила упаковки к строкам списка покупок.

    For each line:
    - If a matching rule exists, creates PackPlan with rounding
    - If no rule exists, adds line to unpacked list

    RU: Для каждой строки:
    - Если есть правило, создаёт PackPlan с округлением
    - Если правила нет, добавляет строку в unpacked

    Args:
        lines: Iterable of ShoplistLine to package
        rules: Iterable of PackageRule

    Returns:
        PackagingResult: Packed and unpacked lines

    Raises:
        ValueError: If line has non-base unit
        ValueError: If unit mismatch between line and rule
        ValueError: If duplicate rules for same food_id

    Examples:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, Quantity, ShoplistLine, Unit
        >>> lines = [
        ...     ShoplistLine(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("1200"), Unit.G)),
        ...     ShoplistLine(food=FoodRef(food_id="salt"), qty=Quantity(Decimal("10"), Unit.G)),
        ... ]
        >>> rules = [
        ...     PackageRule(food_id="chicken", pack_size=Quantity(Decimal("500"), Unit.G)),
        ... ]
        >>> result = apply_packaging(lines, rules)
        >>> len(result.packed) == 1  # True
        >>> len(result.unpacked) == 1  # True

    RU: Примеры:
        >>> from decimal import Decimal
        >>> from core.shoplist_engine.models import FoodRef, Quantity, ShoplistLine, Unit
        >>> lines = [
        ...     ShoplistLine(food=FoodRef(food_id="chicken"), qty=Quantity(Decimal("1200"), Unit.G)),
        ...     ShoplistLine(food=FoodRef(food_id="salt"), qty=Quantity(Decimal("10"), Unit.G)),
        ... ]
        >>> rules = [
        ...     PackageRule(food_id="chicken", pack_size=Quantity(Decimal("500"), Unit.G)),
        ... ]
        >>> result = apply_packaging(lines, rules)
        >>> len(result.packed) == 1  # True
        >>> len(result.unpacked) == 1  # True
    """
    rules_index = build_rules_index(rules)
    packed: list[PackPlan] = []
    unpacked: list[ShoplistLine] = []

    for line in lines:
        # Validate base unit
        if line.qty.unit not in BASE_UNITS:
            raise ValueError(
                f"apply_packaging expects base units only (G, ML, PCS), "
                f"got {line.qty.unit} for food_id={line.food.food_id}"
            )

        food_id = line.food.food_id

        # Check if rule exists
        if food_id not in rules_index:
            unpacked.append(line)
            continue

        rule = rules_index[food_id]

        # Validate unit match
        if line.qty.unit != rule.pack_size.unit:
            raise ValueError(
                f"Unit mismatch for food_id={food_id}: "
                f"line has {line.qty.unit}, rule has {rule.pack_size.unit}. "
                f"Units must match for packaging."
            )

        # Compute packs
        packs = compute_packs(
            requested=line.qty.value,
            pack_size=rule.pack_size.value,
            mode=rule.rounding,
            min_packs=rule.min_packs,
        )

        # Calculate provided and overage
        provided_value = packs * rule.pack_size.value
        overage_value = provided_value - line.qty.value

        # Defensive check: overage should never be negative (packs must cover requested)
        if overage_value < 0:
            raise ValueError(
                f"Negative overage computed for food_id={food_id}: "
                f"provided={provided_value}, requested={line.qty.value}, "
                f"pack_size={rule.pack_size.value}, packs={packs}. "
                f"This indicates a bug in compute_packs logic."
            )

        # Create PackPlan
        plan = PackPlan(
            food=line.food,
            requested=line.qty,
            pack_size=rule.pack_size,
            packs=packs,
            provided=Quantity(value=provided_value, unit=line.qty.unit),
            overage=Quantity(value=overage_value, unit=line.qty.unit),
        )

        packed.append(plan)

    # Sort for determinism
    packed.sort(key=lambda p: p.food.food_id)
    unpacked.sort(key=lambda line: line.food.food_id)

    return PackagingResult(packed=packed, unpacked=unpacked)
