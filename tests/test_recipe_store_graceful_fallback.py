# -*- coding: utf-8 -*-
"""
RU: Тесты для app.services.recipe_store — покрываем lazy-init и graceful fallback.
EN: Tests for app.services.recipe_store — cover lazy init and graceful fallbacks.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from app.services import recipe_store


@pytest.fixture(autouse=True)
def _reset_recipe_store_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU: Сбрасываем ленивый кеш пути к БД между тестами.

    EN: Reset lazy DB path cache between tests.
    """
    monkeypatch.setattr(recipe_store, "_DB_PATH", None)


def _init_sqlite_db(db_path: Path) -> None:
    """Create minimal schema required by recipe_store."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute("""
            CREATE TABLE recipes (
              rowid INTEGER PRIMARY KEY,
              recipe_id TEXT,
              title TEXT,
              kcal_per_serv REAL,
              tags_json TEXT
            )
            """)
        con.execute("""
            CREATE VIRTUAL TABLE recipes_fts USING fts5(title)
            """)
        con.execute(
            "INSERT INTO recipes (rowid, recipe_id, title, kcal_per_serv, tags_json) VALUES (1, ?, ?, ?, ?)",
            ("r1", "Oatmeal", 123.0, "[]"),
        )
        con.execute("INSERT INTO recipes_fts (rowid, title) VALUES (1, ?)", ("Oatmeal",))
        con.commit()
    finally:
        con.close()


def _raise_sqlite_operational_error(*_a: Any, **_kw: Any) -> sqlite3.Connection:
    """Helper for monkeypatching sqlite3.connect to raise operational error."""
    raise sqlite3.OperationalError("boom")


def _prepare_db_and_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal SQLite DB and point RECIPE_DB_PATH to it."""
    db_path = tmp_path / "recipes.sqlite"
    _init_sqlite_db(db_path)
    monkeypatch.setenv("RECIPE_DB_PATH", str(db_path))
    return db_path


def _assert_recipe_db_warning_logged(caplog: pytest.LogCaptureFixture) -> None:
    assert any("Recipe database unavailable" in r.message for r in caplog.records)


def test_validate_db_path_rejects_directory(tmp_path: Path) -> None:
    d = tmp_path / "recipes_dir"
    d.mkdir()
    with pytest.raises(ValueError):
        recipe_store._validate_db_path(d, "test")


def test_validate_db_path_missing_parent_raises(tmp_path: Path) -> None:
    p = tmp_path / "missing-parent" / "recipes.sqlite"
    with pytest.raises(FileNotFoundError):
        recipe_store._validate_db_path(p, "test")


def test_validate_db_path_parent_not_writable_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    p = parent / "recipes.sqlite"

    real_access = os.access

    def fake_access(path: Any, mode: int) -> bool:
        if Path(path) == parent and mode == os.W_OK:
            return False
        return real_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)
    with pytest.raises(PermissionError):
        recipe_store._validate_db_path(p, "test")


def test_validate_db_path_existing_file_not_rw_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    p = parent / "recipes.sqlite"
    p.write_text("x", encoding="utf-8")

    real_access = os.access

    def fake_access(path: Any, mode: int) -> bool:
        if Path(path) == p and mode == (os.R_OK | os.W_OK):
            return False
        return real_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)
    with pytest.raises(PermissionError):
        recipe_store._validate_db_path(p, "test")


def test_validate_db_path_existing_file_parent_not_writable_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    p = parent / "recipes.sqlite"
    p.write_text("x", encoding="utf-8")

    real_access = os.access

    def fake_access(path: Any, mode: int) -> bool:
        if Path(path) == p and mode == (os.R_OK | os.W_OK):
            return True
        if Path(path) == parent and mode == os.W_OK:
            return False
        return real_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)
    with pytest.raises(PermissionError):
        recipe_store._validate_db_path(p, "test")


def test_resolve_db_path_env_empty_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECIPE_DB_PATH", "")
    with pytest.raises(ValueError):
        recipe_store._resolve_db_path()


def test_get_db_path_uses_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "x.sqlite"
    monkeypatch.setenv("RECIPE_DB_PATH", str(db_path))
    resolved = recipe_store._get_db_path()
    assert resolved == db_path


def test_search_recipes_happy_path_returns_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_db_and_env(tmp_path, monkeypatch)

    # Empty query uses simple SQL without FTS
    # sourcery skip: extract-duplicate-method
    rows = recipe_store.search_recipes("", limit=10, offset=0)
    assert rows
    assert rows[0]["recipe_id"] == "r1"

    # Non-empty query uses FTS join
    rows2 = recipe_store.search_recipes("Oatmeal", limit=10, offset=0)
    assert rows2
    assert rows2[0]["title"] == "Oatmeal"


def test_get_recipe_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _prepare_db_and_env(tmp_path, monkeypatch)

    r = recipe_store.get_recipe("r1")
    assert r is not None
    assert r["title"] == "Oatmeal"


def test_search_recipes_sqlite_error_returns_empty(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(recipe_store.sqlite3, "connect", _raise_sqlite_operational_error)

    caplog.set_level(logging.WARNING)
    res = recipe_store.search_recipes("anything")
    assert res == []
    _assert_recipe_db_warning_logged(caplog)


def test_get_recipe_sqlite_error_returns_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(recipe_store.sqlite3, "connect", _raise_sqlite_operational_error)

    caplog.set_level(logging.WARNING)
    res = recipe_store.get_recipe("r1")
    assert res is None
    _assert_recipe_db_warning_logged(caplog)


# End of file
