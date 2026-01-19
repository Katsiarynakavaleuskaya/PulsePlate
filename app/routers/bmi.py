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

from app.routers._helpers import _env_bool
from app.schemas.bmi import (
    BMICalculateRequest,
    BMICalculateResponse,
    SoftPaywallAvailability,
    SoftPaywallHook,
    SoftPaywallMessage,
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
    allowed = yes_values or {"yes", "y", "true", "1", "да", "д", "si", "sí"}
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


def _build_soft_paywall_hook(lang: str) -> SoftPaywallHook | None:
    """
    Build text-only soft paywall hook.

    IMPORTANT:
    - No BMI-dependent logic.
    - No imports from core/bmi/*.
    """
    enabled = _env_bool("SOFT_PAYWALL_ENABLED", default=True)
    if not enabled:
        return None

    # Normalize lang defensively (keep it simple; do not introduce logic here)
    safe_lang = normalize_lang(lang)

    title_key = "soft_paywall.title"
    body_key = "soft_paywall.body"
    cta_key = "soft_paywall.cta"

    message = SoftPaywallMessage(
        lang=safe_lang,
        title_key=title_key,
        body_key=body_key,
        cta_key=cta_key,
        default_title=t(safe_lang, title_key),
        default_body=t(safe_lang, body_key),
        default_cta=t(safe_lang, cta_key),
    )

    availability = SoftPaywallAvailability(pro_available=True, reason_key=None)

    return SoftPaywallHook(
        id="bmi.pro_interpretation_v1",
        message=message,
        availability=availability,
        target="pro_paywall",
    )


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
        resp.soft_paywall = _build_soft_paywall_hook(lang=str(req.lang))

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
