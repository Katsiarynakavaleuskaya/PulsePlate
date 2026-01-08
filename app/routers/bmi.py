# -*- coding: utf-8 -*-
"""
BMI Router

RU: Роутер для расчета BMI через единый engine.
EN: Router for BMI calculation via unified engine.

FREE tier endpoint (no API key required).
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

from fastapi import APIRouter, HTTPException, status

from app.schemas.bmi import (
    BMICalculateRequest,
    BMICalculateResponse,
    BMIInterpretationV1Schema,
    NumericRangeSchema,
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


# Import canonical normalization from engine (removes duplication).
# Keep a local fallback for partial checkouts / early-PR staging, but make it testable.
# TODO(PR-456): Consider making this public API (remove underscore).
def _fallback_normalize_bool_flag(
    value: str | bool,
    yes_values: set[str] | None = None,
) -> bool:
    """RU: Fallback на случай, если core недоступен. EN: Fallback if core is unavailable."""
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return False
    s = value.strip().lower()
    if not s:
        return False
    allowed = yes_values or {"yes", "y", "true", "1", "да", "д", "истина", "si", "sí"}
    return s in allowed


# RU: Тип фиксируем заранее → mypy всегда знает, что возвращается bool.
# EN: Fix type upfront → mypy always knows return type is bool.
# Note: Using ... for args to allow optional yes_values parameter
_normalize_bool_flag: Callable[..., bool] = _fallback_normalize_bool_flag

try:
    # Импортируем в "временное" имя, потом присваиваем typed-callable
    from core.bmi.engine import _normalize_bool_flag as _engine_normalize_bool_flag

    _normalize_bool_flag = _engine_normalize_bool_flag
except ImportError:  # pragma: no cover
    # Fail-soft: используем fallback
    pass


# Removed _get_lang_from_request() - use core.i18n.normalize_lang() directly
# This removes duplication and ensures consistent language normalization across the app.


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

        # Build interpretation_v1 (using request athlete flag, not from group)
        interpretation_v1_schema: BMIInterpretationV1Schema | None = None
        try:
            from core.bmi.interpretation_rules import build_interpretation_v1

            interp = build_interpretation_v1(
                group=result.group,
                bmi=result.bmi,
                athlete=athlete_bool,
            )
            if interp is not None:
                # Convert dataclass to schema
                # Handle target_range: NumericRange dict or qualitative string
                target_range_value: NumericRangeSchema | str | None = None
                if interp.target_range is not None:
                    if isinstance(interp.target_range, dict):
                        target_range_value = NumericRangeSchema(
                            min=interp.target_range["min"],
                            max=interp.target_range["max"],
                        )
                    else:
                        target_range_value = interp.target_range

                interpretation_v1_schema = BMIInterpretationV1Schema(
                    goal_direction=interp.goal_direction,
                    target_range=target_range_value,
                    risk_flags=interp.risk_flags,
                    priority_notes=interp.priority_notes,
                    disclaimers=interp.disclaimers,
                )
        except Exception as e:
            # Fail-soft: if interpretation building fails, log and continue without interpretation_v1
            logger.warning("Failed to build interpretation_v1: %s", e, exc_info=True)

        # Map to API response
        resp = BMICalculateResponse(
            bmi=result.bmi,
            category=result.category,  # Already str | None
            group=result.group,
            group_display=result.group_display,
            interpretation=result.interpretation,
            wht_ratio=result.wht_ratio,
            waist_risk=waist_risk_schema,
            notes=list(result.notes),  # Ensure list[str]
            age_band=result.age_band,
            visualization=None,  # Will be set below if builder succeeds
            interpretation_v1=interpretation_v1_schema,
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
    data: dict[str, Any] = await bmi_calculate_handler(req)
    result: BMICalculateResponse = BMICalculateResponse.model_validate(data)
    return result
