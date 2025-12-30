# -*- coding: utf-8 -*-
"""Tests for ShoplistEngine v1 packager.

RU: Тесты для упаковщика ShoplistEngine v1.
EN: Tests for ShoplistEngine v1 packager.

These are anchor tests to keep invariants. No env/time/random dependencies.
RU: Это якорные тесты для сохранения инвариантов. Нет зависимостей от env/time/random.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.shoplist_engine.models import (
    FoodRef,
    PackageRule,
    PackPlan,
    Quantity,
    RoundingMode,
    ShoplistLine,
    Unit,
)
from core.shoplist_engine.packager import (
    PackagingResult,
    apply_packaging,
    compute_packs,
)


class TestComputePacks:
    """Test compute_packs function."""

    def test_ceil_rounding(self) -> None:
        """Test CEIL rounding mode."""
        # 1200 / 500 = 2.4 → ceil = 3
        packs = compute_packs(Decimal("1200"), Decimal("500"), RoundingMode.CEIL, 1)
        assert packs == 3

    def test_ceil_exact_match(self) -> None:
        """Test CEIL with exact match."""
        # 1000 / 500 = 2.0 → ceil = 2
        packs = compute_packs(Decimal("1000"), Decimal("500"), RoundingMode.CEIL, 1)
        assert packs == 2

    def test_ceil_min_packs_enforced(self) -> None:
        """Test that min_packs is enforced in CEIL mode."""
        # 100 / 500 = 0.2 → ceil = 1, but min_packs=2 → 2
        packs = compute_packs(Decimal("100"), Decimal("500"), RoundingMode.CEIL, 2)
        assert packs == 2

    def test_nearest_rounding_down(self) -> None:
        """Test NEAREST rounding down."""
        # 900 / 500 = 1.8 → nearest = 2
        packs = compute_packs(Decimal("900"), Decimal("500"), RoundingMode.NEAREST, 1)
        assert packs == 2

    def test_nearest_rounding_up(self) -> None:
        """Test NEAREST rounding up."""
        # 1100 / 500 = 2.2 → nearest = 2 (closer to 1000 than 1500)
        packs = compute_packs(Decimal("1100"), Decimal("500"), RoundingMode.NEAREST, 1)
        assert packs == 2

    def test_nearest_tie_prefers_ceil(self) -> None:
        """Test NEAREST tie prefers ceil."""
        # 750 / 500 = 1.5 → tie, prefer ceil = 2
        packs = compute_packs(Decimal("750"), Decimal("500"), RoundingMode.NEAREST, 1)
        assert packs == 2

    def test_nearest_min_packs_enforced(self) -> None:
        """Test that min_packs is enforced in NEAREST mode."""
        # 100 / 500 = 0.2 → nearest = 1, but min_packs=3 → 3
        packs = compute_packs(Decimal("100"), Decimal("500"), RoundingMode.NEAREST, 3)
        assert packs == 3

    def test_none_rounding(self) -> None:
        """Test NONE rounding mode."""
        # NONE: at least 1 pack (or min_packs)
        packs = compute_packs(Decimal("100"), Decimal("500"), RoundingMode.NONE, 1)
        assert packs == 1

    def test_none_min_packs_enforced(self) -> None:
        """Test that min_packs is enforced in NONE mode."""
        packs = compute_packs(Decimal("100"), Decimal("500"), RoundingMode.NONE, 2)
        assert packs == 2

    def test_zero_requested_with_min_packs_zero(self) -> None:
        """Test zero requested with min_packs=0."""
        packs = compute_packs(Decimal("0"), Decimal("500"), RoundingMode.CEIL, 0)
        assert packs == 0

    def test_zero_requested_with_min_packs_nonzero(self) -> None:
        """Test zero requested with min_packs > 0."""
        packs = compute_packs(Decimal("0"), Decimal("500"), RoundingMode.CEIL, 2)
        assert packs == 2


class TestApplyPackaging:
    """Test apply_packaging function."""

    def test_ceil_packaging(self) -> None:
        """Test CEIL packaging creates correct PackPlan."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("1200"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.CEIL,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        assert len(result.unpacked) == 0
        plan = result.packed[0]
        assert plan.packs == 3
        assert plan.provided.value == Decimal("1500")
        assert plan.overage.value == Decimal("300")

    def test_nearest_packaging(self) -> None:
        """Test NEAREST packaging."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("900"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="flour",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.NEAREST,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        plan = result.packed[0]
        assert plan.packs == 2
        assert plan.provided.value == Decimal("1000")
        assert plan.overage.value == Decimal("100")

    def test_none_packaging(self) -> None:
        """Test NONE packaging."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="salt"),
                qty=Quantity(Decimal("10"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="salt",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.NONE,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        plan = result.packed[0]
        assert plan.packs == 1
        assert plan.provided.value == Decimal("500")
        assert plan.overage.value == Decimal("490")

    def test_no_rule_unpacked(self) -> None:
        """Test that lines without rules go to unpacked."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("1200"), Unit.G),
            ),
            ShoplistLine(
                food=FoodRef(food_id="salt"),
                qty=Quantity(Decimal("10"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.G),
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        assert len(result.unpacked) == 1
        assert result.unpacked[0].food.food_id == "salt"

    def test_min_packs_enforced(self) -> None:
        """Test that min_packs is enforced."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="eggs"),
                qty=Quantity(Decimal("0"), Unit.PCS),
            ),
        ]
        rules = [
            PackageRule(
                food_id="eggs",
                pack_size=Quantity(Decimal("6"), Unit.PCS),
                min_packs=2,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        plan = result.packed[0]
        assert plan.packs == 2
        assert plan.provided.value == Decimal("12")
        assert plan.overage.value == Decimal("12")

    def test_pcs_packaging(self) -> None:
        """Test packaging with PCS units."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="eggs"),
                qty=Quantity(Decimal("5"), Unit.PCS),
            ),
        ]
        rules = [
            PackageRule(
                food_id="eggs",
                pack_size=Quantity(Decimal("6"), Unit.PCS),
                rounding=RoundingMode.CEIL,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        plan = result.packed[0]
        assert plan.packs == 1
        assert plan.provided.value == Decimal("6")
        assert plan.overage.value == Decimal("1")

    def test_ml_packaging(self) -> None:
        """Test packaging with ML units."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="milk"),
                qty=Quantity(Decimal("1500"), Unit.ML),
            ),
        ]
        rules = [
            PackageRule(
                food_id="milk",
                pack_size=Quantity(Decimal("1000"), Unit.ML),
                rounding=RoundingMode.CEIL,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        plan = result.packed[0]
        assert plan.packs == 2
        assert plan.provided.value == Decimal("2000")
        assert plan.overage.value == Decimal("500")

    def test_fractional_decimal_values(self) -> None:
        """Test packaging with fractional Decimal values."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="sugar"),
                qty=Quantity(Decimal("1.5"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="sugar",
                pack_size=Quantity(Decimal("1"), Unit.G),
                rounding=RoundingMode.CEIL,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        plan = result.packed[0]
        assert plan.packs == 2
        assert plan.provided.value == Decimal("2")
        assert plan.overage.value == Decimal("0.5")

    def test_deterministic_output_sorted(self) -> None:
        """Test that output is sorted by food_id for determinism."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="zebra"),
                qty=Quantity(Decimal("100"), Unit.G),
            ),
            ShoplistLine(
                food=FoodRef(food_id="apple"),
                qty=Quantity(Decimal("200"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(food_id="zebra", pack_size=Quantity(Decimal("50"), Unit.G)),
            PackageRule(food_id="apple", pack_size=Quantity(Decimal("100"), Unit.G)),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 2
        assert result.packed[0].food.food_id == "apple"
        assert result.packed[1].food.food_id == "zebra"


class TestApplyPackagingValidation:
    """Test validation and error cases."""

    def test_non_base_unit_raises(self) -> None:
        """Test that non-base units raise ValueError."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("1"), Unit.KG),
            ),
        ]
        rules = [
            PackageRule(
                food_id="flour",
                pack_size=Quantity(Decimal("500"), Unit.G),
            ),
        ]

        with pytest.raises(ValueError, match=r"base units only"):
            apply_packaging(lines, rules)

    def test_unit_mismatch_raises(self) -> None:
        """Test that unit mismatch raises ValueError."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.ML),  # Different unit
            ),
        ]

        with pytest.raises(ValueError, match=r"Unit mismatch"):
            apply_packaging(lines, rules)

    def test_duplicate_rules_raises(self) -> None:
        """Test that duplicate rules raise ValueError."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.G),
            ),
            PackageRule(
                food_id="chicken",  # Duplicate
                pack_size=Quantity(Decimal("1000"), Unit.G),
            ),
        ]

        with pytest.raises(ValueError, match=r"Duplicate PackageRule"):
            apply_packaging(lines, rules)

    def test_zero_requested_with_min_packs(self) -> None:
        """Test zero requested quantity with min_packs."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="eggs"),
                qty=Quantity(Decimal("0"), Unit.PCS),
            ),
        ]
        rules = [
            PackageRule(
                food_id="eggs",
                pack_size=Quantity(Decimal("6"), Unit.PCS),
                min_packs=2,
            ),
        ]
        result = apply_packaging(lines, rules)

        assert len(result.packed) == 1
        plan = result.packed[0]
        assert plan.packs == 2
        assert plan.requested.value == Decimal("0")
        assert plan.provided.value == Decimal("12")
        assert plan.overage.value == Decimal("12")


class TestPackPlanInvariants:
    """Test that PackPlan invariants are preserved."""

    def test_pack_plan_arithmetic_consistency(self) -> None:
        """Test that PackPlan arithmetic is consistent."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("1200"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.G),
            ),
        ]
        result = apply_packaging(lines, rules)

        plan = result.packed[0]
        # Verify arithmetic consistency
        assert plan.provided.value == plan.packs * plan.pack_size.value
        assert plan.provided.value >= plan.requested.value
        assert plan.overage.value == plan.provided.value - plan.requested.value
        assert plan.overage.value >= 0
