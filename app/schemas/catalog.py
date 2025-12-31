# -*- coding: utf-8 -*-
"""
Catalog schemas (legacy public API + PR-6 enrichment).

RU: Схемы для catalog API (legacy) и enrichment слоя (PR-6).
EN: Schemas for catalog API (legacy) and enrichment layer (PR-6).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# --- Legacy public surface (MUST stay for app/routers/catalog.py) ---


class CatalogRegion(BaseModel):
    """
    RU: Регион каталога (legacy/public contract).
    EN: Catalog region (legacy/public contract).
    """

    id: str = Field(..., min_length=2, max_length=8)
    name: str = Field(..., min_length=1, max_length=100)

    model_config = ConfigDict(frozen=True)


class CatalogStore(BaseModel):
    """
    RU: Магазин/сеть в регионе (legacy/public contract).
    EN: Store in region (legacy/public contract).
    """

    id: str = Field(..., min_length=1, max_length=64)
    region_id: str = Field(..., min_length=2, max_length=8)
    name: str = Field(..., min_length=1, max_length=100)
    source_id: str = Field(..., min_length=1, max_length=32)

    model_config = ConfigDict(frozen=True)


class CatalogSKU(BaseModel):
    """
    RU: SKU запись (legacy/public contract).
    EN: SKU record (legacy/public contract).
    """

    id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    region_id: str = Field(..., min_length=2, max_length=8)
    store_id: str = Field(..., min_length=1, max_length=64)
    source_id: str = Field(..., min_length=1, max_length=32)

    model_config = ConfigDict(frozen=True)


# --- New PR-6 enrichment DTOs (adapter-only) ---


class CurrencyDTO(str, Enum):
    """Currency codes for price enrichment."""

    EUR = "EUR"
    USD = "USD"
    BYN = "BYN"
    RUB = "RUB"


class MoneyDTO(BaseModel):
    """
    RU: Деньги: Decimal сериализуется в JSON как строка (Pydantic v2).
    EN: Money: Decimal is serialized to JSON as string (Pydantic v2).
    """

    value: Decimal = Field(
        ...,
        description="Decimal-as-string in JSON (no floats)",
        examples=[Decimal("1.29"), Decimal("2.50")],
    )
    currency: CurrencyDTO = Field(..., examples=[CurrencyDTO.EUR, CurrencyDTO.USD])


class CatalogInfoDTO(BaseModel):
    """
    RU: Каталожная информация для enrichment слоя (adapter-only).
    EN: Catalog enrichment info (adapter-only).

    This is attached to shoplist lines when region_id/store_id are provided.
    Missing catalog is not an error (fail-soft).
    """

    sku: str = Field(..., description="Stock Keeping Unit", examples=["CRF-ES-000123"])
    store_id: str = Field(
        ..., description="Store identifier", examples=["carrefour_es", "walmart_us"]
    )
    region_id: str = Field(..., description="Region identifier", examples=["es", "us"])

    pack_label: Optional[str] = Field(
        default=None,
        description="Human-friendly pack label",
        examples=["500 g bag", "1 lb bag"],
    )
    aisle: Optional[str] = Field(
        default=None,
        description="Store aisle/category label",
        examples=["Vegetables", "Produce"],
    )
    price: Optional[MoneyDTO] = Field(
        default=None,
        description="Optional price estimate (Decimal-as-string in JSON)",
    )
