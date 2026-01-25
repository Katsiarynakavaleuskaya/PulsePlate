# -*- coding: utf-8 -*-
"""
RU: Тесты store-aware lookup для SQLiteCatalogProvider (PR-7).
EN: Store-aware lookup tests for SQLiteCatalogProvider (PR-7).

Важно:
- В текущей схеме sku_aliases НЕ содержит store_id.
- Поэтому store-aware реализуется через JOIN skus.store_id.
- Fallback при несовпадении store_id = "любой SKU" детерминированно.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.services.catalog_provider_sqlite import SQLiteCatalogProvider


def _mk_sqlite_catalog(path: Path) -> None:
    """RU/EN: Create minimal schema for provider tests."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript("""
            CREATE TABLE regions (
              region_id TEXT PRIMARY KEY,
              country TEXT NOT NULL,
              currency TEXT NOT NULL,
              locale TEXT NOT NULL
            );

            CREATE TABLE stores (
              store_id TEXT PRIMARY KEY,
              region_id TEXT NOT NULL,
              name TEXT NOT NULL,
              provider TEXT NOT NULL,
              meta_json TEXT,
              FOREIGN KEY(region_id) REFERENCES regions(region_id) ON DELETE CASCADE
            );

            CREATE TABLE skus (
              sku_id TEXT PRIMARY KEY,
              store_id TEXT NOT NULL,
              ean TEXT,
              name TEXT NOT NULL,
              brand TEXT,
              aisle TEXT,
              package_size TEXT,
              unit TEXT,
              price TEXT,
              currency TEXT NOT NULL,
              updated_at TEXT,
              FOREIGN KEY(store_id) REFERENCES stores(store_id) ON DELETE CASCADE
            );

            -- ВАЖНО: sku_aliases без store_id (текущая схема PR-7)
            CREATE TABLE sku_aliases (
              region_id TEXT NOT NULL,
              alias TEXT NOT NULL,
              sku_id TEXT NOT NULL,
              PRIMARY KEY (region_id, alias),
              FOREIGN KEY(region_id) REFERENCES regions(region_id),
              FOREIGN KEY(sku_id) REFERENCES skus(sku_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_stores_region_id ON stores(region_id);
            CREATE INDEX IF NOT EXISTS idx_skus_store_id ON skus(store_id);
            """)
        conn.commit()
    finally:
        conn.close()


def _seed_two_skus_same_alias(path: Path) -> None:
    """
    RU: Вставляет 2 SKU с разными aliases для тестирования store-aware lookup.
    EN: Inserts 2 SKUs with different aliases to test store-aware lookup.

    Note: In PR-7, aliases are unique per (region_id, alias), so we use different aliases.
    """
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            "INSERT INTO regions(region_id, country, currency, locale) VALUES (?, ?, ?, ?)",
            ("ES", "ES", "EUR", "es-ES"),
        )

        conn.execute(
            "INSERT INTO stores(store_id, region_id, name, provider, meta_json) VALUES (?, ?, ?, ?, ?)",
            ("CARREFOUR_ES", "ES", "Carrefour ES", "carrefour", None),
        )
        conn.execute(
            "INSERT INTO stores(store_id, region_id, name, provider, meta_json) VALUES (?, ?, ?, ?, ?)",
            ("WALMART_US", "ES", "Walmart US (test)", "walmart", None),
        )

        # Два SKU: один Carrefour, один Walmart
        # sku_id намеренно так, чтобы детерминированный fallback был проверяем.
        conn.execute(
            """
            INSERT INTO skus(
              sku_id, store_id, ean, name, brand, aisle,
              package_size, unit, price, currency, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("SKU_A", "CARREFOUR_ES", None, "Carrot", None, "Veg", "500", "G", "1.29", "EUR", None),
        )
        conn.execute(
            """
            INSERT INTO skus(
              sku_id, store_id, ean, name, brand, aisle,
              package_size, unit, price, currency, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("SKU_B", "WALMART_US", None, "Carrot", None, "Veg", "400", "G", "0.99", "EUR", None),
        )

        # RU: В PR-7 один alias → один SKU в регионе (PRIMARY KEY (region_id, alias)).
        # EN: In PR-7, one alias maps to one SKU per region (PRIMARY KEY constraint).
        # Для тестирования store-aware lookup используем разные aliases.
        # To test store-aware lookup, we use different aliases.
        conn.execute(
            "INSERT INTO sku_aliases(region_id, alias, sku_id) VALUES (?, ?, ?)",
            ("ES", "carrot_a", "SKU_A"),
        )
        conn.execute(
            "INSERT INTO sku_aliases(region_id, alias, sku_id) VALUES (?, ?, ?)",
            ("ES", "carrot_b", "SKU_B"),
        )

        conn.commit()
    finally:
        conn.close()


def test_store_aware_lookup_prefers_exact_store_match(tmp_path: Path) -> None:
    """
    RU: Если store_id задан и среди кандидатов есть SKU из этого store -> выбираем его.
    EN: If store_id provided and an SKU matches that store -> choose it.
    """
    db_path = tmp_path / "catalog.sqlite"
    _mk_sqlite_catalog(db_path)
    _seed_two_skus_same_alias(db_path)

    p = SQLiteCatalogProvider(str(db_path))

    info = p.get_catalog_info(food_id="carrot_b", region_id="es", store_id="WALMART_US")
    assert info is not None
    assert info.store_id == "WALMART_US"
    assert info.sku == "SKU_B"
    # pack_label строится из package_size + unit
    assert info.pack_label == "400 G"


def test_store_aware_lookup_falls_back_deterministically_when_no_match(tmp_path: Path) -> None:
    """
    RU: Если store_id задан, но точного совпадения нет -> fallback на "любой SKU"
        (детерминированно: по sku_id ASC после CASE).
    EN: If store_id provided but no exact store match -> deterministic fallback to any SKU.
    """
    db_path = tmp_path / "catalog.sqlite"
    _mk_sqlite_catalog(db_path)
    _seed_two_skus_same_alias(db_path)

    p = SQLiteCatalogProvider(str(db_path))

    info = p.get_catalog_info(food_id="carrot_a", region_id="ES", store_id="NON_EXISTING_STORE")
    assert info is not None
    # CASE WHEN s.store_id=? THEN 0 ELSE 1 END + sku_id ASC => SKU_A
    assert info.sku == "SKU_A"
    assert info.store_id == "CARREFOUR_ES"
    assert info.pack_label == "500 G"


def test_no_store_id_returns_deterministic_first_sku(tmp_path: Path) -> None:
    """
    RU: Без store_id возвращаем детерминированный результат (sku_id ASC).
    EN: Without store_id return deterministic (sku_id ASC).
    """
    db_path = tmp_path / "catalog.sqlite"
    _mk_sqlite_catalog(db_path)
    _seed_two_skus_same_alias(db_path)

    p = SQLiteCatalogProvider(str(db_path))

    info = p.get_catalog_info(food_id="carrot_a", region_id="es")
    assert info is not None
    assert info.sku == "SKU_A"
