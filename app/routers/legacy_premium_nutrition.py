"""Legacy premium nutrition route ownership.

These endpoints remain compatibility aliases while canonical PRO contracts keep
the production nutrition behavior. Keep handler bodies thin so legacy direct-call
tests can continue to exercise the existing compatibility functions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError

from app.routers.api_key import _get_api_key_dynamic
from app.schemas.bmr import BMRRequest, BMRRequestLegacy, BMRResponse
from app.schemas.premium_contracts import (
    NutrientGapsRequest,
    NutrientGapsResponse,
    PlateRequest,
    PlateResponse,
    WHOTargetsRequest,
    WHOTargetsResponse,
)
from app.services.pro_nutrition_bmr import calculate_bmr_response
from app.services.pro_nutrition_plate import generate_plate_response
from app.services.pro_nutrition_targets import (
    analyze_nutrient_gaps_response,
    generate_who_targets_response,
)

LEGACY_PREMIUM_NUTRITION_ROUTE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("/api/v1/premium/plate", "POST", True),
    ("/api/v1/premium/bmr", "POST", True),
    ("/premium_bmr", "POST", True),
    ("/api/v1/premium/targets", "POST", True),
    ("/premium_targets", "POST", True),
    ("/api/v1/premium/gaps", "POST", True),
)

router = APIRouter()


@router.post(
    "/api/v1/premium/plate",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=PlateResponse,
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/nutrition/plate",
        "x-migration-path": "Migrate to /api/v1/pro/nutrition/plate (same contract)",
    },
)
async def api_premium_plate(req: PlateRequest) -> PlateResponse:
    """[DEPRECATED] Alias for canonical `POST /api/v1/pro/nutrition/plate`."""
    return await generate_plate_response(req)


@router.post(
    "/api/v1/premium/bmr",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=BMRResponse,
)
async def api_premium_bmr(req: BMRRequest) -> BMRResponse:
    """Legacy-compatible premium BMR endpoint."""
    return await calculate_bmr_response(req)


@router.post("/premium_bmr")
async def premium_bmr_legacy(req: BMRRequestLegacy) -> BMRResponse:
    """Legacy BMR alias; intentionally preserves its historical public route shape."""
    return await calculate_bmr_response(req)


@router.post(
    "/api/v1/premium/targets",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=WHOTargetsResponse,
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/nutrition/targets",
        "x-migration-path": "Migrate to /api/v1/pro/nutrition/targets (same contract)",
    },
)
async def api_who_targets(payload: dict[str, Any] = Body(...)) -> WHOTargetsResponse:
    """[DEPRECATED] Alias for canonical `POST /api/v1/pro/nutrition/targets`."""
    try:
        req: WHOTargetsRequest
        req = WHOTargetsRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors())) from exc

    response: WHOTargetsResponse = generate_who_targets_response(req)
    return response


@router.post("/premium_targets", dependencies=[Depends(_get_api_key_dynamic)])
async def premium_targets_legacy(req: WHOTargetsRequest) -> WHOTargetsResponse:
    """Legacy WHO targets alias."""
    response: WHOTargetsResponse = generate_who_targets_response(
        req,
        allow_backend_fallback=False,
    )
    return response


@router.post(
    "/api/v1/premium/gaps",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=NutrientGapsResponse,
)
async def api_nutrient_gaps(req: NutrientGapsRequest) -> NutrientGapsResponse:
    """Legacy-compatible nutrient gap analysis endpoint."""
    response: NutrientGapsResponse = analyze_nutrient_gaps_response(req)
    return response
