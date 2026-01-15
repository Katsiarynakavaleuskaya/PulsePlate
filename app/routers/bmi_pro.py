from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
from core.bmi.engine import _compute_bmi

# Import i18n functionality
from core.i18n import Language


router = APIRouter(prefix="/api/v1/bmi", tags=["bmi"])


def _adapt_pro_stage_to_response(
    stage_dict: dict[str, str], whr: float | None, lang: str  # noqa: ARG001
) -> tuple[Literal["low", "moderate", "high"], list[str]]:
    """Adapt Pro tier stage_obesity Dict response to BMIProResponse format.

    Pro tier stage_obesity returns Dict with keys: stage, recommendation, risk_factors, etc.
    BMIProResponse expects: risk_level (Literal) and notes (list[str]).

    This is contract adaptation, not tier mixing - all calculations use Pro tier.

    Args:
        stage_dict: Pro tier stage_obesity result (Dict[str, str])
        whr: WHR value (used to determine if None should be passed to response)

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
    if whr_risk and whr_risk != "low":
        notes.append(f"WHR risk: {whr_risk}")
    # If WHR is missing (unknown), add note explaining missing data
    if whr_risk == "unknown":
        from core.i18n import t

        notes.append(t(lang, "bmi_pro_whr_missing_hip"))

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


@router.post("/pro", response_model=BMIProResponse)
def bmi_pro(req: BMIProRequest) -> BMIProResponse:
    try:
        # Convert height to meters for _compute_bmi(weight, height_m)
        bmi_val = _compute_bmi(req.weight_kg, req.height_cm / 100.0)
        # Use Pro tier functions exclusively (no mixing with Free/Simple tier)
        v_whtr = wht_ratio(req.waist_cm, req.height_cm)  # Pro: 3 decimal places
        # Pro tier whr_ratio requires hip_cm; if missing, WHR is None (not 0.0)
        # Do NOT substitute 0.0 - missing data must be treated as "unknown", not "low risk"
        v_whr = (
            whr_ratio(req.waist_cm, float(req.hip_cm), req.sex) if req.hip_cm is not None else None
        )
        # Use Pro tier ffmi (returns dict), extract ffmi value for response compatibility
        # Pro tier ffmi supports estimate mode (bodyfat_pct=None uses default 0.85)
        v_ffmi = (
            ffmi(req.weight_kg, req.height_cm, req.bodyfat_percent)["ffmi"]
            if req.bodyfat_percent is not None
            else ffmi(req.weight_kg, req.height_cm)["ffmi"]  # Estimate mode
        )
        # Pro tier stage_obesity_optional_whr handles missing WHR correctly
        # Returns whr_risk="unknown" if whr is None (not "low")
        stage_dict = stage_obesity_optional_whr(
            bmi=bmi_val, wht=v_whtr, whr=v_whr, sex=req.sex, lang=req.lang
        )
        # Adapt Pro tier Dict response to BMIProResponse format (risk_level, notes)
        risk_level, notes = _adapt_pro_stage_to_response(stage_dict, v_whr, req.lang)
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
