# -*- coding: utf-8 -*-
"""Tests for ShoplistEngine v1 domain models.

RU: Тесты для доменных моделей ShoplistEngine v1.
EN: Tests for ShoplistEngine v1 domain models.

These are anchor tests to keep invariants. No env/time/random dependencies.
RU: Это якорные тесты для сохранения инвариантов. Нет зависимостей от env/time/random.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.shoplist_engine.models import (
    FoodForm,
    FoodRef,
    IngredientSpec,
    PackPlan,
    PackageRule,
    Quantity,
    RoundingMode,
    ShoplistLine,
    Unit,
)


class TestUnit:
    """Test Unit enum."""

    def test_unit_values(self) -> None:
        """Test that all unit values are correct."""
        assert Unit.G == "g"
        assert Unit.ML == "ml"
        assert Unit.PCS == "pcs"
        assert Unit.KG == "kg"
        assert Unit.L == "l"

    def test_unit_enum_membership(self) -> None:
        """Test that units are proper enum members."""
        assert isinstance(Unit.G, Unit)
        assert isinstance(Unit.ML, Unit)
        assert isinstance(Unit.PCS, Unit)


class TestFoodForm:
    """Test FoodForm enum."""

    def test_food_form_values(self) -> None:
        """Test that all food form values are correct."""
        assert FoodForm.RAW == "raw"
        assert FoodForm.COOKED == "cooked"
        assert FoodForm.FROZEN == "frozen"
        assert FoodForm.DRIED == "dried"
        assert FoodForm.CANNED == "canned"


class TestRoundingMode:
    """Test RoundingMode enum."""

    def test_rounding_mode_values(self) -> None:
        """Test that all rounding mode values are correct."""
        assert RoundingMode.CEIL == "ceil"
        assert RoundingMode.NEAREST == "nearest"
        assert RoundingMode.NONE == "none"


class TestQuantity:
    """Test Quantity model."""

    def test_quantity_creation(self) -> None:
        """Test creating a valid quantity."""
        qty = Quantity(value=Decimal("500"), unit=Unit.G)
        assert qty.value == Decimal("500")
        assert qty.unit == Unit.G

    def test_quantity_zero_allowed(self) -> None:
        """Test that zero quantity is allowed (edge case)."""
        qty = Quantity(value=Decimal("0"), unit=Unit.G)
        assert qty.value == Decimal("0")

    def test_quantity_negative_raises(self) -> None:
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            Quantity(value=Decimal("-1"), unit=Unit.G)

    def test_quantity_frozen(self) -> None:
        """Test that Quantity is immutable."""
        qty = Quantity(value=Decimal("500"), unit=Unit.G)
        with pytest.raises(Exception):  # frozen dataclass raises
            qty.value = Decimal("1000")  # type: ignore[misc]


class TestFoodRef:
    """Test FoodRef model."""

    def test_food_ref_creation(self) -> None:
        """Test creating a valid food reference."""
        food = FoodRef(food_id="chicken_breast")
        assert food.food_id == "chicken_breast"

    def test_food_ref_empty_raises(self) -> None:
        """Test that empty food_id raises ValueError."""
        with pytest.raises(ValueError, match="must be non-empty"):
            FoodRef(food_id="")

    def test_food_ref_whitespace_only_raises(self) -> None:
        """Test that whitespace-only food_id raises ValueError."""
        with pytest.raises(ValueError, match="must be non-empty"):
            FoodRef(food_id="   ")

    def test_food_ref_frozen(self) -> None:
        """Test that FoodRef is immutable."""
        food = FoodRef(food_id="chicken_breast")
        with pytest.raises(Exception):  # frozen dataclass raises
            food.food_id = "beef"  # type: ignore[misc]


class TestIngredientSpec:
    """Test IngredientSpec model."""

    def test_ingredient_spec_creation(self) -> None:
        """Test creating a valid ingredient spec."""
        food = FoodRef(food_id="chicken_breast")
        qty = Quantity(value=Decimal("500"), unit=Unit.G)
        spec = IngredientSpec(food=food, qty=qty, form=FoodForm.RAW)
        assert spec.food == food
        assert spec.qty == qty
        assert spec.form == FoodForm.RAW
        assert spec.notes is None

    def test_ingredient_spec_with_notes(self) -> None:
        """Test creating ingredient spec with notes."""
        food = FoodRef(food_id="chicken_breast")
        qty = Quantity(value=Decimal("500"), unit=Unit.G)
        spec = IngredientSpec(food=food, qty=qty, form=FoodForm.RAW, notes="boneless, skinless")
        assert spec.notes == "boneless, skinless"

    def test_ingredient_spec_default_form(self) -> None:
        """Test that default form is RAW."""
        food = FoodRef(food_id="chicken_breast")
        qty = Quantity(value=Decimal("500"), unit=Unit.G)
        spec = IngredientSpec(food=food, qty=qty)
        assert spec.form == FoodForm.RAW

    def test_ingredient_spec_frozen(self) -> None:
        """Test that IngredientSpec is immutable."""
        food = FoodRef(food_id="chicken_breast")
        qty = Quantity(value=Decimal("500"), unit=Unit.G)
        spec = IngredientSpec(food=food, qty=qty)
        with pytest.raises(Exception):  # frozen dataclass raises
            spec.form = FoodForm.COOKED  # type: ignore[misc]


class TestShoplistLine:
    """Test ShoplistLine model."""

    def test_shoplist_line_creation(self) -> None:
        """Test creating a valid shoplist line."""
        food = FoodRef(food_id="chicken_breast")
        qty = Quantity(value=Decimal("1200"), unit=Unit.G)
        line = ShoplistLine(food=food, qty=qty)
        assert line.food == food
        assert line.qty == qty

    def test_shoplist_line_zero_quantity_allowed(self) -> None:
        """Test that zero quantity is allowed in shoplist line (edge case for empty lines).

        RU: Тест, что нулевое количество разрешено в строке списка покупок
        (крайний случай для пустых строк).

        This ensures aggregator/packager can handle zero quantities gracefully.
        RU: Это гарантирует, что агрегатор/пакеджер могут обработать нулевые количества.
        """
        food = FoodRef(food_id="chicken_breast")
        qty = Quantity(value=Decimal("0"), unit=Unit.G)
        line = ShoplistLine(food=food, qty=qty)
        assert line.qty.value == Decimal("0")
        assert line.food == food

    def test_shoplist_line_frozen(self) -> None:
        """Test that ShoplistLine is immutable."""
        food = FoodRef(food_id="chicken_breast")
        qty = Quantity(value=Decimal("1200"), unit=Unit.G)
        line = ShoplistLine(food=food, qty=qty)
        with pytest.raises(Exception):  # frozen dataclass raises
            line.qty = Quantity(value=Decimal("500"), unit=Unit.G)  # type: ignore[misc]


class TestPackageRule:
    """Test PackageRule model."""

    def test_package_rule_creation(self) -> None:
        """Test creating a valid package rule."""
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        rule = PackageRule(
            food_id="chicken_breast",
            pack_size=pack_size,
            rounding=RoundingMode.CEIL,
            min_packs=1,
        )
        assert rule.food_id == "chicken_breast"
        assert rule.pack_size == pack_size
        assert rule.rounding == RoundingMode.CEIL
        assert rule.min_packs == 1

    def test_package_rule_defaults(self) -> None:
        """Test package rule with default values."""
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        rule = PackageRule(food_id="chicken_breast", pack_size=pack_size)
        assert rule.rounding == RoundingMode.CEIL
        assert rule.min_packs == 1

    def test_package_rule_empty_food_id_raises(self) -> None:
        """Test that empty food_id raises ValueError."""
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        with pytest.raises(ValueError, match="must be non-empty"):
            PackageRule(food_id="", pack_size=pack_size)

    def test_package_rule_min_packs_zero_raises(self) -> None:
        """Test that min_packs < 1 raises ValueError."""
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        with pytest.raises(ValueError, match="min_packs must be >= 1"):
            PackageRule(food_id="chicken_breast", pack_size=pack_size, min_packs=0)

    def test_package_rule_min_packs_negative_raises(self) -> None:
        """Test that negative min_packs raises ValueError."""
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        with pytest.raises(ValueError, match="min_packs must be >= 1"):
            PackageRule(food_id="chicken_breast", pack_size=pack_size, min_packs=-1)

    def test_package_rule_pack_size_zero_raises(self) -> None:
        """Test that pack_size.value == 0 raises ValueError."""
        pack_size = Quantity(value=Decimal("0"), unit=Unit.G)
        with pytest.raises(ValueError, match=r"pack_size\.value must be > 0"):
            PackageRule(food_id="chicken_breast", pack_size=pack_size)

    def test_package_rule_frozen(self) -> None:
        """Test that PackageRule is immutable."""
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        rule = PackageRule(food_id="chicken_breast", pack_size=pack_size)
        with pytest.raises(Exception):  # frozen dataclass raises
            rule.min_packs = 2  # type: ignore[misc]


class TestPackPlan:
    """Test PackPlan model."""

    def test_pack_plan_creation(self) -> None:
        """Test creating a valid pack plan."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1500"), unit=Unit.G)
        overage = Quantity(value=Decimal("300"), unit=Unit.G)
        plan = PackPlan(
            food=food,
            requested=requested,
            pack_size=pack_size,
            packs=3,
            provided=provided,
            overage=overage,
        )
        assert plan.food == food
        assert plan.requested == requested
        assert plan.pack_size == pack_size
        assert plan.packs == 3
        assert plan.provided == provided
        assert plan.overage == overage

    def test_pack_plan_unit_mismatch_requested_pack_size_raises(self) -> None:
        """Test that unit mismatch between requested and pack_size raises ValueError."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.ML)  # Different unit!
        provided = Quantity(value=Decimal("1500"), unit=Unit.G)
        overage = Quantity(value=Decimal("300"), unit=Unit.G)
        with pytest.raises(ValueError, match="Unit mismatch"):
            PackPlan(
                food=food,
                requested=requested,
                pack_size=pack_size,
                packs=3,
                provided=provided,
                overage=overage,
            )

    def test_pack_plan_unit_mismatch_provided_raises(self) -> None:
        """Test that unit mismatch between provided and requested raises ValueError."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1500"), unit=Unit.ML)  # Different unit!
        overage = Quantity(value=Decimal("300"), unit=Unit.G)
        with pytest.raises(ValueError, match="Unit mismatch"):
            PackPlan(
                food=food,
                requested=requested,
                pack_size=pack_size,
                packs=3,
                provided=provided,
                overage=overage,
            )

    def test_pack_plan_unit_mismatch_overage_raises(self) -> None:
        """Test that unit mismatch between overage and requested raises ValueError."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1500"), unit=Unit.G)
        overage = Quantity(value=Decimal("300"), unit=Unit.ML)  # Different unit!
        with pytest.raises(ValueError, match="Unit mismatch"):
            PackPlan(
                food=food,
                requested=requested,
                pack_size=pack_size,
                packs=3,
                provided=provided,
                overage=overage,
            )

    def test_pack_plan_negative_packs_raises(self) -> None:
        """Test that negative packs raises ValueError."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1500"), unit=Unit.G)
        overage = Quantity(value=Decimal("300"), unit=Unit.G)
        with pytest.raises(ValueError, match="packs must be non-negative"):
            PackPlan(
                food=food,
                requested=requested,
                pack_size=pack_size,
                packs=-1,  # Negative!
                provided=provided,
                overage=overage,
            )

    def test_pack_plan_zero_packs_allowed(self) -> None:
        """Test that zero packs is allowed (edge case)."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("0"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("0"), unit=Unit.G)
        overage = Quantity(value=Decimal("0"), unit=Unit.G)
        plan = PackPlan(
            food=food,
            requested=requested,
            pack_size=pack_size,
            packs=0,
            provided=provided,
            overage=overage,
        )
        assert plan.packs == 0

    def test_pack_plan_provided_less_than_requested_raises(self) -> None:
        """Test that provided.value < requested.value raises ValueError."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1000"), unit=Unit.G)  # Less than requested!
        overage = Quantity(value=Decimal("-200"), unit=Unit.G)
        with pytest.raises(ValueError, match="provided.value.*must be >=.*requested.value"):
            PackPlan(
                food=food,
                requested=requested,
                pack_size=pack_size,
                packs=2,
                provided=provided,
                overage=overage,
            )

    def test_pack_plan_negative_overage_raises(self) -> None:
        """Test that negative overage.value raises ValueError."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1500"), unit=Unit.G)
        overage = Quantity(value=Decimal("-100"), unit=Unit.G)  # Negative!
        with pytest.raises(ValueError, match="overage.value must be non-negative"):
            PackPlan(
                food=food,
                requested=requested,
                pack_size=pack_size,
                packs=3,
                provided=provided,
                overage=overage,
            )

    def test_pack_plan_overage_mismatch_raises(self) -> None:
        """Test that overage.value != provided.value - requested.value raises ValueError."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1500"), unit=Unit.G)
        overage = Quantity(value=Decimal("200"), unit=Unit.G)  # Should be 300!
        with pytest.raises(
            ValueError, match="overage.value.*must equal.*provided.value - requested.value"
        ):
            PackPlan(
                food=food,
                requested=requested,
                pack_size=pack_size,
                packs=3,
                provided=provided,
                overage=overage,
            )

    def test_pack_plan_frozen(self) -> None:
        """Test that PackPlan is immutable."""
        food = FoodRef(food_id="chicken_breast")
        requested = Quantity(value=Decimal("1200"), unit=Unit.G)
        pack_size = Quantity(value=Decimal("500"), unit=Unit.G)
        provided = Quantity(value=Decimal("1500"), unit=Unit.G)
        overage = Quantity(value=Decimal("300"), unit=Unit.G)
        plan = PackPlan(
            food=food,
            requested=requested,
            pack_size=pack_size,
            packs=3,
            provided=provided,
            overage=overage,
        )
        with pytest.raises(Exception):  # frozen dataclass raises
            plan.packs = 4  # type: ignore[misc]
