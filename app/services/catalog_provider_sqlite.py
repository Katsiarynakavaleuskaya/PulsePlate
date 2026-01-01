# -*- coding: utf-8 -*-
"""
SQLite catalog provider (PR-7).

RU: Провайдер каталога на основе SQLite (read-only).
EN: SQLite-based catalog provider (read-only).

This provider reads from pre-built SQLite snapshots (no I/O in request-path).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.schemas.catalog import CatalogInfoDTO, CurrencyDTO, MoneyDTO
from core.catalog.normalize.alias import norm_alias
from core.catalog.normalize.common import parse_decimal
from core.catalog.provider import CatalogProvider, CatalogSKU, CatalogStore


class SQLiteCatalogProvider(CatalogProvider):
    """
    RU: Read-only provider. Открывает SQLite и отвечает на запросы enrichment.
    EN: Read-only provider used by adapter layer; no network, fail-soft.
    """

    def __init__(self, path: str | Path) -> None:
        """
        Args:
            path: Path to SQLite database file

        Note:
            File existence is checked lazily (fail-soft if missing).
        """
        self._path = Path(path)

    def get_catalog_info(
        self,
        *,
        food_id: str,
        region_id: str,
        store_id: str | None = None,
    ) -> CatalogInfoDTO | None:
        """
        RU: Получить каталожную информацию для food_id в регионе/магазине.
        EN: Get catalog info for food_id in region/store.

        Args:
            food_id: Food identifier (used as alias)
            region_id: Region identifier (e.g., "es", "us") - will be normalized for lookup
            store_id: Optional store identifier

        Returns:
            CatalogInfoDTO if found, None otherwise (fail-soft)

        Contract:
            - Lookup uses UPPER (matches snapshot schema/ids)
            - DTO output uses lowercase (stable API surface for UI/i18n)
        """
        # Contract:
        # - lookup uses UPPER (matches snapshot schema/ids)
        # - DTO output uses lowercase (stable API surface for UI/i18n)
        region_lookup = region_id.strip().upper()
        region_out = region_id.strip().lower()

        sku = self._get_sku_by_alias(region_id=region_lookup, alias=food_id, store_id=store_id)
        if sku is None:
            return None

        # Convert core.CatalogSKU to app.schemas.CatalogInfoDTO
        price: MoneyDTO | None = None
        if sku.price is not None:
            try:
                currency = CurrencyDTO(sku.currency)
                price = MoneyDTO(value=sku.price, currency=currency)
            except ValueError:
                # Unknown currency -> skip price (fail-soft)
                price = None

        # Build pack_label from package_size and unit
        pack_label: str | None = None
        if sku.package_size is not None and sku.unit:
            pack_label = f"{sku.package_size} {sku.unit}"

        return CatalogInfoDTO(
            sku=sku.sku_id,
            store_id=sku.store_id,
            region_id=region_out,
            pack_label=pack_label,
            aisle=sku.aisle,
            price=price,
        )

    def _get_sku_by_alias(
        self, *, region_id: str, alias: str, store_id: str | None = None
    ) -> CatalogSKU | None:
        """
        RU: Найти SKU по alias (food_id, EAN, или название).
        EN: Find SKU by alias (food_id, EAN, or name).

        Args:
            region_id: Region identifier (already normalized to uppercase)
            alias: Food ID, EAN, or name to search
            store_id: Optional store filter

        Returns:
            CatalogSKU if found, None otherwise (fail-soft)
        """
        if not self._path.exists():
            return None

        # Open read-only (SQLite URI mode) with timeout
        uri = f"file:{self._path.as_posix()}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=1.0)
        except sqlite3.Error:
            return None

        try:
            alias_norm = norm_alias(alias)

            # Store-aware lookup with fallback:
            # 1) If store_id provided: exact store match wins, then fallback to any store
            # 2) If store_id not provided: return any matching SKU (deterministic by sku_id)
            if store_id:
                # Prefer exact store match, fallback to any store for this alias
                row = conn.execute(
                    """
                    SELECT s.sku_id, s.store_id, s.ean, s.name, s.brand, s.aisle,
                           s.package_size, s.unit, s.price, s.currency, s.updated_at
                    FROM sku_aliases a
                    JOIN skus s ON s.sku_id = a.sku_id
                    WHERE a.region_id = ? AND a.alias = ?
                    ORDER BY
                      CASE WHEN s.store_id = ? THEN 0 ELSE 1 END,
                      s.sku_id ASC
                    LIMIT 1
                    """,
                    (region_id, alias_norm, store_id),
                ).fetchone()
            else:
                # No store specified: return any matching SKU (deterministic)
                row = conn.execute(
                    """
                    SELECT s.sku_id, s.store_id, s.ean, s.name, s.brand, s.aisle,
                           s.package_size, s.unit, s.price, s.currency, s.updated_at
                    FROM sku_aliases a
                    JOIN skus s ON s.sku_id = a.sku_id
                    WHERE a.region_id = ? AND a.alias = ?
                    ORDER BY s.sku_id ASC
                    LIMIT 1
                    """,
                    (region_id, alias_norm),
                ).fetchone()

            if row is None:
                return None

            package_size = parse_decimal(row[6]) if row[6] is not None else None
            price = parse_decimal(row[8]) if row[8] is not None else None

            return CatalogSKU(
                sku_id=row[0],
                store_id=row[1],
                ean=row[2],
                name=row[3],
                brand=row[4],
                aisle=row[5],
                package_size=package_size,
                unit=row[7],
                price=price,
                currency=row[9],
                updated_at=row[10],
            )
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def list_stores(self, *, region_id: str) -> list[CatalogStore]:
        """
        RU: Список магазинов в регионе.
        EN: List stores in region.

        Args:
            region_id: Region identifier (will be normalized to uppercase)

        Returns:
            List of stores (empty if region not found or file missing)
        """
        if not self._path.exists():
            return []

        # Normalize region_id
        region_id_norm = region_id.strip().upper()

        uri = f"file:{self._path.as_posix()}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=1.0)
        except sqlite3.Error:
            return []

        try:
            rows = conn.execute(
                "SELECT store_id, region_id, name, provider, meta_json FROM stores WHERE region_id = ?",
                (region_id_norm,),
            ).fetchall()
            return [
                CatalogStore(
                    store_id=r[0],
                    region_id=r[1],
                    name=r[2],
                    provider=r[3],
                    meta_json=r[4],
                )
                for r in rows
            ]
        except sqlite3.Error:
            return []
        finally:
            conn.close()
