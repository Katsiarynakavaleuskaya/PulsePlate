"""Thin USDASource facade.

RU: Тонкий фасад обёртки USDA.
EN: Thin facade consumed by coverage tests.
"""

from __future__ import annotations


class USDASource:
    """Minimal USDA source wrapper."""

    def __init__(self, **kwargs: object) -> None:
        pass

    def get_food_data(self, food_id: str, **kwargs: object) -> dict[str, object] | None:
        """Return None (no data available)."""
        return None
