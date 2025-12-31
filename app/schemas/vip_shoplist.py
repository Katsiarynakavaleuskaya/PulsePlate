# -*- coding: utf-8 -*-
"""
VIP Shoplist Schemas

RU: Схемы для VIP списка покупок (preview и generate endpoints).
EN: Schemas for VIP shopping list (preview and generate endpoints).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


# RU: DTO слой — адаптер над core моделями. Здесь можно использовать Decimal.
# EN: DTO layer — adapter over core models. Decimal is allowed.

# RU: Константа для explainability (один источник правды).
# EN: Constant for explainability (single source of truth).
REASON_NO_PACKAGING_RULE = "no_packaging_rule"

UnitDTO = Literal["G", "ML", "PCS", "KG", "L"]  # расширишь по мере надобности
FoodFormDTO = Literal["RAW", "COOKED", "FROZEN", "DRIED", "CANNED"]  # расширится позже
RoundingModeDTO = Literal["CEIL", "NEAREST", "NONE"]


class QuantityDTO(BaseModel):
    value: Decimal = Field(..., ge=0)
    unit: UnitDTO


class ShoplistItemDTO(BaseModel):
    food_id: str = Field(..., min_length=1)
    qty: QuantityDTO
    form: FoodFormDTO = "RAW"


class PackageRuleDTO(BaseModel):
    food_id: str = Field(..., min_length=1)
    pack_size: QuantityDTO
    rounding: RoundingModeDTO = "CEIL"
    min_packs: int = Field(1, ge=1)


class ShoplistGenerateRequest(BaseModel):
    items: list[ShoplistItemDTO] = Field(default_factory=list)
    packaging_rules: Optional[list[PackageRuleDTO]] = None


# --- Response DTOs ---


class PackedLineDTO(BaseModel):
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
    food_id: str
    requested: QuantityDTO
    # RU: Default, чтобы не ломать старые конструкторы и гарантировать стабильный API контракт.
    # EN: Default to keep backward compatibility and stable API contract.
    reason: str = Field(default=REASON_NO_PACKAGING_RULE)


class ShoplistGenerateResponse(BaseModel):
    packed: list[PackedLineDTO]
    unpacked: list[UnpackedLineDTO]


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
