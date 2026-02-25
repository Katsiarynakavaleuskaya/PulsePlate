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
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from app.services import restaurant_store

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
    "source_id": ("source_id", "menu_item_id", "id"),
}
_DATE_YYYY_MM_DD = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def run_import(
    *,
    input_path: Path,
    snapshot_date: str | None,
    source_name: str,
    db_path: Path | None,
) -> dict[str, Any]:
    """Execute import and return summary stats."""
    original_db_path = restaurant_store.DB_PATH
    effective_db_path = original_db_path
    try:
        if db_path is not None:
            restaurant_store.DB_PATH = db_path
            restaurant_store.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            effective_db_path = restaurant_store.DB_PATH

        rows = load_menu_rows(input_path)
        if not rows:
            raise ValueError("no valid menu rows found in input")

        stats = restaurant_store.import_menustat_rows(
            rows,
            snapshot_date=snapshot_date,
            source_name=source_name,
        )
        return {
            "input": str(input_path),
            "db_path": str(effective_db_path),
            "rows_loaded": len(rows),
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
        "--db-path",
        default=None,
        type=Path,
        help="Optional override for SQLite DB path (default: FOOD_DB_PATH or data/food.sqlite).",
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
            db_path=args.db_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
