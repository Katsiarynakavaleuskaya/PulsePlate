# -*- coding: utf-8 -*-
"""
BMR Schemas

RU: Схемы для расчета BMR (базового метаболизма) и TDEE.
EN: Schemas for BMR (basal metabolic rate) and TDEE calculations.
"""

from typing import Optional

from pydantic import BaseModel, Field

from core.i18n import Language


class BMRRequest(BaseModel):
    """Request model for BMR calculation"""

    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    age: int = Field(..., ge=0, le=120)
    sex: str = Field(..., pattern="^(male|female)$")
    activity: str = Field(..., pattern="^(sedentary|light|moderate|active|very_active)$")
    bodyfat: Optional[float] = Field(None, gt=0, le=60)
    lang: Language = "en"


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


class BMRRequestLegacy(BaseModel):
    """
    Lenient legacy request model to allow testing error paths without 422.

    RU: Более мягкая модель для обратной совместимости.
    EN: Lenient model for backward compatibility.
    """

    weight_kg: float
    height_cm: float
    age: int
    sex: str
    activity: str
    bodyfat: Optional[float] = None
    lang: Language = "en"
