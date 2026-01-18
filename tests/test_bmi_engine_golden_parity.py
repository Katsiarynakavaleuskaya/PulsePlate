"""
RU: Golden parity tests: legacy (bmi_core/legacy_app) vs engine (core.bmi.engine).
EN: Golden parity tests: legacy oracle vs canonical engine.

Commit 4: legacy-as-oracle pattern, strict subset comparisons + semantic checks.

Uses existing bmi_core.py logic as reference (scientific/business logic already implemented).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

import bmi_core
import legacy_app
from core.bmi.engine import BMICalculateResult, calculate_bmi_result
from core.i18n import Language

# Canonical rule: groups that must have category=None (medical disclaimer)
# This is a key domain axiom, not a local variable.
_CANONICAL_NO_CATEGORY_GROUPS = frozenset(
    {
        "too_young",
        "child",
        "teen",
        "pregnant",
    }
)


@dataclass(frozen=True)
class _Case:
    """Test case for golden parity comparison."""

    case_id: str
    weight_kg: float
    height_cm: float
    age: int
    gender: str
    pregnant: bool
    athlete: bool
    waist_cm: float | None
    lang: str | None


def _legacy_calculate(case: _Case) -> dict[str, Any]:
    """
    Legacy oracle: uses bmi_core for bmi/group/category/wht_ratio,
    and legacy_app.waist_risk for waist risk string.

    This leverages existing scientific/business logic in bmi_core.py.
    """
    height_m = case.height_cm / 100.0
    lang_norm = case.lang or "en"
    gender_norm = (case.gender or "").strip().lower()
    # Use exact engine logic (canonical parity): male variants only
    # NOTE: "mujer"/"mujeres" are female, so we cannot use startswith("m")
    gender_male = (
        gender_norm == "male" or gender_norm.startswith("муж") or gender_norm.startswith("hombre")
    )

    # Use bmi_core functions (existing logic)
    bmi = bmi_core.bmi_value(case.weight_kg, height_m)  # legacy rounding
    group = bmi_core.auto_group(
        age=case.age,
        gender=case.gender,
        pregnant="yes" if case.pregnant else "no",
        athlete="yes" if case.athlete else "no",
        lang=lang_norm,
    )
    category = bmi_core.bmi_category(
        bmi=bmi,
        lang=lang_norm,
        age=case.age,
        group=group,
    )

    wht_ratio = bmi_core.compute_wht_ratio(case.waist_cm, height_m)

    # Legacy waist_risk returns string or empty string
    waist_risk_str = ""
    if case.waist_cm is not None:
        # legacy_app.waist_risk expects Language type, normalize lang_norm
        lang_for_waist: Language = (
            "ru" if lang_norm == "ru" else ("es" if lang_norm == "es" else "en")
        )
        waist_risk_str = legacy_app.waist_risk(case.waist_cm, gender_male, lang_for_waist)

    return {
        "bmi": bmi,
        "group": group,
        "category": category,  # localized string from bmi_core
        "wht_ratio": wht_ratio,
        "waist_risk_str": waist_risk_str,  # legacy string or ""
    }


def _assert_strict(engine: BMICalculateResult, legacy: dict[str, Any], case_id: str) -> None:
    """
    Compare strict fields: bmi, group, wht_ratio (exact match).

    Category comparison:
    - Engine canonical rule: category=None for too_young/child/teen/pregnant (medical disclaimer)
    - Legacy may return categories for youth (this is divergence we're documenting)
    - For parity: we check that engine follows canonical rule (None for youth/pregnant)
    """
    bmi_msg = f"{case_id}: bmi mismatch (engine={engine.bmi}, legacy={legacy['bmi']})"
    assert engine.bmi == legacy["bmi"], bmi_msg

    group_msg = f"{case_id}: group mismatch (engine={engine.group}, legacy={legacy['group']})"
    assert engine.group == legacy["group"], group_msg

    legacy_wht_ratio = legacy.get("wht_ratio")
    wht_ratio_msg = (
        f"{case_id}: wht_ratio mismatch (engine={engine.wht_ratio}, legacy={legacy_wht_ratio})"
    )
    assert engine.wht_ratio == legacy_wht_ratio, wht_ratio_msg

    # Category: Engine canonical rule (category=None for youth/pregnant) vs legacy behavior
    # Legacy may return categories for youth, but engine correctly returns None
    legacy_cat = legacy.get("category")
    engine_cat = engine.category

    # Canonical groups that should have category=None in engine
    if engine.group in _CANONICAL_NO_CATEGORY_GROUPS:
        # Engine canonical: category must be None for these groups
        category_msg = (
            f"{case_id}: category must be None for group={engine.group} "
            f"(canonical rule, engine={engine_cat})"
        )
        assert engine_cat is None, category_msg
        # Legacy may have category (divergence documented, but engine is canonical)
    else:
        # For other groups, both should have categories (or both None)
        if legacy_cat is None or legacy_cat == "":
            assert engine_cat is None, f"{case_id}: category expected None (engine={engine_cat})"
        else:
            # Legacy has localized string, engine has category key
            assert (
                engine_cat is not None
            ), f"{case_id}: category expected non-None (legacy={legacy_cat})"
            # Category key should be valid
            assert engine_cat in {
                "underweight",
                "normal",
                "overweight",
                "obesity_1",
                "obesity_2",
                "obesity_3",
            }


def _assert_semantic(engine: BMICalculateResult, legacy: dict[str, Any], case_id: str) -> None:
    """Compare semantic fields: waist_risk, notes, interpretation (presence/meaning)."""
    # Waist risk: legacy returns string (or ""), engine returns object or None
    legacy_wr_str = legacy.get("waist_risk_str", "")
    engine_wr = engine.waist_risk

    if not legacy_wr_str:  # Legacy has no risk (empty string)
        assert engine_wr is None, f"{case_id}: waist_risk expected None (legacy='', engine present)"
    else:
        # Legacy has risk string, engine should have risk object
        assert (
            engine_wr is not None
        ), f"{case_id}: waist_risk expected present (legacy='{legacy_wr_str}')"
        # Check risk_level exists
        risk_level = getattr(engine_wr, "risk_level", None)
        assert risk_level is not None, f"{case_id}: waist_risk object missing risk_level"
        assert risk_level in {
            "low",
            "moderate",
            "high",
        }, f"{case_id}: invalid risk_level={risk_level}"

    # Notes: only assert deterministic properties (not exact strings)
    if engine_wr is None:
        assert engine.notes == (), f"{case_id}: notes must be empty when no waist_risk"
    else:
        # Notes should be tuple (from waist_risk.notes)
        assert isinstance(engine.notes, tuple), f"{case_id}: notes must be tuple"
        # If legacy has risk string, engine notes should be non-empty
        if legacy_wr_str:
            assert (
                len(engine.notes) > 0
            ), f"{case_id}: notes should be non-empty when waist_risk present"

    # Interpretation: if category exists, should contain category token
    if engine.category is not None:
        # Engine interpretation format: "{category}. {note}" or just "{category}"
        category_token = engine.category.casefold()
        interpretation_token = engine.interpretation.casefold()
        assert (
            category_token in interpretation_token
        ), f"{case_id}: interpretation should include category '{engine.category}'"


# --- Golden matrix (12-15 cases covering all critical paths) ---
# Weight/height calculated to achieve specific BMI values for category testing
CASES: list[_Case] = [
    # Age boundaries
    _Case("age_11_too_young", 35.0, 145.0, 11, "female", False, False, None, "en"),
    _Case("age_12_child", 40.0, 150.0, 12, "female", False, False, None, "en"),
    _Case("age_13_teen", 45.0, 155.0, 13, "male", False, False, None, "en"),
    _Case("age_19_teen", 55.0, 165.0, 19, "male", False, False, None, "en"),
    _Case(
        "age_20_adult_normal", 70.0, 170.0, 20, "male", False, False, None, "en"
    ),  # BMI ~24.2 (normal)
    _Case(
        "age_60_elderly_normal", 70.0, 170.0, 60, "male", False, False, None, "en"
    ),  # BMI ~24.2 (normal, elderly threshold)
    # Groups
    _Case("pregnant_female", 65.0, 170.0, 30, "female", True, False, None, "en"),
    _Case(
        "athlete_threshold_26_9", 80.0, 173.0, 30, "male", False, True, None, "en"
    ),  # BMI ~26.7 (normal for athlete)
    _Case(
        "elderly_pregnant_priority", 65.0, 170.0, 65, "female", True, False, None, "en"
    ),  # Age priority
    # BMI categories (adult)
    _Case(
        "adult_underweight", 50.0, 170.0, 30, "male", False, False, None, "en"
    ),  # BMI ~17.3 (underweight)
    _Case(
        "adult_overweight", 80.0, 170.0, 30, "male", False, False, None, "en"
    ),  # BMI ~27.7 (overweight)
    _Case(
        "adult_obesity_1", 90.0, 170.0, 30, "male", False, False, None, "en"
    ),  # BMI ~31.1 (obesity_1)
    # Waist risk
    _Case(
        "waist_risk_male_moderate", 90.0, 180.0, 30, "male", False, False, 95.0, "en"
    ),  # waist >= 94 (moderate)
    _Case(
        "waist_risk_female_high", 65.0, 170.0, 30, "female", False, False, 88.0, "en"
    ),  # waist >= 88 (high)
    # Language normalization
    _Case("lang_alias_en_us", 70.0, 170.0, 30, "male", False, False, None, "en-US"),
]


@pytest.mark.parametrize("case", CASES, ids=[c.case_id for c in CASES])
def test_golden_parity_matrix_strict_fields(case: _Case) -> None:
    """
    RU: Golden parity test: engine vs legacy oracle (bmi_core).
    EN: Golden parity test: engine vs legacy oracle (bmi_core).

    Compares strict fields (bmi, group, wht_ratio) and semantic fields (waist_risk, notes, interpretation).
    """
    legacy = _legacy_calculate(case)

    res = calculate_bmi_result(
        weight_kg=case.weight_kg,
        height_cm=case.height_cm,
        age=case.age,
        gender=case.gender,
        pregnant=case.pregnant,
        athlete=case.athlete,
        waist_cm=case.waist_cm,
        hip_cm=None,
        lang=case.lang,
    )

    _assert_strict(res, legacy, case.case_id)
    _assert_semantic(res, legacy, case.case_id)


def test_golden_parity_language_normalization() -> None:
    """Test language normalization (en-US → en) works in both legacy and engine."""
    case = _Case("lang_alias_en_us", 70.0, 170.0, 30, "male", False, False, None, "en-US")
    legacy = _legacy_calculate(case)
    res = calculate_bmi_result(
        weight_kg=case.weight_kg,
        height_cm=case.height_cm,
        age=case.age,
        gender=case.gender,
        pregnant=case.pregnant,
        athlete=case.athlete,
        waist_cm=case.waist_cm,
        hip_cm=None,
        lang=case.lang,
    )
    _assert_strict(res, legacy, case.case_id)
    # NOTE: English display name "General" is part of current API contract.
    # Any change must be accompanied by API versioning or migration.
    # This is currently a hardcoded table in engine (Commit 2), not i18n.
    assert res.group_display == "General"
