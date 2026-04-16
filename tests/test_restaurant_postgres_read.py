from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import NoSuchTableError

from app.services import restaurant_postgres_read


class _FakeMappingsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


class _RecordingConnection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.executed_sql: list[str] = []
        self.params: list[dict[str, Any]] = []

    def execute(self, sql: Any, params: dict[str, Any]) -> _FakeMappingsResult:
        self.executed_sql.append(str(sql))
        self.params.append(params)
        return _FakeMappingsResult(self.rows)


class _ConnectionContext:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def __enter__(self) -> Any:
        return self.connection

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class _FakeEngine:
    def __init__(self, connection: Any, *, dialect_name: str = "postgresql") -> None:
        self.connection = connection
        self.dialect = type("Dialect", (), {"name": dialect_name})()
        self.disposed = False

    def connect(self) -> _ConnectionContext:
        return _ConnectionContext(self.connection)

    def dispose(self) -> None:
        self.disposed = True


class _FakeTable:
    def __init__(self, columns: list[str]) -> None:
        self.columns = [type("Column", (), {"name": name})() for name in columns]


def test_search_restaurants_pg_rejects_non_postgres_dialect(tmp_path: Path) -> None:
    db_path = tmp_path / "shadow.sqlite"
    with pytest.raises(restaurant_postgres_read.RestaurantPostgresReadError) as exc:
        restaurant_postgres_read.search_restaurants_pg(
            pg_url=f"sqlite:///{db_path}",
            query="pulse",
            limit=10,
            offset=0,
        )
    assert "target database must be PostgreSQL" in str(exc.value)


def test_search_restaurants_pg_rejects_missing_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_connection = object()
    fake_engine = _FakeEngine(fake_connection)
    monkeypatch.setattr(restaurant_postgres_read, "create_engine", lambda *a, **k: fake_engine)

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise NoSuchTableError("restaurant_chains")

    monkeypatch.setattr(restaurant_postgres_read, "Table", _boom)

    with pytest.raises(restaurant_postgres_read.RestaurantPostgresReadError) as exc:
        restaurant_postgres_read.search_restaurants_pg(
            pg_url="postgresql://shadow",
            query="pulse",
            limit=5,
            offset=0,
        )
    assert "missing required tables" in str(exc.value)
    assert fake_engine.disposed is True


def test_fetch_search_rows_orders_by_name() -> None:
    connection = _RecordingConnection(
        [{"id": "c1", "name": "Alpha", "country": "US", "source": "menustat"}]
    )
    rows = restaurant_postgres_read._fetch_search_rows(
        connection,
        query="alp",
        limit=7,
        offset=3,
    )
    assert rows[0]["id"] == "c1"
    assert "ORDER BY name ASC" in connection.executed_sql[0]
    assert connection.params[0] == {"query": "alp", "pattern": "%alp%", "limit": 7, "offset": 3}


def test_fetch_menu_rows_orders_by_item_name() -> None:
    connection = _RecordingConnection(
        [
            {
                "id": "m1",
                "chain_id": "c1",
                "item_name": "Protein Bowl",
                "category": "Bowls",
                "serving_size_g": 240,
                "kcal": 510,
                "protein_g": 28,
                "fat_g": 16,
                "carbs_g": 55,
                "sodium_mg": 760,
                "source": "menustat",
                "source_id": "menu-1",
                "is_active": True,
            }
        ]
    )
    rows = restaurant_postgres_read._fetch_menu_rows(connection, chain_id="c1", limit=15)
    assert rows[0]["id"] == "m1"
    assert "AND is_active IS TRUE" in connection.executed_sql[0]
    assert "ORDER BY item_name ASC" in connection.executed_sql[0]
    assert connection.params[0] == {"chain_id": "c1", "limit": 15}


def test_fetch_menu_rows_sets_optional_provenance_to_none() -> None:
    connection = _RecordingConnection(
        [
            {
                "id": "m1",
                "chain_id": "c1",
                "item_name": "Protein Bowl",
                "category": "Bowls",
                "serving_size_g": 240,
                "kcal": 510,
                "protein_g": 28,
                "fat_g": 16,
                "carbs_g": 55,
                "sodium_mg": 760,
                "source": "menustat",
                "source_id": "menu-1",
                "is_active": True,
            }
        ]
    )
    row = restaurant_postgres_read._fetch_menu_rows(connection, chain_id="c1", limit=15)[0]
    assert row["snapshot_date"] is None
    assert row["provenance_source"] is None
    assert row["provenance_record_id"] is None


def test_reflect_read_tables_rejects_missing_required_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tables = iter(
        [
            _FakeTable(["id", "name", "country", "source"]),
            _FakeTable(["id", "chain_id", "item_name"]),
        ]
    )
    monkeypatch.setattr(restaurant_postgres_read, "Table", lambda *a, **k: next(tables))
    with pytest.raises(restaurant_postgres_read.RestaurantPostgresReadError) as exc:
        restaurant_postgres_read._reflect_read_tables(object())
    assert "missing required columns" in str(exc.value)
