# -*- coding: utf-8 -*-
"""
Catalog enrichment schemas (adapter-only).

RU: Схемы для enrichment слоя (каталожная информация: SKU, цена, aisle).
EN: Schemas for enrichment layer (catalog info: SKU, price, aisle).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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
