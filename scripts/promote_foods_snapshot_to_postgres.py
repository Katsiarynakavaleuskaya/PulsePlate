#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promote offline SQLite foods snapshot into PostgreSQL foods.

RU: Продвигает локальный SQLite snapshot `foods` в PostgreSQL-таблицу `foods`
через детерминированный batched upsert.
EN: Promotes the local SQLite `foods` snapshot into the PostgreSQL `foods`
table using deterministic batched upserts.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, TypeAlias, cast

from sqlalchemy import MetaData, Table, bindparam, create_engine, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine

SOURCE_TABLE_NAME = "foods"
TARGET_TABLE_NAME = "foods"
DEFAULT_SQLITE_PATH = Path("data/food.sqlite")
DEFAULT_REPORT_PATH = Path("artifacts/food_lane/foods_postgres_promotion_report.json")
DEFAULT_BATCH_SIZE = 5000
MIN_BATCH_SIZE = 1
CHECKSUM_SORT_KEY = "id"

FOODS_COLUMN_ALLOWLIST: tuple[str, ...] = (
    "id",
    "canonical_name",
    "group_name",
    "per_g",
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    "Fe_mg",
    "Ca_mg",
    "K_mg",
    "Mg_mg",
    "VitD_IU",
    "B12_ug",
    "Folate_ug",
    "Iodine_ug",
    "flags",
    "brand",
    "gtin",
    "fdc_id",
    "source",
    "source_priority",
    "version_date",
    "price_per_100g",
    "nutrition_inputs_json",
    "nutrition_provenance_json",
    "nutrition_confidence",
    "nutrition_nutrient_confidence_json",
)
REQUIRED_TARGET_COLUMNS: frozenset[str] = frozenset(FOODS_COLUMN_ALLOWLIST)
JsonContainerType: TypeAlias = type[list[Any]] | type[dict[str, Any]]

JSON_COLUMN_TYPES: dict[str, JsonContainerType] = {
    "flags": list,
    "nutrition_inputs_json": list,
    "nutrition_provenance_json": cast(JsonContainerType, dict),
    "nutrition_nutrient_confidence_json": cast(JsonContainerType, dict),
}
LEGACY_OPTIONAL_SOURCE_COLUMNS: frozenset[str] = frozenset(
    {
        "nutrition_inputs_json",
        "nutrition_provenance_json",
        "nutrition_confidence",
        "nutrition_nutrient_confidence_json",
    }
)
REQUIRED_SOURCE_COLUMNS = frozenset(
    column for column in FOODS_COLUMN_ALLOWLIST if column not in LEGACY_OPTIONAL_SOURCE_COLUMNS
)


class PromotionError(RuntimeError):
    """RU: Детерминированная ошибка promotion lane. EN: Deterministic promotion-lane error."""


@dataclass(frozen=True)
class PromotionConfig:
    """Runtime configuration for snapshot promotion."""

    sqlite_path: Path
    pg_url: str
    batch_size: int
    report_path: Path


@dataclass(frozen=True)
class PromotionSummary:
    """Serializable promotion execution summary."""

    sqlite_path: str
    target_table: str
    source_count: int
    inserted_count: int
    updated_count: int
    batch_count: int
    source_checksum: str

    def to_json_dict(self) -> dict[str, Any]:
        """Return JSON-safe dict representation."""
        return {
            "sqlite_path": self.sqlite_path,
            "target_table": self.target_table,
            "source_count": self.source_count,
            "inserted_count": self.inserted_count,
            "updated_count": self.updated_count,
            "batch_count": self.batch_count,
            "checksum": self.source_checksum,
            "source_checksum": self.source_checksum,
        }


def _json_default(value: Any) -> str:
    """Serialize Decimal values deterministically for checksum and reports."""
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Unsupported JSON serialization type: {type(value)!r}")


def _parse_args(argv: Sequence[str] | None = None) -> PromotionConfig:
    """Parse CLI arguments into a validated config object."""
    parser = argparse.ArgumentParser(
        description="Promote SQLite foods snapshot into PostgreSQL foods via deterministic upsert."
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=DEFAULT_SQLITE_PATH,
        help=f"Source SQLite database path (default: {DEFAULT_SQLITE_PATH}).",
    )
    parser.add_argument(
        "--pg-url",
        required=True,
        help="Target PostgreSQL DATABASE_URL / SQLAlchemy URL.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size for PostgreSQL upsert (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"JSON report output path (default: {DEFAULT_REPORT_PATH}).",
    )
    args = parser.parse_args(argv)

    if args.batch_size < MIN_BATCH_SIZE:
        raise PromotionError(f"batch-size must be >= {MIN_BATCH_SIZE}, got {args.batch_size}")

    return PromotionConfig(
        sqlite_path=args.sqlite_path,
        pg_url=args.pg_url,
        batch_size=args.batch_size,
        report_path=args.report_path,
    )


