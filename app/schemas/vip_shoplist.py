# -*- coding: utf-8 -*-
"""
VIP Shoplist Schemas

RU: Схемы для VIP списка покупок (preview и generate endpoints).
EN: Schemas for VIP shopping list (preview and generate endpoints).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional, cast

from pydantic import BaseModel, Field

from core.shoplist_engine.models import PackageRule
from core.shoplist_engine.packager import PackagingResult

# RU: DTO слой — адаптер над core моделями. Здесь можно использовать Decimal.
# EN: DTO layer — adapter over core models. Decimal is allowed.

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
    min_packs: int = Field(0, ge=0)


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


class UnpackedLineDTO(BaseModel):
    food_id: str
    requested: QuantityDTO


class ShoplistGenerateResponse(BaseModel):
    packed: list[PackedLineDTO]
    unpacked: list[UnpackedLineDTO]

    @classmethod
    def from_core(
        cls,
        result: PackagingResult,
        rules_index: dict[str, PackageRule],
    ) -> ShoplistGenerateResponse:
        """
        Convert core PackagingResult to DTO response.

        Args:
            result: Core packaging result from ShoplistEngine
            rules_index: Mapping of food_id -> PackageRule for rounding/min_packs lookup

        Note:
            PackPlan does not store rounding/min_packs directly; they come from PackageRule.
        """
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
                provided=QuantityDTO(
                    value=p.provided.value, unit=cast(UnitDTO, p.provided.unit.name)
                ),
                overage=QuantityDTO(value=p.overage.value, unit=cast(UnitDTO, p.overage.unit.name)),
                rounding=cast(RoundingModeDTO, rules_index[p.food.food_id].rounding.name),
                min_packs=rules_index[p.food.food_id].min_packs,
            )
            for p in result.packed
        ]

        unpacked_dto = [
            UnpackedLineDTO(
                food_id=u.food.food_id,
                requested=QuantityDTO(value=u.qty.value, unit=cast(UnitDTO, u.qty.unit.name)),
            )
            for u in result.unpacked
        ]
        return cls(packed=packed_dto, unpacked=unpacked_dto)


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
