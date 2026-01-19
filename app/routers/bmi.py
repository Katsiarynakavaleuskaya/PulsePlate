# -*- coding: utf-8 -*-
"""
BMI Router

RU: Роутер для расчета BMI через единый engine.
EN: Router for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from fastapi import APIRouter, HTTPException, status

from app.routers._helpers import _build_soft_paywall_hook, _normalize_bool_flag
from app.schemas.bmi import (
    BMICalculateRequest,
    BMICalculateResponse,
    WaistRiskResultSchema,
)
from app.services.bmi_visualization import build_bmi_scale_v1
from core.i18n import normalize_lang, t

logger = logging.getLogger(__name__)


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
        hip_cm: float | None,
        lang: str | None,
    ) -> "BMICalculateResult": ...


try:
    from core.bmi.engine import BMICalculateResult, calculate_bmi_result as _calculate_bmi_result
except ImportError:
    # Fallback for development/testing when engine is not yet available
    calculate_bmi_result: CalculateBmiResult | None = None
else:
    calculate_bmi_result = _calculate_bmi_result


router = APIRouter(prefix="/api/v1/bmi", tags=["bmi"])


# Removed _get_lang_from_request() - use core.i18n.normalize_lang() directly
# This removes duplication and ensures consistent language normalization across the app.
# Removed _normalize_bool_flag and _build_soft_paywall_hook - use shared helpers from _helpers.py


async def bmi_calculate_handler(
    req_in: BMICalculateRequest | dict[str, Any],  # noqa: ANN401
) -> dict[str, Any]:
    """
    RU: Канонический Free BMI handler (тонкий адаптер).
    EN: Canonical Free BMI handler (thin adapter).

    Accepts legacy BMIRequestV1-shaped input or BMICalculateRequest; converts to BMICalculateRequest
    and returns response as dict for legacy shim compatibility.

    Args:
        req_in: BMIRequestV1 (legacy) or BMICalculateRequest (new)

    Returns:
        dict[str, Any]: Response as dict (for legacy compatibility)

    Raises:
        HTTPException: 400 if domain validation fails, 500 if engine fails, 501 if engine unavailable
    """
    # Convert to BMICalculateRequest if needed
    if isinstance(req_in, BMICalculateRequest):
        req = req_in
    else:
        # Legacy BMIRequestV1 or dict-like input
        # If it's a Pydantic model, convert to dict first
        if hasattr(req_in, "model_dump"):
            # Type guard: req_in has model_dump method (Pydantic model)
            model_dump = getattr(req_in, "model_dump")
            req = BMICalculateRequest.model_validate(model_dump())
        else:
            req = BMICalculateRequest.model_validate(req_in)

    if calculate_bmi_result is None:
        lang = normalize_lang(str(req.lang))
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=t(lang, "bmi_engine_unavailable"),
        )

    try:
        # Schema already normalizes pregnant to bool via field_validator, but keep normalization
        # for robustness (in case req comes from legacy path that bypasses schema)
        # NOTE: Soft normalization (male+pregnant -> pregnant=False) is handled by schema's
        # _apply_pregnancy_invariant model_validator. Handler remains thin and does not duplicate
        # domain normalization logic.
        pregnant_bool = (
            req.pregnant if isinstance(req.pregnant, bool) else _normalize_bool_flag(req.pregnant)
        )
        athlete_bool = (
            req.athlete if isinstance(req.athlete, bool) else _normalize_bool_flag(req.athlete)
        )

        # Call engine (domain logic)
        # Schema's _apply_pregnancy_invariant already handled soft normalization:
        # - gender=None + pregnant=True -> gender="female"
        # - gender="male" + pregnant=True -> pregnant=False
        result = calculate_bmi_result(
            weight_kg=req.weight_kg,
            height_cm=req.height_cm,
            age=req.age,
            gender=req.gender or "male",  # Engine expects non-None gender
            pregnant=pregnant_bool,
            athlete=athlete_bool,
            waist_cm=req.waist_cm,
            hip_cm=None,  # FREE tier: do not compute WHR
            lang=str(req.lang),
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
        resp = BMICalculateResponse(
            bmi=result.bmi,
            category=result.category,  # Already str | None
            group=result.group,
            group_display=result.group_display,
            interpretation=result.interpretation,
            wht_ratio=result.wht_ratio,
            # whr not included in FREE tier response
            waist_risk=waist_risk_schema,
            notes=list(result.notes),  # Ensure list[str]
            age_band=result.age_band,
            visualization=None,  # Will be set below if builder succeeds
            interpretation_v1=None,  # Optional structured interpretation (not implemented yet)
        )

        # Add visualization spec (graceful fallback: if builder fails, visualization remains None)
        try:
            resp.visualization = build_bmi_scale_v1(result)  # Pass full result, not just bmi
        except Exception:
            # Visualization is optional; don't break the endpoint if builder fails
            # Log the error for debugging while preserving graceful fallback
            # Security: log only BMI value (numeric), not user input data
            logger.exception("Failed to build BMI visualization spec (BMI=%.1f)", result.bmi)
            resp.visualization = None

        # Add soft paywall hook (router layer only, no BMI logic)
        resp.soft_paywall = _build_soft_paywall_hook(str(req.lang), default_enabled=True)

        # Return as dict for legacy compatibility
        # IMPORTANT: use by_alias=True to ensure "from" (not "from_") in JSON
        response_dict: dict[str, Any] = resp.model_dump(by_alias=True)
        return response_dict

    except NotImplementedError as e:
        # Engine stub: deterministic API response
        lang = normalize_lang(str(req.lang))
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=t(lang, "bmi_engine_unavailable"),
        ) from e
    except ValueError as e:
        # Domain validation errors (BMI out of bounds, etc.)
        # Security: do not expose internal error details
        lang = normalize_lang(str(req.lang))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t(lang, "bmi_invalid_parameters"),
        ) from e
    except Exception as e:
        # Unexpected errors (engine failure, etc.)
        lang = normalize_lang(str(req.lang))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t(lang, "bmi_calculation_failed"),
        ) from e


@router.post(
    "/calculate",
    response_model=BMICalculateResponse,
    response_model_by_alias=True,
)
async def calculate_bmi(req: BMICalculateRequest) -> BMICalculateResponse:
    """
    RU: Рассчитывает BMI через единый engine.
    EN: Calculate BMI via unified engine.

    FREE tier endpoint (no API key required).

    Args:
        req: BMICalculateRequest with user parameters

    Returns:
        BMICalculateResponse with BMI calculation results (serialized with by_alias=True)

    Raises:
        HTTPException: 400 if domain validation fails (BMI out of bounds)
                      422 if Pydantic validation fails (handled automatically)
                      500 if engine is not available or other errors occur
    """
    # Handler returns dict for legacy compatibility; convert back to model for FastAPI serialization
    # response_model_by_alias=True ensures "from" (not "from_") in visualization.ranges[]
    # NOTE: model_validate() returns Any for mypy; assign to local to keep return type
    data: dict[str, Any] = await bmi_calculate_handler(req)
    response: BMICalculateResponse = BMICalculateResponse.model_validate(data)
    return response
