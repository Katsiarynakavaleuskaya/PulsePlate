"""VIP shoplist endpoints (offline/deterministic).

Contract:
- VIP tier gated
- VIP_MODULE_ENABLED feature-flag gated (OFF -> 404)
- No DB, no persistence, no external calls
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.api_tiers import require_vip_tier
from app.schemas.vip_shoplist import (
    PackedLineDTO,
    QuantityDTO,
    REASON_NO_PACKAGING_RULE,
    RoundingModeDTO,
    ShoplistAnalyticsDTO,
    ShoplistGenerateRequest,
    ShoplistGenerateResponse,
    ShoplistPreviewItem,
    ShoplistPreviewResponse,
    UnpackedLineDTO,
    UnitDTO,
)
from app.utils.feature_flags import is_vip_module_enabled
from core.shoplist_engine.engine import ShoplistEngine
from core.shoplist_engine.models import (
    FoodForm,
    FoodRef,
    IngredientSpec,
    PackPlan,
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


def _map_form(dto_form: str) -> FoodForm:
    """Map DTO form string to core FoodForm enum."""
    try:
        return FoodForm[dto_form]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid form: {dto_form}",
        ) from exc


def _build_reasons(p: PackPlan, rule: PackageRule) -> list[str]:
    """
    Build explainability reasons for packed line in fixed order.

    RU: Фиксированный порядок — тест на детерминизм.
    EN: Fixed order — determinism test relies on it.
    """
    return [
        f"rounding={rule.rounding.name}",
        f"min_packs={rule.min_packs}",
        f"requested={p.requested.value} {p.requested.unit.name}",
        f"provided={p.provided.value} {p.provided.unit.name}",
        f"overage={p.overage.value} {p.overage.unit.name}",
    ]


def _sum_overage_by_unit(result) -> dict[str, Decimal]:
    """
    Sum overage totals by unit.

    RU: Агрегируем перерасход (overage) по единицам (G/ML/PCS/...).
    EN: Aggregate overage totals by unit (G/ML/PCS/...).

    Adapter-only: uses engine output as-is.
    """
    totals: dict[str, Decimal] = {}
    for p in result.packed:
        unit = p.overage.unit.name
        totals[unit] = totals.get(unit, Decimal("0")) + p.overage.value
    return totals


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
            form=_map_form(item.form),
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

    # Build rules index for lookup (rounding, min_packs, explainability)
    rules_index = {r.food_id: r for r in rules}

    # RU: Контракт: packed линии возможны только при наличии rule.
    # EN: Contract: packed lines require a packaging rule.
    for p in result.packed:
        if p.food.food_id not in rules_index:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Packed item {p.food.food_id} missing packaging rule",
            )

    # Map core result -> DTO response
    packed_dto = [
        PackedLineDTO(
            food_id=p.food.food_id,
            requested=QuantityDTO(
                value=p.requested.value, unit=cast(UnitDTO, p.requested.unit.name)
            ),
            pack_size=QuantityDTO(
                value=p.pack_size.value, unit=cast(UnitDTO, p.pack_size.unit.name)
            ),
            packs=p.packs,
            provided=QuantityDTO(value=p.provided.value, unit=cast(UnitDTO, p.provided.unit.name)),
            overage=QuantityDTO(value=p.overage.value, unit=cast(UnitDTO, p.overage.unit.name)),
            rounding=cast(RoundingModeDTO, rules_index[p.food.food_id].rounding.name),
            min_packs=rules_index[p.food.food_id].min_packs,
            reasons=_build_reasons(p, rules_index[p.food.food_id]),
        )
        for p in result.packed
    ]

    unpacked_dto = [
        UnpackedLineDTO(
            food_id=u.food.food_id,
            requested=QuantityDTO(value=u.qty.value, unit=cast(UnitDTO, u.qty.unit.name)),
            reason=REASON_NO_PACKAGING_RULE,
        )
        for u in result.unpacked
    ]

    overage_totals = _sum_overage_by_unit(result)

    analytics = ShoplistAnalyticsDTO(
        total_lines=len(result.packed) + len(result.unpacked),
        packed_lines=len(result.packed),
        unpacked_lines=len(result.unpacked),
        total_overage_by_unit={cast(UnitDTO, k): str(v) for k, v in overage_totals.items()},
    )

    return ShoplistGenerateResponse(
        packed=packed_dto,
        unpacked=unpacked_dto,
        analytics=analytics,
    )


__all__ = ["router"]
