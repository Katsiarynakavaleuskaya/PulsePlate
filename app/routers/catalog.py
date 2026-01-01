"""Region catalog endpoints (skeleton, offline stubs only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.schemas.catalog import CatalogRegion, CatalogSKU, CatalogStore
from core.catalog.service import CatalogService, default_catalog_service

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


def get_catalog_service() -> CatalogService:
    """
    RU: Dependency provider. Важно: без import-time синглтонов.
    EN: Dependency provider. Avoid import-time singletons for testability.
    """
    return default_catalog_service()


@router.get("/regions", response_model=list[CatalogRegion])
def list_regions(service: CatalogService = Depends(get_catalog_service)) -> list[CatalogRegion]:
    """
    RU: Список доступных регионов каталога.
    EN: List available catalog regions.
    """
    regions = service.list_regions()
    return [CatalogRegion(**region.model_dump()) for region in regions]


@router.get("/stores", response_model=list[CatalogStore])
def list_stores(
    region_id: str = Query(..., min_length=2, max_length=8),
    service: CatalogService = Depends(get_catalog_service),
) -> list[CatalogStore]:
    """
    RU: Список магазинов в регионе.
    EN: List stores in a region.
    """
    stores = service.list_stores(region_id=region_id)
    return [CatalogStore(**store.model_dump()) for store in stores]


@router.get("/search", response_model=list[CatalogSKU])
def search(
    q: str = Query(..., min_length=1, max_length=64),
    region_id: str = Query(..., min_length=2, max_length=8),
    store_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=50),
    service: CatalogService = Depends(get_catalog_service),
) -> list[CatalogSKU]:
    """
    RU: Поиск SKU в каталоге.
    EN: Search for SKUs in catalog.
    """
    skus = service.search(q=q, region_id=region_id, store_id=store_id, limit=limit)
    return [CatalogSKU(**sku.model_dump()) for sku in skus]
