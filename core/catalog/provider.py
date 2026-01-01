# -*- coding: utf-8 -*-
"""
Catalog provider interfaces (PR-7).

RU: Интерфейсы для провайдеров каталога (read-only query surface).
EN: Interfaces for catalog providers (read-only query surface).

This module defines the contract that catalog providers must implement.
Loaders (offline snapshot builders) are separate from providers (runtime readers).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, Sequence


@dataclass(frozen=True)
class CatalogRegion:
    """
    RU: Каноническая модель региона каталога.
    EN: Canonical catalog region model.
    """

    region_id: str  # "ES" / "US"
    country: str  # "ES" / "US"
    currency: str  # "EUR" / "USD"
    locale: str  # "es-ES" / "en-US"


@dataclass(frozen=True)
class CatalogStore:
    """
    RU: Каноническая модель магазина в регионе.
    EN: Canonical store model in region.
    """

    store_id: str  # "carrefour_es_main" / "walmart_us_main"
    region_id: str
    name: str
    provider: str  # "carrefour" / "walmart"
    meta_json: str | None = None  # optional serialized metadata


@dataclass(frozen=True)
class CatalogSKU:
    """
    RU: Каноническая модель SKU (Stock Keeping Unit).
    EN: Canonical SKU model.
    """

    sku_id: str  # provider-specific id or hashed
    store_id: str
    ean: str | None  # barcode if known
    name: str
    brand: str | None
    aisle: str | None
    package_size: Decimal | None
    unit: str | None  # "g", "ml", "pcs"
    price: Decimal | None
    currency: str  # redundantly stored for safety
    updated_at: str | None  # ISO date string


@dataclass(frozen=True)
class CatalogSnapshot:
    """
    RU: Снимок каталога (результат работы loader'а).
    EN: Catalog snapshot (loader output).

    This is the canonical data structure that loaders produce.
    Storage layer (SQLite writer) consumes this.
    """

    regions: Sequence[CatalogRegion]
    stores: Sequence[CatalogStore]
    skus: Sequence[CatalogSKU]
    aliases: Sequence[tuple[str, str]]  # (alias -> sku_id)


class CatalogLoader(Protocol):
    """
    RU: Протокол для загрузчиков каталога (offline snapshot builders).
    EN: Protocol for catalog loaders (offline snapshot builders).

    Loaders read raw sources (CSV/JSON) and produce canonical snapshots.
    No I/O in request-path; loaders run during data preparation.
    """

    source_name: str
    """RU: Имя источника (для логирования). EN: Source name (for logging)."""

    def load(self) -> CatalogSnapshot:
        """
        RU: Загрузить и нормализовать данные в канонический snapshot.
        EN: Load and normalize data into canonical snapshot.

        Returns:
            CatalogSnapshot with all regions, stores, SKUs, and aliases.
        """
        ...


class CatalogProvider(Protocol):
    """
    RU: Протокол для провайдеров каталога (read-only query surface).
    EN: Protocol for catalog providers (read-only query surface).

    Providers are used by adapter layer at runtime (no I/O, no network).
    """

    def get_sku_by_alias(
        self,
        *,
        region_id: str,
        alias: str,
        store_id: str | None = None,
    ) -> CatalogSKU | None:
        """
        RU: Найти SKU по alias (food_id, EAN, или название).
        EN: Find SKU by alias (food_id, EAN, or name).

        Args:
            region_id: Region identifier (e.g., "es", "us")
            alias: Food ID, EAN, or name to search
            store_id: Optional store filter

        Returns:
            CatalogSKU if found, None otherwise (fail-soft)
        """
        ...

    def list_stores(self, *, region_id: str) -> list[CatalogStore]:
        """
        RU: Список магазинов в регионе.
        EN: List stores in region.

        Args:
            region_id: Region identifier

        Returns:
            List of stores (empty if region not found)
        """
        ...
