"""App package facade with a finite backward-compatibility surface.

This module intentionally resolves only explicitly declared lazy exports:
- RU: Не импортируем `legacy_app` eagerly (избегаем циклических импортов).
- EN: Do not eagerly import `legacy_app` (avoid circular imports).

Names that are neither ordinary package attributes nor declared compatibility
exports fail closed without importing `legacy_app`.
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
    "lifespan": ("app.bootstrap.lifespan", "application_lifespan"),
    "get_update_scheduler": (
        "app.services.scheduler_access",
        "get_update_scheduler",
    ),
    "api_key_header": ("app.routers.api_key", "api_key_header"),
    "get_api_key": ("app.routers.api_key", "get_api_key"),
    "_get_api_key_dynamic": ("app.routers.api_key", "_get_api_key_dynamic"),
    # BMI router ownership lives in app.main; these remain compatibility attrs.
    "FEATURE_BMI_PRO_ENABLED": ("app.main", "FEATURE_BMI_PRO_ENABLED"),
    "bmi_router": ("app.main", "bmi_router"),
    "bmi_pro_router": ("app.main", "bmi_pro_router"),
    "bmi_pro_legacy_alias_router": ("app.main", "bmi_pro_legacy_alias_router"),
    "get_bodyfat_router": ("app.routers.bodyfat", "get_router"),
    "BMIRequest": ("app.schemas.bmi_compat", "BMIRequest"),
    "_is_truthy": ("app.utils.feature_flags", "_is_truthy"),
    "_macros_to_kcal": ("app.services.pro_nutrition_plate", "_macros_to_kcal"),
}


def _ensure_canonical_bootstrap() -> Any:
    """Compose and return the canonical singleton without adopting legacy state."""

    main_module = sys.modules.get("app.main")
    if main_module is None:
        main_module = importlib.import_module("app.main")

    application_module = importlib.import_module("app.bootstrap.application")
    canonical_app = getattr(application_module, "app")
    ensure_bootstrap = getattr(main_module, "ensure_canonical_app_bootstrap", None)
    if callable(ensure_bootstrap):
        ensure_bootstrap(canonical_app)
    _legacy()  # Preserve the finite ``app_module`` compatibility seam.
    return canonical_app


@lru_cache(maxsize=1)
def _legacy() -> Any:
    """Load the retained legacy FastAPI instance and ``app_module`` alias.

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
    """Resolve an explicitly supported compatibility export lazily.

    Unknown names fail closed and do not load ``legacy_app``.
    """
    if name == "app":
        return _ensure_canonical_bootstrap()
    if name in _LOCAL_EXPORTS:
        mod_name, attr = _LOCAL_EXPORTS[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LOCAL_EXPORTS) | {"app"})


__all__ = [
    # Explicit compatibility exports resolved via __getattr__
    "app",
    "get_update_scheduler",
    "lifespan",
    "get_api_key",
    # Local explicit re-exports
    "resolve_attr",
    "make_weekly_menu",
    "build_nutrition_targets",
    "FEATURE_BMI_PRO_ENABLED",
    "bmi_router",
    "bmi_pro_router",
    "bmi_pro_legacy_alias_router",
    "get_bodyfat_router",
    "MATPLOTLIB_AVAILABLE",
    "generate_bmi_visualization",
]
