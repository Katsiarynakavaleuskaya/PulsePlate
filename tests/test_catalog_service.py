from __future__ import annotations

from core.catalog.service import default_catalog_service


def test_catalog_service_regions_and_search_are_deterministic() -> None:
    service = default_catalog_service()

    regions = service.list_regions()
    assert [region.id for region in regions] == ["ES", "US"]

    stores_es = service.list_stores(region_id="es")
    store_ids = [store.id for store in stores_es]
    assert store_ids == ["carrefour:ES", "off:ES"]

    results = service.search(q="ban", region_id="ES", limit=20)
    assert [sku.id for sku in results[:2]] == ["carrefour:ES:banana", "off:ES:banana"]

    off_only = service.search(q="ban", region_id="ES", store_id="off:ES", limit=20)
    assert [sku.id for sku in off_only] == ["off:ES:banana"]
