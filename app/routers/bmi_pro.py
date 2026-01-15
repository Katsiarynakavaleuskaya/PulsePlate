from __future__ import annotations

from typing import Literal, Optional, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Use canonical BMI extras module
# Note: Using Simple tier functions (stage_obesity_simple, wht_ratio_simple) for compatibility
# with current response model (tuple return). Pro tier functions (ffmi, whr_ratio) used for Pro tier calculations.
from core.bmi_extras import (
    BMIProCard,
    ffmi as ffmi_pro,
    stage_obesity_simple as stage_obesity,
    whr_ratio as whr_ratio_pro,
    wht_ratio_simple as wht_ratio,
)

# Import canonical BMI engine
from core.bmi.engine import _compute_bmi

# Import i18n functionality
from core.i18n import Language


router = APIRouter(prefix="/api/v1/bmi", tags=["bmi"])

Sex = Literal["female", "male"]


class BMIProRequest(BaseModel):
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    sex: Sex
    age: int = Field(..., ge=10, le=100)
    waist_cm: float = Field(..., gt=0)
    hip_cm: Optional[float] = Field(None, gt=0)
    bodyfat_percent: Optional[float] = Field(None, ge=0, le=60)
    lang: Language = "en"  # Add language parameter


class BMIProResponse(BaseModel):
    bmi: float
    whtr: float
    whr: Optional[float]
    ffmi: Optional[float]
    risk_level: Literal["low", "moderate", "high"]
    notes: list[str]


@router.post("/pro", response_model=BMIProResponse)
def bmi_pro(req: BMIProRequest) -> BMIProResponse:
    try:
        # Convert height to meters for _compute_bmi(weight, height_m)
        bmi_val = _compute_bmi(req.weight_kg, req.height_cm / 100.0)
        v_whtr = wht_ratio(req.waist_cm, req.height_cm)
        v_whr = (
            whr_ratio_pro(req.waist_cm, float(req.hip_cm), req.sex)
            if req.hip_cm is not None
            else None
        )
        # Use Pro tier ffmi (returns dict), extract ffmi value for response compatibility
        # Pro tier ffmi supports estimate mode (bodyfat_pct=None uses default 0.85)
        v_ffmi = (
            ffmi_pro(req.weight_kg, req.height_cm, req.bodyfat_percent)["ffmi"]
            if req.bodyfat_percent is not None
            else ffmi_pro(req.weight_kg, req.height_cm)["ffmi"]  # Estimate mode
        )
        risk, notes = stage_obesity(bmi=bmi_val, whtr=v_whtr, whr=v_whr, sex=req.sex, lang=req.lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    card = BMIProCard(
        bmi=bmi_val,
        whtr=v_whtr,
        whr=v_whr,
        ffmi=v_ffmi,
        risk_level=cast(Literal["low", "moderate", "high"], risk),
        notes=notes,
    )
    return BMIProResponse(**card.__dict__)
