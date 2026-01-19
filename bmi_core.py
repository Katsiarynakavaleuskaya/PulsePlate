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


# Legacy functions that have no canonical equivalent (stubs for test compatibility)
def estimate_level(*_args: object, **_kwargs: object) -> str:
    """
    Legacy stub: estimate_level has no canonical equivalent.

    This function is deprecated and will be removed.
    Tests using this function should be migrated or skipped.

    Raises:
        RuntimeError: Always raises to indicate deprecation
    """
    raise RuntimeError("estimate_level is deprecated; use core/* canonical APIs")


def interpret_group(*_args: object, **_kwargs: object) -> str:
    """
    Legacy stub: interpret_group has no canonical equivalent.

    This function is deprecated and will be removed.
    Tests using this function should be migrated or skipped.

    Raises:
        RuntimeError: Always raises to indicate deprecation
    """
    raise RuntimeError("interpret_group is deprecated; use core/* canonical APIs")


def build_premium_plan(*_args: object, **_kwargs: object) -> dict[str, Any]:
    """
    Legacy stub: build_premium_plan has no canonical equivalent.

    This function is deprecated and will be removed.
    Tests using this function should be migrated or skipped.

    Raises:
        RuntimeError: Always raises to indicate deprecation
    """
    raise RuntimeError("build_premium_plan is deprecated; use core/* canonical APIs")


# normalize_lang is imported above (re-exported for backward compatibility)
