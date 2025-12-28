from __future__ import annotations

from typing import cast

import pytest
from fastapi.testclient import TestClient
from starlette.types import ASGIApp


@pytest.fixture()
def client(test_environment) -> TestClient:
    import app

    return TestClient(cast(ASGIApp, app.app))


def test_catalog_regions_stores_search_smoke(client: TestClient) -> None:
    regions = client.get("/api/v1/catalog/regions")
    assert regions.status_code == 200
    assert [row["id"] for row in regions.json()] == ["ES", "US"]

    stores = client.get("/api/v1/catalog/stores", params={"region_id": "ES"})
    assert stores.status_code == 200
    assert {row["id"] for row in stores.json()} == {"carrefour:ES", "off:ES"}

    search = client.get(
        "/api/v1/catalog/search", params={"q": "ban", "region_id": "ES", "limit": 20}
    )
    assert search.status_code == 200
    assert [row["id"] for row in search.json()[:2]] == ["carrefour:ES:banana", "off:ES:banana"]


def test_catalog_search_validation_returns_422(client: TestClient) -> None:
    empty_q = client.get("/api/v1/catalog/search", params={"q": "", "region_id": "ES"})
    assert empty_q.status_code == 422

    bad_limit = client.get(
        "/api/v1/catalog/search", params={"q": "ban", "region_id": "ES", "limit": 0}
    )
    assert bad_limit.status_code == 422
