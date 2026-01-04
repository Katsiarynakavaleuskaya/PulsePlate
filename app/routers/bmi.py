# -*- coding: utf-8 -*-
"""
BMI Router

RU: Роутер для расчета BMI через единый engine.
EN: Router for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

from typing import Protocol

from fastapi import APIRouter, HTTPException, status

from app.schemas.bmi import BMICalculateRequest, BMICalculateResponse, WaistRiskResultSchema


# Import engine (will be available after PR-453 Commit 2)
class CalculateBmiResult(Protocol):
    def __call__(
        self,
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str,
        pregnant: bool,
        athlete: bool,
        waist_cm: float | None,
        lang: str,
    ) -> "BMICalculateResult": ...


try:
    from core.bmi.engine import BMICalculateResult, calculate_bmi_result as _calculate_bmi_result
except ImportError:
    # Fallback for development/testing when engine is not yet available
    calculate_bmi_result: CalculateBmiResult | None = None
else:
    calculate_bmi_result = _calculate_bmi_result


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

        # Serialize waist_risk (dataclass → Pydantic schema)
        waist_risk_schema: WaistRiskResultSchema | None = None
        if result.waist_risk:
            waist_risk_schema = WaistRiskResultSchema(
                wht_ratio=result.waist_risk.wht_ratio,
                risk_level=result.waist_risk.risk_level,
                notes=result.waist_risk.notes,
            )

        # Map to API response
        return BMICalculateResponse(
            bmi=result.bmi,
            category=result.category,  # Already str | None
            group=result.group,
            group_display=result.group_display,
            interpretation=result.interpretation,
            wht_ratio=result.wht_ratio,
            waist_risk=waist_risk_schema,
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
