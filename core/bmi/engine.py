# -*- coding: utf-8 -*-
"""
BMI Engine Orchestrator

RU: Единый engine для расчета BMI (canonical source of truth).
EN: Unified engine for BMI calculation (canonical source of truth).

This module will be fully implemented in PR-453 Commit 2.
Currently provides a stub implementation for development/testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from core.bmi.risk import WaistRiskResult

AgeBand = Literal["too_young", "child", "teen", "adult", "elderly"]


@dataclass(frozen=True)
class BMICalculateResult:
    """Stub result dataclass for BMI calculation."""

    bmi: float
    category: str | None
    group: str
    group_display: str
    interpretation: str
    wht_ratio: float | None
    waist_risk: WaistRiskResult | None
    notes: tuple[str, ...]
    age_band: AgeBand


def calculate_bmi_result(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    pregnant: str | bool,
    athlete: str | bool,
    waist_cm: float | None,
    lang: str,
) -> BMICalculateResult:
    """
    RU: Рассчитывает BMI через единый engine (stub).
    EN: Calculate BMI via unified engine (stub).

    This is a placeholder implementation.
    Full implementation will be added in PR-453 Commit 2.

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: Gender ("male"/"female")
        pregnant: Pregnant flag (str or bool)
        athlete: Athlete flag (str or bool)
        waist_cm: Waist circumference in cm (optional)
        lang: Language code ("ru"/"en"/"es")

    Returns:
        BMICalculateResult: BMI calculation result (stub)

    Raises:
        NotImplementedError: Always (stub implementation)
    """
    raise NotImplementedError(
        "BMI engine is not yet implemented. This will be available after PR-453 Commit 2."
    )
