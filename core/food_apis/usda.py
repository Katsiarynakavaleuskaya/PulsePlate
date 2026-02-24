"""Re-export USDAClient under the test-expected import path.

RU: Реэкспорт USDAClient по пути, ожидаемому тестами.
EN: ``from core.food_apis.usda import USDAClient`` works after this module.
"""

from __future__ import annotations

from .usda_client import USDAClient

__all__ = ["USDAClient"]
