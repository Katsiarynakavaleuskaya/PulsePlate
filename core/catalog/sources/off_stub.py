"""Open Food Facts catalog source (stub, no network)."""

from __future__ import annotations

from core.catalog.types import Region, SKU, Store


class OffStubSource:
    source_id = "off"
    source_name = "Open Food Facts (stub)"

    _REGIONS = [
        Region(id="ES", name="Spain"),
        Region(id="US", name="United States"),
    ]

    _STORES_BY_REGION: dict[str, list[Store]] = {
        "ES": [Store(id="off:ES", region_id="ES", name="Open Food Facts", source_id=source_id)],
        "US": [Store(id="off:US", region_id="US", name="Open Food Facts", source_id=source_id)],
    }

    _SKUS_BY_REGION: dict[str, list[SKU]] = {
        "ES": [
            SKU(
                id="off:ES:banana",
                name="Banana",
                brand=None,
                barcode="000000000001",
                region_id="ES",
                store_id="off:ES",
                source_id=source_id,
            ),
            SKU(
                id="off:ES:olive-oil",
                name="Extra Virgin Olive Oil",
                brand="Stub Brand",
                barcode="000000000002",
                region_id="ES",
                store_id="off:ES",
                source_id=source_id,
            ),
        ],
        "US": [
            SKU(
                id="off:US:banana",
                name="Banana",
                brand=None,
                barcode="000000000101",
                region_id="US",
                store_id="off:US",
                source_id=source_id,
            ),
            SKU(
                id="off:US:peanut-butter",
                name="Peanut Butter",
                brand="Stub Brand",
                barcode="000000000102",
                region_id="US",
                store_id="off:US",
                source_id=source_id,
            ),
        ],
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
