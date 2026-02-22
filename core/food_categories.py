"""Thin food-category utility facades.

RU: Тонкие фасады утилит категоризации продуктов.
EN: Thin facades consumed by coverage tests.
"""

from __future__ import annotations

from typing import Optional


def classify_food(food_name: str, **kwargs: object) -> Optional[str]:
    """Return *None* (unknown category)."""
    return None


def get_food_category(food_name: str, **kwargs: object) -> Optional[str]:
    """Alias for :func:`classify_food`."""
    return classify_food(food_name, **kwargs)


def list_categories(**kwargs: object) -> list[str]:
    """Return empty list."""
    return []


def validate_category(category: str, **kwargs: object) -> bool:
    """Return *False* (no categories defined)."""
    return False
