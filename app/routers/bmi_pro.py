from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from bmi_core import calc_bmi  # твоя текущая функция
from core.bmi_extras import wht_ratio, whr_ratio, ffmi, stage_obesity, BMIProCard

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

class BMIProResponse(BaseModel):
    bmi: float
    whtr: float
    whr: float | None
    ffmi: float | None
    risk_level: Literal["low", "moderate", "high"]
    notes: list[str]

@router.post("/pro", response_model=BMIProResponse)
def bmi_pro(req: BMIProRequest):
    try:
        bmi_val = calc_bmi(req.height_cm, req.weight_kg)
        v_whtr = wht_ratio(req.waist_cm, req.height_cm)
        v_whr = whr_ratio(req.waist_cm, req.hip_cm) if req.hip_cm else None
        v_ffmi = ffmi(req.weight_kg, req.height_cm, req.bodyfat_percent) if req.bodyfat_percent is not None else None
        risk, notes = stage_obesity(bmi=bmi_val, whtr=v_whtr, whr=v_whr, sex=req.sex)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    card = BMIProCard(bmi=bmi_val, whtr=v_whtr, whr=v_whr, ffmi=v_ffmi, risk_level=risk, notes=notes)
    return BMIProResponse(**card.__dict__)