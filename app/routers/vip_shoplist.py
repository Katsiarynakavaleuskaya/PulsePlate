"""VIP shoplist endpoints (offline/deterministic).

Contract:
- VIP tier gated
- VIP_MODULE_ENABLED feature-flag gated (OFF -> 404)
- No DB, no persistence, no external calls
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated, Any, Optional, Protocol, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.middleware.api_tiers import require_vip_tier
from app.schemas.vip_shoplist import (
    PackageRuleDTO,
    PackedLineDTO,
    QuantityDTO,
    REASON_NO_PACKAGING_RULE,
    RoundingModeDTO,
    ShoplistAnalyticsDTO,
    ShoplistDailyRequest,
    ShoplistGenerateRequest,
    ShoplistGenerateResponse,
    ShoplistItemDTO,
    ShoplistPreviewItem,
    ShoplistPreviewResponse,
    ShoplistWeeklyRequest,
    ShoplistWeeklyResponse,
    UnpackedLineDTO,
    UnitDTO,
)
from app.services.catalog_adapter import CatalogProvider, _get_provider, enrich_shoplist_response
from app.services.shoplist_export.csv_export import export_shoplist_to_csv
from app.utils.feature_flags import is_vip_module_enabled
from core.shoplist_engine.engine import ShoplistEngine
from fastapi import Request

# Rate limiting imports (PR-628)
try:
    from app.security.rate_limit import limit_if_available, RATE_LIMIT_EXPORTS
except ImportError:
    # No-op decorator if rate limiting unavailable
    def limit_if_available(rate: str):  # type: ignore[misc]
        def decorator(func):  # type: ignore[misc]
            return func

        return decorator

    RATE_LIMIT_EXPORTS = "20/minute"
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
from core.shoplist_engine.packager import PackagingResult
from core.shoplist_preview.preview_service import build_preview

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shoplist", tags=["VIP Shoplist"])

# Catalog provider (lazy, selected via CATALOG_PROVIDER env var)
# RU: В PR-6 это mock; в PR-7 можно переключить на sqlite через env var.
# EN: In PR-6 this is mock; in PR-7 can switch to sqlite via env var.
# Fail-soft: если provider недоступен, fallback на mock.
# Lazy evaluation: provider is fetched on each request to allow env var changes in tests.


def _get_catalog_provider() -> CatalogProvider:
    """Get catalog provider (lazy, respects env vars and cache reset)."""
    return _get_provider()


def _export_shoplist_to_pdf(result: ShoplistGenerateResponse) -> bytes:
    from app.services.shoplist_export.pdf_export import export_shoplist_to_pdf

    # With pre-push mypy (--follow-imports=skip), imported functions are treated as Any.
    # Assigning to a typed local ensures type safety in CI.
    pdf_data: bytes = export_shoplist_to_pdf(result)
    return pdf_data


# Common OpenAPI responses for gating matrix
COMMON_VIP_SHOPLIST_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Unauthorized: missing/invalid API key (auth-layer dependent)"},
    403: {"description": "Forbidden: valid auth but insufficient VIP tier"},
    404: {"description": "VIP module disabled"},
    422: {"description": "Validation error (invalid enum / DTO)"},
    500: {"description": "Invariant violation (internal)"},
}


def require_vip_module_enabled() -> None:
    """Require VIP module to be enabled (fail-fast with 404)."""
    if not is_vip_module_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


# RU: Pydantic валидирует DTO literals первым, эти функции — defense-in-depth
#     для случаев, когда валидация обходится (например, прямой вызов из кода).
# EN: Pydantic validates DTO literals first; these functions are defense-in-depth
#     for cases where validation is bypassed (e.g., direct code calls).
def _map_unit(dto_unit: str) -> Unit:
    """Map DTO unit string to core Unit enum."""
    try:
        return Unit[dto_unit]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid unit: {dto_unit}",
        ) from exc


def _map_rounding(dto_rounding: str) -> RoundingMode:
    """Map DTO rounding string to core RoundingMode enum."""
    try:
        return RoundingMode[dto_rounding]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid rounding: {dto_rounding}",
        ) from exc


def _map_form(dto_form: str) -> FoodForm:
    """Map DTO form string to core FoodForm enum."""
    try:
        return FoodForm[dto_form]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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


def _sum_overage_by_unit(result: PackagingResult) -> dict[UnitDTO, Decimal]:
    """
    Sum overage totals by unit.

    RU: Агрегируем перерасход (overage) по единицам (G/ML/PCS/...).
    EN: Aggregate overage totals by unit (G/ML/PCS/...).

    Adapter-only: uses engine output as-is.
    Cast is safe: core.Unit.name values match UnitDTO Literal subset.
    """
    totals: dict[UnitDTO, Decimal] = {}
    for p in result.packed:
        unit = cast(UnitDTO, p.overage.unit.name)
        totals[unit] = totals.get(unit, Decimal("0")) + p.overage.value
    return totals


def _map_dto_to_engine_specs(
    items: list[ShoplistItemDTO],
) -> list[IngredientSpec]:
    """
    Map DTO items to engine IngredientSpec models.

    RU: Преобразует DTO items в core IngredientSpec модели для engine.
    EN: Maps DTO items to core IngredientSpec models for engine.

    Args:
        items: List of ShoplistItemDTO from request

    Returns:
        List of IngredientSpec for engine pipeline
    """
    return [
        IngredientSpec(
            food=FoodRef(food_id=item.food_id),
            qty=Quantity(value=item.qty.value, unit=_map_unit(item.qty.unit)),
            form=_map_form(item.form),
        )
        for item in items
    ]


def _map_dto_to_engine_rules(
    packaging_rules: list[PackageRuleDTO] | None,
) -> list[PackageRule]:
    """
    Map DTO packaging rules to engine PackageRule models.

    RU: Преобразует DTO packaging rules в core PackageRule модели.
    EN: Maps DTO packaging rules to core PackageRule models.

    Args:
        packaging_rules: Optional list of PackageRuleDTO from request

    Returns:
        List of PackageRule for engine pipeline
    """
    if not packaging_rules:
        return []
    return [
        PackageRule(
            food_id=r.food_id,
            pack_size=Quantity(value=r.pack_size.value, unit=_map_unit(r.pack_size.unit)),
            rounding=_map_rounding(r.rounding),
            min_packs=r.min_packs,
        )
        for r in packaging_rules
    ]


def _build_shoplist_response(
    result: PackagingResult,
    rules: list[PackageRule],
    *,
    include_analytics: bool = True,
) -> ShoplistGenerateResponse:
    """
    Build shoplist response DTO from engine result.

    RU: Собирает DTO ответ из результата engine (explainability + analytics).
    EN: Builds DTO response from engine result (explainability + analytics).

    Args:
        result: PackagingResult from ShoplistEngine.generate
        rules: List of PackageRule used for generation
        include_analytics: Whether to include analytics in response

    Returns:
        ShoplistGenerateResponse with packed/unpacked lines and analytics

    Raises:
        HTTPException: 500 if packed item missing packaging rule (contract violation)
    """
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

    analytics = None
    if include_analytics:
        overage_totals = _sum_overage_by_unit(result)
        analytics = ShoplistAnalyticsDTO(
            total_lines=len(result.packed) + len(result.unpacked),
            packed_lines=len(result.packed),
            unpacked_lines=len(result.unpacked),
            # k is already UnitDTO from _sum_overage_by_unit return type
            total_overage_by_unit={k: str(v) for k, v in overage_totals.items()},
        )

    return ShoplistGenerateResponse(
        packed=packed_dto,
        unpacked=unpacked_dto,
        analytics=analytics,
    )


@router.get(
    "/preview",
    response_model=ShoplistPreviewResponse,
    responses=COMMON_VIP_SHOPLIST_RESPONSES,
    summary="VIP shoplist preview (legacy)",
    description="Legacy preview endpoint. For new integrations, use /generate, /daily, or /weekly.",
)
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


class _ShoplistLikeRequest(Protocol):
    """
    RU: Минимальный контракт для генерации shoplist.
    EN: Minimal request contract for shoplist generation.

    Any request DTO that provides these fields can be used by the shared generator.
    """

    items: list[ShoplistItemDTO]
    packaging_rules: list[PackageRuleDTO] | None


async def _generate_vip_shoplist(
    payload: _ShoplistLikeRequest,
    *,
    region_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> ShoplistGenerateResponse:
    """
    Internal function to generate VIP shoplist (shared by /generate, /daily, and /export).

    RU: Внутренняя функция генерации shoplist (используется /generate, /daily и /export).
    EN: Internal shoplist generation function (used by /generate, /daily, and /export).
    """
    # Map DTO -> core models
    specs = _map_dto_to_engine_specs(payload.items)
    rules = _map_dto_to_engine_rules(payload.packaging_rules)

    # Run engine pipeline
    result = ShoplistEngine.generate(specs, packaging_rules=rules)

    # Build response
    response = _build_shoplist_response(result, rules, include_analytics=True)

    # Enrichment (fail-soft, adapter-only)
    response = enrich_shoplist_response(
        response,
        region_id=region_id,
        store_id=store_id,
        provider=_get_catalog_provider(),
    )
    return response


@router.post(
    "/generate",
    response_model=ShoplistGenerateResponse,
    responses=COMMON_VIP_SHOPLIST_RESPONSES,
    summary="Generate VIP shoplist (deterministic)",
    description=(
        "Deterministic shoplist generation. Decimals are serialized as strings. "
        "Includes explainability (reasons/reason) and analytics. "
        "Optional catalog enrichment via region_id/store_id query params."
    ),
)
async def vip_shoplist_generate(
    payload: ShoplistGenerateRequest,
    region_id: Annotated[
        Optional[str],
        Query(description="Optional region id (e.g. 'es', 'us')"),
    ] = None,
    store_id: Annotated[
        Optional[str],
        Query(description="Optional store id (e.g. 'carrefour_es', 'walmart_us')"),
    ] = None,
    _enabled: Annotated[None, Depends(require_vip_module_enabled)] = None,
    _vip: Annotated[str, Depends(require_vip_tier)] = "",
) -> ShoplistGenerateResponse:
    """
    Generate shopping list with packaging rules (ShoplistEngine v1).

    RU: Генерирует список покупок с применением правил упаковки.
    EN: Generates shopping list with packaging rules applied.

    This endpoint uses the pure ShoplistEngine v1 pipeline:
    normalize → aggregate → package

    No prices, no stores, no external calls - pure deterministic calculation.
    """
    return await _generate_vip_shoplist(payload, region_id=region_id, store_id=store_id)


@router.post(
    "/daily",
    response_model=ShoplistGenerateResponse,
    responses=COMMON_VIP_SHOPLIST_RESPONSES,
    summary="Generate daily VIP shoplist (deterministic)",
    description=(
        "Daily shoplist generation. Same contract as /generate: "
        "deterministic, includes explainability (reasons/reason) and analytics. "
        "Decimals serialized as strings. "
        "Optional catalog enrichment via region_id/store_id query params."
    ),
)
async def vip_shoplist_daily(
    payload: ShoplistDailyRequest,
    region_id: Annotated[
        Optional[str],
        Query(description="Optional region id (e.g. 'es', 'us')"),
    ] = None,
    store_id: Annotated[
        Optional[str],
        Query(description="Optional store id (e.g. 'carrefour_es', 'walmart_us')"),
    ] = None,
    _enabled: Annotated[None, Depends(require_vip_module_enabled)] = None,
    _vip: Annotated[str, Depends(require_vip_tier)] = "",
) -> ShoplistGenerateResponse:
    """
    Generate daily shopping list with packaging rules (ShoplistEngine v1).

    RU: Генерирует список покупок на день с применением правил упаковки.
    EN: Generates daily shopping list with packaging rules applied.

    This endpoint uses the same pipeline as /generate:
    normalize → aggregate → package

    Contract matches /generate: same gating, mapping, and response format.
    """
    # DRY: delegate to the shared generator used by /generate and /export.
    return await _generate_vip_shoplist(payload, region_id=region_id, store_id=store_id)


@router.post(
    "/weekly",
    response_model=ShoplistWeeklyResponse,
    responses=COMMON_VIP_SHOPLIST_RESPONSES,
    summary="Generate weekly VIP shoplist (deterministic)",
    description=(
        "Weekly shoplist generation (multiple days). "
        "Each day processed independently with same contract as /generate: "
        "deterministic, includes explainability (reasons/reason) and analytics per day. "
        "Decimals serialized as strings. Days length = as requested (no fixed 7-day requirement). "
        "Optional catalog enrichment via region_id/store_id query params (applied to all days)."
    ),
)
async def vip_shoplist_weekly(
    payload: ShoplistWeeklyRequest,
    region_id: Annotated[
        Optional[str],
        Query(description="Optional region id (e.g. 'es', 'us')"),
    ] = None,
    store_id: Annotated[
        Optional[str],
        Query(description="Optional store id (e.g. 'carrefour_es', 'walmart_us')"),
    ] = None,
    _enabled: Annotated[None, Depends(require_vip_module_enabled)] = None,
    _vip: Annotated[str, Depends(require_vip_tier)] = "",
) -> ShoplistWeeklyResponse:
    """
    Generate weekly shopping list with packaging rules (ShoplistEngine v1).

    RU: Генерирует список покупок на неделю с применением правил упаковки.
    EN: Generates weekly shopping list with packaging rules applied.

    This endpoint processes each day independently using the same pipeline as /generate:
    normalize → aggregate → package

    Contract matches /generate: same gating, mapping, and response format per day.
    """
    # Hoist provider lookup before loop to avoid repeated calls
    provider = _get_catalog_provider()
    days = []
    for day_req in payload.days:
        # Map DTO -> core models
        specs = _map_dto_to_engine_specs(day_req.items)
        rules = _map_dto_to_engine_rules(day_req.packaging_rules)

        # Run engine pipeline
        result = ShoplistEngine.generate(specs, packaging_rules=rules)

        # Build response for this day
        day_response = _build_shoplist_response(result, rules, include_analytics=True)

        # Enrichment (fail-soft, adapter-only)
        day_response = enrich_shoplist_response(
            day_response,
            region_id=region_id,
            store_id=store_id,
            provider=provider,
        )
        days.append(day_response)

    return ShoplistWeeklyResponse(days=days)


@router.post(
    "/export",
    responses={
        **COMMON_VIP_SHOPLIST_RESPONSES,
        429: {"description": "Rate limit exceeded"},
    },
    summary="Export VIP shoplist to CSV or PDF",
    description=(
        "Export shoplist in CSV or PDF format. "
        "Uses same generation logic as /generate endpoint. "
        "Deterministic ordering: store_id, aisle, food_id."
    ),
)
@limit_if_available(RATE_LIMIT_EXPORTS)
async def vip_shoplist_export(
    request: Request,  # Required by slowapi for rate limiting
    payload: ShoplistGenerateRequest,
    export_format: Annotated[
        str | None, Query(description="Export format (export_format; csv or pdf)")
    ] = None,
    _legacy_format: Annotated[
        str | None,
        Query(alias="format", include_in_schema=False, description="Deprecated: use export_format"),
    ] = None,
    region_id: Annotated[
        Optional[str],
        Query(description="Optional region id (e.g. 'es', 'us')"),
    ] = None,
    store_id: Annotated[
        Optional[str],
        Query(description="Optional store id (e.g. 'carrefour_es', 'walmart_us')"),
    ] = None,
    _enabled: Annotated[None, Depends(require_vip_module_enabled)] = None,
    _vip: Annotated[str, Depends(require_vip_tier)] = "",
) -> Response:
    """
    Export shopping list to CSV or PDF format.

    RU: Экспортирует список покупок в CSV или PDF.
    EN: Exports shopping list to CSV or PDF.

    This endpoint reuses the /generate logic without duplicating engine code.
    No engine changes, pure export function.
    """

    export_format = export_format or _legacy_format or "csv"
    format_lower = export_format.lower()

    if format_lower not in ("csv", "pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only csv and pdf formats are supported",
        )

    # Важно: НЕ дублируем логику, не трогаем engine — переиспользуем внутреннюю функцию.
    result = await _generate_vip_shoplist(payload, region_id=region_id, store_id=store_id)

    if format_lower == "csv":
        csv_data = export_shoplist_to_csv(result)
        return Response(
            content=csv_data,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="shoplist.csv"'},
        )
    else:  # pdf
        try:
            pdf_data = _export_shoplist_to_pdf(result)
            return Response(
                content=pdf_data,
                media_type="application/pdf",
                headers={"Content-Disposition": 'attachment; filename="shoplist.pdf"'},
            )
        except ImportError as e:
            logger.exception("PDF export is not available")
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="PDF export is not available",
            ) from e


__all__ = ["router"]
