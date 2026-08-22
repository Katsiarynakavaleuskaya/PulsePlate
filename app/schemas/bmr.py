# -*- coding: utf-8 -*-
"""
BMR Schemas

RU: Схемы для расчета BMR (базового метаболизма) и TDEE.
EN: Schemas for BMR (basal metabolic rate) and TDEE calculations.
"""

from typing import Any, Literal, Optional

import math

from pydantic import BaseModel, Field, field_validator

from core.i18n import Language


class _BMRRequestBase(BaseModel):
    """Shared validation contract for canonical and compatibility BMR routes."""

    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    age: int = Field(..., ge=1, le=120)
    sex: Literal["male", "female"]
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"]
    bodyfat: Optional[float] = Field(None, gt=0, le=50)
    lang: Language = "en"

    @field_validator("weight_kg", "height_cm", "bodyfat", mode="before")
    @classmethod
    def reject_invalid_measurements(cls, value: Any) -> Any:
        """Reject booleans and non-finite/non-positive numeric inputs before coercion."""

        if value is None:
            return value
        if isinstance(value, bool):
            raise ValueError("measurement must be a positive finite number")
        try:
            numeric_value = float(value)
        except (OverflowError, TypeError, ValueError):
            return value
        if not math.isfinite(numeric_value) or numeric_value <= 0:
            raise ValueError("measurement must be a positive finite number")
        return value

    @field_validator("age", mode="before")
    @classmethod
    def reject_boolean_age(cls, value: Any) -> Any:
        """Keep numeric-string compatibility without accepting bool as an integer."""

        if isinstance(value, bool):
            raise ValueError("age must be an integer between 1 and 120")
        return value


class BMRRequest(_BMRRequestBase):
    """Request model for BMR calculation."""


class BMRRequestLegacy(_BMRRequestBase):
    """Compatibility request model with the same effective safety invariants."""


class BMRResponse(BaseModel):
    """Response model for BMR calculation"""

    bmr: dict[str, float] = Field(
        ...,
        description="BMR values calculated by different formulas. Keys are formula names (e.g., 'mifflin', 'harris', 'katch'), values are BMR in kcal/day.",
    )
    tdee: dict[str, float] = Field(
        ...,
        description="TDEE (Total Daily Energy Expenditure) values for different formulas and activity levels. Keys are formula names, values are TDEE in kcal/day.",
    )
    activity_level: str = Field(
        ...,
        description="Localized description of the activity level used in calculations (e.g., 'sedentary', 'light', 'moderate', 'active', 'very_active').",
    )
    recommended_intake: dict[str, float] = Field(
        ...,
        description="Recommended daily calorie intake for different goals. Keys: 'maintenance', 'weight_loss' (20% deficit), 'weight_gain' (20% surplus); values are calories in kcal/day.",
    )
    formulas_used: list[str] = Field(
        ...,
        description="List of BMR formula names that were used in the calculation (e.g., ['mifflin', 'harris', 'katch']).",
    )
    notes: list[str] = Field(
        ...,
        description="Informational messages about the calculation (e.g., notes about body fat usage, warnings, or fallback explanations).",
    )
