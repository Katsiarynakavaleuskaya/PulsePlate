"""Behavior helpers for the legacy premium weekly-plan compatibility alias."""

from __future__ import annotations

import math
import sys
from typing import Any, Callable, Dict, Optional, cast

from app.schemas.legacy_premium_weekly_plan import WeeklyMenuResponse


def _coerce_weekly_menu_float(value: Any, default: float = 0.0) -> float:
    """Normalize weekly-menu numeric values for legacy compatibility."""

    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        try:
            coerced = float(value)
        except OverflowError:
            return default
        return coerced if math.isfinite(coerced) else default
    return default


def _is_valid_weekly_menu_number(value: Any) -> bool:
    """Check whether a weekly-menu numeric value is JSON-safe."""

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _normalize_weekly_menu_number_map(raw_values: Any) -> Dict[str, float]:
    """Keep only finite numeric values in weekly-menu maps."""

    if not isinstance(raw_values, dict):
        return {}

    return {
        key: _coerce_weekly_menu_float(value, 0.0)
        for key, value in raw_values.items()
        if isinstance(key, str) and _is_valid_weekly_menu_number(value)
    }


def build_legacy_weekly_menu_response(menu_payload: Dict[str, Any]) -> WeeklyMenuResponse:
    """Translate canonical VIP weekly payload into legacy weekly-menu response."""

    raw_daily_menus = menu_payload.get("daily_menus")
    daily_menus_payload: list[dict[str, Any]] = []
    if isinstance(raw_daily_menus, list):
        for raw_menu in raw_daily_menus:
            if not isinstance(raw_menu, dict):
                continue
            raw_date = raw_menu.get("date")
            raw_meals = raw_menu.get("meals")
            if not isinstance(raw_date, str) or not raw_date.strip():
                continue
            if not isinstance(raw_meals, list):
                continue
            meals = list(raw_meals)
            raw_total_kcal = raw_menu.get("total_kcal")
            if not _is_valid_weekly_menu_number(raw_total_kcal):
                total_kcal = sum(
                    meal.get("kcal", 0)
                    for meal in meals
                    if isinstance(meal, dict) and _is_valid_weekly_menu_number(meal.get("kcal"))
                )
            else:
                total_kcal = raw_total_kcal
            raw_daily_cost = raw_menu.get("daily_cost")
            if not _is_valid_weekly_menu_number(raw_daily_cost):
                raw_daily_cost = raw_menu.get("estimated_cost")
            daily_menus_payload.append(
                {
                    "date": raw_date,
                    "meals": meals,
                    "total_kcal": _coerce_weekly_menu_float(total_kcal, 0.0),
                    "daily_cost": _coerce_weekly_menu_float(raw_daily_cost, 0.0),
                }
            )

    weekly_coverage = _normalize_weekly_menu_number_map(menu_payload.get("weekly_coverage"))
    shopping_list = _normalize_weekly_menu_number_map(menu_payload.get("shopping_list"))

    total_cost = _coerce_weekly_menu_float(menu_payload.get("total_cost"), 0.0)
    adherence_score = _coerce_weekly_menu_float(menu_payload.get("adherence_score"), 0.0)
    week_start = menu_payload.get("week_start", "")
    total_days = len(daily_menus_payload)
    returned_day_cost_total = sum(
        _coerce_weekly_menu_float(day.get("daily_cost"), 0.0) for day in daily_menus_payload
    )

    return WeeklyMenuResponse(
        week_summary={
            "week_start": str(week_start),
            "total_days": total_days,
            "avg_daily_cost": round(returned_day_cost_total / total_days, 2) if total_days else 0.0,
        },
        daily_menus=daily_menus_payload,
        weekly_coverage=weekly_coverage,
        shopping_list=shopping_list,
        total_cost=total_cost,
        adherence_score=adherence_score,
    )


def _get_app_package_module() -> Optional[Any]:
    """Return the loaded `app` package module if present."""

    return sys.modules.get("app")


def _get_legacy_app_module() -> Optional[Any]:
    """Return the loaded `legacy_app` module if present without importing it."""

    return sys.modules.get("legacy_app")


def _resolve_package_weekly_menu_export(package_module: Any) -> Optional[Callable[..., Any]]:
    """Resolve lazy `app.make_weekly_menu` export without surfacing ImportError."""

    try:
        package_builder = getattr(package_module, "make_weekly_menu", None)
    except ImportError:
        return None

    return cast(Callable[..., Any], package_builder) if callable(package_builder) else None


def resolve_legacy_weekly_menu_builder() -> Optional[Callable[..., Any]]:
    """Resolve the canonical weekly-menu builder for the legacy premium alias."""

    def _callable_or_none(value: Any) -> Optional[Callable[..., Any]]:
        return cast(Callable[..., Any], value) if callable(value) else None

    package_module = _get_app_package_module()
    package_namespace = getattr(package_module, "__dict__", {}) if package_module else {}

    if "make_weekly_menu" in package_namespace:
        return _callable_or_none(package_namespace.get("make_weekly_menu"))

    legacy_module = _get_legacy_app_module()
    legacy_namespace = getattr(legacy_module, "__dict__", {}) if legacy_module else {}
    resolved_legacy_builder = _callable_or_none(legacy_namespace.get("make_weekly_menu"))
    if resolved_legacy_builder is not None:
        return resolved_legacy_builder

    if package_module is None:
        return None

    return _resolve_package_weekly_menu_export(package_module)
