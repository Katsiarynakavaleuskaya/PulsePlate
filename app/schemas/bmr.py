# -*- coding: utf-8 -*-
"""
BMR Schemas

RU: Схемы для расчета BMR (базового метаболизма) и TDEE.
EN: Schemas for BMR (basal metabolic rate) and TDEE calculations.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from core.i18n import Language


class BMRRequest(BaseModel):
    """Request model for BMR calculation"""

    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    age: int = Field(..., ge=0, le=120)
    sex: str = Field(..., pattern="^(male|female)$")
    activity: str = Field(..., pattern="^(sedentary|light|moderate|active|very_active)$")
    bodyfat: Optional[float] = Field(None, ge=0, le=60)
    lang: Language = "en"


class BMRResponse(BaseModel):
    """Response model for BMR calculation"""

    bmr: Dict[str, float]
    tdee: Dict[str, float]
    activity_level: str
    recommended_intake: Dict[str, float]
    formulas_used: List[str]
    notes: List[str]


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
