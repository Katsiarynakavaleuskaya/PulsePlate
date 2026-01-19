"""
Shared helper functions for routers.

RU: Общие вспомогательные функции для роутеров.
EN: Shared helper functions for routers.
"""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool) -> bool:
    """
    Parse boolean env var.

    RU/EN note: Accepts common truthy/falsey strings.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default
