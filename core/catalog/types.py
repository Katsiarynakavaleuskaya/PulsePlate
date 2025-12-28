"""Domain types for the (stubbed) region catalog."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Region(BaseModel):
    """A geographic region that scopes available stores and SKUs."""

    id: str = Field(
        ..., min_length=2, max_length=8, description="Stable region identifier (e.g. ES)"
    )
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable region name")

    model_config = ConfigDict(frozen=True)


class Store(BaseModel):
    """A store within a region backed by a catalog source."""

    id: str = Field(..., min_length=1, max_length=64, description="Stable store identifier")
    region_id: str = Field(..., min_length=2, max_length=8, description="Owning region id")
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable store name")
    source_id: str = Field(..., min_length=1, max_length=32, description="Source/provider id")

    model_config = ConfigDict(frozen=True)


class SKU(BaseModel):
    """A product listing entry returned from search."""

    id: str = Field(..., min_length=1, max_length=128, description="Stable SKU identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    brand: str | None = Field(default=None, max_length=100, description="Brand name (optional)")
    barcode: str | None = Field(
        default=None, max_length=64, description="Barcode/EAN/UPC (optional)"
    )
    region_id: str = Field(..., min_length=2, max_length=8, description="Region id")
    store_id: str = Field(..., min_length=1, max_length=64, description="Store id")
    source_id: str = Field(..., min_length=1, max_length=32, description="Source/provider id")

    model_config = ConfigDict(frozen=True)
