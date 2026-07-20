"""PRO nutrition contracts (canonical): /targets and /plate.

RU: Канонические PRO контракты для targets/plate.
EN: Canonical PRO contracts for targets/plate.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.middleware.api_tiers import require_pro_tier
from app.schemas.premium_contracts import (
    PlateRequest,
    PlateResponse,
    WHOTargetsRequest,
    WHOTargetsResponse,
)
from app.services.pro_nutrition_plate import generate_plate_response
from app.services.pro_nutrition_targets import generate_who_targets_response

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
    return generate_who_targets_response(req)


@router.post(
    "/plate",
    response_model=PlateResponse,
    summary="Enhanced plate (PRO)",
)
async def pro_nutrition_plate(req: PlateRequest) -> PlateResponse:
    """Canonical plate endpoint for PRO tier (PlateRequest → PlateResponse)."""
    return await generate_plate_response(req)
