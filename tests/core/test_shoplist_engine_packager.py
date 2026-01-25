# -*- coding: utf-8 -*-
"""Tests for core.shoplist_engine.packager module.

RU: Тесты для модуля packager (упаковщик списков покупок).
EN: Tests for packager module (shopping list packager).

This test suite ensures all code paths in packager are covered:
- compute_packs with all rounding modes (CEIL, NEAREST, NONE)
- apply_packaging with rules and without rules
- build_rules_index with duplicates
- Edge cases (zero requested, min_packs, unit mismatches)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.shoplist_engine.models import (
    FoodRef,
    PackageRule,
    Quantity,
    RoundingMode,
    ShoplistLine,
    Unit,
)
from core.shoplist_engine.packager import (
    PackagingResult,
    apply_packaging,
    build_rules_index,
    compute_packs,
)

# --- compute_packs tests ---


class TestComputePacks:
    """Test compute_packs function with all rounding modes."""

    def test_compute_packs_ceil_rounds_up(self) -> None:
        """CEIL mode always rounds up."""
        # requested=1800g, pack=1000g -> ratio=1.8 -> ceil=2
        packs = compute_packs(
            requested=Decimal("1800"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.CEIL,
            min_packs=1,
        )
        assert packs == 2

    def test_compute_packs_ceil_respects_min_packs(self) -> None:
        """CEIL mode respects min_packs constraint."""
        # requested=100g, pack=1000g -> ratio=0.1 -> ceil=1, but min_packs=2
        packs = compute_packs(
            requested=Decimal("100"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.CEIL,
            min_packs=2,
        )
        assert packs == 2

    def test_compute_packs_nearest_rounds_to_nearest(self) -> None:
        """NEAREST mode rounds to nearest, but never under-supplies."""
        # requested=900g, pack=1000g -> ratio=0.9
        # floor=0, ceil=1
        # floor_dist=900, ceil_dist=100 -> ceil is closer
        packs = compute_packs(
            requested=Decimal("900"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.NEAREST,
            min_packs=1,
        )
        assert packs == 1

    def test_compute_packs_nearest_floor_wins_when_closer_and_covers(self) -> None:
        """NEAREST mode uses floor when floor is closer and covers requested."""
        # requested=100g, pack=100g -> ratio=1.0
        # floor=1 (100g, dist=0), ceil=2 (200g, dist=100)
        # floor is closer AND covers -> use floor
        packs = compute_packs(
            requested=Decimal("100"),
            pack_size=Decimal("100"),
            mode=RoundingMode.NEAREST,
            min_packs=0,
        )
        assert packs == 1

    def test_compute_packs_nearest_never_undersupply(self) -> None:
        """NEAREST mode never under-supplies even if floor is closer."""
        # requested=1100g, pack=1000g -> ratio=1.1
        # floor=1 (1000g, dist=100), ceil=2 (2000g, dist=900)
        # floor is closer, but doesn't cover -> must use ceil
        packs = compute_packs(
            requested=Decimal("1100"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.NEAREST,
            min_packs=1,
        )
        assert packs == 2  # Must cover 1100g, so 2 packs needed

    def test_compute_packs_nearest_tie_uses_ceil(self) -> None:
        """NEAREST mode uses ceil on tie (never under-supply)."""
        # requested=1500g, pack=1000g -> ratio=1.5
        # floor=1 (1000g, dist=500), ceil=2 (2000g, dist=500)
        # Tie -> use ceil to never under-supply
        packs = compute_packs(
            requested=Decimal("1500"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.NEAREST,
            min_packs=1,
        )
        assert packs == 2

    def test_compute_packs_nearest_respects_min_packs(self) -> None:
        """NEAREST mode respects min_packs even if calculated packs is lower."""
        # requested=100g, pack=1000g -> ratio=0.1 -> nearest=1, but min_packs=2
        packs = compute_packs(
            requested=Decimal("100"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.NEAREST,
            min_packs=2,
        )
        assert packs == 2

    def test_compute_packs_none_uses_floor_with_coverage_guarantee(self) -> None:
        """NONE mode uses floor but adds pack if floor doesn't cover."""
        # requested=1800g, pack=1000g -> ratio=1.8 -> floor=1
        # floor=1 covers 1000g < 1800g -> must add 1 pack
        packs = compute_packs(
            requested=Decimal("1800"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.NONE,
            min_packs=1,
        )
        assert packs == 2  # floor=1 doesn't cover, so add 1

    def test_compute_packs_none_floor_covers_no_extra_pack(self) -> None:
        """NONE mode doesn't add pack if floor already covers."""
        # requested=800g, pack=1000g -> ratio=0.8 -> floor=0, but min_packs=1
        # After min_packs: packs=1, covers 1000g >= 800g -> no extra pack needed
        packs = compute_packs(
            requested=Decimal("800"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.NONE,
            min_packs=1,
        )
        assert packs == 1

    def test_compute_packs_none_respects_min_packs(self) -> None:
        """NONE mode respects min_packs constraint."""
        # requested=100g, pack=1000g -> ratio=0.1 -> floor=0, but min_packs=2
        packs = compute_packs(
            requested=Decimal("100"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.NONE,
            min_packs=2,
        )
        assert packs == 2

    def test_compute_packs_zero_requested_returns_min_packs_or_zero(self) -> None:
        """Zero requested returns min_packs if > 0, else 0."""
        # Zero requested, min_packs=0 -> return 0
        packs = compute_packs(
            requested=Decimal("0"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.CEIL,
            min_packs=0,
        )
        assert packs == 0

        # Zero requested, min_packs=2 -> return 2
        packs = compute_packs(
            requested=Decimal("0"),
            pack_size=Decimal("1000"),
            mode=RoundingMode.CEIL,
            min_packs=2,
        )
        assert packs == 2

    def test_compute_packs_raises_on_negative_requested(self) -> None:
        """compute_packs raises ValueError on negative requested."""
        with pytest.raises(ValueError, match="requested must be >= 0"):
            compute_packs(
                requested=Decimal("-1"),
                pack_size=Decimal("1000"),
                mode=RoundingMode.CEIL,
                min_packs=1,
            )

    def test_compute_packs_raises_on_zero_pack_size(self) -> None:
        """compute_packs raises ValueError on zero pack_size."""
        with pytest.raises(ValueError, match="pack_size must be > 0"):
            compute_packs(
                requested=Decimal("100"),
                pack_size=Decimal("0"),
                mode=RoundingMode.CEIL,
                min_packs=1,
            )

    def test_compute_packs_raises_on_negative_min_packs(self) -> None:
        """compute_packs raises ValueError on negative min_packs."""
        with pytest.raises(ValueError, match="min_packs must be >= 0"):
            compute_packs(
                requested=Decimal("100"),
                pack_size=Decimal("1000"),
                mode=RoundingMode.CEIL,
                min_packs=-1,
            )

    def test_compute_packs_raises_on_unknown_mode(self) -> None:
        """compute_packs raises ValueError on unknown rounding mode."""

        # Use a mock mode that doesn't exist
        class UnknownMode:
            pass

        with pytest.raises(ValueError, match="Unknown rounding mode"):
            compute_packs(
                requested=Decimal("100"),
                pack_size=Decimal("1000"),
                mode=UnknownMode(),  # type: ignore[arg-type]
                min_packs=1,
            )


# --- build_rules_index tests ---


class TestBuildRulesIndex:
    """Test build_rules_index function."""

    def test_build_rules_index_creates_dict(self) -> None:
        """build_rules_index creates dict indexed by food_id."""
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
            PackageRule(
                food_id="rice",
                pack_size=Quantity(Decimal("1000"), Unit.G),
                rounding=RoundingMode.NEAREST,
                min_packs=1,
            ),
        ]
        index = build_rules_index(rules)
        assert len(index) == 2
        assert index["chicken"].pack_size.value == Decimal("500")
        assert index["rice"].pack_size.value == Decimal("1000")

    def test_build_rules_index_raises_on_duplicate_food_id(self) -> None:
        """build_rules_index raises ValueError on duplicate food_id."""
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
            PackageRule(
                food_id="chicken",  # Duplicate!
                pack_size=Quantity(Decimal("1000"), Unit.G),
                rounding=RoundingMode.NEAREST,
                min_packs=1,
            ),
        ]
        with pytest.raises(ValueError, match="Duplicate PackageRule for food_id=chicken"):
            build_rules_index(rules)


# --- apply_packaging tests ---


class TestApplyPackaging:
    """Test apply_packaging function."""

    def test_apply_packaging_with_rule_creates_pack_plan(self) -> None:
        """apply_packaging creates PackPlan when rule exists."""
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
                min_packs=1,
            ),
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 1
        assert len(result.unpacked) == 0
        plan = result.packed[0]
        assert plan.food.food_id == "chicken"
        assert plan.packs == 3  # ceil(1200/500) = 3
        assert plan.provided.value == Decimal("1500")  # 3 * 500
        assert plan.overage.value == Decimal("300")  # 1500 - 1200

    def test_apply_packaging_without_rule_adds_to_unpacked(self) -> None:
        """apply_packaging adds line to unpacked when no rule exists."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="salt"),
                qty=Quantity(Decimal("10"), Unit.G),
            ),
        ]
        rules = []  # No rules
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 0
        assert len(result.unpacked) == 1
        assert result.unpacked[0].food.food_id == "salt"

    def test_apply_packaging_mixed_rules_and_no_rules(self) -> None:
        """apply_packaging handles mix of lines with and without rules."""
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
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
            # No rule for salt
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 1
        assert len(result.unpacked) == 1
        assert result.packed[0].food.food_id == "chicken"
        assert result.unpacked[0].food.food_id == "salt"

    def test_apply_packaging_sorts_results_by_food_id(self) -> None:
        """apply_packaging sorts packed and unpacked by food_id."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="zucchini"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
            ShoplistLine(
                food=FoodRef(food_id="apple"),
                qty=Quantity(Decimal("300"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="zucchini",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
            PackageRule(
                food_id="apple",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 2
        # Should be sorted by food_id
        assert result.packed[0].food.food_id == "apple"
        assert result.packed[1].food.food_id == "zucchini"

    def test_apply_packaging_raises_on_non_base_unit(self) -> None:
        """apply_packaging raises ValueError on non-base unit (KG, L)."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("1"), Unit.KG),  # Non-base unit!
            ),
        ]
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
        ]
        with pytest.raises(ValueError, match="apply_packaging expects base units only"):
            apply_packaging(lines, rules)

    def test_apply_packaging_raises_on_unit_mismatch(self) -> None:
        """apply_packaging raises ValueError on unit mismatch between line and rule."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="chicken"),
                qty=Quantity(Decimal("500"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="chicken",
                pack_size=Quantity(Decimal("500"), Unit.ML),  # Different unit!
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
        ]
        with pytest.raises(ValueError, match="Unit mismatch for food_id=chicken"):
            apply_packaging(lines, rules)

    def test_apply_packaging_with_ml_unit(self) -> None:
        """apply_packaging works with ML unit (base unit)."""
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
                min_packs=1,
            ),
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 1
        assert result.packed[0].packs == 2  # ceil(1500/1000) = 2

    def test_apply_packaging_with_pcs_unit(self) -> None:
        """apply_packaging works with PCS unit (base unit)."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="eggs"),
                qty=Quantity(Decimal("5"), Unit.PCS),
            ),
        ]
        rules = [
            PackageRule(
                food_id="eggs",
                pack_size=Quantity(Decimal("10"), Unit.PCS),
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 1
        assert result.packed[0].packs == 1  # ceil(5/10) = 1

    def test_apply_packaging_with_nearest_rounding(self) -> None:
        """apply_packaging uses NEAREST rounding mode correctly."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="rice"),
                qty=Quantity(Decimal("1100"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="rice",
                pack_size=Quantity(Decimal("1000"), Unit.G),
                rounding=RoundingMode.NEAREST,
                min_packs=1,
            ),
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 1
        # 1100g needs 2 packs (never under-supply)
        assert result.packed[0].packs == 2
        assert result.packed[0].provided.value == Decimal("2000")
        assert result.packed[0].overage.value == Decimal("900")

    def test_apply_packaging_with_none_rounding(self) -> None:
        """apply_packaging uses NONE rounding mode correctly."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("1800"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="flour",
                pack_size=Quantity(Decimal("1000"), Unit.G),
                rounding=RoundingMode.NONE,
                min_packs=1,
            ),
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 1
        # floor(1800/1000) = 1, but 1*1000 < 1800, so add 1 pack = 2
        assert result.packed[0].packs == 2
        assert result.packed[0].provided.value == Decimal("2000")
        assert result.packed[0].overage.value == Decimal("200")

    def test_apply_packaging_with_min_packs(self) -> None:
        """apply_packaging respects min_packs constraint."""
        lines = [
            ShoplistLine(
                food=FoodRef(food_id="spices"),
                qty=Quantity(Decimal("100"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="spices",
                pack_size=Quantity(Decimal("1000"), Unit.G),
                rounding=RoundingMode.CEIL,
                min_packs=2,  # Force minimum 2 packs
            ),
        ]
        result = apply_packaging(lines, rules)
        assert len(result.packed) == 1
        # ceil(100/1000) = 1, but min_packs=2, so packs=2
        assert result.packed[0].packs == 2
        assert result.packed[0].provided.value == Decimal("2000")
        assert result.packed[0].overage.value == Decimal("1900")

    def test_apply_packaging_raises_on_negative_overage(self) -> None:
        """apply_packaging raises ValueError if computed overage is negative (defensive check)."""
        # This should never happen with correct compute_packs logic,
        # but we test the defensive check for coverage
        from unittest.mock import patch

        lines = [
            ShoplistLine(
                food=FoodRef(food_id="flour"),
                qty=Quantity(Decimal("1000"), Unit.G),
            ),
        ]
        rules = [
            PackageRule(
                food_id="flour",
                pack_size=Quantity(Decimal("500"), Unit.G),
                rounding=RoundingMode.CEIL,
                min_packs=1,
            ),
        ]

        # Mock compute_packs to return packs that don't cover requested (bug scenario)
        with patch("core.shoplist_engine.packager.compute_packs", return_value=1):
            with pytest.raises(ValueError, match="Negative overage computed for food_id=flour"):
                apply_packaging(lines, rules)
