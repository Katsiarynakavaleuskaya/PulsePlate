"""Application-level nutrition target adapters for weekly planning."""

from __future__ import annotations

from typing import Any, TypedDict

from core.recommendations import build_nutrition_targets
from core.targets import Activity, Goal, Sex, UserProfile

PlanningNumeric = int | float


class PlanningTargetsPayload(TypedDict):
    """Weekly-planning target payload shape consumed by plan generators."""

    kcal: int
    macros: dict[str, PlanningNumeric]
    micro: dict[str, PlanningNumeric]
    water_ml: int
    activity_week: dict[str, int]


def is_complete_planning_targets(targets: dict[str, Any]) -> bool:
    """Return whether a target payload is complete enough for weekly planning."""
    required_keys = {"kcal", "macros", "micro", "water_ml"}
    if not required_keys.issubset(targets.keys()):
        return False
    if not isinstance(targets.get("macros"), dict):
        return False
    if not isinstance(targets.get("micro"), dict):
        return False
    if "activity_week" in targets and targets.get("activity_week") is not None:
        if not isinstance(targets["activity_week"], dict):
            return False
    if not targets.get("micro"):
        return False
    if not targets.get("macros"):
        return False
    return True


def estimate_targets_from_profile(
    *,
    sex: Sex,
    age: int,
    height_cm: float,
    weight_kg: float,
    activity: Activity,
    goal: Goal,
) -> PlanningTargetsPayload:
    """Build existing WHO-based core targets and adapt them for weekly planning."""
    profile = UserProfile(
        sex=sex,
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity=activity,
        goal=goal,
    )
    targets = build_nutrition_targets(profile)

    return {
        "kcal": targets.kcal_daily,
        "macros": {
            "protein_g": targets.macros.protein_g,
            "fat_g": targets.macros.fat_g,
            "carbs_g": targets.macros.carbs_g,
            "fiber_g": targets.macros.fiber_g,
        },
        "micro": targets.micros.get_priority_nutrients(),
        "water_ml": targets.water_ml_daily,
        "activity_week": {
            "moderate_aerobic_min": targets.activity.moderate_aerobic_min,
            "vigorous_aerobic_min": targets.activity.vigorous_aerobic_min,
            "strength_sessions": targets.activity.strength_sessions,
            "steps_daily": targets.activity.steps_daily,
        },
    }
