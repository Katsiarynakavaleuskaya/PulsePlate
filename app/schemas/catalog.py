"""Pydantic schemas for catalog endpoints (region/store/SKU stubs)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CatalogRegion(BaseModel):
    id: str = Field(..., min_length=2, max_length=8)
    name: str = Field(..., min_length=1, max_length=100)

    model_config = ConfigDict(frozen=True)


class CatalogStore(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    region_id: str = Field(..., min_length=2, max_length=8)
    name: str = Field(..., min_length=1, max_length=100)
    source_id: str = Field(..., min_length=1, max_length=32)

    model_config = ConfigDict(frozen=True)


class CatalogSKU(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    region_id: str = Field(..., min_length=2, max_length=8)
    store_id: str = Field(..., min_length=1, max_length=64)
    source_id: str = Field(..., min_length=1, max_length=32)

    model_config = ConfigDict(frozen=True)
