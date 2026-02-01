"""Diff-coverage tests for core.db engine reuse/recreate branches.

Covers _get_raw_engine() reuse (same URL) and recreate (URL changed) paths
and _get_sqlite_poolclass() branches (non-SQLite, :memory:) for diff-coverage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import core.db as core_db


def test_get_sqlite_poolclass_returns_none_for_non_sqlite() -> None:
    """Cover core/db.py line 203: get_backend_name() != 'sqlite' → return None."""
    result = core_db._get_sqlite_poolclass("postgresql://localhost/mydb")
    assert result is None


def test_get_sqlite_poolclass_returns_none_for_memory() -> None:
    """Cover core/db.py is_memory branch: :memory: → return None."""
    result = core_db._get_sqlite_poolclass("sqlite:///:memory:")
    assert result is None


def test_get_sqlite_poolclass_returns_none_when_not_test_nor_xdist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cover core/db.py line 211: file-based SQLite but not test/xdist → return None."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    result = core_db._get_sqlite_poolclass(f"sqlite:///{tmp_path / 'x.db'}")
    assert result is None


def _reset_engine() -> None:
    # RU: чистим глобальный singleton engine, иначе он "прилипает" между тестами.
    # EN: clear global singleton engine; otherwise it leaks across tests.
    engine = getattr(core_db, "_RAW_ENGINE", None)
    if engine is not None:
        engine.dispose()
        core_db._RAW_ENGINE = None


def test_raw_engine_reuses_same_engine_for_same_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same URL → _get_raw_engine returns same engine instance (reuse branch)."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'a.sqlite'}")

    _reset_engine()
    e1 = core_db.init_db()
    e2 = core_db.init_db()
    assert e1 is e2

    _reset_engine()


def test_raw_engine_recreates_engine_when_url_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """URL change → init_db recreates engine (recreate branch)."""
    monkeypatch.setenv("APP_ENV", "test")
    db1 = tmp_path / "a.sqlite"
    db2 = tmp_path / "b.sqlite"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db1}")
    _reset_engine()
    core_db.init_db()
    e1 = getattr(core_db, "_RAW_ENGINE")
    url1 = str(e1.url)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db2}")
    core_db.init_db()
    e2 = getattr(core_db, "_RAW_ENGINE")
    url2 = str(e2.url)

    assert e1 is not e2
    assert url1 != url2

    _reset_engine()
