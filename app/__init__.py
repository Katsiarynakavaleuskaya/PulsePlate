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
}


def _ensure_canonical_bootstrap() -> None:
    """Run canonical additive bootstrap without changing facade identity.

    RU: Импорт `app.main` нужен только для запуска additive bootstrap поверх
    `legacy_app.app`; наружу пакет всё равно должен отдавать именно
    `legacy_app.app`, чтобы сохранялся инвариант identity в тестах и reload path.
    EN: Import `app.main` only to execute additive bootstrap on top of
    `legacy_app.app`; the package must still expose `legacy_app.app` itself to
    preserve identity under tests and reload scenarios.
    """
    legacy_app_instance = getattr(_legacy(), "app")
    main_module = sys.modules.get("app.main")

    if main_module is None:
        main_module = importlib.import_module("app.main")

    main_app_instance = getattr(main_module, "app", None)
    ensure_bootstrap = getattr(main_module, "ensure_canonical_app_bootstrap", None)
    if main_app_instance is legacy_app_instance:
        # RU: Даже при совпадающем объекте дополнительно удерживаем ссылку
        # `app.main.app` синхронизированной для reload / monkeypatch churn.
        # EN: Keep `app.main.app` synchronized even when identity already matches
        # to stabilize reload / monkeypatch churn across Python versions.
        setattr(main_module, "app", legacy_app_instance)
        return

    if callable(ensure_bootstrap):
        ensure_bootstrap(legacy_app_instance)
        return

    # RU: Фолбэк только для safety-path; нормальный runtime идёт через
    # `ensure_canonical_app_bootstrap` в app.main.
    # EN: Safety fallback only; normal runtime should go through
    # `ensure_canonical_app_bootstrap` in app.main.
    setattr(main_module, "app", legacy_app_instance)


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