@contextmanager
def _connect_sqlite(path: Path) -> Iterator[sqlite3.Connection]:
    """Open source SQLite connection with row access enabled."""
    if not path.exists():
        raise PromotionError(f"SQLite source does not exist: {path}")
    if not path.is_file():
        raise PromotionError(f"SQLite source path is not a file: {path}")

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _build_pg_engine(pg_url: str) -> Engine:
    """Create and validate a PostgreSQL SQLAlchemy engine."""
    engine = create_engine(pg_url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise PromotionError(
            f"Target database must be PostgreSQL, got dialect {engine.dialect.name!r}"
        )
    return engine


def _fetch_sqlite_columns(connection: sqlite3.Connection) -> set[str]:
    """Return source SQLite table column names."""
    try:
        rows = connection.execute(f"PRAGMA table_info({SOURCE_TABLE_NAME})").fetchall()
    except sqlite3.Error as exc:
        raise PromotionError(
            f"Unable to inspect source SQLite table {SOURCE_TABLE_NAME!r}: {exc}"
        ) from exc

    if not rows:
        raise PromotionError(
            f"Source SQLite table {SOURCE_TABLE_NAME!r} is missing in the snapshot database."
        )
    return {str(row["name"]) for row in rows}


def _reflect_target_table(connection: Connection) -> Table:
    """Reflect the target PostgreSQL foods table and validate required columns."""
    inspector = inspect(connection)
    if not inspector.has_table(TARGET_TABLE_NAME):
        raise PromotionError(
            f"Target PostgreSQL table {TARGET_TABLE_NAME!r} is missing. "
            "Run the foods foundation migrations before promotion."
        )

    metadata = MetaData()
    table = Table(TARGET_TABLE_NAME, metadata, autoload_with=connection)
    target_columns = {column.name for column in table.columns}
    missing_columns = sorted(REQUIRED_TARGET_COLUMNS - target_columns)
    if missing_columns:
        missing_str = ", ".join(missing_columns)
        raise PromotionError(
            f"Target PostgreSQL table {TARGET_TABLE_NAME!r} is missing required columns: {missing_str}"
        )
    return table


def _normalize_json_column(
    *,
    row_id: str,
    column_name: str,
    raw_value: Any,
    expected_type: JsonContainerType,
) -> list[Any] | dict[str, Any]:
    """Parse and validate JSON-encoded source columns."""
    if raw_value is None:
        return expected_type()
    if not isinstance(raw_value, str):
        raise PromotionError(
            f"Row {row_id!r} column {column_name!r} must be TEXT JSON in SQLite source."
        )
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise PromotionError(
            f"Row {row_id!r} column {column_name!r} contains invalid JSON: {exc.msg}"
        ) from exc
    if not isinstance(parsed, expected_type):
        raise PromotionError(
            f"Row {row_id!r} column {column_name!r} must decode to "
            f"{expected_type.__name__}, got {type(parsed).__name__}."
        )
    return cast(list[Any] | dict[str, Any], parsed)


def _normalize_source_row(row: sqlite3.Row) -> dict[str, Any]:
    """Normalize a SQLite row into a PostgreSQL-ready payload."""
    row_keys = set(row.keys())
    normalized = {
        column: row[column] if column in row_keys else None for column in FOODS_COLUMN_ALLOWLIST
    }
    row_id = str(normalized["id"])
    for column_name, expected_type in JSON_COLUMN_TYPES.items():
        normalized[column_name] = _normalize_json_column(
            row_id=row_id,
            column_name=column_name,
            raw_value=normalized[column_name],
            expected_type=expected_type,
        )
    return normalized


def _iter_source_rows(
    connection: sqlite3.Connection,
    source_columns: set[str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield normalized source rows in deterministic primary-key order."""
    active_source_columns = source_columns or _fetch_sqlite_columns(connection)
    select_columns = [
        column_name
        for column_name in FOODS_COLUMN_ALLOWLIST
        if column_name in active_source_columns
    ]
    query = (
        "SELECT "
        + ", ".join(select_columns)
        + f" FROM {SOURCE_TABLE_NAME} ORDER BY {CHECKSUM_SORT_KEY}"
    )
    try:
        cursor = connection.execute(query)
    except sqlite3.Error as exc:
        raise PromotionError(f"Unable to read source rows from SQLite: {exc}") from exc
    for row in cursor:
        yield _normalize_source_row(row)


def _chunk_rows(rows: list[dict[str, Any]], batch_size: int) -> Iterator[list[dict[str, Any]]]:
    """Yield fixed-size row batches."""
    for start in range(0, len(rows), batch_size):
        yield rows[start : start + batch_size]


def _compute_checksum(rows: list[dict[str, Any]]) -> str:
    """Compute deterministic checksum over normalized source rows."""
    digest = hashlib.sha256()
    for row in rows:
        encoded = json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=_json_default,
        ).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
    return digest.hexdigest()


def _count_existing_ids(
    connection: Connection,
    target_table: Table,
    ids: Sequence[str],
) -> set[str]:
    """Return target ids already present in PostgreSQL."""
    if not ids:
        return set()
    stmt = select(target_table.c.id).where(target_table.c.id.in_(bindparam("ids", expanding=True)))
    rows = connection.execute(stmt, {"ids": list(ids)}).scalars().all()
    return {str(value) for value in rows}


def _build_upsert_statement(target_table: Table):
    """Build PostgreSQL UPSERT statement for the foods target table."""
    insert_stmt = pg_insert(target_table)
    update_columns = {
        column: insert_stmt.excluded[column] for column in FOODS_COLUMN_ALLOWLIST if column != "id"
    }
    return insert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_=update_columns,
    )


def _promote_rows(
    *,
    source_rows: list[dict[str, Any]],
    connection: Connection,
    target_table: Table,
    batch_size: int,
) -> tuple[int, int, int]:
    """Promote rows to PostgreSQL and return insert/update/batch counts."""
    inserted_total = 0
    updated_total = 0
    batch_total = 0
    upsert_stmt = _build_upsert_statement(target_table)

    for batch in _chunk_rows(source_rows, batch_size):
        batch_total += 1
        batch_ids = [str(row["id"]) for row in batch]
        existing_ids = _count_existing_ids(connection, target_table, batch_ids)
        inserted_total += len(batch_ids) - len(existing_ids)
        updated_total += len(existing_ids)
        connection.execute(upsert_stmt, batch)

    return inserted_total, updated_total, batch_total


def _write_report(summary: PromotionSummary, report_path: Path) -> None:
    """Persist execution summary as tracked-out artifact JSON."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(summary.to_json_dict(), indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def run_promotion(config: PromotionConfig) -> PromotionSummary:
    """Execute snapshot promotion and return a deterministic summary."""
    with _connect_sqlite(config.sqlite_path) as sqlite_connection:
        source_columns = _fetch_sqlite_columns(sqlite_connection)
        missing_source_columns = sorted(REQUIRED_SOURCE_COLUMNS - source_columns)
        if missing_source_columns:
            missing_str = ", ".join(missing_source_columns)
            raise PromotionError(
                f"Source SQLite table {SOURCE_TABLE_NAME!r} is missing required columns: {missing_str}"
            )
        source_rows = list(_iter_source_rows(sqlite_connection, source_columns))

    engine = _build_pg_engine(config.pg_url)
    try:
        with engine.begin() as pg_connection:
            target_table = _reflect_target_table(pg_connection)
            inserted_count, updated_count, batch_count = _promote_rows(
                source_rows=source_rows,
                connection=pg_connection,
                target_table=target_table,
                batch_size=config.batch_size,
            )
    finally:
        engine.dispose()

    summary = PromotionSummary(
        sqlite_path=str(config.sqlite_path),
        target_table=TARGET_TABLE_NAME,
        source_count=len(source_rows),
        inserted_count=inserted_count,
        updated_count=updated_count,
        batch_count=batch_count,
        source_checksum=_compute_checksum(source_rows),
    )
    _write_report(summary, config.report_path)
    return summary


def promote_foods_snapshot_to_postgres(
    *,
    sqlite_path: str | Path,
    pg_url: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    report_path: str | Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """Run the canonical B1 promotion interface and return the JSON summary."""
    config = PromotionConfig(
        sqlite_path=Path(sqlite_path),
        pg_url=pg_url,
        batch_size=batch_size,
        report_path=Path(report_path),
    )
    if config.batch_size < MIN_BATCH_SIZE:
        raise PromotionError(f"batch-size must be >= {MIN_BATCH_SIZE}, got {config.batch_size}")
    summary = run_promotion(config)
    return summary.to_json_dict()


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    try:
        config = _parse_args(argv)
        summary = promote_foods_snapshot_to_postgres(
            sqlite_path=config.sqlite_path,
            pg_url=config.pg_url,
            batch_size=config.batch_size,
            report_path=config.report_path,
        )
    except PromotionError as exc:
        print(f"Promotion failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
