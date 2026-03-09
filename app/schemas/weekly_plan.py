"""Canonical weekly-plan DTOs and payload normalization helpers."""

from __future__ import annotations

import math
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict


def _coerce_float(value: Any) -> float | None:
    """Convert supported numeric-like values to float; reject invalid values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric_value):
        return None
    return numeric_value


def _normalize_numeric_map(raw_value: Any) -> dict[str, float]:
    """Keep only string->float pairs for OpenAPI-stable numeric maps."""
    if not isinstance(raw_value, Mapping):
        return {}

    normalized: dict[str, float] = {}
    for key, value in raw_value.items():
        if not isinstance(key, str):
            continue
        numeric_value = _coerce_float(value)
        if numeric_value is None:
            continue
        normalized[key] = numeric_value
    return normalized


def _normalize_meal_item(raw_value: Any) -> dict[str, Any]:
    """Normalize one meal entry into the canonical typed payload."""
    payload = raw_value if isinstance(raw_value, Mapping) else {}
    title = str(payload.get("title") or "")
    title_translated = str(payload.get("title_translated") or title)

    return {
        "title": title,
        "title_translated": title_translated,
        "grams": _normalize_numeric_map(payload.get("grams")),
        "kcal": _coerce_float(payload.get("kcal")) or 0.0,
        "macros": _normalize_numeric_map(payload.get("macros")),
        "micros": _normalize_numeric_map(payload.get("micros")),
        "price_est": _coerce_float(payload.get("price_est")),
    }


def _normalize_day_menu(raw_value: Any) -> dict[str, Any]:
    """Normalize one day menu into the canonical typed payload."""
    payload = raw_value if isinstance(raw_value, Mapping) else {}
    raw_meals = payload.get("meals")
    meals = (
        [_normalize_meal_item(meal) for meal in raw_meals] if isinstance(raw_meals, list) else []
    )

    raw_tips = payload.get("tips")
    tips = [str(tip) for tip in raw_tips] if isinstance(raw_tips, list) else []

    total_cost = _coerce_float(payload.get("total_cost"))
    if total_cost is None:
        total_cost = round(
            sum(meal["price_est"] or 0.0 for meal in meals),
            2,
        )

    return {
        "meals": meals,
        "kcal": _coerce_float(payload.get("kcal")) or 0.0,
        "macros": _normalize_numeric_map(payload.get("macros")),
        "micros": _normalize_numeric_map(payload.get("micros")),
        "coverage": _normalize_numeric_map(payload.get("coverage")),
        "tips": tips,
        "total_cost": total_cost,
    }


def normalize_weekly_plan_payload(raw_value: Any) -> dict[str, Any]:
    """Normalize build_week output before validating with typed DTOs."""
    payload = raw_value if isinstance(raw_value, Mapping) else {}
    raw_daily_menus = payload.get("daily_menus")
    daily_menus = (
        [_normalize_day_menu(day) for day in raw_daily_menus]
        if isinstance(raw_daily_menus, list)
        else []
    )

    total_cost = _coerce_float(payload.get("total_cost"))
    if total_cost is None:
        total_cost = round(sum(day["total_cost"] for day in daily_menus), 2)

    return {
        "daily_menus": daily_menus,
        "weekly_coverage": _normalize_numeric_map(payload.get("weekly_coverage")),
        "shopping_list": _normalize_numeric_map(payload.get("shopping_list")),
        "total_cost": total_cost,
        "adherence_score": _coerce_float(payload.get("adherence_score")) or 0.0,
    }


def require_weekly_plan_payload_shape(raw_value: Any) -> Mapping[str, Any]:
    """Fail closed when build_week returns a payload outside the public contract."""
    if not isinstance(raw_value, Mapping):
        raise ValueError("weekly plan payload must be a mapping")

    raw_daily_menus = raw_value.get("daily_menus")
    if not isinstance(raw_daily_menus, list):
        raise ValueError("weekly plan payload missing required daily_menus list")

    return raw_value


class WeeklyMealPlanItem(BaseModel):
    """Typed representation of one generated meal entry."""

    model_config = ConfigDict(title="WeeklyMealPlanItem")

    title: str
    title_translated: str
    grams: dict[str, float]
    kcal: float
    macros: dict[str, float]
    micros: dict[str, float]
    price_est: float | None = None


class WeeklyMealPlanDayMenu(BaseModel):
    """Typed representation of one generated day menu."""

    model_config = ConfigDict(title="WeeklyMealPlanDayMenu")

    meals: list[WeeklyMealPlanItem]
    kcal: float
    macros: dict[str, float]
    micros: dict[str, float]
    coverage: dict[str, float]
    tips: list[str]
    total_cost: float


class WeeklyMealPlanResponse(BaseModel):
    """Typed canonical response for PRO/premium weekly-plan endpoints."""

    model_config = ConfigDict(title="WeeklyMealPlanResponse")

    daily_menus: list[WeeklyMealPlanDayMenu]
    weekly_coverage: dict[str, float]
    shopping_list: dict[str, float]
    total_cost: float
    adherence_score: float
