"""Compatibility helpers for legacy /plan.

This module provides a small, policy-compliant bridge between the canonical BMI engine output
and the legacy `/plan` endpoint contract in `legacy_app.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.i18n import Language, normalize_lang, t

# Decimal thresholds (policy-compliant: no float in core/)
D17_5 = Decimal("17.5")
D18_5 = Decimal("18.5")
D24_5 = Decimal("24.5")
D25_0 = Decimal("25.0")
D26_0 = Decimal("26.0")
D30_0 = Decimal("30.0")
D35_0 = Decimal("35.0")
D40_0 = Decimal("40.0")


@dataclass(frozen=True)
class LegacyPlanCategoryResult:
    category: str | None


def legacy_plan_category(
    *,
    engine_category: str | None,
    bmi: Decimal,
    age: int,
    lang: str | Language | None,
    group: str,
) -> LegacyPlanCategoryResult:
    """Return the legacy `/plan` category display string.

    The canonical BMI engine returns category slugs (e.g. "normal") and may return None for
    minors/pregnancy. The legacy `/plan` endpoint historically returns a string category for minors
    (pregnancy is handled earlier in the endpoint).
    """
    # Normalize lang: normalize_lang handles str | None and returns Language
    lang_norm = normalize_lang(lang)

    category_slug = engine_category
    if category_slug is None and age < 18:
        # Legacy /plan parity: minors still receive a category string.
        category_slug = _category_slug_from_bmi(bmi=bmi, group=group)

    if category_slug is None:
        return LegacyPlanCategoryResult(category=None)

    i18n_key = _CATEGORY_I18N_KEY.get(category_slug)
    if i18n_key is None:
        return LegacyPlanCategoryResult(category=str(category_slug))

    return LegacyPlanCategoryResult(category=t(lang_norm, i18n_key))


def _category_slug_from_bmi(*, bmi: Decimal, group: str) -> str | None:
    """Map BMI value to category slug based on legacy thresholds.

    Used for minors when canonical engine returns category=None.
    Uses Decimal comparisons (policy-compliant: no float in core/).
    """
    # too_young (age < 12): no category classification (canonical policy)
    if group == "too_young":
        return None

    # Legacy thresholds (from bmi_core.py and legacy_app.py)
    if group == "athlete":
        # Legacy /plan parity: athlete still uses full adult BMI buckets.
        # Underweight/obesity tiers must remain reachable.
        if bmi < D18_5:
            return "underweight"
        elif bmi < D25_0:
            return "normal"
        elif bmi < D30_0:
            return "overweight"
        elif bmi < D35_0:
            return "obesity_1"
        elif bmi < D40_0:
            return "obesity_2"
        return "obesity_3"
    elif group == "elderly":
        # Elderly thresholds: 17.5 / 26.0
        if bmi < D17_5:
            return "underweight"
        elif bmi < D26_0:
            return "normal"
        return "overweight"
    elif group in ("child", "teen"):
        # Child/teen thresholds: 17.5 / 24.5
        if bmi < D17_5:
            return "underweight"
        elif bmi < D24_5:
            return "normal"
        return "overweight"
    else:
        # General thresholds: 18.5 / 25.0 / 30.0 / 35.0 / 40.0
        if bmi < D18_5:
            return "underweight"
        elif bmi < D25_0:
            return "normal"
        elif bmi < D30_0:
            return "overweight"
        elif bmi < D35_0:
            return "obesity_1"
        elif bmi < D40_0:
            return "obesity_2"
        return "obesity_3"


_CATEGORY_I18N_KEY: dict[str, str] = {
    "underweight": "bmi_underweight",
    "normal": "bmi_normal",
    "overweight": "bmi_overweight",
    "obesity_1": "bmi_obese_1",
    "obesity_2": "bmi_obese_2",
    "obesity_3": "bmi_obese_3",
}
