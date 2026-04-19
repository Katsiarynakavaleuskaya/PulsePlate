# -*- coding: utf-8 -*-
"""
FK integrity tests for SQLite catalog writer (PR-7).

RU: Проверяем FK integrity: sku_aliases.region_id должен ссылаться на regions.region_id.
EN: FK integrity test: sku_aliases.region_id must reference regions.region_id.

This is an OFFLINE builder test (write_snapshot), not request-path.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.catalog.provider import CatalogRegion, CatalogSKU, CatalogSnapshot, CatalogStore
from core.catalog.storage.sqlite_writer import write_snapshot

ALLOWED_PRAGMA_TABLES = frozenset({"sku_aliases"})


def _fk_targets(conn: sqlite3.Connection, table: str) -> set[tuple[str, str, str]]:
    """
    RU: Возвращает набор FK (from_col, ref_table, ref_col) для таблицы.
    EN: Return FK set (from_col, ref_table, ref_col) for a table.
    """
    if table not in ALLOWED_PRAGMA_TABLES:
        raise ValueError(f"Unsupported table for FK inspection: {table}")

    rows = conn.execute(f"PRAGMA foreign_key_list({table});").fetchall()
    return {(r[3], r[2], r[4]) for r in rows}


def test_sku_aliases_has_fk_region_id_to_regions_region_id(tmp_path: Path) -> None:
    """
    RU: Проверяем, что в schema есть FK: sku_aliases.region_id -> regions.region_id.
    EN: Verify FK exists in schema.
    """
    db_path = tmp_path / "catalog.sqlite"

    # Create minimal valid snapshot to trigger schema creation
    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            )
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_1",
                store_id="carrefour_es_main",
                ean=None,
                name="Test Product",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="EUR",
                updated_at=None,
            )
        ],
        aliases=[("test_alias", "sku_1")],
    )

    write_snapshot(db_path, snapshot)

    # Verify FK exists in schema
    conn = sqlite3.connect(str(db_path))
    try:
        fks = _fk_targets(conn, "sku_aliases")
        assert (
            "region_id",
            "regions",
            "region_id",
        ) in fks, "FK sku_aliases.region_id -> regions.region_id must exist"
    finally:
        conn.close()


def test_fk_enforced_unknown_region_in_alias_fails(tmp_path: Path) -> None:
    """
    RU: Проверяем, что FK реально enforced (PRAGMA foreign_keys=ON).
        Если alias ссылается на несуществующий region_id, writer должен упасть.
    EN: Verify FK is enforced: inserting alias for missing region must fail.
    """
    db_path = tmp_path / "catalog.sqlite"

    # Create snapshot with alias referencing non-existent region
    # IMPORTANT: regions is empty, but alias references region_id="ES"
    snapshot = CatalogSnapshot(
        regions=[],  # <- нет region_id "ES"
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",  # Store references non-existent region
                name="Carrefour (ES)",
                provider="carrefour",
            )
        ],
        skus=[
            CatalogSKU(
                sku_id="sku_1",
                store_id="carrefour_es_main",
                ean=None,
                name="Milk 1L",
                brand=None,
                aisle="Dairy",
                package_size=None,
                unit=None,
                price=None,
                currency="EUR",
                updated_at=None,
            )
        ],
        aliases=[
            # alias will reference region_id="ES" (derived from store), which doesn't exist in regions
            ("milk", "sku_1")
        ],
    )

    # Expect FK error when trying to insert alias for missing region
    # Note: This will fail at store insertion (store.region_id FK) or alias insertion (alias.region_id FK)
    with pytest.raises(
        (sqlite3.IntegrityError, ValueError), match="Unknown|foreign key|FOREIGN KEY"
    ):
        write_snapshot(db_path, snapshot)


def test_fk_enforced_unknown_sku_id_in_alias_fails(tmp_path: Path) -> None:
    """
    RU: Проверяем, что FK для sku_id тоже enforced.
        Если alias ссылается на несуществующий sku_id, writer должен упасть.
    EN: Verify FK for sku_id is enforced: inserting alias for missing sku_id must fail.
    """
    db_path = tmp_path / "catalog.sqlite"

    # Create snapshot with alias referencing non-existent sku_id
    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[
            CatalogStore(
                store_id="carrefour_es_main",
                region_id="ES",
                name="Carrefour (ES)",
                provider="carrefour",
            )
        ],
        skus=[],  # <- нет SKU
        aliases=[
            # alias references non-existent sku_id
            ("milk", "unknown_sku_id")
        ],
    )

    # Expect FK error when trying to insert alias for missing sku_id
    with pytest.raises(
        (sqlite3.IntegrityError, ValueError), match="Unknown sku_id|foreign key|FOREIGN KEY"
    ):
        write_snapshot(db_path, snapshot)


def test_fk_enforced_unknown_store_id_in_sku_fails(tmp_path: Path) -> None:
    """
    RU: Проверяем, что FK для store_id в skus тоже enforced.
        Если SKU ссылается на несуществующий store_id, writer должен упасть.
    EN: Verify FK for store_id in skus is enforced: inserting SKU for missing store_id must fail.
    """
    db_path = tmp_path / "catalog.sqlite"

    # Create snapshot with SKU referencing non-existent store_id
    snapshot = CatalogSnapshot(
        regions=[CatalogRegion(region_id="ES", country="ES", currency="EUR", locale="es-ES")],
        stores=[],  # <- нет store
        skus=[
            CatalogSKU(
                sku_id="sku_1",
                store_id="unknown_store",  # Store doesn't exist
                ean=None,
                name="Test Product",
                brand=None,
                aisle=None,
                package_size=None,
                unit=None,
                price=None,
                currency="EUR",
                updated_at=None,
            )
        ],
        aliases=[],
    )

    # Expect error when trying to insert SKU for missing store_id
    # This should be caught by our validation (ValueError) before FK check
    with pytest.raises(ValueError, match="Unknown store_id"):
        write_snapshot(db_path, snapshot)
