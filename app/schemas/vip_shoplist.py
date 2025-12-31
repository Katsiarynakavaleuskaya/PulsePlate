# -*- coding: utf-8 -*-
"""
VIP Shoplist Schemas

RU: Схемы для VIP списка покупок (preview и generate endpoints).
EN: Schemas for VIP shopping list (preview and generate endpoints).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


# RU: DTO слой — адаптер над core моделями. Здесь можно использовать Decimal.
# EN: DTO layer — adapter over core models. Decimal is allowed.

# RU: Константа для explainability (один источник правды).
# EN: Constant for explainability (single source of truth).
REASON_NO_PACKAGING_RULE = "no_packaging_rule"

UnitDTO = Literal["G", "ML", "PCS", "KG", "L"]  # расширишь по мере надобности / expand as needed
FoodFormDTO = Literal[
    "RAW", "COOKED", "FROZEN", "DRIED", "CANNED"
]  # расширится позже / will expand later
RoundingModeDTO = Literal["CEIL", "NEAREST", "NONE"]  # rounding mode


class QuantityDTO(BaseModel):
    """Quantity with value and unit (deterministic, no prices)."""

    value: Decimal = Field(..., ge=0)
    unit: UnitDTO


class ShoplistItemDTO(BaseModel):
    """Shopping list item specification (food, quantity, form)."""

    food_id: str = Field(..., min_length=1)
    qty: QuantityDTO
    form: FoodFormDTO = "RAW"


class PackageRuleDTO(BaseModel):
    """Packaging rule for a food item (pack size, rounding mode, minimum packs)."""

    food_id: str = Field(..., min_length=1)
    pack_size: QuantityDTO
    rounding: RoundingModeDTO = "CEIL"
    min_packs: int = Field(1, ge=1)


class ShoplistGenerateRequest(BaseModel):
    """Request payload for POST /api/v1/vip/shoplist/generate."""

    items: list[ShoplistItemDTO] = Field(default_factory=list)
    packaging_rules: list[PackageRuleDTO] | None = None


class ShoplistDailyRequest(BaseModel):
    """Request payload for POST /api/v1/vip/shoplist/daily."""

    items: list[ShoplistItemDTO] = Field(default_factory=list)
    packaging_rules: list[PackageRuleDTO] | None = None


class ShoplistWeeklyDayRequest(BaseModel):
    """Request payload for one day in weekly shoplist."""

    items: list[ShoplistItemDTO] = Field(default_factory=list)
    packaging_rules: list[PackageRuleDTO] | None = None


class ShoplistWeeklyRequest(BaseModel):
    """Request payload for POST /api/v1/vip/shoplist/weekly."""

    days: list[ShoplistWeeklyDayRequest] = Field(default_factory=list)


class ShoplistWeeklyResponse(BaseModel):
    """Response for POST /api/v1/vip/shoplist/weekly."""

    days: list[ShoplistGenerateResponse] = Field(default_factory=list)


# --- Response DTOs ---


class PackedLineDTO(BaseModel):
    """Packed shopping list line with packaging details and explainability reasons."""

    food_id: str
    requested: QuantityDTO
    pack_size: QuantityDTO
    packs: int
    provided: QuantityDTO
    overage: QuantityDTO
    rounding: RoundingModeDTO
    min_packs: int
    reasons: list[str] = Field(default_factory=list)


class UnpackedLineDTO(BaseModel):
    """Unpacked shopping list line (no packaging rule available)."""

    food_id: str
    requested: QuantityDTO
    # RU: Default, чтобы не ломать старые конструкторы и гарантировать стабильный API контракт.
    # EN: Default to keep backward compatibility and stable API contract.
    reason: str = Field(default=REASON_NO_PACKAGING_RULE)


class ShoplistAnalyticsDTO(BaseModel):
    """Analytics summary for shoplist generation (deterministic, no prices)."""

    total_lines: int = Field(..., ge=0)
    packed_lines: int = Field(..., ge=0)
    unpacked_lines: int = Field(..., ge=0)

    # RU: Decimal отдаём строкой → стабильный JSON, без float.
    # EN: Return Decimal totals as strings for stable JSON and no floats.
    total_overage_by_unit: dict[UnitDTO, str] = Field(default_factory=dict)


class ShoplistGenerateResponse(BaseModel):
    """Response for POST /api/v1/vip/shoplist/generate (deterministic, no prices)."""

    packed: list[PackedLineDTO]
    unpacked: list[UnpackedLineDTO]

    # RU: Optional для backward-compat (старые конструкторы/тесты).
    # EN: Optional for backward compatibility with older constructors/tests.
    analytics: ShoplistAnalyticsDTO | None = None


# --- Preview schemas (legacy) ---


class ShoplistPreviewItem(BaseModel):
    """One shopping list preview item (deterministic, no prices)."""

    category: str = Field(..., examples=["vegetables"])
    name: str = Field(..., examples=["Tomatoes"])
    quantity: str = Field(..., examples=["500 g"])


class ShoplistPreviewMeta(BaseModel):
    """Preview metadata; explicitly states that prices are not included."""

    preview: bool = True
    currency: str | None = None
    prices_included: bool = False


class ShoplistPreviewResponse(BaseModel):
    """Response for GET /api/v1/vip/shoplist/preview."""

    items: list[ShoplistPreviewItem]
    meta: ShoplistPreviewMeta = Field(default_factory=ShoplistPreviewMeta)
