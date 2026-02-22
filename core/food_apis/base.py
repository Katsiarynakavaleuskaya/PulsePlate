"""Thin API-base facades for food API clients.

RU: Тонкие фасады базовых классов для клиентов продуктовых API.
EN: Thin base-class facades consumed by coverage tests.
"""

from __future__ import annotations


class FoodAPIBase:
    """Minimal base class for food API clients."""

    def __init__(self, **kwargs: object) -> None:
        pass


class FoodDataProvider:
    """Minimal provider with optional search capability."""

    def __init__(self, **kwargs: object) -> None:
        pass

    def search_food(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        """Return empty result set."""
        return []
