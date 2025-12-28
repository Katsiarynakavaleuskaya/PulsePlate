"""Carrefour catalog source (stub, no network)."""

from __future__ import annotations

from core.catalog.types import Region, SKU, Store


class CarrefourStubSource:
    source_id = "carrefour"
    source_name = "Carrefour (stub)"

    _REGIONS = [Region(id="ES", name="Spain")]
    _STORES_BY_REGION: dict[str, list[Store]] = {
        "ES": [Store(id="carrefour:ES", region_id="ES", name="Carrefour", source_id=source_id)]
    }
    _SKUS_BY_REGION: dict[str, list[SKU]] = {
        "ES": [
            SKU(
                id="carrefour:ES:banana",
                name="Banana",
                brand="Carrefour",
                barcode="100000000001",
                region_id="ES",
                store_id="carrefour:ES",
                source_id=source_id,
            ),
            SKU(
                id="carrefour:ES:milk",
                name="Whole Milk",
                brand="Carrefour",
                barcode="100000000002",
                region_id="ES",
                store_id="carrefour:ES",
                source_id=source_id,
            ),
        ]
    }

    def list_regions(self) -> list[Region]:
        return list(self._REGIONS)

    def list_stores(self, *, region_id: str) -> list[Store]:
        rid = region_id.strip().upper()
        return list(self._STORES_BY_REGION.get(rid, []))

    def search(
        self,
        *,
        q: str,
        region_id: str,
        store_id: str | None,
        limit: int,
    ) -> list[SKU]:
        rid = region_id.strip().upper()
        if rid not in self._SKUS_BY_REGION:
            return []

        expected_store_ids = {store.id for store in self._STORES_BY_REGION.get(rid, [])}
        if store_id is not None and store_id not in expected_store_ids:
            return []

        query = q.strip().lower()
        if not query:
            return []

        matches = [sku for sku in self._SKUS_BY_REGION[rid] if query in sku.name.lower()]
        matches.sort(key=lambda sku: (sku.name.lower(), sku.id))
        return matches[:limit]
