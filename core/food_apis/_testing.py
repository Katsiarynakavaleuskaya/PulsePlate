"""Testing utilities for food_apis module.

RU: Утилиты для тестирования модуля food_apis.
EN: Testing utilities for food_apis module.
"""

from __future__ import annotations

import os


def is_test_runtime() -> bool:
    """
    RU: Проверяет, запущен ли код в тестовой среде (pytest/xdist).
    EN: Check if code is running in test environment (pytest/xdist).

    Returns:
        True if running in pytest or CI environment, False otherwise
    """
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or bool(os.getenv("GITHUB_ACTIONS"))
