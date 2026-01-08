# -*- coding: utf-8 -*-
"""
BMI Interpretation Rules (v1)

RU: Правила интерпретации BMI (v1) — только i18n keys, без текстов.
EN: BMI interpretation rules (v1) — i18n keys only, no translated text.

Scope:
- general / athlete / elderly → numeric targets (where applicable)
- child / teen → qualitative targets (growth monitoring)
- pregnant → always returns interpretation (with or without athlete)
- too_young → interpretation None
"""

from __future__ import annotations

from core.bmi.interpretation_models import (
    BMIInterpretation,
    GoalDirection,
    I18nKey,
    NumericRange,
    QualitativeTarget,
    TargetRange,
)

# Canonical numeric boundaries (inclusive/exclusive semantics are documented in models)
# NOTE: All boundaries are mathematically correct (no -0.1 UI tricks).
# UI is responsible for rendering labels like "≤ 24.9" for max=25.0.
_BMI_UNDERWEIGHT_MAX = 18.5
_BMI_NORMAL_MAX = 25.0
_BMI_OVERWEIGHT_MAX = 30.0

# Athlete "normal-ish" range per frozen scope
_ATHLETE_MAX_MAINTAIN = 27.0

# i18n keys (keep centralized here to avoid drift)
# risk flags
K_EXTREME_VALUE: I18nKey = "bmi.interpretation.risk.extreme_value"
K_ATHLETE_BODY_COMP: I18nKey = "bmi.interpretation.risk.athlete_body_composition"

# priority notes
K_STABILITY_FIRST: I18nKey = "bmi.interpretation.priority.stability_first"
K_GROWTH_MONITORING: I18nKey = "bmi.interpretation.priority.growth_monitoring"

# disclaimers
K_DISCLAIMER_GENERAL: I18nKey = "bmi.interpretation.disclaimer.general"
K_DISCLAIMER_MEDICAL_REVIEW: I18nKey = "bmi.interpretation.disclaimer.medical_review"
K_DISCLAIMER_ATHLETE: I18nKey = "bmi.interpretation.disclaimer.athlete_body_composition"
K_DISCLAIMER_PEDIATRIC: I18nKey = "bmi.interpretation.disclaimer.pediatric_growth"
K_DISCLAIMER_PREGNANCY: I18nKey = "bmi.interpretation.disclaimer.pregnancy"

# target qualitative (typed as QualitativeTarget, not I18nKey)
Q_GROWTH: QualitativeTarget = "age_appropriate_growth"
Q_PRENATAL: QualitativeTarget = "prenatal_guidelines"


def _numeric(min_v: float, max_v: float) -> NumericRange:
    """
    Create numeric target range (both min and max inclusive per interpretation_models.py).

    RU: Создать числовой диапазон цели (min и max включительно).
    EN: Create numeric target range (both min and max inclusive).

    Boundary semantics:
    - Backend returns mathematically correct boundaries (e.g., {"min": 18.5, "max": 25.0}).
    - UI is responsible for rendering labels (e.g., "≤ 24.9" for max=25.0).
    - Backend never adjusts numbers for UI display (no -0.1 tricks).
    """
    return NumericRange(min=min_v, max=max_v)


def _mk(
    goal_direction: GoalDirection,
    target_range: TargetRange | None,
    *,
    risk_flags: tuple[I18nKey, ...] = (),
    priority_notes: tuple[I18nKey, ...] = (),
    disclaimers: tuple[I18nKey, ...] = (),
) -> BMIInterpretation:
    """Helper to create BMIInterpretation (DRY)."""
    return BMIInterpretation(
        goal_direction=goal_direction,
        target_range=target_range,
        risk_flags=risk_flags,
        priority_notes=priority_notes,
        disclaimers=disclaimers,
    )


