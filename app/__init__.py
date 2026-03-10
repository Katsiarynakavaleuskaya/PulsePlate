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

# Optional visualization (safe import with aliases)
MATPLOTLIB_AVAILABLE: bool = False
generate_bmi_visualization: Optional[Any] = None
try:
    from bmi_visualization import (
        MATPLOTLIB_AVAILABLE as _MPL_OK,
        generate_bmi_visualization as _gen_viz,
    )

    MATPLOTLIB_AVAILABLE = _MPL_OK
    generate_bmi_visualization = _gen_viz
except ImportError:
    pass

# Local explicit re-exports (lazy-loaded to avoid import-time side effects)
# RU: Ленивые ре-экспорты из core.*, чтобы не тянуть БД/модели на import-time.
# EN: Lazy re-exports from core.* to avoid pulling DB/models at import-time.
_LOCAL_EXPORTS: dict[str, tuple[str, str]] = {
    # name: (module, attr)
    "resolve_attr": ("core.utils", "resolve_attr"),
    "make_weekly_menu": ("core.menu_engine", "make_weekly_menu"),
    "build_nutrition_targets": ("core.recommendations", "build_nutrition_targets"),
    # Expose metrics_endpoint for patch-based tests (patch("app.metrics"))
    "metrics": ("app.bootstrap.metrics", "metrics_endpoint"),
}


@lru_cache(maxsize=1)
def _ensure_canonical_bootstrap() -> None:
    """Run canonical additive bootstrap without changing facade identity.

    RU: Импорт `app.main` нужен только для запуска additive bootstrap поверх
    `legacy_app.app`; наружу пакет всё равно должен отдавать именно
    `legacy_app.app`, чтобы сохранялся инвариант identity в тестах и reload path.
    EN: Import `app.main` only to execute additive bootstrap on top of
    `legacy_app.app`; the package must still expose `legacy_app.app` itself to
    preserve identity under tests and reload scenarios.
    """
    importlib.import_module("app.main")


@lru_cache(maxsize=1)
def _legacy() -> Any:
    """Import legacy_app lazily and cache it.

    RU: Ленивая загрузка, чтобы не ломать порядок импортов (особенно в тестах).
    EN: Lazy import to keep import order stable and prevent cycles.
    """
    legacy = importlib.import_module("legacy_app")
    # Keep app facade compatible while ensuring canonical OpenAPI filtering is installed.
    install_openapi_builder = getattr(legacy, "_install_openapi_builder", None)
    legacy_app_instance = getattr(legacy, "app", None)
    if callable(install_openapi_builder) and legacy_app_instance is not None:
        install_openapi_builder(legacy_app_instance)
    # Backward-compat for tests/utilities that patch the "real" module by name.
    # RU: Не создаём атрибуты в `app` пакете; используем sys.modules mapping.
    # EN: Do not add extra attributes on the `app` package; use sys.modules mapping.
    sys.modules.setdefault("app_module", legacy)
    return legacy


def __getattr__(name: str) -> Any:
    """Resolve attribute lazily from local exports or legacy_app.

    RU: Сначала проверяем локальные ре-экспорты (core.*), затем legacy_app.
    EN: First check local re-exports (core.*), then fall back to legacy_app.

    PEP 562 forwarder: pure delegation, no side effects.
    Observability bootstrap (register_metrics) is applied ONLY in app/main.py.
    """
    if name == "app":
        _ensure_canonical_bootstrap()
        return getattr(_legacy(), "app")
    if name in _LOCAL_EXPORTS:
        mod_name, attr = _LOCAL_EXPORTS[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
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
