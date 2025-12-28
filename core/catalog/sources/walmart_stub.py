"""Walmart catalog source (stub, no network)."""

from __future__ import annotations

from core.catalog.types import Region, SKU, Store


class WalmartStubSource:
    source_id = "walmart"
    source_name = "Walmart (stub)"

    _REGIONS = [Region(id="US", name="United States")]
    _STORES_BY_REGION: dict[str, list[Store]] = {
        "US": [Store(id="walmart:US", region_id="US", name="Walmart", source_id=source_id)]
    }
    _SKUS_BY_REGION: dict[str, list[SKU]] = {
        "US": [
            SKU(
                id="walmart:US:banana",
                name="Banana",
                brand="Walmart",
                barcode="200000000001",
                region_id="US",
                store_id="walmart:US",
                source_id=source_id,
            ),
            SKU(
                id="walmart:US:oats",
                name="Rolled Oats",
                brand="Walmart",
                barcode="200000000002",
                region_id="US",
                store_id="walmart:US",
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