def build_interpretation_v1(
    *,
    group: str,
    bmi: float,
    athlete: bool,
) -> BMIInterpretation | None:
    """
    Build interpretation for a given group and BMI.

    RU: Построить интерпретацию для группы и BMI.
    EN: Build interpretation for a given group and BMI.

    NOTE: We accept `athlete` separately from `group`, because pregnant+athlete exists
    while group remains "pregnant" (pregnancy priority in auto_group).

    Args:
        group: BMI group (too_young, child, teen, general, athlete, elderly, pregnant)
        bmi: BMI value
        athlete: Athlete flag from request (needed for pregnant+athlete special case)

    Returns:
        BMIInterpretation | None: Interpretation or None for too_young only
    """
    g = (group or "").strip().lower()

    # 1) too_young: always None
    if g == "too_young":
        return None

    # 2) pregnant: always return interpretation (with or without athlete)
    if g == "pregnant":
        if athlete:
            # pregnant + athlete special case:
            # we avoid numeric guidance, keep conservative and disclaimers combined
            return _mk(
                goal_direction="medical_review",
                target_range=Q_PRENATAL,
                risk_flags=(K_ATHLETE_BODY_COMP,),
                priority_notes=(K_STABILITY_FIRST,),
                disclaimers=(
                    K_DISCLAIMER_PREGNANCY,
                    K_DISCLAIMER_ATHLETE,
                    K_DISCLAIMER_MEDICAL_REVIEW,
                ),
            )
        # pregnant (without athlete): also return interpretation
        # Conservative approach: medical_review with prenatal guidelines
        return _mk(
            goal_direction="medical_review",
            target_range=Q_PRENATAL,
            priority_notes=(K_STABILITY_FIRST,),
            disclaimers=(K_DISCLAIMER_PREGNANCY, K_DISCLAIMER_MEDICAL_REVIEW),
        )

    # 3) child/teen: qualitative targets only
    if g in {"child", "teen"}:
        # always mention growth monitoring
        if bmi < _BMI_UNDERWEIGHT_MAX or bmi >= _BMI_NORMAL_MAX:
            # out of "adult normal" is not a pediatric rule; we keep conservative
            return _mk(
                goal_direction="medical_review",
                target_range=Q_GROWTH,
                priority_notes=(K_GROWTH_MONITORING,),
                disclaimers=(K_DISCLAIMER_PEDIATRIC, K_DISCLAIMER_MEDICAL_REVIEW),
            )
        return _mk(
            goal_direction="maintain",
            target_range=Q_GROWTH,
            priority_notes=(K_GROWTH_MONITORING,),
            disclaimers=(K_DISCLAIMER_PEDIATRIC,),
        )

    # 4) elderly: stability-first (age>=60 already mapped to group elsewhere)
    if g == "elderly":
        if bmi < _BMI_UNDERWEIGHT_MAX:
            return _mk(
                goal_direction="increase",
                target_range=_numeric(_BMI_UNDERWEIGHT_MAX, _BMI_NORMAL_MAX),
                priority_notes=(K_STABILITY_FIRST,),
                disclaimers=(K_DISCLAIMER_GENERAL,),
            )
        if bmi < _BMI_OVERWEIGHT_MAX:
            # includes 18.5–30: maintain (stability first)
            return _mk(
                goal_direction="maintain",
                target_range=_numeric(_BMI_UNDERWEIGHT_MAX, _BMI_OVERWEIGHT_MAX),
                priority_notes=(K_STABILITY_FIRST,),
                disclaimers=(K_DISCLAIMER_GENERAL,),
            )
        # bmi >= 30
        return _mk(
            goal_direction="medical_review",
            target_range=None,
            risk_flags=(K_EXTREME_VALUE,),
            priority_notes=(K_STABILITY_FIRST,),
            disclaimers=(K_DISCLAIMER_MEDICAL_REVIEW,),
        )

    # 5) athlete group (not pregnant)
    if g == "athlete":
        if bmi < _BMI_UNDERWEIGHT_MAX or bmi >= _BMI_OVERWEIGHT_MAX:
            return _mk(
                goal_direction="medical_review",
                target_range=None,
                risk_flags=(K_EXTREME_VALUE,),
                disclaimers=(K_DISCLAIMER_ATHLETE, K_DISCLAIMER_MEDICAL_REVIEW),
            )
        # 18.5 <= bmi < 30 (athlete normal range)
        return _mk(
            goal_direction="maintain",
            target_range=_numeric(_BMI_UNDERWEIGHT_MAX, _ATHLETE_MAX_MAINTAIN),
            disclaimers=(K_DISCLAIMER_ATHLETE,),
        )

    # 6) general adult default
    # NOTE: per scope freeze: bmi >= 30 => medical_review
    if bmi < _BMI_UNDERWEIGHT_MAX:
        return _mk(
            goal_direction="increase",
            target_range=_numeric(_BMI_UNDERWEIGHT_MAX, _BMI_NORMAL_MAX),
            disclaimers=(K_DISCLAIMER_GENERAL,),
        )
    if bmi < _BMI_NORMAL_MAX:
        return _mk(
            goal_direction="maintain",
            target_range=_numeric(_BMI_UNDERWEIGHT_MAX, _BMI_NORMAL_MAX),
            disclaimers=(K_DISCLAIMER_GENERAL,),
        )
    if bmi < _BMI_OVERWEIGHT_MAX:
        return _mk(
            goal_direction="reduce",
            target_range=_numeric(_BMI_UNDERWEIGHT_MAX, _BMI_NORMAL_MAX),
            disclaimers=(K_DISCLAIMER_GENERAL,),
        )
    # bmi >= 30
    return _mk(
        goal_direction="medical_review",
        target_range=None,
        risk_flags=(K_EXTREME_VALUE,),
        disclaimers=(K_DISCLAIMER_MEDICAL_REVIEW,),
    )
