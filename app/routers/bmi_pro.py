from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.api_tiers import require_pro_tier

# Use canonical BMI extras module - Pro tier functions only
# Pro endpoint must use Pro tier functions exclusively (no mixing with Free/Simple tier)
from core.bmi_extras import (
    BMIProCard,
    ffmi,
    stage_obesity_optional_whr,
    whr_ratio,
    wht_ratio,
)

# Import canonical BMI engine
# Alias calc_bmi for test patching compatibility (no BMI math in router, just symbol)
from core.bmi.engine import _compute_bmi as calc_bmi

# Import i18n functionality
from core.i18n import Language, t


router = APIRouter(prefix="/api/v1/pro", tags=["pro"])


def _adapt_pro_stage_to_response(
    stage_dict: dict[str, str], lang: Language
) -> tuple[Literal["low", "moderate", "high"], list[str]]:
    """Adapt Pro tier stage_obesity Dict response to BMIProResponse format.

    Pro tier stage_obesity returns Dict with keys: stage, recommendation, risk_factors, etc.
    BMIProResponse expects: risk_level (Literal) and notes (list[str]).

    This is contract adaptation, not tier mixing - all calculations use Pro tier.

    Args:
        stage_dict: Pro tier stage_obesity result (Dict[str, str])
        lang: Language code for i18n notes

    Returns:
        Tuple of (risk_level, notes_list) compatible with BMIProResponse
    """
    stage = stage_dict.get("stage", "low_risk")

    # Map Pro tier stage to risk_level
    if stage == "high_risk":
        risk_level: Literal["low", "moderate", "high"] = "high"
    elif stage == "moderate_risk":
        risk_level = "moderate"
    else:
        risk_level = "low"

    # Build notes list from Pro tier recommendations
    notes: list[str] = []
    recommendation = stage_dict.get("recommendation")
    if recommendation:
        notes.append(recommendation)

    # Add risk factor information if available
    risk_factors = stage_dict.get("risk_factors")
    if risk_factors and risk_factors != "0":
        notes.append(f"Risk factors: {risk_factors}")

    # Add individual risk assessments (wht_risk, whr_risk) if available
    # These provide additional context from Pro tier analysis
    wht_risk = stage_dict.get("wht_risk")
    whr_risk = stage_dict.get("whr_risk")
    if wht_risk and wht_risk != "low":
        notes.append(f"WHtR risk: {wht_risk}")

    # WHR: if unknown (missing hip), show only the translated explanation (no duplicate "WHR risk: unknown")
    if whr_risk == "unknown":
        notes.append(t(lang, "bmi_pro_whr_missing_hip"))
    elif whr_risk and whr_risk != "low":
        notes.append(f"WHR risk: {whr_risk}")

    return risk_level, notes


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


@router.post("/bmi", response_model=BMIProResponse, dependencies=[Depends(require_pro_tier)])
def bmi_pro(req: BMIProRequest) -> BMIProResponse:
    try:
        # Convert height to meters for calc_bmi(weight, height_m)
        bmi_val = calc_bmi(req.weight_kg, req.height_cm / 100.0)
        # Use Pro tier functions exclusively (no mixing with Free/Simple tier)
        v_whtr = wht_ratio(req.waist_cm, req.height_cm)  # Pro: 3 decimal places
        # Pro tier whr_ratio requires hip_cm; if missing, WHR is None (not 0.0)
        # Do NOT substitute 0.0 - missing data must be treated as "unknown", not "low risk"
        v_whr = (
            whr_ratio(req.waist_cm, float(req.hip_cm), req.sex) if req.hip_cm is not None else None
        )
        # Use Pro tier ffmi (returns dict), extract ffmi value for response compatibility
        # Contract: ffmi=None when bodyfat_percent is missing (no estimate mode in remediation)
        # Estimate mode can be added in separate product PR with contract update
        v_ffmi: Optional[float] = None
        if req.bodyfat_percent is not None:
            ffmi_dict = ffmi(req.weight_kg, req.height_cm, req.bodyfat_percent)
            v_ffmi = ffmi_dict["ffmi"]
        # Pro tier stage_obesity_optional_whr handles missing WHR correctly
        # Returns whr_risk="unknown" if whr is None (not "low")
        stage_dict = stage_obesity_optional_whr(
            bmi=bmi_val, wht=v_whtr, whr=v_whr, sex=req.sex, lang=req.lang
        )
        # Adapt Pro tier Dict response to BMIProResponse format (risk_level, notes)
        risk_level, notes = _adapt_pro_stage_to_response(stage_dict, req.lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    card = BMIProCard(
        bmi=bmi_val,
        whtr=v_whtr,
        whr=v_whr,
        ffmi=v_ffmi,
        risk_level=risk_level,
        notes=notes,
    )
    return BMIProResponse(**card.__dict__)
