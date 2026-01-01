# -*- coding: utf-8 -*-
"""
SQLite catalog writer (PR-7).

RU: Запись каталога в SQLite (offline snapshot builder).
EN: Write catalog to SQLite (offline snapshot builder).

This module writes canonical snapshots to read-only SQLite files.
No I/O in request-path; used during data preparation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.catalog.provider import CatalogSnapshot


def write_snapshot(path: str | Path, snapshot: CatalogSnapshot) -> None:
    """
    RU: Записывает snapshot в SQLite одним транзакционным коммитом.
    EN: Writes snapshot to SQLite in a single transaction.

    Args:
        path: Path to SQLite database file (will be created/overwritten)
        snapshot: Canonical catalog snapshot to write

    Raises:
        sqlite3.Error: If database operations fail
    """
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # RU: Для offline builder логично перезаписывать файл целиком.
    # EN: Offline builder: overwrite the SQLite file to avoid bloat.
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        _apply_schema(conn)

        with conn:

            for r in snapshot.regions:
                conn.execute(
                    "INSERT INTO regions(region_id,country,currency,locale) VALUES (?,?,?,?)",
                    (r.region_id, r.country, r.currency, r.locale),
                )

            for s in snapshot.stores:
                conn.execute(
                    "INSERT INTO stores(store_id,region_id,name,provider,meta_json) VALUES (?,?,?,?,?)",
                    (s.store_id, s.region_id, s.name, s.provider, s.meta_json),
                )

            for sku in snapshot.skus:
                conn.execute(
                    """
                    INSERT INTO skus(
                      sku_id, store_id, ean, name, brand, aisle,
                      package_size, unit, price, currency, updated_at
                    )
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        sku.sku_id,
                        sku.store_id,
                        sku.ean,
                        sku.name,
                        sku.brand,
                        sku.aisle,
                        str(sku.package_size) if sku.package_size is not None else None,
                        sku.unit,
                        str(sku.price) if sku.price is not None else None,
                        sku.currency,
                        sku.updated_at,
                    ),
                )

            # Precompute lookup maps to avoid O(n*m) in alias loop
            store_by_id = {store.store_id: store for store in snapshot.stores}

            # Build sku_id_to_region_id with strict validation
            sku_id_to_region_id: dict[str, str] = {}
            for sku in snapshot.skus:
                store = store_by_id.get(sku.store_id)
                if store is None:
                    raise ValueError(
                        f"Unknown store_id referenced by sku: {sku.store_id} (sku_id={sku.sku_id})"
                    )
                sku_id_to_region_id[sku.sku_id] = store.region_id

            # Validate alias uniqueness and insert
            seen_alias_keys: set[tuple[str, str]] = set()
            for alias, sku_id in snapshot.aliases:
                region_id = sku_id_to_region_id.get(sku_id)
                if region_id is None:
                    raise ValueError(f"Unknown sku_id in aliases: {sku_id}")
                key = (region_id, alias)
                if key in seen_alias_keys:
                    raise ValueError(
                        f"Duplicate alias in snapshot: region_id={region_id}, alias={alias}"
                    )
                seen_alias_keys.add(key)

                conn.execute(
                    "INSERT INTO sku_aliases(region_id,alias,sku_id) VALUES (?,?,?)",
                    (region_id, alias, sku_id),
                )

    finally:
        conn.close()


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Apply SQLite schema from schema.sql file."""
    schema_sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema_sql)
