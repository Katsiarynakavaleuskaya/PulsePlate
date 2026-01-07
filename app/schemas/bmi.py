# -*- coding: utf-8 -*-
"""
BMI Schemas

RU: Схемы для расчета BMI через единый engine.
EN: Schemas for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.i18n import Language

RiskLevel = Literal["low", "moderate", "high"]


class BMIRangeSpec(BaseModel):
    """BMI range with i18n key."""

    key: str = Field(..., description="i18n key for range label")
    from_: float = Field(..., alias="from", description="Range start (inclusive)")
    to: float = Field(..., description="Range end (exclusive)")

    @model_validator(mode="after")
    def validate_range(self) -> "BMIRangeSpec":
        if self.from_ >= self.to:
            raise ValueError(f"Range start ({self.from_}) must be less than end ({self.to})")
        return self


class BMIMarkerSpec(BaseModel):
    """BMI marker position."""

    value: float = Field(..., description="Current BMI value", examples=[23.4, 25.0, 18.5])


class BMIScaleV1Spec(BaseModel):
    """BMI scale visualization spec v1."""

    kind: Literal["bmi_scale_v1"] = "bmi_scale_v1"
    bmi: float = Field(..., description="BMI value", examples=[23.4, 25.0, 18.5])
    min: float = Field(0.0, description="Scale minimum", examples=[0.0])
    max: float = Field(60.0, description="Scale maximum", examples=[60.0])
    ranges: list[BMIRangeSpec] = Field(
        ...,
        description="BMI ranges with i18n keys",
        examples=[
            [
                {"key": "bmi.underweight", "from": 0, "to": 18.5},
                {"key": "bmi.normal", "from": 18.5, "to": 25},
                {"key": "bmi.overweight", "from": 25, "to": 30},
                {"key": "bmi.obesity", "from": 30, "to": 60},
            ]
        ],
    )
    marker: BMIMarkerSpec = Field(..., description="Current BMI marker", examples=[{"value": 23.4}])

    @model_validator(mode="after")
    def validate_scale(self) -> "BMIScaleV1Spec":
        """Validate scale constraints and consistency."""
        # Ensure min < max
        if self.min >= self.max:
            raise ValueError(f"Scale minimum ({self.min}) must be less than maximum ({self.max})")

        # Ensure bmi is within scale bounds
        if not (self.min <= self.bmi <= self.max):
            raise ValueError(f"BMI value ({self.bmi}) must be between min ({self.min}) and max ({self.max})")

        # Ensure marker.value equals bmi (consistency check)
        if self.marker.value != self.bmi:
            raise ValueError(f"Marker value ({self.marker.value}) must equal BMI ({self.bmi})")

        return self


class WaistRiskResultSchema(BaseModel):
    """
    RU: API-схема для сериализованного WaistRiskResult (domain dataclass).
    EN: API schema for serialized WaistRiskResult (domain dataclass).
    """

    wht_ratio: float | None = Field(
        None,
        description="Waist-to-Height Ratio (WHtR) used for this assessment, if available.",
        examples=[0.47, 0.52, None],
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Waist-related risk level derived from the WHtR.",
        examples=["moderate"],
    )
    notes: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Additional notes providing context for the waist risk assessment.",
        examples=[("Increased waist-related risk",)],
    )


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
            "None for users in 'pregnant', 'too_young', 'child' or 'teen' age bands "
            "- not an error, medical disclaimer. "
            "BMI categories are not provided during pregnancy or for users in "
            "'too_young', 'child' and 'teen' age bands."
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

    waist_risk: WaistRiskResultSchema | None = Field(
        None,
        description=(
            "Waist risk assessment result. Present only if waist_cm was provided "
            "and risk was calculated."
        ),
        examples=[
            {
                "wht_ratio": 0.52,
                "risk_level": "moderate",
                "notes": ("Increased waist-related risk",),
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

    visualization: BMIScaleV1Spec | None = Field(
        None,
        description="Optional BMI scale visualization spec (v1). Frontend should render this if available.",
    )
