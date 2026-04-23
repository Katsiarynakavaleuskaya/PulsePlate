"""Core package exports.

RU: Ленивая публикация публичных symbol exports, чтобы import `core`
не тянул тяжёлые runtime-зависимости для offline/contract entrypoints.
EN: Lazily expose public symbols so importing `core` does not eagerly load
heavy runtime dependencies for offline/contract entrypoints.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

_EXPORT_MAP = {
    "make_plate": (".plate", "make_plate"),
    "UserProfile": (".targets", "UserProfile"),
    "NutritionTargets": (".targets", "NutritionTargets"),
    "build_nutrition_targets": (".recommendations", "build_nutrition_targets"),
    "make_daily_menu": (".menu_engine", "make_daily_menu"),
    "make_weekly_menu": (".menu_engine", "make_weekly_menu"),
    "analyze_nutrient_gaps": (".menu_engine", "analyze_nutrient_gaps"),
}

if TYPE_CHECKING:
    from .menu_engine import analyze_nutrient_gaps, make_daily_menu, make_weekly_menu
    from .plate import make_plate
    from .recommendations import build_nutrition_targets
    from .targets import NutritionTargets, UserProfile


def __getattr__(name: str) -> Any:
    """Resolve exported core symbols lazily to keep package import-light."""

    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name, package=__name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = [
    "make_plate",
    "UserProfile",
    "NutritionTargets",
    "build_nutrition_targets",
    "make_daily_menu",
    "make_weekly_menu",
    "analyze_nutrient_gaps",
]
