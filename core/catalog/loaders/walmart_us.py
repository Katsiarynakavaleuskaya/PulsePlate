# -*- coding: utf-8 -*-
"""
Walmart US loader (PR-7).

RU: Загрузчик каталога Walmart для США.
EN: Walmart catalog loader for USA.

This loader reads raw CSV snapshots and produces canonical CatalogSnapshot.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from core.catalog.loaders.base import read_csv_rows
from core.catalog.normalize.alias import norm_alias
from core.catalog.normalize.common import normalize_currency, normalize_unit, parse_decimal
from core.catalog.provider import (
    CatalogRegion,
    CatalogSKU,
    CatalogSnapshot,
    CatalogStore,
)


class WalmartUSLoader:
    """
    RU: Загрузчик каталога Walmart US.
    EN: Walmart US catalog loader.

    Reads CSV from raw_path and produces canonical snapshot.
    """

    source_name = "walmart_us"

    def __init__(self, raw_path: str | Path) -> None:
        """
        Args:
            raw_path: Path to CSV file with raw catalog data
        """
        self._raw_path = Path(raw_path)

    def load(self) -> CatalogSnapshot:
        """
        RU: Загрузить каталог Walmart US.
        EN: Load Walmart US catalog.

        Returns:
            CatalogSnapshot with regions, stores, SKUs, and aliases
        """
        rows = read_csv_rows(self._raw_path)
        region = CatalogRegion(region_id="US", country="US", currency="USD", locale="en-US")

        stores: dict[str, CatalogStore] = {}
        skus: list[CatalogSKU] = []
        aliases: list[tuple[str, str]] = []
        seen_aliases: set[str] = set()

        for row in rows:
            if row.get("region_id") != "US":
                continue

            store_id = (row.get("store_id") or "walmart_us_main").strip()
            if store_id not in stores:
                stores[store_id] = CatalogStore(
                    store_id=store_id,
                    region_id="US",
                    name="Walmart (US)",
                    provider="walmart",
                    meta_json=None,
                )

            alias = norm_alias(row.get("alias") or row.get("ean") or row.get("name") or "")
            if not alias:
                continue

            name = (row.get("name") or "").strip()
            if not name:
                continue

            sku_id = (row.get("sku_id") or "").strip() or _stable_sku_id(
                "walmart", "US", store_id, alias
            )

            currency = normalize_currency(row.get("currency"), default="USD")
            sku = CatalogSKU(
                sku_id=sku_id,
                store_id=store_id,
                ean=_opt(row.get("ean")),
                name=name,
                brand=_opt(row.get("brand")),
                aisle=_opt(row.get("aisle")),
                package_size=parse_decimal(_opt(row.get("package_size"))),
                unit=normalize_unit(_opt(row.get("unit"))),
                price=parse_decimal(_opt(row.get("price"))),
                currency=currency,
                updated_at=_opt(row.get("updated_at")),
            )
            skus.append(sku)

            if alias in seen_aliases:
                continue
            seen_aliases.add(alias)
            aliases.append((alias, sku_id))

        return CatalogSnapshot(
            regions=[region],
            stores=list(stores.values()),
            skus=skus,
            aliases=aliases,
        )


def _stable_sku_id(provider: str, region_id: str, store_id: str, alias: str) -> str:
    """Generate stable deterministic SKU ID from provider/region/store/alias."""
    payload = f"{provider}:{region_id}:{store_id}:{alias}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def _opt(v: str | None) -> str | None:
    """Return None if value is empty/whitespace."""
    if v is None:
        return None
    s = v.strip()
    return s or None


