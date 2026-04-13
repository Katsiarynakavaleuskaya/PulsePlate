#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RU: CLI-импорт MenuStat-совместимого CSV в локальный restaurant store.
EN: CLI import of MenuStat-compatible CSV into local restaurant store.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any

from app.services import restaurant_postgres_bridge
from app.services import restaurant_store
from sqlalchemy.exc import SQLAlchemyError

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "chain_name": ("chain_name", "restaurant", "restaurant_name", "chain"),
    "item_name": ("item_name", "menu_item", "name"),
    "category": ("category", "menu_category"),
    "country": ("country",),
    "serving_size_g": ("serving_size_g", "serving_size_grams"),
    "kcal": ("kcal", "calories"),
    "protein_g": ("protein_g", "protein"),
    "fat_g": ("fat_g", "total_fat"),
    "carbs_g": ("carbs_g", "total_carbohydrate"),
    "sodium_mg": ("sodium_mg", "sodium"),
    "source_id": ("source_id", "menu_item_id"),
}
_DATE_YYYY_MM_DD = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TARGET_BACKEND_SQLITE = "sqlite"
TARGET_BACKEND_POSTGRES = "postgres"
TARGET_BACKEND_CHOICES = (TARGET_BACKEND_SQLITE, TARGET_BACKEND_POSTGRES)


def _has_required_header_aliases(fieldnames: list[str] | None) -> bool:
    """Check that CSV headers contain required alias groups."""
    if fieldnames is None:
        return False
    headers = {field.strip() for field in fieldnames if field and field.strip()}
    chain_aliases = set(_FIELD_ALIASES["chain_name"])
    item_aliases = set(_FIELD_ALIASES["item_name"])
    return bool(headers.intersection(chain_aliases)) and bool(headers.intersection(item_aliases))


def _parse_snapshot_date(value: str) -> str:
    """Validate CLI snapshot date and return canonical YYYY-MM-DD."""
    if not _DATE_YYYY_MM_DD.fullmatch(value):
        raise argparse.ArgumentTypeError(f"snapshot-date must be YYYY-MM-DD, got: {value!r}")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"snapshot-date must be YYYY-MM-DD, got: {value!r}"
        ) from exc


def _first_present_value(row: dict[str, Any], aliases: tuple[str, ...]) -> str | None:
    """Return first non-empty value for any alias."""
    for alias in aliases:
        raw = row.get(alias)
        if raw is None:
            continue
        value = str(raw).strip()
        if value:
            return value
    return None


def normalize_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a MenuStat-style row into restaurant_store contract keys."""
    normalized: dict[str, Any] = {}
    for target_key, aliases in _FIELD_ALIASES.items():
        value = _first_present_value(raw_row, aliases)
        if value is not None:
            normalized[target_key] = value
    return normalized


def load_menu_rows(csv_path: Path) -> list[dict[str, Any]]:
    """Load and normalize valid rows from CSV file."""
    if not csv_path.exists():
        raise FileNotFoundError(f"input file does not exist: {csv_path}")
    if not csv_path.is_file():
        raise ValueError(f"input path is not a file: {csv_path}")

    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("input CSV has no header row")
        if not _has_required_header_aliases(reader.fieldnames):
            raise ValueError(
                "input CSV missing required columns/aliases: "
                f"one of {list(_FIELD_ALIASES['chain_name'])} and "
                f"one of {list(_FIELD_ALIASES['item_name'])}"
            )
        for raw_row in reader:
            normalized_input = {
                str(key).strip(): value for key, value in raw_row.items() if key is not None
            }
            normalized = normalize_row(normalized_input)
            if not normalized.get("chain_name") or not normalized.get("item_name"):
                continue
            rows.append(normalized)
    return rows


def _resolve_postgres_url(pg_url: str | None) -> str:
    """Resolve PostgreSQL URL from explicit flag or environment."""
    resolved = (pg_url or os.getenv("DATABASE_URL") or "").strip()
    if not resolved:
        raise ValueError("postgres target requires --pg-url or DATABASE_URL pointing to PostgreSQL")
    return resolved


def run_import(
    *,
    input_path: Path,
    snapshot_date: str | None,
    source_name: str,
    target_backend: str,
    db_path: Path | None,
    pg_url: str | None,
) -> dict[str, Any]:
    """Execute import and return summary stats."""
    original_db_path = restaurant_store.DB_PATH
    effective_db_path = original_db_path
    try:
        if target_backend not in TARGET_BACKEND_CHOICES:
            supported_backends = ", ".join(TARGET_BACKEND_CHOICES)
            raise ValueError(
                f"unsupported target-backend {target_backend!r}; expected one of: {supported_backends}"
            )

        rows = load_menu_rows(input_path)
        if not rows:
            raise ValueError("no valid menu rows found in input")

        if target_backend == TARGET_BACKEND_POSTGRES:
            if db_path is not None:
                raise ValueError("--db-path is only supported for sqlite target-backend")
            resolved_pg_url = _resolve_postgres_url(pg_url)
            stats = restaurant_postgres_bridge.import_menustat_rows_to_postgres(
                rows,
                snapshot_date=snapshot_date,
                source_name=source_name,
                pg_url=resolved_pg_url,
            )
            return {
                "input": str(input_path),
                "rows_loaded": len(rows),
                "snapshot_date": snapshot_date,
                "source_name": source_name,
                "target_backend": TARGET_BACKEND_POSTGRES,
                **stats,
            }

        if db_path is not None:
            restaurant_store.DB_PATH = db_path
            restaurant_store.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            effective_db_path = restaurant_store.DB_PATH

        stats = restaurant_store.import_menustat_rows(
            rows,
            snapshot_date=snapshot_date,
            source_name=source_name,
        )
        return {
            "input": str(input_path),
            "db_path": str(effective_db_path),
            "rows_loaded": len(rows),
            "snapshot_date": snapshot_date,
            "source_name": source_name,
            "target_backend": TARGET_BACKEND_SQLITE,
            **stats,
        }
    finally:
        restaurant_store.DB_PATH = original_db_path


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Import MenuStat-style restaurant menu CSV into local store."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to CSV file with MenuStat-compatible columns.",
    )
    parser.add_argument(
        "--snapshot-date",
        default=None,
        type=_parse_snapshot_date,
        help="Snapshot date (YYYY-MM-DD). Defaults to today's UTC date.",
    )
    parser.add_argument(
        "--source-name",
        default="menustat",
        help="Provenance source name for imported rows (default: menustat).",
    )
    parser.add_argument(
        "--target-backend",
        choices=TARGET_BACKEND_CHOICES,
        default=TARGET_BACKEND_SQLITE,
        help="Import target backend (default: sqlite).",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        type=Path,
        help="Optional override for SQLite DB path (default: FOOD_DB_PATH or data/food.sqlite).",
    )
    parser.add_argument(
        "--pg-url",
        default=None,
        help="Optional PostgreSQL DATABASE_URL override for postgres target-backend.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run_import(
            input_path=args.input,
            snapshot_date=args.snapshot_date,
            source_name=args.source_name,
            target_backend=args.target_backend,
            db_path=args.db_path,
            pg_url=args.pg_url,
        )
    except (
        FileNotFoundError,
        ValueError,
        OSError,
        sqlite3.Error,
        SQLAlchemyError,
        restaurant_postgres_bridge.RestaurantPostgresBridgeError,
    ) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
