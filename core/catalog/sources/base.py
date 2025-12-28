"""Catalog source interface used by CatalogService."""

from __future__ import annotations

from typing import Protocol, Sequence

from core.catalog.types import Region, SKU, Store


class CatalogSource(Protocol):
    """Source/provider contract for listing regions/stores and searching SKUs."""

    source_id: str
    source_name: str

    def list_regions(self) -> Sequence[Region]:
        """Return supported regions for this source."""

    def list_stores(self, *, region_id: str) -> Sequence[Store]:
        """Return stores for a given region."""

    def search(
        self,
        *,
        q: str,
        region_id: str,
        store_id: str | None,
        limit: int,
    ) -> Sequence[SKU]:
        """Search for SKUs in a region, optionally scoped to a store."""
