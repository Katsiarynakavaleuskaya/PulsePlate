"""Region catalog endpoints (skeleton, offline stubs only)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.catalog import CatalogRegion, CatalogSKU, CatalogStore
from core.catalog.service import default_catalog_service

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])
_service = default_catalog_service()


@router.get("/regions", response_model=list[CatalogRegion])
async def list_regions() -> list[CatalogRegion]:
    regions = _service.list_regions()
    return [CatalogRegion(**region.model_dump()) for region in regions]


@router.get("/stores", response_model=list[CatalogStore])
async def list_stores(
    region_id: str = Query(..., min_length=2, max_length=8)
) -> list[CatalogStore]:
    stores = _service.list_stores(region_id=region_id)
    return [CatalogStore(**store.model_dump()) for store in stores]


@router.get("/search", response_model=list[CatalogSKU])
async def search(
    q: str = Query(..., min_length=1, max_length=64),
    region_id: str = Query(..., min_length=2, max_length=8),
    store_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=50),
) -> list[CatalogSKU]:
    skus = _service.search(q=q, region_id=region_id, store_id=store_id, limit=limit)
    return [CatalogSKU(**sku.model_dump()) for sku in skus]
