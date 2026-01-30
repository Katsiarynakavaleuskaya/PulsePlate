"""Diff-coverage tests for core.db engine reuse/recreate branches.

Covers _get_raw_engine() reuse (same URL) and recreate (URL changed) paths
to fix Codecov partial line in core/db.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import core.db as core_db


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
