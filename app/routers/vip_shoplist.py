"""VIP shoplist endpoints (offline/deterministic).

Contract:
- VIP tier gated
- VIP_MODULE_ENABLED feature-flag gated (OFF -> 404)
- No DB, no persistence, no external calls
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.api_tiers import require_vip_tier
from app.schemas.vip_shoplist import (
    ShoplistGenerateRequest,
    ShoplistGenerateResponse,
    ShoplistPreviewItem,
    ShoplistPreviewResponse,
)
from app.utils.feature_flags import is_vip_module_enabled
from core.shoplist_engine.engine import ShoplistEngine
from core.shoplist_engine.models import (
    FoodForm,
    FoodRef,
    IngredientSpec,
    PackageRule,
    Quantity,
    RoundingMode,
    Unit,
)
from core.shoplist_preview.preview_service import build_preview

router = APIRouter(prefix="/shoplist", tags=["vip"])


def require_vip_module_enabled() -> None:
    """Require VIP module to be enabled (fail-fast with 404)."""
    if not is_vip_module_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


def _map_unit(dto_unit: str) -> Unit:
    """Map DTO unit string to core Unit enum."""
    try:
        return Unit[dto_unit]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid unit: {dto_unit}",
        ) from exc


def _map_rounding(dto_rounding: str) -> RoundingMode:
    """Map DTO rounding string to core RoundingMode enum."""
    try:
        return RoundingMode[dto_rounding]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid rounding: {dto_rounding}",
        ) from exc


@router.get("/preview", response_model=ShoplistPreviewResponse)
async def vip_shoplist_preview(
    _enabled: Annotated[None, Depends(require_vip_module_enabled)],
    _vip: Annotated[str, Depends(require_vip_tier)],
) -> ShoplistPreviewResponse:
    """VIP shoplist preview endpoint (legacy)."""
    preview = build_preview()
    return ShoplistPreviewResponse(
        items=[
            ShoplistPreviewItem(category=i.category, name=i.name, quantity=i.quantity)
            for i in preview.items
        ]
    )


@router.post("/generate", response_model=ShoplistGenerateResponse)
async def vip_shoplist_generate(
    payload: ShoplistGenerateRequest,
    _enabled: Annotated[None, Depends(require_vip_module_enabled)],
    _vip: Annotated[str, Depends(require_vip_tier)],
) -> ShoplistGenerateResponse:
    """
    Generate shopping list with packaging rules (ShoplistEngine v1).

    RU: Генерирует список покупок с применением правил упаковки.
    EN: Generates shopping list with packaging rules applied.

    This endpoint uses the pure ShoplistEngine v1 pipeline:
    normalize → aggregate → package

    No prices, no stores, no external calls - pure deterministic calculation.
    """
    # Map DTO -> core models
    specs = [
        IngredientSpec(
            food=FoodRef(food_id=item.food_id),
            qty=Quantity(value=item.qty.value, unit=_map_unit(item.qty.unit)),
            form=FoodForm[item.form],
        )
        for item in payload.items
    ]

    rules = []
    if payload.packaging_rules:
        rules = [
            PackageRule(
                food_id=r.food_id,
                pack_size=Quantity(value=r.pack_size.value, unit=_map_unit(r.pack_size.unit)),
                rounding=_map_rounding(r.rounding),
                min_packs=r.min_packs,
            )
            for r in payload.packaging_rules
        ]

    # Run engine pipeline
    result = ShoplistEngine.generate(specs, packaging_rules=rules)

    # Build rules index for lookup (rounding, min_packs)
    rules_index = {r.food_id: r for r in rules}

    # Map core result -> DTO response using from_core helper
    return ShoplistGenerateResponse.from_core(result, rules_index)


__all__ = ["router"]
