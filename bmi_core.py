# -*- coding: utf-8 -*-
# pragma: no cover
"""
Legacy compatibility shim for bmi_core.

IMPORTANT:
- Do NOT implement BMI math here.
- One BMI Engine invariant: all calculations live in core/bmi/*.
- This module exists only to keep legacy tests / callers working during cleanup.
- All functions are thin wrappers delegating to canonical modules.

This shim will be removed in a future PR after all callers are migrated.

Coverage exclusion rationale:
- This is a legacy compatibility shim without domain logic.
- All behavior is delegated to core/bmi/* which is fully covered (≥97%).
- Excluded from coverage by design to avoid false diff-cover failures.
"""

from __future__ import annotations

from typing import Any

# Core engine functions (re-export with legacy names)
from core.bmi.engine import (
    HEALTHY_BMI_RANGE,
    _auto_group,
    _bmi_category,
    _compute_bmi,
    _compute_wht_ratio,
    _group_display_name,
    _normalize_bool_flag,
)

from core.i18n import normalize_lang, t


# Legacy function signatures (wrappers for backward compatibility)
def auto_group(
    age: int,
    gender: str,
    pregnant: str | bool,
    athlete: str | bool,
    lang: str | None = None,  # Legacy parameter, 5th positional (BC requirement)
    athlete_text: str | None = None,  # 6th positional (optional)
) -> str:
    """
    Legacy wrapper for _auto_group.

    IMPORTANT: Positional order must remain:
      auto_group(age, gender, pregnant, athlete, lang_code, athlete_text=None)

    This preserves legacy callers that pass `lang` as the 5th positional arg.
    Changing the order would silently misroute lang into athlete_text.

    Args:
        age: Age in years
        gender: Gender string
        pregnant: Pregnant flag (str or bool)
        athlete: Athlete flag (str or bool)
        lang: Language (legacy parameter, ignored in canonical engine)
        athlete_text: Optional athlete text for heuristics (6th positional)

    Returns:
        Group string (e.g., "general", "athlete", "pregnant")
    """
    pregnant_bool = _normalize_bool_flag(pregnant) if isinstance(pregnant, str) else bool(pregnant)
    athlete_bool = _normalize_bool_flag(athlete) if isinstance(athlete, str) else bool(athlete)
    # Preserve athlete_text if provided as string and not recognized as yes/no
    if athlete_text is None and isinstance(athlete, str):
        athlete_lower = athlete.strip().lower()
        if athlete_bool is False and athlete_lower not in {
            "no",
            "false",
            "0",
            "",
            "нет",
            "н",
            "не",
        }:
            athlete_text = athlete

    return _auto_group(
        age=age,
        gender=gender,
        pregnant=pregnant_bool,
        athlete=athlete_bool,
        athlete_text=athlete_text,
    )


def bmi_category(
    bmi: float,
    lang: str = "en",
    age: int | None = None,
    group: str = "general",
) -> str | None:
    """
    Legacy wrapper for _bmi_category with localization.

    Args:
        bmi: BMI value
        lang: Language code (ru/en/es)
        age: Age (optional, defaults to 30 for compatibility)
        group: User group (optional, defaults to "general")

    Returns:
        Localized category string or None
    """
    if age is None:
        age = 30  # Safe default for legacy compatibility

    category_key = _bmi_category(bmi=bmi, age=age, group=group)
    if category_key is None:
        return None

    lang_norm = normalize_lang(lang)

    # Try canonical i18n key format: bmi.<category_key>
    i18n_key = f"bmi.{category_key}"
    try:
        translated = t(lang_norm, i18n_key)
        # Guard: if translation missing and t() returns the key itself, try legacy keys
        if translated != i18n_key:
            return translated
    except KeyError:
        pass

    # Fallback to legacy keys (bmi_obese_1, bmi_underweight, etc.)
    legacy_map = {
        "underweight": "bmi_underweight",
        "normal": "bmi_normal",
        "overweight": "bmi_overweight",
        "obesity_1": "bmi_obese_1",
        "obesity_2": "bmi_obese_2",
        "obesity_3": "bmi_obese_3",
    }
    legacy_key = legacy_map.get(category_key, f"bmi_{category_key}")
    try:
        return t(lang_norm, legacy_key)
    except KeyError:
        # Last resort: return None (should not happen with proper i18n)
        return None


def bmi_value(weight_kg: float, height_m: float) -> float:
    """
    Legacy wrapper for _compute_bmi.

    Args:
        weight_kg: Weight in kilograms
        height_m: Height in meters

    Returns:
        BMI value
    """
    return _compute_bmi(weight_kg=weight_kg, height_m=height_m)


def compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
    """
    Legacy wrapper for _compute_wht_ratio.

    Args:
        waist_cm: Waist circumference in centimeters (may be None for missing/invalid input)
        height_m: Height in meters

    Returns:
        WHtR ratio or None if invalid
    """
    return _compute_wht_ratio(waist_cm=waist_cm, height_m=height_m)


def group_display_name(group: str, lang: str = "en") -> str:
    """
    Legacy wrapper for _group_display_name.

    Args:
        group: Group string (e.g., "general", "athlete")
        lang: Language code (ru/en/es)

    Returns:
        Localized group display name
    """
    lang_norm = normalize_lang(lang)
    return _group_display_name(group, lang_norm)


def healthy_bmi_range(
    age: int,
    group: str = "general",
    premium: bool = False,  # Legacy parameter, ignored
) -> tuple[float, float]:
    """
    Legacy wrapper for HEALTHY_BMI_RANGE.

    Args:
        age: Age (legacy parameter, ignored for general population)
        group: User group (legacy parameter, ignored for general population)
        premium: Premium flag (legacy parameter, ignored)

    Returns:
        Tuple of (min_bmi, max_bmi) for healthy range
    """
    # Always return canonical HEALTHY_BMI_RANGE for general population
    # Group-specific ranges are not supported in legacy API
    return (HEALTHY_BMI_RANGE.min, HEALTHY_BMI_RANGE.max)


# Legacy shims: delegate to canonical core.bmi.engine implementations
def estimate_level(
    freq_per_week: int = 0,
    years: float = 0.0,
    lang: str | None = None,
    *_args: object,
    **_kwargs: object,
) -> str:
    """
    Legacy shim: delegates to canonical core.bmi.engine.estimate_level.

    RU: Оценка уровня физической подготовки на основе опыта тренировок.
    EN: Estimate fitness experience level based on training history.

    Args:
        freq_per_week: Training sessions per week
        years: Years of training experience
        lang: Language code (reserved for localization)

    Returns:
        Fitness level: "beginner", "novice", "intermediate", or "advanced"
    """
    from core.bmi.engine import estimate_level as _canonical_estimate_level

    return _canonical_estimate_level(freq_per_week=freq_per_week, years=years, lang=lang)


def interpret_group(
    bmi: float,
    group: str,
    lang: str = "en",
    age: int | None = None,
) -> str:
    """
    Legacy shim: delegates to canonical core.bmi.engine.interpret_group.

    RU: Расширенная интерпретация группы с контекстными заметками.
    EN: Enhanced group interpretation with context notes.

    Args:
        bmi: BMI value
        group: BMI group (general, athlete, pregnant, elderly, child, teen)
        lang: Language code ("ru", "en", "es")
        age: Age in years (optional)

    Returns:
        Localized interpretation string
    """
    from typing import cast

    from core.bmi.engine import BMIGroup
    from core.bmi.engine import interpret_group as _canonical_interpret_group

    # Cast string to BMIGroup (legacy API accepts str, canonical uses Literal)
    normalized_group = cast(BMIGroup, group if group else "general")
    return _canonical_interpret_group(bmi=bmi, group=normalized_group, lang=lang, age=age)


def build_premium_plan(
    age: int,
    weight_kg: float,
    height_m: float,
    bmi: float,
    lang: str = "en",
    group: str = "general",
    premium: bool = True,
) -> dict[str, Any]:
    """
    Legacy shim: delegates to canonical core.bmi.engine.build_premium_plan.

    RU: Построение премиум плана с рекомендациями.
    EN: Build premium plan with recommendations.

    Args:
        age: Age in years
        weight_kg: Weight in kilograms
        height_m: Height in meters
        bmi: Pre-calculated BMI value
        lang: Language code
        group: BMI group
        premium: Premium flag (legacy, ignored)

    Returns:
        Dict with plan details (legacy format)
    """
    from core.bmi.engine import build_premium_plan as _canonical_build_premium_plan

    result = _canonical_build_premium_plan(
        age=age,
        weight_kg=weight_kg,
        height_m=height_m,
        bmi=bmi,
        lang=lang,
        group=group,  # type: ignore[arg-type]
        premium=premium,
    )

    # Convert dataclass to dict for legacy compatibility
    return {
        "healthy_bmi": result.healthy_bmi,
        "healthy_weight": result.healthy_weight,
        "current_weight": result.current_weight,
        "current_bmi": result.current_bmi,
        "action": result.action,
        "delta_kg": result.delta_kg,
        "est_weeks": result.est_weeks,
        "nutrition_tip": result.nutrition_tip,
        "activity_tip": result.activity_tip,
    }


# normalize_lang is imported above (re-exported for backward compatibility)
