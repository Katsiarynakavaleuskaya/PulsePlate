# -*- coding: utf-8 -*-
"""
VIP Shoplist Preview Schemas

RU: Схемы для preview-only списка покупок VIP.
EN: Schemas for VIP preview-only shopping list.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
