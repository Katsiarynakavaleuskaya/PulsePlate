# -*- coding: utf-8 -*-
"""Restaurant SQLite-vs-PostgreSQL shadow parity helpers.

RU: Сравнение SQLite canonical rows и PostgreSQL shadow rows без cutover-решений.
EN: Compare SQLite canonical rows and PostgreSQL shadow rows without making cutover decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ParityResult:
    """RU: Результат parity-сравнения. EN: Result of parity comparison."""

    match: bool
    sqlite_count: int
    postgres_count: int
    mismatched_indexes: tuple[int, ...]
    mismatch_reasons: tuple[str, ...]


_SEARCH_FIELDS: tuple[str, ...] = ("id", "name", "country", "source")
_MENU_FIELDS: tuple[str, ...] = (
    "id",
    "chain_id",
    "item_name",
    "category",
    "serving_size_g",
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "sodium_mg",
    "source",
    "source_id",
    "is_active",
)


def _normalize_numeric(value: Any) -> str | None:
    """RU: Привести numeric к стабильной строке для parity.

    EN: Normalize numeric values into stable parity strings.
    """

    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    normalized = parsed.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal(1)), "f")
    return format(normalized, "f")


def _normalize_bool_like(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y"}:
        return True
    if text in {"0", "false", "f", "no", "n"}:
        return False
    return None


def normalize_restaurant_hit(row: Mapping[str, Any]) -> dict[str, Any]:
    """RU: Нормализация search row для parity. EN: Normalize search row for parity."""

    return {
        "id": str(row.get("id") or ""),
        "name": str(row.get("name") or ""),
        "country": row.get("country"),
        "source": row.get("source"),
    }


def normalize_restaurant_menu_item_for_parity(row: Mapping[str, Any]) -> dict[str, Any]:
    """RU: Нормализация menu row для parity v1.

    EN: Normalize menu row for parity v1.
    """

    return {
        "id": str(row.get("id") or ""),
        "chain_id": str(row.get("chain_id") or ""),
        "item_name": str(row.get("item_name") or ""),
        "category": row.get("category"),
        "serving_size_g": _normalize_numeric(row.get("serving_size_g")),
        "kcal": _normalize_numeric(row.get("kcal")),
        "protein_g": _normalize_numeric(row.get("protein_g")),
        "fat_g": _normalize_numeric(row.get("fat_g")),
        "carbs_g": _normalize_numeric(row.get("carbs_g")),
        "sodium_mg": _normalize_numeric(row.get("sodium_mg")),
        "source": row.get("source"),
        "source_id": row.get("source_id"),
        "is_active": _normalize_bool_like(row.get("is_active")),
    }


def _compare_rows(
    *,
    sqlite_rows: Sequence[dict[str, Any]],
    postgres_rows: Sequence[dict[str, Any]],
    fields: tuple[str, ...],
) -> ParityResult:
    mismatched_indexes: list[int] = []
    mismatch_reasons: list[str] = []

    if len(sqlite_rows) != len(postgres_rows):
        mismatch_reasons.append(
            f"row-count mismatch sqlite={len(sqlite_rows)} postgres={len(postgres_rows)}"
        )

    max_len = max(len(sqlite_rows), len(postgres_rows))
    for idx in range(max_len):
        if idx >= len(sqlite_rows):
            mismatched_indexes.append(idx)
            mismatch_reasons.append(f"missing sqlite row at index {idx}")
            continue
        if idx >= len(postgres_rows):
            mismatched_indexes.append(idx)
            mismatch_reasons.append(f"missing postgres row at index {idx}")
            continue

        sqlite_row = sqlite_rows[idx]
        postgres_row = postgres_rows[idx]
        for field_name in fields:
            if sqlite_row.get(field_name) != postgres_row.get(field_name):
                mismatched_indexes.append(idx)
                mismatch_reasons.append(f"index {idx} field {field_name} mismatch")
                break

    return ParityResult(
        match=not mismatch_reasons,
        sqlite_count=len(sqlite_rows),
        postgres_count=len(postgres_rows),
        mismatched_indexes=tuple(mismatched_indexes),
        mismatch_reasons=tuple(mismatch_reasons),
    )


def compare_restaurant_hits(
    sqlite_rows: Sequence[Mapping[str, Any]], postgres_rows: Sequence[Mapping[str, Any]]
) -> ParityResult:
    """RU: Сравнить search rows из SQLite и PostgreSQL.

    EN: Compare restaurant search rows from SQLite and PostgreSQL.
    """

    normalized_sqlite = [normalize_restaurant_hit(row) for row in sqlite_rows]
    normalized_postgres = [normalize_restaurant_hit(row) for row in postgres_rows]
    return _compare_rows(
        sqlite_rows=normalized_sqlite,
        postgres_rows=normalized_postgres,
        fields=_SEARCH_FIELDS,
    )


def compare_restaurant_menu(
    sqlite_rows: Sequence[Mapping[str, Any]], postgres_rows: Sequence[Mapping[str, Any]]
) -> ParityResult:
    """RU: Сравнить menu rows по общим runtime полям.

    EN: Compare menu rows using common runtime fields only.
    """

    normalized_sqlite = [normalize_restaurant_menu_item_for_parity(row) for row in sqlite_rows]
    normalized_postgres = [normalize_restaurant_menu_item_for_parity(row) for row in postgres_rows]
    return _compare_rows(
        sqlite_rows=normalized_sqlite,
        postgres_rows=normalized_postgres,
        fields=_MENU_FIELDS,
    )
