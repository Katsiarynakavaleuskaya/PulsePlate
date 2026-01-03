# -*- coding: utf-8 -*-
"""
BMI Schemas

RU: Схемы для расчета BMI через единый engine.
EN: Schemas for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from core.i18n import Language


class BMICalculateRequest(BaseModel):
    """
    RU: Запрос для расчета BMI через единый engine.
    EN: Request for BMI calculation via unified engine.

    FREE tier endpoint (no API key required).
    """

    weight_kg: float = Field(
        ...,
        gt=0,
        description="Weight in kilograms. Must be positive.",
        examples=[65.5, 70.0, 80.3],
    )

    height_cm: float = Field(
        ...,
        gt=0,
        description="Height in centimeters. Must be positive.",
        examples=[170.0, 175.5, 180.0],
    )

    age: int = Field(
        ...,
        ge=1,
        le=120,
        description="Age in years. Range: 1-120.",
        examples=[25, 30, 45, 65],
    )

    gender: str = Field(
        default="male",
        description="Gender: 'male' or 'female'. Will be normalized by engine.",
        examples=["male", "female", "муж", "жен"],
    )

    pregnant: str | bool = Field(
        default="no",
        description=(
            "Pregnancy status. Accepts: 'yes'/'no' (string) or True/False (bool). "
            "Will be normalized to bool by engine."
        ),
        examples=["no", "yes", False, True],
    )

    athlete: str | bool = Field(
        default="no",
        description=(
            "Athlete status. Accepts: 'yes'/'no' (string) or True/False (bool). "
            "Will be normalized to bool by engine."
        ),
        examples=["no", "yes", False, True],
    )

    waist_cm: float | None = Field(
        None,
        gt=0,
        description=(
            "Waist circumference in centimeters (optional). "
            "If provided, enables WHtR and waist risk assessment."
        ),
        examples=[80.0, 90.5, None],
    )

    lang: Language = Field(
        default="en",
        description="Language for localized responses: 'ru', 'en', or 'es'.",
        examples=["en", "ru", "es"],
    )


class BMICalculateResponse(BaseModel):
    """
    RU: Ответ с результатами расчета BMI через единый engine.
    EN: Response with BMI calculation results via unified engine.

    Note: `category` может быть `None` для беременных и детей/подростков
    (это не ошибка, а медицинский дисклеймер).
    """

    bmi: float = Field(
        ...,
        description="Calculated BMI value (weight_kg / (height_m ** 2)).",
        examples=[22.5, 25.3, 18.7],
    )

    category: str | None = Field(
        None,
        description=(
            "BMI category (localized). "
            "None for pregnant/too_young/child/teen - not an error, medical disclaimer. "
            "BMI is not valid during pregnancy or for children <12 years."
        ),
        examples=["normal", "overweight", None],
    )

    group: str = Field(
        ...,
        description=(
            "User group determined by auto_group(): "
            "'general', 'athlete', 'elderly', 'child', 'teen', 'too_young', 'pregnant'."
        ),
        examples=["general", "athlete", "elderly"],
    )

    group_display: str = Field(
        ...,
        description="Localized display name for the group.",
        examples=["General", "Athlete", "Elderly"],
    )

    interpretation: str = Field(
        ...,
        description="Localized interpretation text for the BMI value in the context of the group.",
        examples=["Your BMI is within the normal range for your age group."],
    )

    wht_ratio: float | None = Field(
        None,
        description="Waist-to-Height Ratio (WHtR). Calculated only if waist_cm was provided.",
        examples=[0.47, 0.52, None],
    )

    waist_risk: dict[str, Any] | None = Field(
        None,
        description=(
            "Waist risk assessment result (serialized WaistRiskResult). "
            "Present only if waist_cm was provided and risk was calculated. "
            "Structure: {'wht_ratio': float | None, 'risk_level': 'low'|'moderate'|'high', 'notes': tuple[str, ...]}"
        ),
        examples=[
            {
                "wht_ratio": 0.52,
                "risk_level": "moderate",
                "notes": ["Increased waist-related risk"],
            },
            None,
        ],
    )

    notes: list[str] = Field(
        default_factory=list,
        description=(
            "Aggregated notes (currently only from waist_risk.notes). Empty list if no notes."
        ),
        examples=[[], ["Increased waist-related risk"]],
    )

    age_band: Literal["too_young", "child", "teen", "adult", "elderly"] = Field(
        ...,
        description=(
            "Age band for UI differentiation: "
            "'too_young' (<12), 'child' (12-14), 'teen' (15-18), "
            "'adult' (19-59), 'elderly' (>=60)."
        ),
        examples=["adult", "teen", "elderly"],
    )
