# -*- coding: utf-8 -*-
"""ShoplistEngine v1: Clean domain model for shopping list generation.

RU: ShoplistEngine v1: Чистая доменная модель для генерации списков покупок.
EN: ShoplistEngine v1: Clean domain model for shopping list generation.

This module provides a stable, offline-first domain model for shopping list
generation. Stores, prices, and CV integrations will be added as adapters later.

RU: Этот модуль предоставляет стабильную, offline-first доменную модель для
генерации списков покупок. Магазины, цены и CV интеграции будут добавлены
как адаптеры позже.
"""

from .aggregator import aggregate_specs
from .models import (
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
from .normalizer import normalize_ingredient, normalize_quantity, normalize_specs
from .packager import PackagingResult, apply_packaging

__all__ = [
    "FoodForm",
    "FoodRef",
    "IngredientSpec",
    "PackPlan",
    "PackageRule",
    "PackagingResult",
    "Quantity",
    "RoundingMode",
    "ShoplistLine",
    "Unit",
    "aggregate_specs",
    "apply_packaging",
    "normalize_ingredient",
    "normalize_quantity",
    "normalize_specs",
]
