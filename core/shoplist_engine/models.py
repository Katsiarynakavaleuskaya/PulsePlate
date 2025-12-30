# -*- coding: utf-8 -*-
"""Domain models for ShoplistEngine v1.

RU: Доменные модели для ShoplistEngine v1.
EN: Domain models for ShoplistEngine v1.

This module defines the core domain model for shopping list generation:
- Units and quantities (normalized to base units)
- Food references (canonical food_id)
- Ingredient specifications (input to engine)
- Shoplist lines (aggregated output)
- Packaging rules and plans (rounding to packages)

RU: Этот модуль определяет основную доменную модель для генерации списков покупок:
- Единицы и количества (нормализованы к базовым единицам)
- Ссылки на продукты (канонический food_id)
- Спецификации ингредиентов (вход в движок)
- Строки списка покупок (агрегированный выход)
- Правила и планы упаковки (округление до упаковок)

All models are immutable (frozen dataclasses) and use Decimal for precision.
RU: Все модели неизменяемы (frozen dataclasses) и используют Decimal для точности.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class Unit(str, Enum):
    """Base measurement units for deterministic aggregation.

    RU: Базовые единицы измерения для детерминированного суммирования.

    Base units (G, ML, PCS) are used for aggregation.
    Convenience units (KG, L) are normalized to base units.

    RU: Базовые единицы (G, ML, PCS) используются для агрегирования.
    Удобные единицы (KG, L) нормализуются к базовым.
    """

    G = "g"
    ML = "ml"
    PCS = "pcs"
    KG = "kg"  # convenience, normalized to G
    L = "l"  # convenience, normalized to ML


class FoodForm(str, Enum):
    """Food form can affect conversions later (not used in v1 math).

    RU: Форма продукта может влиять на конверсии позже (в v1 не влияет на математику).

    This enum is reserved for future use when we need to account for
    weight changes during cooking (e.g., raw vs cooked chicken).

    RU: Этот enum зарезервирован для будущего использования, когда нужно будет
    учитывать изменения веса при готовке (например, сырая vs приготовленная курица).
    """

    RAW = "raw"
    COOKED = "cooked"
    FROZEN = "frozen"
    DRIED = "dried"
    CANNED = "canned"


class RoundingMode(str, Enum):
    """How to round packs.

    RU: Как округлять количество упаковок.

    - CEIL: Always round up (e.g., 1.2 packs → 2 packs)
    - NEAREST: Round to nearest (e.g., 1.2 packs → 1 pack, 1.6 packs → 2 packs)
    - NONE: No rounding (exact quantity, may result in fractional packs)

    RU:
    - CEIL: Всегда округлять вверх (например, 1.2 упаковки → 2 упаковки)
    - NEAREST: Округлить до ближайшего (например, 1.2 → 1, 1.6 → 2)
    - NONE: Без округления (точное количество, может быть дробное число упаковок)
    """

    CEIL = "ceil"
    NEAREST = "nearest"
    NONE = "none"


@dataclass(frozen=True)
class Quantity:
    """A value with unit. Use Decimal for reproducibility.

    RU: Значение + единица. Decimal даёт воспроизводимость и аккуратность.

    Examples:
        Quantity(Decimal("500"), Unit.G)  # 500 grams
        Quantity(Decimal("1.5"), Unit.L)  # 1.5 liters
        Quantity(Decimal("10"), Unit.PCS)  # 10 pieces

    RU: Примеры:
        Quantity(Decimal("500"), Unit.G)  # 500 грамм
        Quantity(Decimal("1.5"), Unit.L)  # 1.5 литра
        Quantity(Decimal("10"), Unit.PCS)  # 10 штук
    """

    value: Decimal
    unit: Unit

    # Conversion constants for convenience units
    KG_TO_G = Decimal("1000")
    L_TO_ML = Decimal("1000")

    def __post_init__(self) -> None:
        """Validate quantity value.

        RU: Валидация значения количества.
        """
        if self.value < 0:
            raise ValueError(f"Quantity value must be non-negative, got {self.value}")
        # Allow zero for edge cases (empty shoplist lines)

    def to_base_unit(self) -> "Quantity":
        """Return quantity converted to base units when possible.

        RU: Возвращает Quantity, приведённый к базовым единицам, если это возможно.

        Converts KG → G and L → ML. Base units (G, ML, PCS) are returned unchanged.

        RU: Конвертирует KG → G и L → ML. Базовые единицы (G, ML, PCS) возвращаются без изменений.

        Examples:
            Quantity(Decimal("1.5"), Unit.KG).to_base_unit()  # Quantity(1500, G)
            Quantity(Decimal("2"), Unit.L).to_base_unit()  # Quantity(2000, ML)
            Quantity(Decimal("500"), Unit.G).to_base_unit()  # Quantity(500, G) (unchanged)

        RU: Примеры:
            Quantity(Decimal("1.5"), Unit.KG).to_base_unit()  # Quantity(1500, G)
            Quantity(Decimal("2"), Unit.L).to_base_unit()  # Quantity(2000, ML)
            Quantity(Decimal("500"), Unit.G).to_base_unit()  # Quantity(500, G) (без изменений)
        """
        if self.unit == Unit.KG:
            return Quantity(value=self.value * self.KG_TO_G, unit=Unit.G)
        if self.unit == Unit.L:
            return Quantity(value=self.value * self.L_TO_ML, unit=Unit.ML)
        return self


@dataclass(frozen=True)
class FoodRef:
    """Canonical reference to a food item.

    RU: Каноническая ссылка на продукт.

    This is a minimal reference that points to a stable food_id.
    Display names and other metadata are handled by adapters/UI layers.

    RU: Это минимальная ссылка, указывающая на стабильный food_id.
    Отображаемые имена и другая метаданные обрабатываются адаптерами/UI слоями.

    Examples:
        FoodRef(food_id="chicken_breast")
        FoodRef(food_id="tomato_raw")

    RU: Примеры:
        FoodRef(food_id="chicken_breast")
        FoodRef(food_id="tomato_raw")
    """

    food_id: str

    def __post_init__(self) -> None:
        """Validate food_id.

        RU: Валидация food_id.
        """
        if not self.food_id or not self.food_id.strip():
            raise ValueError("food_id must be non-empty")


@dataclass(frozen=True)
class IngredientSpec:
    """Ingredient in a recipe/plan (engine input).

    RU: Ингредиент в рецепте/плане (вход движка).

    This is the input to the shoplist engine. It represents one ingredient
    from a recipe or meal plan that needs to be purchased.

    RU: Это вход в движок списка покупок. Представляет один ингредиент
    из рецепта или плана питания, который нужно купить.

    Examples:
        IngredientSpec(
            food=FoodRef(food_id="chicken_breast"),
            qty=Quantity(Decimal("500"), Unit.G),
            form=FoodForm.RAW
        )

    RU: Примеры:
        IngredientSpec(
            food=FoodRef(food_id="chicken_breast"),
            qty=Quantity(Decimal("500"), Unit.G),
            form=FoodForm.RAW
        )
    """

    food: FoodRef
    qty: Quantity
    form: FoodForm = FoodForm.RAW
    notes: Optional[str] = None


@dataclass(frozen=True)
class ShoplistLine:
    """Aggregated line before packaging.

    RU: Агрегированная строка до упаковок.

    This represents one line in the shopping list after aggregation
    (summing quantities by food_id) but before packaging rules are applied.

    RU: Представляет одну строку в списке покупок после агрегирования
    (суммирование количеств по food_id), но до применения правил упаковки.

    Examples:
        ShoplistLine(
            food=FoodRef(food_id="chicken_breast"),
            qty=Quantity(Decimal("1200"), Unit.G)  # Sum of all chicken in week
        )

    RU: Примеры:
        ShoplistLine(
            food=FoodRef(food_id="chicken_breast"),
            qty=Quantity(Decimal("1200"), Unit.G)  # Сумма всей курицы за неделю
        )
    """

    food: FoodRef
    qty: Quantity


@dataclass(frozen=True)
class PackageRule:
    """Packaging rule for a given food_id (v1).

    RU: Правило упаковки для food_id (v1).

    In v1, rules match by food_id only. Future versions may support
    category/tag-based matching.

    RU: В v1 правила сопоставляются только по food_id. Будущие версии могут
    поддерживать сопоставление по категории/тегу.

    Examples:
        PackageRule(
            food_id="chicken_breast",
            pack_size=Quantity(Decimal("500"), Unit.G),
            rounding=RoundingMode.CEIL,
            min_packs=1
        )

    RU: Примеры:
        PackageRule(
            food_id="chicken_breast",
            pack_size=Quantity(Decimal("500"), Unit.G),
            rounding=RoundingMode.CEIL,
            min_packs=1
        )
    """

    food_id: str
    pack_size: Quantity
    rounding: RoundingMode = RoundingMode.CEIL
    min_packs: int = 1

    def __post_init__(self) -> None:
        """Validate package rule.

        RU: Валидация правила упаковки.
        """
        if not self.food_id or not self.food_id.strip():
            raise ValueError("food_id must be non-empty")
        if self.min_packs < 1:
            raise ValueError(f"min_packs must be >= 1, got {self.min_packs}")
        if self.pack_size.value <= 0:
            raise ValueError(f"pack_size must be positive, got {self.pack_size.value}")
        if self.pack_size.unit in (Unit.KG, Unit.L):
            raise ValueError(f"pack_size must use base units (g/ml/pcs), got {self.pack_size.unit}")


@dataclass(frozen=True)
class PackPlan:
    """Packaging result for one shoplist line.

    RU: Результат упаковки для одной строки списка покупок.

    This represents the result of applying a PackageRule to a ShoplistLine.
    It shows how many packs are needed and what the overage is.

    RU: Представляет результат применения PackageRule к ShoplistLine.
    Показывает, сколько упаковок нужно и какой избыток.

    Examples:
        PackPlan(
            food=FoodRef(food_id="chicken_breast"),
            requested=Quantity(Decimal("1200"), Unit.G),
            pack_size=Quantity(Decimal("500"), Unit.G),
            packs=3,  # ceil(1200 / 500) = 3
            provided=Quantity(Decimal("1500"), Unit.G),  # 3 * 500
            overage=Quantity(Decimal("300"), Unit.G)  # 1500 - 1200
        )

    RU: Примеры:
        PackPlan(
            food=FoodRef(food_id="chicken_breast"),
            requested=Quantity(Decimal("1200"), Unit.G),
            pack_size=Quantity(Decimal("500"), Unit.G),
            packs=3,  # ceil(1200 / 500) = 3
            provided=Quantity(Decimal("1500"), Unit.G),  # 3 * 500
            overage=Quantity(Decimal("300"), Unit.G)  # 1500 - 1200
        )
    """

    food: FoodRef
    requested: Quantity
    pack_size: Quantity
    packs: int
    provided: Quantity
    overage: Quantity

    def __post_init__(self) -> None:
        """Validate pack plan.

        RU: Валидация плана упаковки.

        Validates:
        - Unit consistency across all quantities
        - Non-negative packs
        - Arithmetic consistency: provided = packs * pack_size, provided >= requested
        - overage = provided - requested (exact match for Decimal)

        RU: Валидирует:
        - Согласованность единиц во всех количествах
        - Неотрицательное количество упаковок
        - Арифметическую согласованность: provided = packs * pack_size, provided >= requested
        - overage = provided - requested (точное совпадение для Decimal)
        """
        if self.packs < 0:
            raise ValueError(f"packs must be non-negative, got {self.packs}")
        if self.requested.unit != self.pack_size.unit:
            raise ValueError(
                f"Unit mismatch: requested.unit={self.requested.unit}, "
                f"pack_size.unit={self.pack_size.unit}"
            )
        if self.provided.unit != self.requested.unit:
            raise ValueError(
                f"Unit mismatch: provided.unit={self.provided.unit}, "
                f"requested.unit={self.requested.unit}"
            )
        if self.overage.unit != self.requested.unit:
            raise ValueError(
                f"Unit mismatch: overage.unit={self.overage.unit}, "
                f"requested.unit={self.requested.unit}"
            )
        # Arithmetic consistency validations
        # Verify provided = packs * pack_size (if pack_size > 0)
        if self.pack_size.value > 0:
            expected_provided = self.pack_size.value * Decimal(self.packs)
            if self.provided.value != expected_provided:
                raise ValueError(
                    f"provided.value ({self.provided.value}) must equal "
                    f"packs * pack_size.value ({expected_provided})"
                )
        if self.provided.value < self.requested.value:
            raise ValueError(
                f"provided.value ({self.provided.value}) must be >= "
                f"requested.value ({self.requested.value})"
            )
        if self.overage.value < 0:
            raise ValueError(f"overage.value must be non-negative, got {self.overage.value}")
        # Verify overage = provided - requested (exact for Decimal)
        expected_overage = self.provided.value - self.requested.value
        if self.overage.value != expected_overage:
            raise ValueError(
                f"overage.value ({self.overage.value}) must equal "
                f"provided.value - requested.value ({expected_overage})"
            )
