"""Diff-coverage tests for core.db engine reuse/recreate branches.

Covers _get_raw_engine() reuse (same URL) and recreate (URL changed) paths
and _get_sqlite_poolclass() branches (non-SQLite, :memory:) for diff-coverage.
"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import logging
from pathlib import Path
from threading import Barrier, Event
import shutil

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, URL

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


@pytest.mark.parametrize("driver", ["sqlite", "sqlite+pysqlite", "sqlite+aiosqlite"])
def test_extract_sqlite_path_accepts_known_ordinary_file_urls(driver: str, tmp_path: Path) -> None:
    absolute_path = tmp_path / "owned.sqlite"
    assert core_db._extract_sqlite_path(f"{driver}:///{absolute_path}?timeout=5") == str(
        absolute_path
    )
    assert core_db._extract_sqlite_cleanup_path(f"{driver}:///{absolute_path}?timeout=5") == str(
        absolute_path
    )
    assert core_db._extract_sqlite_path(f"{driver}:///relative/owned.sqlite") == (
        "relative/owned.sqlite"
    )
    assert core_db._extract_sqlite_path(f"{driver}:///{absolute_path}?mode=rwc&uri=true") == str(
        absolute_path
    )


def test_ordinary_sqlite_uri_option_creates_missing_parent(tmp_path: Path) -> None:
    database_path = tmp_path / "new-parent" / "owned.sqlite"
    core_db._ensure_sqlite_directory(f"sqlite:///{database_path}?mode=rwc&uri=true")
    assert database_path.parent.is_dir()


@pytest.mark.parametrize("uri_key", ["uri", "URI", "Uri"])
def test_sqlite_cleanup_path_rejects_casefolded_uri_option(uri_key: str) -> None:
    database_url = f"sqlite:///ordinary.sqlite?mode=rwc&{uri_key}=true"
    assert core_db._extract_sqlite_path(database_url) == "ordinary.sqlite"
    assert core_db._extract_sqlite_cleanup_path(database_url) is None


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///:memory:",
        "sqlite+aiosqlite:///:memory:",
        "sqlite:///file:memdb1?mode=memory&uri=true",
        "sqlite:///file:ambiguous.sqlite",
        "sqlite:///ordinary.sqlite?mode=memory",
        "sqlite+unknown:///ordinary.sqlite",
        "sqlite:///",
        "not-a-database-url",
    ],
)
def test_extract_sqlite_path_rejects_unknown_or_non_file_identity(database_url: str) -> None:
    assert core_db._extract_sqlite_path(database_url) is None
    assert core_db._extract_sqlite_cleanup_path(database_url) is None


def _reset_engine() -> None:
    # RU: чистим глобальный singleton engine, иначе он "прилипает" между тестами.
    # EN: clear global singleton engine; otherwise it leaks across tests.
    engine = getattr(core_db, "_RAW_ENGINE", None)
    if engine is not None:
        engine.dispose()
        core_db._RAW_ENGINE = None


def test_raw_engine_repairs_missing_factory_without_replacing_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'selected.sqlite'}")
        core_db.reset_db_for_tests()
        try:
            selected = core_db._get_raw_engine()
            prior_factory = core_db.SessionLocal
            with monkeypatch.context() as missing:
                missing.setattr(core_db, "SessionLocal", None)
                assert core_db._get_raw_engine() is selected
                assert core_db.SessionLocal is not prior_factory
                assert core_db.SessionLocal is not None
                with core_db.SessionLocal() as session:
                    assert session.bind is selected
        finally:
            core_db.reset_db_for_tests()
    core_db.init_db()


def test_raw_engine_factory_failure_preserves_prior_pair_and_primary_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'prior.sqlite'}")
        core_db.reset_db_for_tests()
        try:
            prior = core_db._get_raw_engine()
            prior_factory = core_db.SessionLocal
            original_create = core_db._create_sync_engine
            candidate: Engine | None = None
            disposal_attempted = False
            primary = ValueError("synthetic factory failure")

            def create_candidate(db_url: str) -> Engine:
                nonlocal candidate
                candidate = original_create(db_url)

                def fail_disposal() -> None:
                    nonlocal disposal_attempted
                    disposal_attempted = True
                    raise RuntimeError("synthetic cleanup failure")

                failing.setattr(candidate, "dispose", fail_disposal)
                return candidate

            def fail_factory(_engine: Engine) -> None:
                raise primary

            with monkeypatch.context() as failing:
                failing.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'candidate.sqlite'}")
                failing.setattr(core_db, "_create_sync_engine", create_candidate)
                failing.setattr(core_db, "_make_sync_session_factory", fail_factory)
                with caplog.at_level(logging.ERROR), pytest.raises(ValueError) as observed:
                    core_db._get_raw_engine()
            assert observed.value is primary
            assert candidate is not None and disposal_attempted
            assert core_db._RAW_ENGINE is prior
            assert core_db.SessionLocal is prior_factory
            assert "Sync engine disposal failed: RuntimeError" in caplog.text
            assert "synthetic cleanup failure" not in caplog.text
        finally:
            if candidate is not None:
                candidate.dispose()
            core_db.reset_db_for_tests()
    core_db.init_db()


def test_raw_engine_retirement_disposal_failure_is_visible_without_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'prior.sqlite'}")
        core_db.reset_db_for_tests()
        prior = core_db._get_raw_engine()
        original_dispose = prior.dispose
        try:
            with monkeypatch.context() as failing:
                failing.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'selected.sqlite'}")

                def fail_retirement() -> None:
                    raise RuntimeError("synthetic retirement failure")

                failing.setattr(prior, "dispose", fail_retirement)
                with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError):
                    core_db._get_raw_engine()
                assert core_db._RAW_ENGINE is not prior
                assert core_db.SessionLocal is not None
                with core_db.SessionLocal() as session:
                    assert session.bind is core_db._RAW_ENGINE
            assert "Sync engine disposal failed: RuntimeError" in caplog.text
            assert "synthetic retirement failure" not in caplog.text
        finally:
            original_dispose()
            core_db.reset_db_for_tests()
    core_db.init_db()


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


def test_reused_init_db_rebinds_missing_factory_to_selected_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit_url = f"sqlite:///{tmp_path / 'selected.sqlite'}"
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ambient.sqlite'}")
        core_db.reset_db_for_tests()
        try:
            selected = core_db.init_db(explicit_url)
            with monkeypatch.context() as missing:
                missing.setattr(core_db, "SessionLocal", None)
                assert core_db.init_db(explicit_url) is selected
                assert core_db.SessionLocal is not None
                with core_db.SessionLocal() as session:
                    assert session.bind is selected
        finally:
            core_db.reset_db_for_tests()
    core_db.init_db()


def test_ambient_init_rejects_unpublished_configuration_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prior_url = f"sqlite:///{tmp_path / 'prior.sqlite'}"
    candidate_url = f"sqlite:///{tmp_path / 'candidate.sqlite'}"
    changed_url = f"sqlite:///{tmp_path / 'changed.sqlite'}"
    entered_schema = Event()
    release_schema = Event()
    candidate: Engine | None = None
    candidate_disposed = False
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", prior_url)
        core_db.reset_db_for_tests()
        prior = core_db.init_db()
        prior_factory = core_db.SessionLocal
        original_create = core_db._create_sync_engine

        def create_candidate(db_url: str) -> Engine:
            nonlocal candidate
            candidate = original_create(db_url)
            original_dispose = candidate.dispose

            def dispose() -> None:
                nonlocal candidate_disposed
                candidate_disposed = True
                original_dispose()

            racing.setattr(candidate, "dispose", dispose)
            return candidate

        class PausedMetadata:
            def create_all(self, *, bind: Engine) -> None:
                if bind.url == core_db.make_url(candidate_url):
                    entered_schema.set()
                    assert release_schema.wait(timeout=5)

        try:
            with monkeypatch.context() as racing:
                racing.setattr(core_db, "_create_sync_engine", create_candidate)
                racing.setattr(core_db, "load_canonical_orm_metadata", lambda: PausedMetadata())
                racing.setenv("DATABASE_URL", candidate_url)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    future = workers.submit(core_db.init_db)
                    assert entered_schema.wait(timeout=5)
                    racing.setenv("DATABASE_URL", changed_url)
                    release_schema.set()
                    with pytest.raises(
                        RuntimeError, match="DATABASE_URL changed during database initialization"
                    ):
                        future.result(timeout=5)
            assert candidate is not None and candidate_disposed
            assert core_db._RAW_ENGINE is prior
            assert core_db.SessionLocal is prior_factory
        finally:
            release_schema.set()
            core_db.reset_db_for_tests()
    core_db.init_db()


def test_init_db_explicit_sqlite_url_creates_its_missing_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit_path = tmp_path / "new-directory" / "explicit.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'unrelated.sqlite'}")
    core_db.reset_db_for_tests()
    try:
        selected = core_db.init_db(f"sqlite:///{explicit_path}")
        assert selected.url.database == str(explicit_path)
        assert explicit_path.is_file()
    finally:
        core_db.reset_db_for_tests()


def test_same_url_explicit_reinit_restores_missing_sqlite_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "removable-parent" / "selected.sqlite"
    explicit_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'unrelated.sqlite'}")
    core_db.reset_db_for_tests()
    try:
        selected = core_db.init_db(explicit_url)
        selected.dispose()
        shutil.rmtree(database_path.parent)
        assert not database_path.parent.exists()

        reused = core_db.init_db(explicit_url)
        assert reused is selected
        assert database_path.is_file()
        assert inspect(reused).has_table("users")
    finally:
        core_db.reset_db_for_tests()


def test_query_only_sqlite_replacement_preserves_selected_database_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "shared.sqlite"
    first_url = f"sqlite:///{database_path}?timeout=5"
    second_url = f"sqlite:///{database_path}?timeout=6"
    monkeypatch.setenv("DATABASE_URL", first_url)
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        first = core_db.init_db()
        assert database_path.is_file()
        monkeypatch.setenv("DATABASE_URL", second_url)
        selected = core_db.init_db()
        assert selected is not first
        assert database_path.is_file()
        assert inspect(selected).has_table("users")
        with core_db.get_session_factory()() as session:
            assert session.bind is selected
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        core_db.reset_db_for_tests()


def test_sqlite_to_pysqlite_same_file_replacement_preserves_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "shared-dialect.sqlite"
    original_url = f"sqlite:///{database_path}?timeout=5"
    selected_url = f"sqlite+pysqlite:///{database_path}?timeout=5"
    monkeypatch.setenv("DATABASE_URL", original_url)
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        original = core_db.init_db()
        assert database_path.is_file()
        monkeypatch.setenv("DATABASE_URL", selected_url)
        selected = core_db.init_db()
        assert selected is not original
        assert database_path.is_file()
        assert inspect(selected).has_table("users")
        with core_db.get_session_factory()() as session:
            assert session.bind is selected
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        core_db.reset_db_for_tests()


def test_uri_retirement_never_deletes_unsuffixed_decoy_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy_path = tmp_path / "ordinary.sqlite"
    actual_uri_path = Path(f"{decoy_path}?mode=rwc")
    uri_url = f"sqlite:///{decoy_path}?mode=rwc&uri=true"
    selected_path = tmp_path / "selected.sqlite"
    monkeypatch.setenv("DATABASE_URL", uri_url)
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        core_db.init_db()
        assert actual_uri_path.is_file()
        decoy_path.write_bytes(b"unrelated decoy")

        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{selected_path}?timeout=5")
        selected = core_db.init_db()
        assert decoy_path.read_bytes() == b"unrelated decoy"
        assert actual_uri_path.is_file()
        assert inspect(selected).has_table("users")
        with core_db.get_session_factory()() as session:
            assert session.bind is selected
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        core_db.reset_db_for_tests()


def test_uri_selected_generation_withholds_old_file_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_path = tmp_path / "old.sqlite"
    selected_base = tmp_path / "uri-selected.sqlite"
    selected_actual = Path(f"{selected_base}?mode=rwc")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{old_path}?timeout=5")
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        core_db.init_db()
        assert old_path.is_file()
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{selected_base}?mode=rwc&uri=true")
        selected = core_db.init_db()
        assert old_path.is_file()
        assert selected_actual.is_file()
        assert inspect(selected).has_table("users")
    finally:
        core_db.reset_db_for_tests()


def test_sqlite_cleanup_removes_distinct_retired_file_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_path = tmp_path / "old.sqlite"
    selected_path = tmp_path / "selected.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{old_path}?timeout=5")
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        core_db.init_db()
        assert old_path.is_file()
        monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{selected_path}?timeout=5")
        selected = core_db.init_db()
        assert not old_path.exists()
        assert selected_path.is_file()
        assert inspect(selected).has_table("users")
    finally:
        core_db.reset_db_for_tests()


def test_sqlite_cleanup_waits_for_inflight_candidate_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_path = tmp_path / "original.sqlite"
    original_url = f"sqlite:///{original_path}"
    interim_url = f"sqlite:///{tmp_path / 'interim.sqlite'}"
    retiring = Event()
    release_retirement = Event()
    schema_ready = Event()
    release_schema = Event()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", original_url)
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        original = core_db.init_db()
        metadata = core_db.load_canonical_orm_metadata()
        dispose = core_db._dispose_sync_engine

        class PausedMetadata:
            def create_all(self, *, bind: Engine) -> None:
                metadata.create_all(bind=bind)
                if bind.url == core_db.make_url(original_url) and bind is not original:
                    schema_ready.set()
                    assert release_schema.wait(timeout=10)

        def pause_retirement(engine: Engine, *, best_effort: bool = False) -> None:
            if engine is original:
                retiring.set()
                assert release_retirement.wait(timeout=10)
            dispose(engine, best_effort=best_effort)

        with monkeypatch.context() as racing:
            racing.setattr(core_db, "load_canonical_orm_metadata", lambda: PausedMetadata())
            racing.setattr(core_db, "_dispose_sync_engine", pause_retirement)
            racing.setenv("DATABASE_URL", interim_url)
            with ThreadPoolExecutor(max_workers=2) as workers:
                to_interim = workers.submit(core_db.init_db)
                assert retiring.wait(timeout=10)
                try:
                    racing.setenv("DATABASE_URL", original_url)
                    back_to_original = workers.submit(core_db.init_db)
                    assert schema_ready.wait(timeout=10)
                    release_retirement.set()
                    with pytest.raises(
                        RuntimeError, match="DB generation changed during initialization"
                    ):
                        to_interim.result(timeout=10)
                    assert original_path.is_file()
                finally:
                    release_retirement.set()
                    release_schema.set()
                selected = back_to_original.result(timeout=10)
        assert selected is core_db._RAW_ENGINE
        assert original_path.is_file()
        assert inspect(selected).has_table("users")
        assert core_db._inflight_sqlite_candidate_paths == {}
    finally:
        release_retirement.set()
        release_schema.set()
        core_db.reset_db_for_tests()


def test_sqlite_cleanup_removes_retired_file_for_confirmed_non_sqlite_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_path = tmp_path / "retired.sqlite"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{original_path}")
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        core_db.init_db()
        assert original_path.is_file()

        class NoConnectionMetadata:
            def create_all(self, *, bind: Engine) -> None:
                assert bind.url.get_backend_name() == "postgresql"

        with monkeypatch.context() as replacement:
            replacement.setenv("DATABASE_URL", "postgresql+psycopg://localhost/ops02")
            replacement.setattr(core_db, "load_canonical_orm_metadata", NoConnectionMetadata)
            selected = core_db.init_db()
        assert selected.url.get_backend_name() == "postgresql"
        assert not original_path.exists()
        assert core_db._inflight_sqlite_candidate_paths == {}
    finally:
        core_db.reset_db_for_tests()


def test_sqlite_cleanup_preserves_file_reselected_before_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_path = tmp_path / "selected-again.sqlite"
    first_url = f"sqlite:///{first_path}"
    second_url = f"sqlite:///{tmp_path / 'temporary.sqlite'}"
    monkeypatch.setenv("DATABASE_URL", first_url)
    monkeypatch.setenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", "1")
    core_db.reset_db_for_tests()
    try:
        first_engine = core_db.init_db()
        retirement_started = Event()
        release_retirement = Event()
        original_dispose = core_db._dispose_sync_engine

        def pause_old_disposal(engine: Engine, *, best_effort: bool = False) -> None:
            if engine is first_engine:
                retirement_started.set()
                assert release_retirement.wait(timeout=5)
            original_dispose(engine, best_effort=best_effort)

        with monkeypatch.context() as racing:
            racing.setattr(core_db, "_dispose_sync_engine", pause_old_disposal)
            racing.setenv("DATABASE_URL", second_url)
            with ThreadPoolExecutor(max_workers=1) as workers:
                future = workers.submit(core_db.init_db)
                assert retirement_started.wait(timeout=5)
                try:
                    racing.setenv("DATABASE_URL", first_url)
                    selected_again = core_db._get_raw_engine()
                finally:
                    release_retirement.set()
                with pytest.raises(
                    RuntimeError, match="DB generation changed during initialization"
                ):
                    future.result(timeout=5)

        assert selected_again is core_db._RAW_ENGINE
        assert first_path.is_file()
        assert inspect(selected_again).has_table("users")
    finally:
        core_db.reset_db_for_tests()


def test_ambient_init_discards_candidate_after_fallback_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from core import db_fallback

    primary_url = f"sqlite:///{tmp_path / 'primary.sqlite'}"
    stale_url = f"sqlite:///{tmp_path / 'stale.sqlite'}"
    fallback_url = f"sqlite:///{tmp_path / 'fallback.sqlite'}"
    schema_ready = Event()
    release_schema = Event()
    candidates: list[Engine] = []
    disposed: list[Engine] = []
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", primary_url)
        env.delenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE", raising=False)
        core_db.reset_db_for_tests()
        core_db.init_db()
        fallback_engine = create_engine(fallback_url)
        original_create = core_db._create_sync_engine

        def make_candidate(db_url: str) -> Engine:
            engine = original_create(db_url)
            candidates.append(engine)
            original_dispose = engine.dispose

            def dispose() -> None:
                disposed.append(engine)
                original_dispose()

            monkeypatch.setattr(engine, "dispose", dispose)
            return engine

        class PausedMetadata:
            def create_all(self, *, bind: Engine) -> None:
                if bind.url == core_db.make_url(stale_url):
                    schema_ready.set()
                    assert release_schema.wait(timeout=5)

        try:
            with monkeypatch.context() as racing:
                racing.setattr(core_db, "_create_sync_engine", make_candidate)
                racing.setattr(core_db, "load_canonical_orm_metadata", lambda: PausedMetadata())
                racing.setenv("DATABASE_URL", stale_url)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    future = workers.submit(core_db.init_db)
                    assert schema_ready.wait(timeout=5)
                    db_fallback._configure_session_bindings(
                        fallback_engine, False, fallback_url, "test"
                    )
                    release_schema.set()
                    selected = future.result(timeout=5)

            assert selected is fallback_engine
            assert core_db._RAW_ENGINE is fallback_engine
            with core_db.get_session_factory()() as session:
                assert session.bind is fallback_engine
            assert len(candidates) == 1
            assert disposed == candidates
        finally:
            release_schema.set()
            core_db.reset_db_for_tests()
            db_fallback.reset_fallback_state()
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
        candidates: list[Engine] = []
        disposed: list[Engine] = []

        def make_candidate(db_url: str) -> Engine:
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


@pytest.mark.parametrize("failure", ["ambient_change", "selected_schema"])
def test_losing_candidate_disposal_preserves_primary_error(
    failure: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    initial_url = f"sqlite:///{tmp_path / 'initial.sqlite'}"
    candidate_url = f"sqlite:///{tmp_path / 'candidate.sqlite'}"
    later_url = f"sqlite:///{tmp_path / 'later.sqlite'}"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", initial_url)
    core_db.reset_db_for_tests()
    try:
        initial = core_db.init_db()
        initial_factory = core_db.get_session_factory()
        original_create = core_db._create_sync_engine
        metadata = core_db.load_canonical_orm_metadata()
        candidates: list[Engine] = []
        disposal_attempts: list[Engine] = []

        def make_candidate(db_url: str) -> Engine:
            engine = original_create(db_url)
            candidates.append(engine)
            if len(candidates) == 1:

                def fail_disposal() -> None:
                    disposal_attempts.append(engine)
                    raise RuntimeError("synthetic cleanup failure")

                failing.setattr(engine, "dispose", fail_disposal)
            return engine

        class RacingMetadata:
            def create_all(self, *, bind: Engine) -> None:
                metadata.create_all(bind=bind)
                if bind is candidates[0]:
                    if failure == "ambient_change":
                        failing.setenv("DATABASE_URL", later_url)
                    else:
                        core_db._get_raw_engine()
                elif failure == "selected_schema" and bind is core_db._RAW_ENGINE:
                    raise ValueError("synthetic selected schema failure")

        with monkeypatch.context() as failing:
            failing.setenv("DATABASE_URL", candidate_url)
            failing.setattr(core_db, "_create_sync_engine", make_candidate)
            failing.setattr(core_db, "load_canonical_orm_metadata", lambda: RacingMetadata())
            with caplog.at_level(logging.ERROR):
                if failure == "ambient_change":
                    with pytest.raises(
                        RuntimeError, match="DATABASE_URL changed during database initialization"
                    ):
                        core_db.init_db()
                else:
                    with pytest.raises(ValueError, match="synthetic selected schema failure"):
                        core_db.init_db()

        assert disposal_attempts == candidates[:1]
        assert "Sync engine disposal failed: RuntimeError" in caplog.text
        assert "synthetic cleanup failure" not in caplog.text
        assert core_db._inflight_sqlite_candidate_paths == {}
        if failure == "ambient_change":
            assert core_db._RAW_ENGINE is initial
            assert core_db.get_session_factory() is initial_factory
        else:
            assert core_db._RAW_ENGINE is candidates[1]
    finally:
        core_db.reset_db_for_tests()


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
        candidates: list[Engine] = []
        disposed: list[Engine] = []

        def make_candidate(db_url: str) -> Engine:
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


def test_losing_init_rechecks_after_its_candidate_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial_url = f"sqlite:///{tmp_path / 'initial.sqlite'}"
    target_url = f"sqlite:///{tmp_path / 'target.sqlite'}"
    later_url = f"sqlite:///{tmp_path / 'later.sqlite'}"
    rendezvous = Barrier(2)
    loser_cleanup_started = Event()
    release_loser = Event()
    with monkeypatch.context() as env:
        env.setenv("DATABASE_URL", initial_url)
        core_db.reset_db_for_tests()
        core_db.init_db()
        original_create = core_db._create_sync_engine
        original_dispose = core_db._dispose_sync_engine
        loser_engine: Engine | None = None

        def make_candidate(db_url: str) -> Engine:
            candidate = original_create(db_url)
            if core_db.make_url(db_url) == core_db.make_url(target_url):
                rendezvous.wait(timeout=5)
            return candidate

        def pause_loser(engine: Engine, *, best_effort: bool = False) -> None:
            nonlocal loser_engine
            if (
                loser_engine is None
                and engine.url == core_db.make_url(target_url)
                and engine is not core_db._RAW_ENGINE
            ):
                loser_engine = engine
                loser_cleanup_started.set()
                assert release_loser.wait(timeout=5)
            original_dispose(engine, best_effort=best_effort)

        class NoopMetadata:
            def create_all(self, *, bind: Engine) -> None:
                return None

        try:
            with monkeypatch.context() as racing:
                racing.setattr(core_db, "_create_sync_engine", make_candidate)
                racing.setattr(core_db, "_dispose_sync_engine", pause_loser)
                racing.setattr(core_db, "load_canonical_orm_metadata", lambda: NoopMetadata())
                racing.setenv("DATABASE_URL", target_url)
                with ThreadPoolExecutor(max_workers=2) as workers:
                    first = workers.submit(core_db.init_db)
                    second = workers.submit(core_db.init_db)
                    assert loser_cleanup_started.wait(timeout=5)
                    completed, pending = wait(
                        (first, second), timeout=5, return_when=FIRST_COMPLETED
                    )
                    assert len(completed) == len(pending) == 1
                    winner = next(iter(completed))
                    loser = next(iter(pending))
                    assert winner.result(timeout=5).url == core_db.make_url(target_url)
                    try:
                        racing.setenv("DATABASE_URL", later_url)
                        current = core_db._get_raw_engine()
                    finally:
                        release_loser.set()
                    with pytest.raises(
                        RuntimeError, match="DB generation changed during initialization"
                    ):
                        loser.result(timeout=5)

            assert current is core_db._RAW_ENGINE
            assert current.url == core_db.make_url(later_url)
        finally:
            release_loser.set()
            core_db.reset_db_for_tests()
    core_db.init_db()


@pytest.mark.parametrize("explicit_replacement", [False, True])
def test_raw_getter_checks_selector_after_concurrent_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, explicit_replacement: bool
) -> None:
    initial_url = f"sqlite:///{tmp_path / 'initial.sqlite'}"
    first_url = f"sqlite:///{tmp_path / 'first.sqlite'}"
    second_url = f"sqlite:///{tmp_path / 'second.sqlite'}"
    entered_retirement = Event()
    release_retirement = Event()
    with monkeypatch.context() as env:
        env.setenv("DATABASE_URL", initial_url)
        core_db.reset_db_for_tests()
        original = core_db._get_raw_engine()
        dispose = core_db._dispose_sync_engine

        def paused_dispose(engine: Engine, *, best_effort: bool = False) -> None:
            if engine is original:
                entered_retirement.set()
                assert release_retirement.wait(timeout=5)
            dispose(engine, best_effort=best_effort)

        try:
            with monkeypatch.context() as racing:
                racing.setattr(core_db, "_dispose_sync_engine", paused_dispose)
                racing.setenv("DATABASE_URL", first_url)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    first = workers.submit(core_db._get_raw_engine)
                    assert entered_retirement.wait(timeout=5)
                    try:
                        if explicit_replacement:
                            second = core_db.init_db(second_url)
                        else:
                            racing.setenv("DATABASE_URL", second_url)
                            second = core_db._get_raw_engine()
                    finally:
                        release_retirement.set()
                    if explicit_replacement:
                        with pytest.raises(
                            RuntimeError, match="DB generation changed during acquisition"
                        ):
                            first.result(timeout=5)
                    else:
                        assert first.result(timeout=5) is second
            assert second is core_db._RAW_ENGINE
            with core_db.get_session_factory()() as session:
                assert session.bind is second
        finally:
            release_retirement.set()
            core_db.reset_db_for_tests()
    core_db.init_db()


def test_concurrent_explicit_init_rejects_superseded_generation(
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

        def paused_dispose(engine: Engine, *, best_effort: bool = False) -> None:
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
                with pytest.raises(
                    RuntimeError, match="DB generation changed during initialization"
                ):
                    first.result(timeout=5)

        assert second_result.url == core_db.make_url(second_url)
        assert core_db._RAW_ENGINE is second_result
        with core_db.get_session_factory()() as session:
            assert session.bind is second_result
    finally:
        core_db.reset_db_for_tests()
        core_db.init_db()


def test_ambient_init_rejects_generation_replaced_after_schema_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initial_url = f"sqlite:///{tmp_path / 'initial.sqlite'}"
    first_url = f"sqlite:///{tmp_path / 'first.sqlite'}"
    second_url = f"sqlite:///{tmp_path / 'second.sqlite'}"
    entered_retirement = Event()
    release_retirement = Event()
    with monkeypatch.context() as env:
        env.setenv("DATABASE_URL", initial_url)
        core_db.reset_db_for_tests()
        original = core_db.init_db()
        dispose = core_db._dispose_sync_engine

        def paused_dispose(engine: Engine, *, best_effort: bool = False) -> None:
            if engine is original:
                entered_retirement.set()
                assert release_retirement.wait(timeout=5)
            dispose(engine, best_effort=best_effort)

        try:
            with monkeypatch.context() as racing:
                racing.setattr(core_db, "_dispose_sync_engine", paused_dispose)
                racing.setenv("DATABASE_URL", first_url)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    first = workers.submit(core_db.init_db)
                    assert entered_retirement.wait(timeout=5)
                    try:
                        racing.setenv("DATABASE_URL", second_url)
                        second = core_db.init_db()
                    finally:
                        release_retirement.set()
                    with pytest.raises(
                        RuntimeError, match="DB generation changed during initialization"
                    ):
                        first.result(timeout=5)
            assert second is core_db._RAW_ENGINE
            with core_db.get_session_factory()() as session:
                assert session.bind is second
        finally:
            release_retirement.set()
            core_db.reset_db_for_tests()
    core_db.init_db()
