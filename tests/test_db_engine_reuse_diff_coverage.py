"""Diff-coverage tests for core.db engine reuse/recreate branches.

Covers _get_raw_engine() reuse (same URL) and recreate (URL changed) paths
and _get_sqlite_poolclass() branches (non-SQLite, :memory:) for diff-coverage.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL

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


def test_raw_engine_uses_full_structured_credentialed_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real getter must reuse a complete URL without opening PostgreSQL."""
    url = URL.create(
        "postgresql+psycopg",
        "ops",
        "synthetic/secret",
        "localhost",
        database="ops",
        query={"sslmode": "require", "application_name": "ops02"},
    )
    base = url.render_as_string(hide_password=False)
    variants = (
        URL.create(
            url.drivername, url.username, "other", url.host, url.port, url.database, url.query
        ),
        url.set(host="other-host"),
        url.set(database="other"),
        url.update_query_dict({"sslmode": "disable"}),
    )

    core_db.reset_db_for_tests()
    try:
        with monkeypatch.context() as env:
            env.setenv("APP_ENV", "test")
            env.setenv("DATABASE_URL", base)
            first = core_db._get_raw_engine()
            assert core_db._get_raw_engine() is first

            equivalent = base.replace("%2F", "%2f").replace(
                "application_name=ops02&sslmode=require",
                "sslmode=require&application_name=ops02",
            )
            env.setenv("DATABASE_URL", equivalent)
            assert core_db._get_raw_engine() is first

            previous = first
            for variant in variants:
                env.setenv("DATABASE_URL", variant.render_as_string(hide_password=False))
                current = core_db._get_raw_engine()
                assert current is not previous
                previous = current
    finally:
        core_db.reset_db_for_tests()
        core_db.init_db()


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


def test_init_db_explicit_url_keeps_new_session_factory_selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ambient = f"sqlite:///{tmp_path / 'ambient.sqlite'}"
    explicit = f"sqlite:///{tmp_path / 'explicit.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", ambient)
    core_db.reset_db_for_tests()
    try:
        selected = core_db.init_db(explicit)
        factory = core_db.get_session_factory()
        with factory() as session:
            assert session.bind is selected
            assert session.scalar(text("SELECT 1")) == 1
        assert core_db.get_session_factory() is factory
        assert core_db._RAW_ENGINE is selected
    finally:
        core_db.reset_db_for_tests()
        core_db.init_db()


def test_failed_init_candidate_preserves_selected_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial = f"sqlite:///{tmp_path / 'initial.sqlite'}"
    replacement = f"sqlite:///{tmp_path / 'replacement.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", initial)
    core_db.reset_db_for_tests()
    try:
        selected = core_db.init_db()
        selected_factory = core_db.get_session_factory()
        original_create = core_db._create_sync_engine
        candidates = []
        disposed = []

        def make_candidate(db_url: str):
            candidate = original_create(db_url)
            candidates.append(candidate)
            original_dispose = candidate.dispose

            def dispose() -> None:
                disposed.append(candidate)
                original_dispose()

            monkeypatch.setattr(candidate, "dispose", dispose)
            return candidate

        class FailingMetadata:
            def create_all(self, *, bind: object) -> None:
                raise RuntimeError("synthetic schema failure")

        with monkeypatch.context() as failing:
            failing.setattr(core_db, "_create_sync_engine", make_candidate)
            failing.setattr(core_db, "load_canonical_orm_metadata", lambda: FailingMetadata())
            with pytest.raises(RuntimeError, match="synthetic schema failure"):
                core_db.init_db(replacement)

        assert len(candidates) == 1
        assert disposed == candidates
        assert core_db._RAW_ENGINE is selected
        assert core_db.get_session_factory() is selected_factory
        with selected_factory() as session:
            assert session.scalar(text("SELECT 1")) == 1

        def reject_candidate(_db_url: str) -> None:
            raise RuntimeError("synthetic engine creation failure")

        with monkeypatch.context() as failing:
            failing.setattr(core_db, "_create_sync_engine", reject_candidate)
            with pytest.raises(RuntimeError, match="synthetic engine creation failure"):
                core_db.init_db(replacement)
        assert core_db._RAW_ENGINE is selected
        assert core_db.get_session_factory() is selected_factory
    finally:
        core_db.reset_db_for_tests()
        core_db.init_db()


def test_concurrent_init_disposes_losing_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial = f"sqlite:///{tmp_path / 'initial.sqlite'}"
    target = f"sqlite:///{tmp_path / 'target.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", initial)
    core_db.reset_db_for_tests()
    try:
        core_db.init_db()
        rendezvous = Barrier(2)
        original_create = core_db._create_sync_engine
        candidates = []
        disposed = []

        def make_candidate(db_url: str):
            candidate = original_create(db_url)
            candidates.append(candidate)
            original_dispose = candidate.dispose

            def dispose() -> None:
                disposed.append(candidate)
                original_dispose()

            monkeypatch.setattr(candidate, "dispose", dispose)
            rendezvous.wait(timeout=5)
            return candidate

        class NoopMetadata:
            def create_all(self, *, bind: object) -> None:
                return None

        with monkeypatch.context() as racing:
            racing.setattr(core_db, "_create_sync_engine", make_candidate)
            racing.setattr(core_db, "load_canonical_orm_metadata", lambda: NoopMetadata())
            with ThreadPoolExecutor(max_workers=2) as workers:
                results = tuple(workers.map(core_db.init_db, (target, target)))

        assert results[0] is results[1] is core_db._RAW_ENGINE
        assert len(candidates) == 2
        assert len(disposed) == 1
        assert disposed[0] is not core_db._RAW_ENGINE
        with core_db.get_session_factory()() as session:
            assert session.bind is core_db._RAW_ENGINE
    finally:
        core_db.reset_db_for_tests()
        core_db.init_db()


def test_concurrent_distinct_url_init_returns_its_own_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial = f"sqlite:///{tmp_path / 'initial.sqlite'}"
    first_url = f"sqlite:///{tmp_path / 'first.sqlite'}"
    second_url = f"sqlite:///{tmp_path / 'second.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", initial)
    core_db.reset_db_for_tests()
    try:
        original = core_db.init_db()
        first_retirement_started = Event()
        release_first = Event()
        dispose = core_db._dispose_sync_engine

        def paused_dispose(engine, *, best_effort: bool = False) -> None:
            if engine is original:
                first_retirement_started.set()
                assert release_first.wait(timeout=5)
            dispose(engine, best_effort=best_effort)

        with monkeypatch.context() as racing:
            racing.setattr(core_db, "_dispose_sync_engine", paused_dispose)
            with ThreadPoolExecutor(max_workers=2) as workers:
                first = workers.submit(core_db.init_db, first_url)
                assert first_retirement_started.wait(timeout=5)
                try:
                    second = workers.submit(core_db.init_db, second_url)
                    second_result = second.result(timeout=5)
                finally:
                    release_first.set()
                first_result = first.result(timeout=5)

        assert first_result.url == core_db.make_url(first_url)
        assert second_result.url == core_db.make_url(second_url)
        assert first_result is not second_result
        assert core_db._RAW_ENGINE is second_result
        with core_db.get_session_factory()() as session:
            assert session.bind is second_result
    finally:
        core_db.reset_db_for_tests()
        core_db.init_db()
