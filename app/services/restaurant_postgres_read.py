# -*- coding: utf-8 -*-
"""Read-only PostgreSQL adapter for restaurant shadow reads.

RU: Никакого runtime cutover — только shadow read path.
EN: No runtime cutover here — this module serves shadow-read path only.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import NoSuchTableError

RESTAURANT_CHAINS_TABLE = "restaurant_chains"
RESTAURANT_MENU_ITEMS_TABLE = "restaurant_menu_items"
REQUIRED_CHAIN_COLUMNS = frozenset({"id", "name", "country", "source"})
REQUIRED_MENU_COLUMNS = frozenset(
    {
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
    }
)
POSTGRES_CONNECT_TIMEOUT_SECONDS = 5
logger = logging.getLogger(__name__)


class RestaurantPostgresReadError(RuntimeError):
    """RU: Детерминированная ошибка read adapter. EN: Deterministic read-adapter failure."""


def _build_pg_engine(pg_url: str) -> Engine:
    """RU: Создать PostgreSQL engine и fail-closed проверить dialect.

    EN: Build a PostgreSQL engine and fail-closed validate dialect.
    """

    engine = create_engine(
        pg_url,
        pool_pre_ping=True,
        future=True,
        connect_args={"connect_timeout": POSTGRES_CONNECT_TIMEOUT_SECONDS},
    )
    if engine.dialect.name != "postgresql":
        logger.debug(
            "restaurant shadow-read adapter rejected non-PostgreSQL dialect: %s",
            engine.dialect.name,
        )
        engine.dispose()
        raise RestaurantPostgresReadError("target database must be PostgreSQL")
    return engine


def _reflect_read_tables(connection: Connection) -> None:
    """RU: Проверить обязательные таблицы/колонки для shadow read.

    EN: Validate required tables/columns for shadow reads.
    """

    metadata = MetaData()
    try:
        chains_table = Table(RESTAURANT_CHAINS_TABLE, metadata, autoload_with=connection)
        menu_table = Table(RESTAURANT_MENU_ITEMS_TABLE, metadata, autoload_with=connection)
    except NoSuchTableError as exc:
        raise RestaurantPostgresReadError(
            "restaurant PostgreSQL foundation is missing required tables; "
            "run foods catalog foundation migrations first"
        ) from exc

    chain_columns = {column.name for column in chains_table.columns}
    missing_chain_columns = sorted(REQUIRED_CHAIN_COLUMNS - chain_columns)
    if missing_chain_columns:
        missing_str = ", ".join(missing_chain_columns)
        raise RestaurantPostgresReadError(
            f"{RESTAURANT_CHAINS_TABLE!r} is missing required columns: {missing_str}"
        )

    menu_columns = {column.name for column in menu_table.columns}
    missing_menu_columns = sorted(REQUIRED_MENU_COLUMNS - menu_columns)
    if missing_menu_columns:
        missing_str = ", ".join(missing_menu_columns)
        raise RestaurantPostgresReadError(
            f"{RESTAURANT_MENU_ITEMS_TABLE!r} is missing required columns: {missing_str}"
        )


def _fetch_search_rows(
    connection: Connection,
    *,
    query: str,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    """RU: Прочитать restaurant search rows в deterministic order.

    EN: Fetch deterministic restaurant search rows.
    """

    sql = text("""
        SELECT id, name, country, source
        FROM restaurant_chains
        WHERE (:query = '' OR lower(name) LIKE lower(:pattern))
        ORDER BY name ASC, id ASC
        LIMIT :limit OFFSET :offset
        """)
    pattern = f"%{query.strip()}%"
    rows = connection.execute(
        sql,
        {
            "query": query.strip(),
            "pattern": pattern,
            "limit": limit,
            "offset": offset,
        },
    ).mappings()
    return [dict(row) for row in rows]


def _fetch_menu_rows(connection: Connection, *, chain_id: str, limit: int) -> list[dict[str, Any]]:
    """RU: Прочитать menu rows в deterministic order.

    EN: Fetch deterministic menu rows.
    """

    sql = text("""
        SELECT
            id,
            chain_id,
            item_name,
            category,
            serving_size_g,
            kcal,
            protein_g,
            fat_g,
            carbs_g,
            sodium_mg,
            source,
            source_id,
            is_active
        FROM restaurant_menu_items
        WHERE chain_id = :chain_id
          AND is_active IS TRUE
        ORDER BY item_name ASC, id ASC
        LIMIT :limit
        """)
    rows = connection.execute(sql, {"chain_id": chain_id, "limit": limit}).mappings()
    menu_rows: list[dict[str, Any]] = []
    for row in rows:
        materialized = dict(row)
        # RU/EN: Foundation tables do not store provenance metadata yet.
        materialized.setdefault("snapshot_date", None)
        materialized.setdefault("provenance_source", None)
        materialized.setdefault("provenance_record_id", None)
        menu_rows.append(materialized)
    return menu_rows


def search_restaurants_pg(
    *,
    pg_url: str,
    query: str,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    """RU: Shadow-read search rows from PostgreSQL.

    EN: Read search rows from PostgreSQL for shadow comparison.
    """

    engine = _build_pg_engine(pg_url)
    try:
        with engine.connect() as connection:
            _reflect_read_tables(connection)
            return _fetch_search_rows(connection, query=query, limit=limit, offset=offset)
    finally:
        engine.dispose()


def get_restaurant_menu_pg(*, pg_url: str, chain_id: str, limit: int) -> list[dict[str, Any]]:
    """RU: Shadow-read menu rows from PostgreSQL.

    EN: Read menu rows from PostgreSQL for shadow comparison.
    """

    engine = _build_pg_engine(pg_url)
    try:
        with engine.connect() as connection:
            _reflect_read_tables(connection)
            return _fetch_menu_rows(connection, chain_id=chain_id, limit=limit)
    finally:
        engine.dispose()
