from __future__ import annotations

from core.catalog.sources.carrefour_stub import CarrefourStubSource
from core.catalog.sources.off_stub import OffStubSource
from core.catalog.sources.walmart_stub import WalmartStubSource


def test_off_stub_source_search_edge_cases() -> None:
    source = OffStubSource()

    assert source.search(q="ban", region_id="FR", store_id=None, limit=10) == []
    assert source.search(q="ban", region_id="ES", store_id="off:US", limit=10) == []
    assert source.search(q="  ", region_id="ES", store_id="off:ES", limit=10) == []


def test_carrefour_stub_source_search_edge_cases() -> None:
    source = CarrefourStubSource()

    assert source.search(q="ban", region_id="US", store_id=None, limit=10) == []
    assert source.search(q="ban", region_id="ES", store_id="off:ES", limit=10) == []
    assert source.search(q=" ", region_id="ES", store_id="carrefour:ES", limit=10) == []


def test_walmart_stub_source_search_edge_cases_and_happy_path() -> None:
    source = WalmartStubSource()

    assert source.search(q="ban", region_id="US", store_id="wrong-store", limit=10) == []
    assert source.search(q=" ", region_id="US", store_id=None, limit=10) == []

    results = source.search(q="oat", region_id="US", store_id="walmart:US", limit=10)
    assert [sku.id for sku in results] == ["walmart:US:oats"]
