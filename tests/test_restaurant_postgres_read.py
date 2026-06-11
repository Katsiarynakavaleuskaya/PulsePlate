from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy.exc import NoSuchTableError

from app.services import restaurant_postgres_read


@pytest.fixture(autouse=True)
def _reset_pg_runtime_cache() -> Iterator[None]:
    restaurant_postgres_read.reset_restaurant_postgres_runtime_cache()
    yield
    restaurant_postgres_read.reset_restaurant_postgres_runtime_cache()


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


def test_build_pg_engine_sets_bounded_connect_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    fake_engine = _FakeEngine(object())

    def _fake_create_engine(*args: Any, **kwargs: Any) -> _FakeEngine:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return fake_engine

    monkeypatch.setattr(restaurant_postgres_read, "create_engine", _fake_create_engine)

    engine = restaurant_postgres_read._build_pg_engine("postgresql://shadow")

    assert engine is fake_engine
    assert captured["kwargs"]["connect_args"] == {
        "connect_timeout": restaurant_postgres_read.POSTGRES_CONNECT_TIMEOUT_SECONDS,
        "options": (
            f"-c statement_timeout="
            f"{restaurant_postgres_read.POSTGRES_STATEMENT_TIMEOUT_MS}"
        ),
    }
    assert captured["kwargs"]["pool_size"] == restaurant_postgres_read.POSTGRES_POOL_SIZE
    assert captured["kwargs"]["max_overflow"] == restaurant_postgres_read.POSTGRES_MAX_OVERFLOW
    assert captured["kwargs"]["pool_timeout"] == (
        restaurant_postgres_read.POSTGRES_POOL_TIMEOUT_SECONDS
    )


def test_search_restaurants_pg_rejects_non_postgres_dialect(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _unexpected_create_engine(*args: Any, **kwargs: Any) -> _FakeEngine:
        raise AssertionError("non-PostgreSQL URLs must be rejected before engine creation")

    monkeypatch.setattr(restaurant_postgres_read, "create_engine", _unexpected_create_engine)

    with caplog.at_level("DEBUG"):
        with pytest.raises(restaurant_postgres_read.RestaurantPostgresReadError) as exc:
            restaurant_postgres_read.search_restaurants_pg(
                pg_url="sqlite:///shadow.sqlite",
                query="pulse",
                limit=10,
                offset=0,
            )

    assert "target database must be PostgreSQL" in str(exc.value)
    assert "rejected non-PostgreSQL dialect: sqlite" in caplog.text


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


def test_fetch_search_rows_orders_by_name_then_id() -> None:
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
    assert "ORDER BY name ASC, id ASC" in connection.executed_sql[0]
    assert connection.params[0] == {"query": "alp", "pattern": "%alp%", "limit": 7, "offset": 3}


def test_fetch_menu_rows_orders_by_item_name_then_id() -> None:
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
    assert "ORDER BY item_name ASC, id ASC" in connection.executed_sql[0]
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


def test_search_restaurants_pg_builds_reflects_and_keeps_engine_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = _RecordingConnection(
        [{"id": "c1", "name": "Alpha", "country": "US", "source": "menustat"}]
    )
    fake_engine = _FakeEngine(fake_connection)
    reflected_connections: list[Any] = []

    monkeypatch.setattr(
        restaurant_postgres_read,
        "_build_pg_engine",
        lambda pg_url: fake_engine,
    )
    monkeypatch.setattr(
        restaurant_postgres_read,
        "_reflect_read_tables",
        lambda connection: reflected_connections.append(connection),
    )

    rows = restaurant_postgres_read.search_restaurants_pg(
        pg_url="postgresql://shadow",
        query="alp",
        limit=10,
        offset=5,
    )

    assert rows[0]["id"] == "c1"
    assert reflected_connections == [fake_connection]
    assert fake_engine.disposed is False


def test_get_restaurant_menu_pg_builds_reflects_and_keeps_engine_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = _RecordingConnection(
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
    fake_engine = _FakeEngine(fake_connection)
    reflected_connections: list[Any] = []

    monkeypatch.setattr(
        restaurant_postgres_read,
        "_build_pg_engine",
        lambda pg_url: fake_engine,
    )
    monkeypatch.setattr(
        restaurant_postgres_read,
        "_reflect_read_tables",
        lambda connection: reflected_connections.append(connection),
    )

    rows = restaurant_postgres_read.get_restaurant_menu_pg(
        pg_url="postgresql://shadow",
        chain_id="c1",
        limit=25,
    )

    assert rows[0]["id"] == "m1"
    assert reflected_connections == [fake_connection]
    assert fake_engine.disposed is False


def test_search_restaurants_pg_reuses_cached_engine_and_schema_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = _RecordingConnection(
        [{"id": "c1", "name": "Alpha", "country": "US", "source": "menustat"}]
    )
    fake_engine = _FakeEngine(fake_connection)
    build_calls: list[str] = []
    reflected_connections: list[Any] = []

    def _build(pg_url: str) -> _FakeEngine:
        build_calls.append(pg_url)
        return fake_engine

    monkeypatch.setattr(restaurant_postgres_read, "_build_pg_engine", _build)
    monkeypatch.setattr(
        restaurant_postgres_read,
        "_reflect_read_tables",
        lambda connection: reflected_connections.append(connection),
    )

    first = restaurant_postgres_read.search_restaurants_pg(
        pg_url="postgresql://shadow", query="alp", limit=10, offset=0
    )
    second = restaurant_postgres_read.search_restaurants_pg(
        pg_url="postgresql://shadow", query="bet", limit=10, offset=0
    )

    assert first[0]["id"] == "c1"
    assert second[0]["id"] == "c1"
    assert build_calls == ["postgresql://shadow"]
    assert reflected_connections == [fake_connection]
    assert fake_engine.disposed is False


def test_reset_restaurant_postgres_runtime_cache_disposes_cached_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_connection = _RecordingConnection(
        [{"id": "c1", "name": "Alpha", "country": "US", "source": "menustat"}]
    )
    fake_engine = _FakeEngine(fake_connection)
    monkeypatch.setattr(restaurant_postgres_read, "_build_pg_engine", lambda pg_url: fake_engine)
    monkeypatch.setattr(restaurant_postgres_read, "_reflect_read_tables", lambda connection: None)

    restaurant_postgres_read.search_restaurants_pg(
        pg_url="postgresql://shadow", query="alp", limit=10, offset=0
    )
    restaurant_postgres_read.reset_restaurant_postgres_runtime_cache()

    assert fake_engine.disposed is True
