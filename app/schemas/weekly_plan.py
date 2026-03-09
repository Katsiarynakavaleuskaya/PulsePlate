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


def _require_mapping(raw_value: Any, field_name: str) -> Mapping[str, Any]:
    """Require a mapping payload for typed weekly-plan normalization."""
    if not isinstance(raw_value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    return raw_value


def _require_non_empty_string(value: Any, field_name: str) -> str:
    """Require a non-empty string for canonical typed fields."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _require_float(value: Any, field_name: str) -> float:
    """Require a finite numeric value for canonical typed fields."""
    numeric_value = _coerce_float(value)
    if numeric_value is None:
        raise ValueError(f"{field_name} must be a finite number")
    return numeric_value


def _normalize_numeric_map(raw_value: Any, field_name: str) -> dict[str, float]:
    """Keep only string->float pairs for OpenAPI-stable numeric maps."""
    if raw_value is None:
        return {}
    mapping = _require_mapping(raw_value, field_name)

    normalized: dict[str, float] = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} keys must be strings")
        numeric_value = _require_float(value, f"{field_name}.{key}")
        normalized[key] = numeric_value
    return normalized


def _normalize_meal_item(raw_value: Any) -> dict[str, Any]:
    """Normalize one meal entry into the canonical typed payload."""
    payload = _require_mapping(raw_value, "daily_menus[].meals[]")
    title = _require_non_empty_string(payload.get("title"), "daily_menus[].meals[].title")
    raw_title_translated = payload.get("title_translated")
    if raw_title_translated is None:
        title_translated = title
    else:
        title_translated = _require_non_empty_string(
            raw_title_translated,
            "daily_menus[].meals[].title_translated",
        )

    return {
        "title": title,
        "title_translated": title_translated,
        "grams": _normalize_numeric_map(payload.get("grams"), "daily_menus[].meals[].grams"),
        "kcal": _require_float(payload.get("kcal"), "daily_menus[].meals[].kcal"),
        "macros": _normalize_numeric_map(payload.get("macros"), "daily_menus[].meals[].macros"),
        "micros": _normalize_numeric_map(payload.get("micros"), "daily_menus[].meals[].micros"),
        "price_est": (
            None
            if payload.get("price_est") is None
            else _require_float(payload.get("price_est"), "daily_menus[].meals[].price_est")
        ),
    }


def _normalize_day_menu(raw_value: Any) -> dict[str, Any]:
    """Normalize one day menu into the canonical typed payload."""
    payload = _require_mapping(raw_value, "daily_menus[]")
    raw_meals = payload.get("meals")
    if not isinstance(raw_meals, list):
        raise ValueError("daily_menus[].meals must be a list")
    meals = [_normalize_meal_item(meal) for meal in raw_meals]

    raw_tips = payload.get("tips")
    if raw_tips is None:
        tips: list[str] = []
    elif isinstance(raw_tips, list):
        tips = [_require_non_empty_string(tip, "daily_menus[].tips[]") for tip in raw_tips]
    else:
        raise ValueError("daily_menus[].tips must be a list of strings")

    total_cost = _coerce_float(payload.get("total_cost"))
    if payload.get("total_cost") is None:
        total_cost = round(
            sum(meal["price_est"] or 0.0 for meal in meals),
            2,
        )
    elif total_cost is None:
        raise ValueError("daily_menus[].total_cost must be a finite number")

    return {
        "meals": meals,
        "kcal": _require_float(payload.get("kcal"), "daily_menus[].kcal"),
        "macros": _normalize_numeric_map(payload.get("macros"), "daily_menus[].macros"),
        "micros": _normalize_numeric_map(payload.get("micros"), "daily_menus[].micros"),
        "coverage": _normalize_numeric_map(payload.get("coverage"), "daily_menus[].coverage"),
        "tips": tips,
        "total_cost": total_cost,
    }


def normalize_weekly_plan_payload(raw_value: Any) -> dict[str, Any]:
    """Normalize build_week output before validating with typed DTOs."""
    payload = _require_mapping(raw_value, "weekly_plan")
    raw_daily_menus = payload.get("daily_menus")
    if not isinstance(raw_daily_menus, list):
        raise ValueError("weekly plan payload missing required daily_menus list")
    daily_menus = [_normalize_day_menu(day) for day in raw_daily_menus]

    total_cost = _coerce_float(payload.get("total_cost"))
    if payload.get("total_cost") is None:
        total_cost = round(sum(day["total_cost"] for day in daily_menus), 2)
    elif total_cost is None:
        raise ValueError("weekly_plan.total_cost must be a finite number")

    return {
        "daily_menus": daily_menus,
        "weekly_coverage": _normalize_numeric_map(
            payload.get("weekly_coverage"),
            "weekly_coverage",
        ),
        "shopping_list": _normalize_numeric_map(payload.get("shopping_list"), "shopping_list"),
        "total_cost": total_cost,
        "adherence_score": _require_float(payload.get("adherence_score"), "adherence_score"),
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
