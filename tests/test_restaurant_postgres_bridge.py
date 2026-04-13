from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import Boolean, Column, DateTime, MetaData, Numeric, Table, Text
from sqlalchemy.dialects import postgresql as pg_dialect

from app.services import restaurant_postgres_bridge as bridge


def _chains_table(metadata: MetaData) -> Table:
    return Table(
        bridge.RESTAURANT_CHAINS_TABLE,
        metadata,
        Column("id", Text, primary_key=True),
        Column("name", Text, nullable=False),
        Column("country", Text),
        Column("source", Text, nullable=False),
        Column("source_id", Text),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )


def _menu_items_table(metadata: MetaData) -> Table:
    return Table(
        bridge.RESTAURANT_MENU_ITEMS_TABLE,
        metadata,
        Column("id", Text, primary_key=True),
        Column("chain_id", Text, nullable=False),
        Column("food_id", Text),
        Column("item_name", Text, nullable=False),
        Column("category", Text),
        Column("serving_size_g", Numeric(10, 2)),
        Column("kcal", Numeric(8, 2)),
        Column("protein_g", Numeric(8, 2)),
        Column("fat_g", Numeric(8, 2)),
        Column("carbs_g", Numeric(8, 2)),
        Column("sodium_mg", Numeric(10, 2)),
        Column("source", Text, nullable=False),
        Column("source_id", Text),
        Column("is_active", Boolean, nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )


class _FakeConnection:
    def __init__(self) -> None:
        self.executed: list[object] = []

    def execute(self, statement: object) -> None:
        self.executed.append(statement)


class _FakeBeginContext:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection

    def __enter__(self) -> _FakeConnection:
        return self._connection

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class _FakeEngine:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection
        self.disposed = False

    def begin(self) -> _FakeBeginContext:
        return _FakeBeginContext(self._connection)

    def dispose(self) -> None:
        self.disposed = True


def test_build_menu_item_records_deduplicates_and_uses_deterministic_fallback_ids() -> None:
    updated_at = datetime(2026, 4, 13, tzinfo=timezone.utc)
    rows = [
        {
            "chain_name": "Chain A",
            "item_name": "Item 1",
            "source_id": "menu-001",
            "kcal": "500",
        },
        {
            "chain_name": "Chain A",
            "item_name": "Item 1",
            "source_id": "menu-001",
            "kcal": "500",
            "category": "Burgers",
            "protein_g": "22",
        },
        {
            "chain_name": "Пицца Дом",
            "item_name": "Маргарита",
        },
    ]

    records = bridge._build_menu_item_records(
        rows,
        source_name="menustat",
        updated_at=updated_at,
    )

    assert len(records) == 2

    first_record = records[0]
    assert first_record["id"] == "chain-a:menu-001"
    assert first_record["category"] == "Burgers"
    assert first_record["kcal"] == Decimal("500")
    assert first_record["protein_g"] == Decimal("22")
    assert first_record["food_id"] is None
    assert first_record["updated_at"] == updated_at

    second_record = records[1]
    expected_chain_id = bridge._slugify("Пицца Дом")
    expected_item_id = bridge._slugify("Маргарита")
    assert second_record["id"] == f"{expected_chain_id}:{expected_item_id}"
    assert second_record["chain_id"] == expected_chain_id
    assert second_record["country"] == bridge.DEFAULT_COUNTRY


def test_build_chain_records_uses_deterministic_chain_source_id() -> None:
    updated_at = datetime(2026, 4, 13, tzinfo=timezone.utc)
    menu_records = [
        {
            "id": "chain-a:item-001",
            "chain_id": "chain-a",
            "chain_name": "Chain A",
            "country": "US",
            "item_name": "Item 1",
            "source_id": "item-001",
        },
        {
            "id": "chain-a:item-002",
            "chain_id": "chain-a",
            "chain_name": "Chain A",
            "country": "CA",
            "item_name": "Item 2",
            "source_id": "item-002",
        },
    ]

    chain_records = bridge._build_chain_records(
        menu_records,
        source_name="menustat",
        updated_at=updated_at,
    )

    assert chain_records == [
        {
            "id": "chain-a",
            "name": "Chain A",
            "country": "CA",
            "source": "menustat",
            "source_id": "item-001",
            "updated_at": updated_at,
        }
    ]


def test_build_menu_item_records_rejects_country_exceeding_schema_limit() -> None:
    updated_at = datetime(2026, 4, 13, tzinfo=timezone.utc)

    with pytest.raises(
        bridge.RestaurantPostgresBridgeError,
        match="country exceeds 16 characters",
    ):
        bridge._build_menu_item_records(
            [
                {
                    "chain_name": "Chain A",
                    "item_name": "Item 1",
                    "country": "United States of America",
                }
            ],
            source_name="menustat",
            updated_at=updated_at,
        )


def test_build_menu_item_records_rejects_numeric_precision_overflow() -> None:
    updated_at = datetime(2026, 4, 13, tzinfo=timezone.utc)

    with pytest.raises(
        bridge.RestaurantPostgresBridgeError,
        match=r"kcal exceeds NUMERIC\(8,2\)",
    ):
        bridge._build_menu_item_records(
            [
                {
                    "chain_name": "Chain A",
                    "item_name": "Item 1",
                    "kcal": "1234567.89",
                }
            ],
            source_name="menustat",
            updated_at=updated_at,
        )


def test_build_menu_item_upsert_preserves_existing_food_id_on_conflict() -> None:
    metadata = MetaData()
    table = _menu_items_table(metadata)
    record = {
        "id": "chain-a:item-001",
        "chain_id": "chain-a",
        "chain_name": "Chain A",
        "country": "US",
        "food_id": None,
        "item_name": "Item 1",
        "category": "Wraps",
        "serving_size_g": Decimal("100"),
        "kcal": Decimal("500"),
        "protein_g": Decimal("20"),
        "fat_g": Decimal("10"),
        "carbs_g": Decimal("40"),
        "sodium_mg": Decimal("700"),
        "source": "menustat",
        "source_id": "item-001",
        "is_active": True,
        "updated_at": datetime(2026, 4, 13, tzinfo=timezone.utc),
    }

    statement = bridge._build_menu_item_upsert(table, [record])
    compiled = str(
        statement.compile(
            dialect=pg_dialect.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "INSERT INTO restaurant_menu_items" in compiled
    assert "ON CONFLICT (id) DO UPDATE SET" in compiled
    assert "chain_id = excluded.chain_id" in compiled
    assert "food_id = excluded.food_id" not in compiled
    assert "chain_name" not in compiled
    assert "country" not in compiled


def test_build_pg_engine_rejects_non_postgres_dialect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disposed: dict[str, bool] = {"value": False}

    class _BadEngine:
        def __init__(self) -> None:
            self.dialect = SimpleNamespace(name="sqlite")

        def dispose(self) -> None:
            disposed["value"] = True

    monkeypatch.setattr(bridge, "create_engine", lambda *args, **kwargs: _BadEngine())

    with pytest.raises(
        bridge.RestaurantPostgresBridgeError,
        match="target database must be PostgreSQL",
    ):
        bridge._build_pg_engine("sqlite:///:memory:")

    assert disposed["value"] is True


def test_import_menustat_rows_to_postgres_executes_unique_chain_and_menu_upserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _FakeConnection()
    engine = _FakeEngine(connection)
    metadata = MetaData()
    chains_table = _chains_table(metadata)
    menu_items_table = _menu_items_table(metadata)

    monkeypatch.setattr(bridge, "_build_pg_engine", lambda pg_url: engine)
    monkeypatch.setattr(
        bridge,
        "_reflect_bridge_tables",
        lambda _: (chains_table, menu_items_table),
    )
    monkeypatch.setattr(
        bridge,
        "_utc_now",
        lambda: datetime(2026, 4, 13, tzinfo=timezone.utc),
    )

    summary = bridge.import_menustat_rows_to_postgres(
        [
            {
                "chain_name": "Chain A",
                "item_name": "Item 1",
                "source_id": "menu-001",
                "kcal": "500",
            },
            {
                "chain_name": "Chain A",
                "item_name": "Item 1",
                "source_id": "menu-001",
                "kcal": "500",
            },
        ],
        snapshot_date="2026-04-13",
        source_name="menustat",
        pg_url="postgresql+psycopg://user:pass@db/pulseplate",  # pragma: allowlist secret
    )

    assert summary == {"chains_upserted": 1, "menu_items_upserted": 1}
    assert [statement.table.name for statement in connection.executed] == [
        bridge.RESTAURANT_CHAINS_TABLE,
        bridge.RESTAURANT_MENU_ITEMS_TABLE,
    ]
    assert engine.disposed is True
