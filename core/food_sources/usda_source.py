"""Thin USDASource facade.

RU: Тонкий фасад обёртки USDA.
EN: Thin facade consumed by coverage tests.
"""

from __future__ import annotations

from typing import Any, Optional


class USDASource:
    """Minimal USDA source wrapper."""

    def __init__(self, **kwargs: object) -> None:
        pass

    def get_food_data(self, food_id: str, **kwargs: object) -> Optional[dict[str, Any]]:
        """Return None (no data available)."""
        return None
