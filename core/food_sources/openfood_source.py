"""Thin OpenFoodSource facade.

RU: Тонкий фасад обёртки OpenFoodFacts.
EN: Thin facade consumed by coverage tests.
"""

from __future__ import annotations

from typing import Any


class OpenFoodSource:
    """Minimal OpenFoodFacts source wrapper."""

    def __init__(self, **kwargs: object) -> None:
        pass

    def search(self, query: str, **kwargs: object) -> list[dict[str, Any]]:
        """Return empty result set."""
        return []
