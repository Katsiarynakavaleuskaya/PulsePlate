"""Canonical PRO nutrition contracts.

RU: Канонические PRO контракты для targets/plate/bmr/gaps.
EN: Canonical PRO contracts for targets/plate/bmr/gaps.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.middleware.api_tiers import require_pro_tier
from app.schemas.bmr import BMRRequest, BMRResponse
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

router = APIRouter(
    prefix="/api/v1/pro/nutrition",
    tags=["pro", "nutrition"],
    dependencies=[Depends(require_pro_tier)],
)


@router.post(
    "/targets",
    response_model=WHOTargetsResponse,
    summary="WHO nutrition targets (PRO)",
)
async def pro_nutrition_targets(req: WHOTargetsRequest) -> WHOTargetsResponse:
    """Canonical targets endpoint for PRO tier."""
    response: WHOTargetsResponse = generate_who_targets_response(req)
    return response


@router.post(
    "/plate",
    response_model=PlateResponse,
    summary="Enhanced plate (PRO)",
)
async def pro_nutrition_plate(req: PlateRequest) -> PlateResponse:
    """Canonical plate endpoint for PRO tier (PlateRequest → PlateResponse)."""
    return await generate_plate_response(req)


@router.post(
    "/bmr",
    response_model=BMRResponse,
    summary="BMR and TDEE calculations (PRO)",
)
async def pro_nutrition_bmr(req: BMRRequest) -> BMRResponse:
    """Canonical BMR/TDEE endpoint for PRO tier."""
    response: BMRResponse = await calculate_bmr_response(req)
    return response


@router.post(
    "/gaps",
    response_model=NutrientGapsResponse,
    summary="Nutrient gap analysis (PRO)",
)
async def pro_nutrition_gaps(req: NutrientGapsRequest) -> NutrientGapsResponse:
    """Canonical nutrient-gap endpoint for PRO tier."""
    response: NutrientGapsResponse = analyze_nutrient_gaps_response(req)
    return response
