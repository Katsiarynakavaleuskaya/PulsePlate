"""Migration coverage for the foods catalog foundation revision.

RU: Проверки миграции foundation-слоя для foods/restaurants.
EN: Smoke and contract checks for the foods/restaurants foundation migration.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
SCRIPT_LOCATION_REWRITE = f"script_location = {REPO_ROOT / 'alembic'}"
FOUNDATION_REVISION = "202604120001"
TRIGRAM_SEAM_REVISION = "202604060001"
MIGRATION_PATH = REPO_ROOT / "alembic" / "versions" / "202604120001_add_foods_catalog_foundation.py"


def _write_temp_alembic_ini(tmp_path: Path) -> Path:
    temp_alembic_ini = tmp_path / "alembic.ini"
    temp_alembic_ini.write_text(
        ALEMBIC_INI.read_text(encoding="utf-8").replace(
            "script_location = alembic",
            SCRIPT_LOCATION_REWRITE,
        ),
        encoding="utf-8",
    )
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
    )
    assert completed.returncode == 0, completed.stderr


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
    assert '_table_exists("foods")' in migration_text
    assert "food_items" not in migration_text
    assert "rename_table" not in migration_text
