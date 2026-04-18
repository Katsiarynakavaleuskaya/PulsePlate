"""Migration coverage for the foods catalog foundation revision.

RU: Проверки миграции foundation-слоя для foods/restaurants.
EN: Smoke and contract checks for the foods/restaurants foundation migration.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path
import runpy
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest
from sqlalchemy import create_engine, inspect

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
FOUNDATION_REVISION = "202604120001"
TRIGRAM_SEAM_REVISION = "202604060001"
MIGRATION_PATH = REPO_ROOT / "alembic" / "versions" / "202604120001_add_foods_catalog_foundation.py"
ALEMBIC_SUBPROCESS_TIMEOUT_SECONDS = 60
OWNERSHIP_REGISTRY_TABLE = "pulseplate_migration_ownership"


def _write_temp_alembic_ini(tmp_path: Path) -> Path:
    temp_alembic_ini = tmp_path / "alembic.ini"
    parser = configparser.ConfigParser()
    parser.read(ALEMBIC_INI, encoding="utf-8")
    parser["alembic"]["script_location"] = str(REPO_ROOT / "alembic")
    with temp_alembic_ini.open("w", encoding="utf-8") as temp_file:
        parser.write(temp_file)
    return temp_alembic_ini


def _run_alembic_command(
    config_path: Path,
    repo_root: Path,
    verb: str,
    revision: str,
    env: dict[str, str],
) -> None:
    """RU: Запустить Alembic-команду в отдельном процессе.

    EN: Run Alembic command in an isolated subprocess.
    """

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "config_path, repo_root, verb, revision = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]; "
                "from alembic.config import main; "
                "sys.path.append(repo_root); "
                'main(argv=["-c", config_path, verb, revision], prog="alembic")'
            ),
            str(config_path),
            str(repo_root),
            verb,
            revision,
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(config_path.parent),
        env=env,
        timeout=ALEMBIC_SUBPROCESS_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, (
        f"Alembic command failed: {verb} {revision}\n"
        f"STDERR:\n{completed.stderr}\n"
        f"STDOUT:\n{completed.stdout}"
    )


def _fk_signature(
    foreign_key: dict[str, object],
) -> tuple[tuple[str, ...], str | None, tuple[str, ...]]:
    """Return stable FK identity for downgrade/re-upgrade comparisons."""

    constrained = tuple(str(value) for value in (foreign_key.get("constrained_columns") or ()))
    referred_columns = tuple(str(value) for value in (foreign_key.get("referred_columns") or ()))
    referred_table = foreign_key.get("referred_table")
    return (
        constrained,
        str(referred_table) if referred_table is not None else None,
        referred_columns,
    )


def _ownership_signature(
    row: tuple[object, object, object, object],
) -> tuple[str, str, str, str]:
    """Normalize ownership rows for deterministic assertions."""

    return tuple(str(value) for value in row)  # type: ignore[return-value]


def _read_ownership_rows(database_url: str) -> set[tuple[str, str, str, str]]:
    """RU: Считать ownership registry. EN: Read ownership registry rows."""

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if OWNERSHIP_REGISTRY_TABLE not in inspector.get_table_names():
                return set()
            rows = connection.exec_driver_sql(f"""
                SELECT revision_id, object_type, table_name, object_name
                FROM {OWNERSHIP_REGISTRY_TABLE}
                """).fetchall()
    finally:
        engine.dispose()
    return {_ownership_signature(row) for row in rows}


def _seed_preexisting_foods_catalog(
    database_url: str,
    *,
    preexisting_indexes: tuple[str, ...] = (),
) -> None:
    """Create a minimal compatible foods table before running the migration."""

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("""
                CREATE TABLE foods (
                    id TEXT NOT NULL PRIMARY KEY,
                    canonical_name TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    gtin TEXT,
                    brand TEXT
                )
                """)
            for index_name in preexisting_indexes:
                if index_name == "ix_foods_canonical_name":
                    connection.exec_driver_sql(
                        "CREATE INDEX ix_foods_canonical_name ON foods (canonical_name)"
                    )
                elif index_name == "ix_foods_group_name":
                    connection.exec_driver_sql(
                        "CREATE INDEX ix_foods_group_name ON foods (group_name)"
                    )
                elif index_name == "ix_foods_source":
                    connection.exec_driver_sql("CREATE INDEX ix_foods_source ON foods (source)")
                elif index_name == "ix_foods_gtin":
                    connection.exec_driver_sql("CREATE INDEX ix_foods_gtin ON foods (gtin)")
                else:
                    raise AssertionError(f"Unsupported preexisting index seed: {index_name}")
    finally:
        engine.dispose()


class _FakeMigrationInspector:
    """Deterministic inspector for stateful migration unit tests."""

    def __init__(self, state: dict[str, object]) -> None:
        self._state = state

    def has_table(self, table_name: str) -> bool:
        return table_name in self._state["tables"]

    def get_indexes(self, table_name: str) -> list[dict[str, str]]:
        table_indexes = self._state["indexes"].get(table_name, set())
        return [{"name": index_name} for index_name in sorted(table_indexes)]


class _FakeMigrationOp:
    """Stateful fake Alembic `op` surface for deterministic revision tests."""

    def __init__(self, state: dict[str, object]) -> None:
        self._state = state
        self._bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def get_bind(self) -> SimpleNamespace:
        return self._bind

    def create_table(self, table_name: str, *args: object, **kwargs: object) -> None:
        self._state["tables"].add(table_name)
        self._state["indexes"].setdefault(table_name, set())

    def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: list[str],
        *,
        unique: bool = False,
    ) -> None:
        del columns, unique
        self._state["indexes"].setdefault(table_name, set()).add(index_name)

    def drop_index(self, index_name: str, *, table_name: str) -> None:
        self._state["dropped_indexes"].append((table_name, index_name))
        self._state["indexes"].setdefault(table_name, set()).discard(index_name)

    def drop_table(self, table_name: str) -> None:
        self._state["dropped_tables"].append(table_name)
        self._state["tables"].discard(table_name)
        self._state["indexes"].pop(table_name, None)

    def execute(self, statement: object) -> None:
        sql = str(statement).strip()
        self._state["executed_sql"].append(sql)
        if sql.startswith("CREATE INDEX "):
            index_name = sql.split()[2]
            self._state["indexes"].setdefault("foods", set()).add(index_name)


def _load_foundation_migration_runtime(
    monkeypatch: pytest.MonkeyPatch,
    state: dict[str, object],
) -> dict[str, object]:
    """Load the migration module with a fake Alembic op binding."""

    fake_alembic = ModuleType("alembic")
    fake_alembic.op = _FakeMigrationOp(state)
    monkeypatch.setitem(sys.modules, "alembic", fake_alembic)

    runtime = runpy.run_path(str(MIGRATION_PATH))
    runtime_globals = runtime["upgrade"].__globals__
    monkeypatch.setattr(
        runtime_globals["sa"],
        "inspect",
        lambda bind: _FakeMigrationInspector(state),
    )
    runtime_globals["_record_owned_object"] = lambda object_type, table_name, object_name: (
        state["owned"].add((object_type, table_name, object_name))
    )
    runtime_globals["_owned_object_exists"] = (
        lambda object_type, table_name, object_name: (
            object_type,
            table_name,
            object_name,
        )
        in state["owned"]
    )
    runtime_globals["_remove_owned_object_record"] = (
        lambda object_type, table_name, object_name: state["owned"].discard(
            (object_type, table_name, object_name)
        )
    )
    runtime_globals["_drop_ownership_registry_if_empty"] = lambda: (
        state["registry_cleanup"].append("drop") if not state["owned"] else None
    )
    return runtime


def test_foods_catalog_foundation_migration_sqlite_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "foods-foundation.sqlite3"
    database_url = f"sqlite:///{db_path}"
    temp_alembic_ini = _write_temp_alembic_ini(tmp_path)

    monkeypatch.setenv("DATABASE_URL", database_url)
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.pop("PYTHONPATH", None)

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "upgrade",
        FOUNDATION_REVISION,
        env,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        foods_columns = {column["name"] for column in inspector.get_columns("foods")}
        restaurant_columns = {
            column["name"] for column in inspector.get_columns("restaurant_chains")
        }
        menu_columns = {column["name"] for column in inspector.get_columns("restaurant_menu_items")}
        foods_indexes = {
            index["name"] for index in inspector.get_indexes("foods") if index.get("name")
        }
        menu_indexes = {
            index["name"]
            for index in inspector.get_indexes("restaurant_menu_items")
            if index.get("name")
        }
        menu_fks = {
            _fk_signature(foreign_key)
            for foreign_key in inspector.get_foreign_keys("restaurant_menu_items")
        }
    finally:
        engine.dispose()

    assert "foods" in tables
    assert "restaurant_chains" in tables
    assert "restaurant_menu_items" in tables
    assert {"id", "canonical_name", "group_name", "gtin", "nutrition_confidence"} <= foods_columns
    assert {"id", "name", "source", "updated_at"} <= restaurant_columns
    assert {"id", "chain_id", "food_id", "item_name", "source"} <= menu_columns
    assert {
        "ix_foods_canonical_name",
        "ix_foods_group_name",
        "ix_foods_source",
        "ix_foods_gtin",
    } <= foods_indexes
    assert {
        "ix_restaurant_menu_items_chain_id",
        "ix_restaurant_menu_items_item_name",
        "ix_restaurant_menu_items_food_id",
    } <= menu_indexes
    assert {
        (("chain_id",), "restaurant_chains", ("id",)),
        (("food_id",), "foods", ("id",)),
    } <= menu_fks


def test_foods_catalog_foundation_migration_sqlite_downgrade_cycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "foods-foundation-cycle.sqlite3"
    database_url = f"sqlite:///{db_path}"
    temp_alembic_ini = _write_temp_alembic_ini(tmp_path)

    monkeypatch.setenv("DATABASE_URL", database_url)
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.pop("PYTHONPATH", None)

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "upgrade",
        FOUNDATION_REVISION,
        env,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        initial_menu_fks = {
            _fk_signature(foreign_key)
            for foreign_key in inspector.get_foreign_keys("restaurant_menu_items")
        }
        initial_menu_indexes = {
            index["name"]
            for index in inspector.get_indexes("restaurant_menu_items")
            if index.get("name")
        }
    finally:
        engine.dispose()
    ownership_rows_after_upgrade = _read_ownership_rows(database_url)

    assert {
        (FOUNDATION_REVISION, "table", "foods", "foods"),
        (FOUNDATION_REVISION, "table", "restaurant_chains", "restaurant_chains"),
        (FOUNDATION_REVISION, "table", "restaurant_menu_items", "restaurant_menu_items"),
        (FOUNDATION_REVISION, "index", "foods", "ix_foods_canonical_name"),
        (FOUNDATION_REVISION, "index", "foods", "ix_foods_group_name"),
        (FOUNDATION_REVISION, "index", "foods", "ix_foods_source"),
        (FOUNDATION_REVISION, "index", "foods", "ix_foods_gtin"),
        (FOUNDATION_REVISION, "index", "restaurant_chains", "ix_restaurant_chains_name"),
        (
            FOUNDATION_REVISION,
            "index",
            "restaurant_menu_items",
            "ix_restaurant_menu_items_chain_id",
        ),
        (
            FOUNDATION_REVISION,
            "index",
            "restaurant_menu_items",
            "ix_restaurant_menu_items_item_name",
        ),
        (
            FOUNDATION_REVISION,
            "index",
            "restaurant_menu_items",
            "ix_restaurant_menu_items_food_id",
        ),
    } <= ownership_rows_after_upgrade

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "downgrade",
        TRIGRAM_SEAM_REVISION,
        env,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables_after_downgrade = set(inspector.get_table_names())
    finally:
        engine.dispose()

    assert "foods" not in tables_after_downgrade
    assert "restaurant_chains" not in tables_after_downgrade
    assert "restaurant_menu_items" not in tables_after_downgrade
    assert OWNERSHIP_REGISTRY_TABLE not in tables_after_downgrade

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "upgrade",
        FOUNDATION_REVISION,
        env,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables_after_reupgrade = set(inspector.get_table_names())
        final_menu_fks = {
            _fk_signature(foreign_key)
            for foreign_key in inspector.get_foreign_keys("restaurant_menu_items")
        }
        final_menu_indexes = {
            index["name"]
            for index in inspector.get_indexes("restaurant_menu_items")
            if index.get("name")
        }
    finally:
        engine.dispose()

    assert "foods" in tables_after_reupgrade
    assert "restaurant_chains" in tables_after_reupgrade
    assert "restaurant_menu_items" in tables_after_reupgrade
    assert initial_menu_fks == final_menu_fks
    assert initial_menu_indexes == final_menu_indexes


def test_foods_catalog_foundation_preserves_preexisting_foods_table_on_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "foods-foundation-preexisting-table.sqlite3"
    database_url = f"sqlite:///{db_path}"
    temp_alembic_ini = _write_temp_alembic_ini(tmp_path)

    _seed_preexisting_foods_catalog(database_url)

    monkeypatch.setenv("DATABASE_URL", database_url)
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.pop("PYTHONPATH", None)

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "upgrade",
        FOUNDATION_REVISION,
        env,
    )

    ownership_rows_after_upgrade = _read_ownership_rows(database_url)
    assert (FOUNDATION_REVISION, "table", "foods", "foods") not in ownership_rows_after_upgrade
    assert (
        FOUNDATION_REVISION,
        "index",
        "foods",
        "ix_foods_canonical_name",
    ) in ownership_rows_after_upgrade
    assert (
        FOUNDATION_REVISION,
        "index",
        "foods",
        "ix_foods_group_name",
    ) in ownership_rows_after_upgrade
    assert (
        FOUNDATION_REVISION,
        "index",
        "foods",
        "ix_foods_source",
    ) in ownership_rows_after_upgrade
    assert (FOUNDATION_REVISION, "index", "foods", "ix_foods_gtin") in ownership_rows_after_upgrade

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "downgrade",
        TRIGRAM_SEAM_REVISION,
        env,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables_after_downgrade = set(inspector.get_table_names())
        foods_indexes_after_downgrade = {
            index["name"] for index in inspector.get_indexes("foods") if index.get("name")
        }
    finally:
        engine.dispose()

    assert "foods" in tables_after_downgrade
    assert "restaurant_chains" not in tables_after_downgrade
    assert "restaurant_menu_items" not in tables_after_downgrade
    assert foods_indexes_after_downgrade == set()
    assert OWNERSHIP_REGISTRY_TABLE not in tables_after_downgrade


def test_foods_catalog_foundation_preserves_preexisting_foods_indexes_on_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "foods-foundation-preexisting-indexes.sqlite3"
    database_url = f"sqlite:///{db_path}"
    temp_alembic_ini = _write_temp_alembic_ini(tmp_path)

    _seed_preexisting_foods_catalog(
        database_url,
        preexisting_indexes=("ix_foods_canonical_name", "ix_foods_group_name"),
    )

    monkeypatch.setenv("DATABASE_URL", database_url)
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.pop("PYTHONPATH", None)

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "upgrade",
        FOUNDATION_REVISION,
        env,
    )

    ownership_rows_after_upgrade = _read_ownership_rows(database_url)
    assert (FOUNDATION_REVISION, "table", "foods", "foods") not in ownership_rows_after_upgrade
    assert (
        FOUNDATION_REVISION,
        "index",
        "foods",
        "ix_foods_canonical_name",
    ) not in ownership_rows_after_upgrade
    assert (
        FOUNDATION_REVISION,
        "index",
        "foods",
        "ix_foods_group_name",
    ) not in ownership_rows_after_upgrade
    assert (
        FOUNDATION_REVISION,
        "index",
        "foods",
        "ix_foods_source",
    ) in ownership_rows_after_upgrade
    assert (FOUNDATION_REVISION, "index", "foods", "ix_foods_gtin") in ownership_rows_after_upgrade

    _run_alembic_command(
        temp_alembic_ini,
        REPO_ROOT,
        "downgrade",
        TRIGRAM_SEAM_REVISION,
        env,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables_after_downgrade = set(inspector.get_table_names())
        foods_indexes_after_downgrade = {
            index["name"] for index in inspector.get_indexes("foods") if index.get("name")
        }
    finally:
        engine.dispose()

    assert "foods" in tables_after_downgrade
    assert foods_indexes_after_downgrade == {
        "ix_foods_canonical_name",
        "ix_foods_group_name",
    }
    assert OWNERSHIP_REGISTRY_TABLE not in tables_after_downgrade


def test_foods_catalog_foundation_postgres_trigram_mixed_preexisting_cycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        "tables": {"foods"},
        "indexes": {
            "foods": {
                "ix_foods_canonical_name_gin_trgm",
            }
        },
        "owned": set(),
        "executed_sql": [],
        "dropped_indexes": [],
        "dropped_tables": [],
        "registry_cleanup": [],
    }
    runtime = _load_foundation_migration_runtime(monkeypatch, state)

    runtime["upgrade"]()

    assert any("CREATE EXTENSION IF NOT EXISTS pg_trgm" in sql for sql in state["executed_sql"])
    assert (
        runtime["_OBJECT_TYPE_INDEX"],
        "foods",
        "ix_foods_canonical_name_gin_trgm",
    ) not in state["owned"]
    assert (
        runtime["_OBJECT_TYPE_INDEX"],
        "foods",
        "ix_foods_group_name_gin_trgm",
    ) in state["owned"]
    assert (
        runtime["_OBJECT_TYPE_INDEX"],
        "foods",
        "ix_foods_brand_gin_trgm",
    ) in state["owned"]

    runtime["downgrade"]()

    assert "foods" in state["tables"]
    assert "restaurant_chains" not in state["tables"]
    assert "restaurant_menu_items" not in state["tables"]
    assert state["indexes"]["foods"] == {"ix_foods_canonical_name_gin_trgm"}
    assert ("foods", "ix_foods_group_name_gin_trgm") in state["dropped_indexes"]
    assert ("foods", "ix_foods_brand_gin_trgm") in state["dropped_indexes"]
    assert ("foods", "ix_foods_canonical_name_gin_trgm") not in state["dropped_indexes"]
    assert state["registry_cleanup"] == ["drop"]


def test_foods_catalog_foundation_postgres_clean_room_cycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        "tables": set(),
        "indexes": {},
        "owned": set(),
        "executed_sql": [],
        "dropped_indexes": [],
        "dropped_tables": [],
        "registry_cleanup": [],
    }
    runtime = _load_foundation_migration_runtime(monkeypatch, state)

    runtime["upgrade"]()

    assert {
        "foods",
        "restaurant_chains",
        "restaurant_menu_items",
    } <= state["tables"]
    assert {
        "ix_foods_canonical_name_gin_trgm",
        "ix_foods_group_name_gin_trgm",
        "ix_foods_brand_gin_trgm",
    } <= state["indexes"]["foods"]

    runtime["downgrade"]()

    assert state["tables"] == set()
    assert state["indexes"] == {}
    assert state["owned"] == set()
    assert state["registry_cleanup"] == ["drop"]


def test_foods_catalog_foundation_migration_contract_text() -> None:
    migration_text = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "op.create_table(" in migration_text
    assert '"foods"' in migration_text
    assert '"restaurant_chains"' in migration_text
    assert '"restaurant_menu_items"' in migration_text
    assert '"chain_id"' in migration_text
    assert "restaurant_id" not in migration_text
    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in migration_text
    assert "ix_foods_canonical_name_gin_trgm" in migration_text
    assert "ix_foods_group_name_gin_trgm" in migration_text
    assert "ix_foods_brand_gin_trgm" in migration_text
    assert "food_items" not in migration_text
    assert "rename_table" not in migration_text
    assert "pulseplate_migration_ownership" in migration_text
    assert "_create_owned_table(" in migration_text
    assert "_create_owned_index(" in migration_text
    assert "_record_owned_object(" in migration_text
    assert "_drop_owned_index(" in migration_text
    assert "_drop_owned_table(" in migration_text
    assert 'op.drop_table("foods")' not in migration_text
    assert 'op.drop_index("ix_foods_canonical_name", table_name="foods")' not in migration_text
