"""CatalogService aggregates multiple sources into a unified catalog API."""

from __future__ import annotations

from collections.abc import Sequence

from core.catalog.sources.base import CatalogSource
from core.catalog.sources.carrefour_stub import CarrefourStubSource
from core.catalog.sources.off_stub import OffStubSource
from core.catalog.sources.walmart_stub import WalmartStubSource
from core.catalog.types import Region, SKU, Store


def _normalize_region_id(region_id: str) -> str:
    return region_id.strip().upper()


class CatalogService:
    """Fan-out service over multiple catalog sources (stubbed, offline)."""

    def __init__(self, *, sources: Sequence[CatalogSource]) -> None:
        self._sources = list(sources)

    def list_regions(self) -> list[Region]:
        by_id: dict[str, Region] = {}
        for source in self._sources:
            for region in source.list_regions():
                by_id.setdefault(_normalize_region_id(region.id), region)
        regions = list(by_id.values())
        regions.sort(key=lambda region: (region.id, region.name))
        return regions

    def list_stores(self, *, region_id: str) -> list[Store]:
        rid = _normalize_region_id(region_id)
        by_id: dict[str, Store] = {}
        for source in self._sources:
            for store in source.list_stores(region_id=rid):
                by_id.setdefault(store.id, store)
        stores = list(by_id.values())
        stores.sort(key=lambda store: (store.region_id, store.source_id, store.name, store.id))
        return stores

    def search(
        self,
        *,
        q: str,
        region_id: str,
        store_id: str | None = None,
        limit: int = 20,
    ) -> list[SKU]:
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")

        rid = _normalize_region_id(region_id)
        query = q.strip()
        if not query:
            return []

        allowed_source_ids: set[str] | None = None
        if store_id is not None:
            # Restrict fan-out to the source that owns the given store_id (if any).
            stores = self.list_stores(region_id=rid)
            store_map = {store.id: store for store in stores}
            store = store_map.get(store_id)
            if store is None:
                return []
            allowed_source_ids = {store.source_id}

        results: list[SKU] = []
        for source in self._sources:
            if allowed_source_ids is not None and source.source_id not in allowed_source_ids:
                continue
            results.extend(source.search(q=query, region_id=rid, store_id=store_id, limit=limit))

        by_id: dict[str, SKU] = {}
        for sku in results:
            by_id.setdefault(sku.id, sku)
        merged = list(by_id.values())
        merged.sort(key=lambda sku: (sku.name.lower(), sku.source_id, sku.id))
        return merged[:limit]


def default_catalog_service() -> CatalogService:
    """Default offline service composed from stub sources only."""

    return CatalogService(
        sources=[
            OffStubSource(),
            CarrefourStubSource(),
            WalmartStubSource(),
        ]
    )
