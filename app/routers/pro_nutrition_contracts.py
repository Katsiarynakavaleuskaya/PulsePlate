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
    from legacy_app import _generate_who_targets_response

    resp: WHOTargetsResponse = _generate_who_targets_response(req)
    return resp


@router.post(
    "/plate",
    response_model=PlateResponse,
    summary="Enhanced plate (PRO)",
)
async def pro_nutrition_plate(req: PlateRequest) -> PlateResponse:
    """Canonical plate endpoint for PRO tier (PlateRequest → PlateResponse)."""
    from legacy_app import _compute_premium_plate

    resp: PlateResponse = await _compute_premium_plate(req)
    return resp
