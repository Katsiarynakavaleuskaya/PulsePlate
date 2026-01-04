# -*- coding: utf-8 -*-
"""
BMI Router

RU: Роутер для расчета BMI через единый engine.
EN: Router for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.schemas.bmi import BMICalculateRequest, BMICalculateResponse

# Import engine (will be available after PR-453 Commit 2)
try:
    from core.bmi.engine import calculate_bmi_result
except ImportError:
    # Fallback for development/testing when engine is not yet available
    calculate_bmi_result = None  # type: ignore[assignment, misc]


router = APIRouter(prefix="/api/v1/bmi", tags=["bmi"])


def _normalize_bool_flag(value: str | bool) -> bool:
    """
    RU: Конвертирует string/bool в bool (fail-soft).
    EN: Convert string/bool to bool (fail-soft).

    Args:
        value: String ("yes"/"no") or bool

    Returns:
        bool: True if value indicates "yes", False otherwise
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        return s in {"yes", "y", "да", "true", "1"}
    return False


@router.post("/calculate", response_model=BMICalculateResponse)
async def calculate_bmi(req: BMICalculateRequest) -> BMICalculateResponse:
    """
    RU: Рассчитывает BMI через единый engine.
    EN: Calculate BMI via unified engine.

    FREE tier endpoint (no API key required).

    Args:
        req: BMICalculateRequest with user parameters

    Returns:
        BMICalculateResponse with BMI calculation results

    Raises:
        HTTPException: 400 if domain validation fails (BMI out of bounds)
                      422 if Pydantic validation fails (handled automatically)
                      500 if engine is not available or other errors occur
    """
    if calculate_bmi_result is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="BMI engine is not available",
        )

    try:
        # Normalize flags (string → bool)
        pregnant_bool = _normalize_bool_flag(req.pregnant)
        athlete_bool = _normalize_bool_flag(req.athlete)

        # Call engine (domain logic)
        result = calculate_bmi_result(
            weight_kg=req.weight_kg,
            height_cm=req.height_cm,
            age=req.age,
            gender=req.gender,
            pregnant=pregnant_bool,
            athlete=athlete_bool,
            waist_cm=req.waist_cm,
            lang=req.lang,
        )

        # Serialize waist_risk (dataclass → dict)
        waist_risk_dict: dict[str, Any] | None = None
        if result.waist_risk:
            waist_risk_dict = dataclasses.asdict(result.waist_risk)
            # Convert tuple to list for JSON serialization
            if "notes" in waist_risk_dict and isinstance(waist_risk_dict["notes"], tuple):
                waist_risk_dict["notes"] = list(waist_risk_dict["notes"])

        # Map to API response
        return BMICalculateResponse(
            bmi=result.bmi,
            category=result.category,  # Already str | None
            group=result.group,
            group_display=result.group_display,
            interpretation=result.interpretation,
            wht_ratio=result.wht_ratio,
            waist_risk=waist_risk_dict,
            notes=list(result.notes),  # Ensure list[str]
            age_band=result.age_band,
        )

    except ValueError as e:
        # Domain validation errors (BMI out of bounds, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        # Unexpected errors (engine failure, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BMI calculation failed",
        ) from e

