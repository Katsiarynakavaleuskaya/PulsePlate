"""App package - shim facade for legacy_app backward compatibility.

This module is intentionally a thin PEP 562 forwarder:
- RU: Не импортируем `legacy_app` eagerly (избегаем циклических импортов).
- EN: Do not eagerly import `legacy_app` (avoid circular imports).

All unknown attributes are resolved from `legacy_app` lazily at access time.
"""

from __future__ import annotations

import importlib
import sys
from functools import lru_cache
from typing import Any, Optional

from core.menu_engine import make_weekly_menu
from core.recommendations import build_nutrition_targets
from core.utils import resolve_attr

# Optional visualization (safe import)
MATPLOTLIB_AVAILABLE: bool = False
generate_bmi_visualization: Optional[Any] = None
try:
    from bmi_visualization import MATPLOTLIB_AVAILABLE, generate_bmi_visualization
except ImportError:
    pass


@lru_cache(maxsize=1)
def _legacy() -> Any:
    """Import legacy_app lazily and cache it.

    RU: Ленивая загрузка, чтобы не ломать порядок импортов (особенно в тестах).
    EN: Lazy import to keep import order stable and prevent cycles.
    """
    legacy = importlib.import_module("legacy_app")
    # Backward-compat for tests/utilities that patch the "real" module by name.
    # RU: Не создаём атрибуты в `app` пакете; используем sys.modules mapping.
    # EN: Do not add extra attributes on the `app` package; use sys.modules mapping.
    sys.modules.setdefault("app_module", legacy)
    return legacy


def __getattr__(name: str) -> Any:
    return getattr(_legacy(), name)


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(dir(_legacy())))


__all__ = [
    # Forwarded from legacy_app via __getattr__
    "app",
    "get_update_scheduler",
    # Local explicit re-exports
    "resolve_attr",
    "make_weekly_menu",
    "build_nutrition_targets",
    "MATPLOTLIB_AVAILABLE",
    "generate_bmi_visualization",
]
