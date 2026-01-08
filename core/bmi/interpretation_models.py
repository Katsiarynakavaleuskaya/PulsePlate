"""
BMI Interpretation Models

RU: Модели данных для интерпретации BMI результатов.
EN: Data models for BMI result interpretation.

All text fields are i18n keys (not translated strings).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, TypedDict, Union

# i18n key type alias (semantic marker, runtime is str)
I18nKey = str


# Goal direction types
GoalDirection = Literal["maintain", "reduce", "increase", "medical_review"]


# Numeric target range
class NumericRange(TypedDict, total=True):
    """
    Numeric BMI target range.

    RU: Числовой диапазон BMI для цели.
    EN: Numeric BMI range for target.

    Both min and max are inclusive.
    """

    min: float
    max: float


# Qualitative target types
QualitativeTarget = Literal[
    "age_appropriate_growth",
    "prenatal_guidelines",
]

# Target range union
TargetRange = Union[NumericRange, QualitativeTarget]


@dataclass(frozen=True)
class BMIInterpretation:
    """
    RU: Каноническая интерпретация BMI результата с рекомендациями и целями.
    EN: Canonical BMI result interpretation with recommendations and targets.

    All text fields are i18n keys (not translated strings).
    """

    goal_direction: GoalDirection
    target_range: Optional[TargetRange]
    risk_flags: tuple[I18nKey, ...]  # i18n keys only
    priority_notes: tuple[I18nKey, ...]  # i18n keys only
    disclaimers: tuple[I18nKey, ...]  # i18n keys only
