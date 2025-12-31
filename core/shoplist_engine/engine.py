# -*- coding: utf-8 -*-
"""ShoplistEngine v1 orchestrator.

RU: ShoplistEngine v1 — тонкий orchestrator пайплайна (pure/offline/deterministic).
EN: ShoplistEngine v1 — thin pipeline orchestrator (pure/offline/deterministic).

This module provides a stateless orchestrator that wires the shopping list
generation pipeline: normalize → aggregate → package.

RU: Этот модуль предоставляет stateless orchestrator, который связывает пайплайн
генерации списка покупок: normalize → aggregate → package.

Инварианты:
- no I/O, no env/time/random
- no FastAPI / SQLAlchemy / app/*
- Decimal-only math (делают нижние слои)
- никаких повторных валидаций — только wiring
"""

from __future__ import annotations

from typing import Optional, Sequence

from .aggregator import aggregate_specs
from .models import IngredientSpec, PackageRule
from .normalizer import normalize_specs
from .packager import PackagingResult, apply_packaging

__all__ = ["ShoplistEngine", "generate_shoplist"]


class ShoplistEngine:
    """
    RU: Stateless orchestrator для пайплайна генерации списка покупок.
    EN: Stateless orchestrator for shopping list generation pipeline.

    Этот класс не содержит бизнес-логики и не дублирует валидации.
    Он только связывает существующие слои: normalize → aggregate → package.
    """

    @staticmethod
    def generate(
        specs: Sequence[IngredientSpec],
        *,
        packaging_rules: Optional[Sequence[PackageRule]] = None,
    ) -> PackagingResult:
        """
        RU: Собирает pipeline: normalize -> aggregate -> package.
        EN: Wires pipeline: normalize -> aggregate -> package.

        Args:
            specs: Последовательность IngredientSpec (входные ингредиенты).
            packaging_rules: Опциональные правила упаковки.

        Returns:
            PackagingResult с packed и unpacked линиями.

        Важно:
        - Не ловим исключения: ошибки lower-level слоёв должны bubble-up.
        - Не делаем повторную валидацию: lower layers fail-fast.
        """
        normalized = normalize_specs(specs)
        aggregated = aggregate_specs(normalized)
        return apply_packaging(
            aggregated,
            packaging_rules or (),
        )


def generate_shoplist(
    specs: Sequence[IngredientSpec],
    *,
    packaging_rules: Optional[Sequence[PackageRule]] = None,
) -> PackagingResult:
    """
    RU: Функциональный entrypoint (удобно для тестов/интеграции).
    EN: Functional entrypoint (nice for tests/integration).

    Args:
        specs: Последовательность IngredientSpec (входные ингредиенты).
        packaging_rules: Опциональные правила упаковки.

    Returns:
        PackagingResult с packed и unpacked линиями.
    """
    return ShoplistEngine.generate(specs, packaging_rules=packaging_rules)
