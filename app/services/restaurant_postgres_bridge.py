# -*- coding: utf-8 -*-
"""PostgreSQL writer bridge for importer-only restaurant persistence.

RU: Узкий writer bridge для импорта ресторанных меню в PostgreSQL без runtime cutover.
EN: Narrow writer bridge for restaurant-menu imports into PostgreSQL without runtime cutover.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any

from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.dialects.postgresql.dml import Insert as PostgresInsert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import NoSuchTableError

DEFAULT_COUNTRY = "US"
COUNTRY_MAX_LENGTH = 16
RESTAURANT_CHAINS_TABLE = "restaurant_chains"
RESTAURANT_MENU_ITEMS_TABLE = "restaurant_menu_items"
NUMERIC_FIELD_LIMITS: dict[str, tuple[int, int]] = {
    "serving_size_g": (10, 2),
    "kcal": (8, 2),
    "protein_g": (8, 2),
    "fat_g": (8, 2),
    "carbs_g": (8, 2),
    "sodium_mg": (10, 2),
}

REQUIRED_CHAIN_COLUMNS = frozenset({"id", "name", "country", "source", "source_id", "updated_at"})
REQUIRED_MENU_ITEM_COLUMNS = frozenset(
    {
        "id",
        "chain_id",
        "food_id",
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
        "updated_at",
    }
)
_MENU_COMPLETENESS_FIELDS: tuple[str, ...] = (
    "item_name",
    "category",
    "serving_size_g",
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "sodium_mg",
    "source_id",
)


class RestaurantPostgresBridgeError(RuntimeError):
    """RU: Детерминированная ошибка bridge-слоя. EN: Deterministic bridge-layer failure."""


def _utc_now() -> datetime:
    """RU: Вернуть timezone-aware UTC now. EN: Return timezone-aware UTC now."""

    return datetime.now(timezone.utc)


def _slugify(value: str) -> str:
    """Build deterministic IDs compatible with the existing SQLite importer contract."""

    normalized = value.strip().casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    if slug:
        return slug
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"id-{digest}"


def _as_clean_str(value: Any) -> str | None:
    """RU: Обрезать строку или вернуть None. EN: Strip string-ish values or return None."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_decimal(value: Any) -> Decimal | None:
    """RU: Нормализовать optional numeric input. EN: Normalize optional numeric input."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return Decimal(raw)
        except InvalidOperation:
            return None
    return None


def _fits_numeric_bounds(value: Decimal, *, precision: int, scale: int) -> bool:
    """RU: Проверить precision/scale до INSERT. EN: Validate precision/scale before INSERT."""

    if not value.is_finite():
        return False

    sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        return False
    del sign
    decimal_places = max(-exponent, 0)
    if decimal_places > scale:
        return False

    integer_digits = len(digits) + exponent if exponent >= 0 else len(digits) - decimal_places
    integer_digits = max(integer_digits, 0)
    allowed_integer_digits = precision - scale
    if integer_digits > allowed_integer_digits:
        return False

    total_digits = integer_digits + decimal_places
    if total_digits == 0:
        total_digits = 1
    return total_digits <= precision


def _validate_menu_item_candidate(candidate: dict[str, Any]) -> None:
    """RU: Fail closed on obvious schema overflows. EN: Fail closed on obvious schema overflows."""

    country = _as_clean_str(candidate.get("country"))
    if country and len(country) > COUNTRY_MAX_LENGTH:
        raise RestaurantPostgresBridgeError(
            f"country exceeds {COUNTRY_MAX_LENGTH} characters for menu item {candidate['id']!r}"
        )

    for field_name, (precision, scale) in NUMERIC_FIELD_LIMITS.items():
        value = candidate.get(field_name)
        if value is None:
            continue
        if not isinstance(value, Decimal):
            raise RestaurantPostgresBridgeError(
                f"{field_name} must be Decimal or None for menu item {candidate['id']!r}"
            )
        if not _fits_numeric_bounds(value, precision=precision, scale=scale):
            raise RestaurantPostgresBridgeError(
                f"{field_name} exceeds NUMERIC({precision},{scale}) for menu item {candidate['id']!r}"
            )


def _json_default(value: Any) -> str:
    """Serialize Decimal values deterministically for tie-break comparisons."""

    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Unsupported JSON serialization type: {type(value)!r}")


def _completeness_score(record: dict[str, Any], fields: Sequence[str]) -> int:
    """Count populated fields so richer duplicate rows win deterministically."""

    return sum(record.get(field) is not None for field in fields)


def _canonical_record_key(record: dict[str, Any], fields: Sequence[str]) -> str:
    """Build a stable lexical tie-break key for duplicate-row consolidation."""

    payload = {field: record.get(field) for field in fields}
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, default=_json_default)


def _choose_preferred_record(
    *,
    current: dict[str, Any],
    candidate: dict[str, Any],
    fields: Sequence[str],
) -> dict[str, Any]:
    """Pick the richer duplicate record; tie-break lexically for order independence."""

    current_score = _completeness_score(current, fields)
    candidate_score = _completeness_score(candidate, fields)
    if candidate_score > current_score:
        return candidate
    if candidate_score < current_score:
        return current
    candidate_key = _canonical_record_key(candidate, fields)
    current_key = _canonical_record_key(current, fields)
    if candidate_key < current_key:
        return candidate
    return current


def _build_menu_item_records(
    rows: Sequence[dict[str, Any]],
    *,
    source_name: str,
    updated_at: datetime,
) -> list[dict[str, Any]]:
    """Convert importer rows into deterministic PostgreSQL menu-item payloads."""

    best_records_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        chain_name = _as_clean_str(row.get("chain_name")) or ""
        item_name = _as_clean_str(row.get("item_name")) or ""
        if not chain_name or not item_name:
            continue

        source_id = _as_clean_str(row.get("source_id"))
        chain_id = _slugify(chain_name)
        menu_source_part = source_id or _slugify(item_name)
        menu_id = f"{chain_id}:{menu_source_part}"
        candidate = {
            "id": menu_id,
            "chain_id": chain_id,
            "chain_name": chain_name,
            "country": _as_clean_str(row.get("country")) or DEFAULT_COUNTRY,
            "food_id": None,
            "item_name": item_name,
            "category": _as_clean_str(row.get("category")),
            "serving_size_g": _as_decimal(row.get("serving_size_g")),
            "kcal": _as_decimal(row.get("kcal")),
            "protein_g": _as_decimal(row.get("protein_g")),
            "fat_g": _as_decimal(row.get("fat_g")),
            "carbs_g": _as_decimal(row.get("carbs_g")),
            "sodium_mg": _as_decimal(row.get("sodium_mg")),
            "source": source_name,
            "source_id": source_id,
            "is_active": True,
            "updated_at": updated_at,
        }
        _validate_menu_item_candidate(candidate)
        existing = best_records_by_id.get(menu_id)
        if existing is None:
            best_records_by_id[menu_id] = candidate
            continue
        best_records_by_id[menu_id] = _choose_preferred_record(
            current=existing,
            candidate=candidate,
            fields=_MENU_COMPLETENESS_FIELDS,
        )

    return [best_records_by_id[menu_id] for menu_id in sorted(best_records_by_id)]


def _build_chain_records(
    menu_records: Sequence[dict[str, Any]],
    *,
    source_name: str,
    updated_at: datetime,
) -> list[dict[str, Any]]:
    """Aggregate deterministic chain rows from normalized menu-item payloads."""

    records_by_chain_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for menu_record in menu_records:
        records_by_chain_id[str(menu_record["chain_id"])].append(menu_record)

    chain_records: list[dict[str, Any]] = []
    for chain_id in sorted(records_by_chain_id):
        grouped_records = records_by_chain_id[chain_id]
        names = sorted(
            {
                str(record["chain_name"])
                for record in grouped_records
                if _as_clean_str(record.get("chain_name"))
            },
            key=lambda value: (value.casefold(), value),
        )
        countries = sorted(
            {
                str(record["country"])
                for record in grouped_records
                if _as_clean_str(record.get("country"))
            },
            key=lambda value: (value.casefold(), value),
        )
        source_ids = sorted(
            {
                str(record["source_id"])
                for record in grouped_records
                if _as_clean_str(record.get("source_id"))
            },
            key=lambda value: (value.casefold(), value),
        )
        resolved_source_id = source_ids[0] if source_ids else None
        chain_records.append(
            {
                "id": chain_id,
                "name": names[0] if names else chain_id,
                "country": countries[0] if countries else DEFAULT_COUNTRY,
                "source": source_name,
                "source_id": resolved_source_id,
                "updated_at": updated_at,
            }
        )

    return chain_records


def _build_pg_engine(pg_url: str) -> Engine:
    """Create and validate a PostgreSQL SQLAlchemy engine."""

    engine = create_engine(pg_url, pool_pre_ping=True, future=True)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise RestaurantPostgresBridgeError(
            f"target database must be PostgreSQL, got dialect {engine.dialect.name!r}"
        )
    return engine


def _reflect_bridge_tables(connection: Connection) -> tuple[Table, Table]:
    """Reflect target tables and validate the additive B2 schema contract."""

    metadata = MetaData()
    try:
        chains_table = Table(RESTAURANT_CHAINS_TABLE, metadata, autoload_with=connection)
        menu_items_table = Table(RESTAURANT_MENU_ITEMS_TABLE, metadata, autoload_with=connection)
    except NoSuchTableError as exc:
        raise RestaurantPostgresBridgeError(
            "restaurant PostgreSQL foundation is missing required tables; "
            "run the foods catalog foundation migrations first"
        ) from exc

    chain_columns = {column.name for column in chains_table.columns}
    missing_chain_columns = sorted(REQUIRED_CHAIN_COLUMNS - chain_columns)
    if missing_chain_columns:
        missing_str = ", ".join(missing_chain_columns)
        raise RestaurantPostgresBridgeError(
            f"{RESTAURANT_CHAINS_TABLE!r} is missing required columns: {missing_str}"
        )

    menu_item_columns = {column.name for column in menu_items_table.columns}
    missing_menu_item_columns = sorted(REQUIRED_MENU_ITEM_COLUMNS - menu_item_columns)
    if missing_menu_item_columns:
        missing_str = ", ".join(missing_menu_item_columns)
        raise RestaurantPostgresBridgeError(
            f"{RESTAURANT_MENU_ITEMS_TABLE!r} is missing required columns: {missing_str}"
        )

    return chains_table, menu_items_table


def _build_chain_upsert(table: Table, records: Sequence[dict[str, Any]]):
    """Build an idempotent upsert statement for restaurant chains."""

    statement = pg_insert(table).values(list(records))
    return statement.on_conflict_do_update(
        index_elements=[table.c.id],
        set_={
            "name": statement.excluded.name,
            "country": statement.excluded.country,
            "source": statement.excluded.source,
            "source_id": statement.excluded.source_id,
            "updated_at": statement.excluded.updated_at,
        },
    )


def _project_records_to_table_columns(
    table: Table,
    records: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """RU: Отфильтровать payload до колонок target table. EN: Keep only real table columns."""

    allowed_columns = {column.name for column in table.columns}
    return [
        {
            key: value
            for key, value in record.items()
            if key in allowed_columns
        }
        for record in records
    ]


def _build_menu_item_upsert(table: Table, records: Sequence[dict[str, Any]]) -> PostgresInsert:
    """Build an idempotent upsert statement that preserves existing food links."""

    statement = pg_insert(table).values(_project_records_to_table_columns(table, records))
    return statement.on_conflict_do_update(
        index_elements=[table.c.id],
        set_={
            "chain_id": statement.excluded.chain_id,
            "item_name": statement.excluded.item_name,
            "category": statement.excluded.category,
            "serving_size_g": statement.excluded.serving_size_g,
            "kcal": statement.excluded.kcal,
            "protein_g": statement.excluded.protein_g,
            "fat_g": statement.excluded.fat_g,
            "carbs_g": statement.excluded.carbs_g,
            "sodium_mg": statement.excluded.sodium_mg,
            "source": statement.excluded.source,
            "source_id": statement.excluded.source_id,
            "is_active": statement.excluded.is_active,
            "updated_at": statement.excluded.updated_at,
        },
    )


def import_menustat_rows_to_postgres(
    rows: Iterable[dict[str, Any]],
    *,
    pg_url: str,
    snapshot_date: str | None = None,
    source_name: str = "menustat",
) -> dict[str, int]:
    """Write importer-normalized restaurant rows into PostgreSQL foundation tables.

    RU: `snapshot_date` сохраняется в сигнатуре ради importer parity, но B2 bridge
    пишет только `restaurant_chains` и `restaurant_menu_items`.
    EN: `snapshot_date` remains in the signature for importer compatibility, but
    the B2 bridge writes only `restaurant_chains` and `restaurant_menu_items`.
    """

    del snapshot_date

    materialized_rows = list(rows)
    updated_at = _utc_now()
    menu_item_records = _build_menu_item_records(
        materialized_rows,
        source_name=source_name,
        updated_at=updated_at,
    )
    chain_records = _build_chain_records(
        menu_item_records,
        source_name=source_name,
        updated_at=updated_at,
    )

    if not menu_item_records:
        return {"chains_upserted": 0, "menu_items_upserted": 0}

    engine = _build_pg_engine(pg_url)
    try:
        with engine.begin() as connection:
            chains_table, menu_items_table = _reflect_bridge_tables(connection)
            connection.execute(_build_chain_upsert(chains_table, chain_records))
            connection.execute(_build_menu_item_upsert(menu_items_table, menu_item_records))
    finally:
        engine.dispose()

    return {
        "chains_upserted": len(chain_records),
        "menu_items_upserted": len(menu_item_records),
    }
