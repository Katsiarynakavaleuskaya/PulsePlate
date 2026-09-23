"""
Targeted tests for core.db_fallback DB fallback logic to reach 97% coverage.

Covers _attempt_db_fallback function branches:
- Production in-memory fallback rejection
- Production persistent fallback rejection
- Non-production fallback paths
"""

import asyncio
import os
import inspect
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, RLock, get_ident
from types import TracebackType
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class _TrackingLock:
    """Expose lock ownership to deterministic fallback race tests."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.owner: int | None = None
        self.depth = 0

    def __enter__(self) -> "_TrackingLock":
        self.lock.acquire()
        self.owner = get_ident()
        self.depth += 1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.depth -= 1
        if self.depth == 0:
            self.owner = None
        self.lock.release()

    def held_by_current(self) -> bool:
        return self.owner == get_ident()


def test_fallback_publishes_environment_and_session_generation_together(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An acquisition before fallback publication keeps the prior generation."""
    from sqlalchemy import create_engine

    from core import db
    from core import db_fallback

    entered = Event()
    release = Event()
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'primary.sqlite'}")
        db.reset_db_for_tests()
        primary = db.init_db()
        primary_factory = db.get_session_factory()
        fallback_url = f"sqlite:///{tmp_path / 'fallback.sqlite'}"
        fallback_engine = create_engine(fallback_url)
        original_sessionmaker = db.sessionmaker

        def waiting_sessionmaker(*args: object, **kwargs: object) -> sessionmaker[Session]:
            if kwargs.get("bind") is fallback_engine:
                entered.set()
                assert release.wait(timeout=5)
            return original_sessionmaker(*args, **kwargs)

        try:
            with monkeypatch.context() as active:
                active.setattr(db, "sessionmaker", waiting_sessionmaker)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    future = workers.submit(
                        db_fallback._configure_session_bindings,
                        fallback_engine,
                        False,
                        fallback_url,
                        "test",
                    )
                    assert entered.wait(timeout=5)
                    assert db.get_session_factory() is primary_factory
                    assert db._RAW_ENGINE is primary
                    assert os.environ["DATABASE_URL"] != fallback_url
                    release.set()
                    future.result(timeout=5)

            with db.get_session_factory()() as session:
                assert session.bind is fallback_engine
            assert db._RAW_ENGINE is fallback_engine
            assert os.environ["DATABASE_URL"] == fallback_url
        finally:
            release.set()
            db.reset_db_for_tests()
            db_fallback.reset_fallback_state()
    db.init_db()


def test_fallback_rejects_generation_replaced_during_retirement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A fallback publisher must not report success after a newer pair wins."""
    from sqlalchemy import create_engine

    from core import db, db_fallback

    retirement_started = Event()
    release_retirement = Event()
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'primary.sqlite'}")
        db.reset_db_for_tests()
        primary = db.init_db()
        fallback_url = f"sqlite:///{tmp_path / 'fallback.sqlite'}"
        replacement_url = f"sqlite:///{tmp_path / 'replacement.sqlite'}"
        fallback_engine = create_engine(fallback_url)
        dispose = db._dispose_sync_engine

        def pause_retirement(engine: Engine, *, best_effort: bool = False) -> None:
            if engine is primary:
                retirement_started.set()
                assert release_retirement.wait(timeout=10)
            dispose(engine, best_effort=best_effort)

        try:
            with monkeypatch.context() as racing:
                racing.setattr(db, "_dispose_sync_engine", pause_retirement)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    fallback = workers.submit(
                        db_fallback._configure_session_bindings,
                        fallback_engine,
                        False,
                        fallback_url,
                        "test",
                    )
                    assert retirement_started.wait(timeout=10)
                    try:
                        replacement = db.init_db(replacement_url)
                    finally:
                        release_retirement.set()
                    with pytest.raises(
                        RuntimeError, match="DB fallback generation changed during activation"
                    ):
                        fallback.result(timeout=10)
            assert db._RAW_ENGINE is replacement
            with db.get_session_factory()() as session:
                assert session.bind is replacement
            assert db_fallback.is_fallback_active() is False
            assert os.environ.get("DB_HEALTH_DEGRADED") is None

            # Fallback had changed the ambient URL before the explicit primary
            # selection. If that URL is selected again, readiness degrades again.
            reselected_fallback = db._get_raw_engine()
            assert reselected_fallback.url == db.make_url(fallback_url)
            assert db_fallback.is_fallback_active() is True
            assert os.environ["DB_HEALTH_DEGRADED"] == "1"
        finally:
            release_retirement.set()
            db.reset_db_for_tests()
            db_fallback.reset_fallback_state()
    db.init_db()


def test_superseded_fallback_preserves_new_fallback_markers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from sqlalchemy import create_engine

    from core import db, db_fallback

    retirement_started = Event()
    release_retirement = Event()
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'primary.sqlite'}")
        db.reset_db_for_tests()
        primary = db.init_db()
        first_url = f"sqlite:///{tmp_path / 'first-fallback.sqlite'}"
        second_url = f"sqlite:///{tmp_path / 'second-fallback.sqlite'}"
        first_engine = create_engine(first_url)
        second_engine = create_engine(second_url)
        dispose = db._dispose_sync_engine

        def pause_retirement(engine: Engine, *, best_effort: bool = False) -> None:
            if engine is primary:
                retirement_started.set()
                assert release_retirement.wait(timeout=10)
            dispose(engine, best_effort=best_effort)

        try:
            with monkeypatch.context() as racing:
                racing.setattr(db, "_dispose_sync_engine", pause_retirement)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    first = workers.submit(
                        db_fallback._configure_session_bindings,
                        first_engine,
                        False,
                        first_url,
                        "test",
                    )
                    assert retirement_started.wait(timeout=10)
                    try:
                        db_fallback._configure_session_bindings(
                            second_engine, False, second_url, "test"
                        )
                    finally:
                        release_retirement.set()
                    with pytest.raises(
                        RuntimeError, match="DB fallback generation changed during activation"
                    ):
                        first.result(timeout=10)
            assert db._RAW_ENGINE is second_engine
            with db.get_session_factory()() as session:
                assert session.bind is second_engine
            assert db_fallback.is_fallback_active() is True
            assert os.environ["DB_HEALTH_DEGRADED"] == "1"
        finally:
            release_retirement.set()
            db.reset_db_for_tests()
            db_fallback.reset_fallback_state()
    db.init_db()


def test_raw_getter_cannot_resurrect_primary_after_fallback_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The ambient URL read must participate in fallback's publication lock."""
    from sqlalchemy import create_engine

    from core import db, db_fallback

    entered = Event()
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'primary.sqlite'}")
        db.reset_db_for_tests()
        db.init_db()
        fallback_url = f"sqlite:///{tmp_path / 'fallback.sqlite'}"
        fallback_engine = create_engine(fallback_url)
        original_get_database_url = db.get_database_url
        publication_lock = _TrackingLock()

        def checked_database_url() -> str:
            assert publication_lock.held_by_current()
            return original_get_database_url()

        def acquire_after_signal() -> Engine:
            entered.set()
            return db._get_raw_engine()

        try:
            with monkeypatch.context() as tracked:
                tracked.setattr(db, "_init_lock", publication_lock)
                tracked.setattr(db, "get_database_url", checked_database_url)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    with publication_lock:
                        future = workers.submit(acquire_after_signal)
                        assert entered.wait(timeout=5)
                        db_fallback._configure_session_bindings(
                            fallback_engine, False, fallback_url, "test"
                        )
                    assert future.result(timeout=5) is fallback_engine
                    assert db._RAW_ENGINE is fallback_engine
        finally:
            db.reset_db_for_tests()
            db_fallback.reset_fallback_state()
    db.init_db()


def test_derived_async_url_cannot_publish_stale_primary_after_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Derived async selection shares fallback's sync publication boundary."""
    from sqlalchemy import create_engine

    from core import db, db_fallback

    class AsyncCandidate:
        def __init__(self, url: str) -> None:
            self.url = db.make_url(url)
            self.disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    created: list[AsyncCandidate] = []
    entered = Event()
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "test")
        env.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'primary.sqlite'}")
        env.setenv("DATABASE_USE_ASYNC", "1")
        env.delenv("DATABASE_ASYNC_URL", raising=False)
        db.reset_db_for_tests()
        db.init_db()
        fallback_url = f"sqlite:///{tmp_path / 'fallback.sqlite'}"
        fallback_engine = create_engine(fallback_url)
        publication_lock = _TrackingLock()
        original_async_url = db._get_async_database_url

        def checked_async_url() -> str | None:
            assert publication_lock.held_by_current()
            return original_async_url()

        def create_candidate(url: str, **_kwargs: object) -> AsyncCandidate:
            candidate = AsyncCandidate(url)
            created.append(candidate)
            return candidate

        def make_factory(**_kwargs: object) -> Callable[[], object]:
            return lambda: object()

        def acquire_after_signal() -> tuple[object, object] | None:
            entered.set()
            return asyncio.run(db._get_async_engine_and_factory())

        async def close_selected() -> None:
            if db._ASYNC_ENGINE is not None:
                await db._ASYNC_ENGINE.dispose()
            db._ASYNC_ENGINE = None
            db.AsyncSessionLocal = None
            db.async_engine = None

        try:
            with monkeypatch.context() as tracked:
                tracked.setattr(db, "_init_lock", publication_lock)
                tracked.setattr(db, "_get_async_database_url", checked_async_url)
                tracked.setattr(db, "create_async_engine", create_candidate)
                tracked.setattr(db, "async_sessionmaker", make_factory)
                with ThreadPoolExecutor(max_workers=1) as workers:
                    with publication_lock:
                        future = workers.submit(acquire_after_signal)
                        assert entered.wait(timeout=5)
                        db_fallback._configure_session_bindings(
                            fallback_engine, False, fallback_url, "test"
                        )
                    generation = future.result(timeout=5)

                assert generation is not None
                assert generation[0].url == db.make_url(
                    fallback_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
                )
                assert db._RAW_ENGINE is fallback_engine

                explicit_url = f"sqlite+aiosqlite:///{tmp_path / 'explicit.sqlite'}"
                tracked.setenv("DATABASE_ASYNC_URL", explicit_url)
                explicit = asyncio.run(db._get_async_engine_and_factory())
                assert explicit is not None and explicit[0].url == db.make_url(explicit_url)
                assert created[0].disposed is True
                asyncio.run(close_selected())
        finally:
            db.reset_db_for_tests()
            db_fallback.reset_fallback_state()
    db.init_db()


@pytest.mark.parametrize("dispose_fails", [False, True])
def test_fallback_schema_failure_disposes_unpublished_candidate(
    monkeypatch: pytest.MonkeyPatch,
    dispose_fails: bool,
) -> None:
    from core import db
    from core import db_fallback

    class Candidate:
        disposed = False

        def dispose(self) -> None:
            self.disposed = True
            if dispose_fails:
                raise RuntimeError("synthetic disposal failure")

    class FailingMetadata:
        def create_all(self, *, bind: object) -> None:
            raise RuntimeError("synthetic schema failure")

    candidate = Candidate()
    monkeypatch.setattr(db, "load_canonical_orm_metadata", lambda: FailingMetadata())
    monkeypatch.setattr(db_fallback, "create_engine", lambda *args, **kwargs: candidate)
    original = OSError("primary failed")
    with pytest.raises(OSError, match="primary failed") as failure:
        db_fallback._initialize_fallback_engine("sqlite:///:memory:", original)
    assert isinstance(failure.value.__cause__, RuntimeError)
    assert candidate.disposed is True


def test_fallback_factory_failure_preserves_original_error_on_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import db
    from core import db_fallback

    class Candidate:
        disposed = False

        def dispose(self) -> None:
            self.disposed = True
            raise RuntimeError("synthetic disposal failure")

    candidate = Candidate()

    def fail_sessionmaker(*args: object, **kwargs: object) -> None:
        raise ValueError("synthetic factory failure")

    monkeypatch.setattr(db, "sessionmaker", fail_sessionmaker)
    with pytest.raises(ValueError, match="synthetic factory failure"):
        db_fallback._configure_session_bindings(candidate, False, "sqlite:///:memory:", "test")
    assert candidate.disposed is True


class TestAppDBFallback97:
    """Tests for core.db_fallback DB fallback logic to achieve 97% coverage."""

    TRUTHY: set[str] = {"1", "true", "yes", "on"}

    @pytest.fixture(autouse=True)
    def _reset_fallback_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reset fallback state and ENV before each test to avoid cross-test leakage."""
        import core.db_fallback as fallback_mod

        fallback_mod.reset_fallback_state()
        for key in ("DB_HEALTH_DEGRADED", "DB_FALLBACK_URL", "DATABASE_URL"):
            monkeypatch.delenv(key, raising=False)

    def test_loader_diagnostics_cover_empty_mapper_registry_in_process(self) -> None:
        import core.db as db

        registry_type = type(db.Base.registry)
        with patch.object(
            registry_type,
            "mappers",
            new_callable=PropertyMock,
            return_value=frozenset(),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                db.load_canonical_orm_metadata()

        message = str(exc_info.value)
        assert message.startswith("Canonical ORM registry mismatch: missing_classes=[")
        assert "mapper_count=0" in message
        assert "extra_classes=[]" in message
        assert "missing_tables=[]" in message
        assert "extra_tables=[]" in message
        assert "core.models.User" in message
        assert "app.models.fitchef_support_outcomes.FitChefSupportOutcomeEvent" in message

    def test_create_tables_uses_loaded_metadata_and_current_engine(self) -> None:
        import core.db as db

        metadata = Mock()
        engine = object()
        with (
            patch.object(db, "load_canonical_orm_metadata", return_value=metadata) as load_metadata,
            patch.object(db, "_get_raw_engine", return_value=engine) as get_raw_engine,
        ):
            db.create_tables()

        load_metadata.assert_called_once_with()
        get_raw_engine.assert_called_once_with()
        metadata.create_all.assert_called_once_with(bind=engine)

    def test_attempt_db_fallback_production_inmemory_rejected(self) -> None:
        """Production environment rejects in-memory DB fallback."""
        from core.db_fallback import _attempt_db_fallback

        # Simulate production environment with in-memory fallback
        with patch.dict(os.environ, {"DB_FALLBACK_URL": "sqlite:///:memory:"}):
            mock_err = Exception("Primary DB failed")

            with pytest.raises(Exception, match="Primary DB failed"):
                _attempt_db_fallback(
                    env_name="production",
                    is_production=True,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )

    def test_public_attempt_db_fallback_owns_fixed_truthy_policy(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import core.db_fallback as fallback_mod

        captured: list[tuple[str | None, bool, Exception, set[str]]] = []
        error = OSError("primary failed")
        monkeypatch.setattr(
            fallback_mod,
            "_attempt_db_fallback",
            lambda env, production, db_err, truthy: captured.append(
                (env, production, db_err, truthy)
            ),
        )

        fallback_mod.attempt_db_fallback("local", False, error)

        assert captured == [("local", False, error, {"1", "true", "yes", "on"})]
        assert list(inspect.signature(fallback_mod.attempt_db_fallback).parameters) == [
            "env_name",
            "is_production",
            "db_err",
        ]

    def test_attempt_db_fallback_production_inmemory_rejected_logs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover db_fallback lines 81/87: production in-memory branch logs and raises."""
        from core.db_fallback import _attempt_db_fallback

        with patch.dict(os.environ, {"DB_FALLBACK_URL": "sqlite:///:memory:"}):
            mock_err = Exception("Primary DB failed")
            with pytest.raises(Exception, match="Primary DB failed"):
                _attempt_db_fallback(
                    env_name="production",
                    is_production=True,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )
        assert "in-memory" in caplog.text or "CRITICAL" in caplog.text

    def test_attempt_db_fallback_production_no_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Production rejects persistent SQLite fallback without legacy override."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./fallback.db")
        # Ensure the legacy override is not set.
        monkeypatch.delenv("ALLOW_DB_PERSISTENT_FALLBACK", raising=False)

        mock_err = Exception("Primary DB failed")

        with pytest.raises(Exception, match="Primary DB failed"):
            _attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

    def test_attempt_db_fallback_production_persistent_rejected_even_with_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Production-like env rejects persistent SQLite even with legacy override."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./prod_fallback.db")
        monkeypatch.setenv("ALLOW_DB_PERSISTENT_FALLBACK", "1")

        mock_err = Exception("Primary DB failed")

        with patch("core.db_fallback.create_engine") as mock_create_engine:
            with pytest.raises(Exception, match="Primary DB failed"):
                _attempt_db_fallback(
                    env_name="production",
                    is_production=True,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )

            mock_create_engine.assert_not_called()

    def test_attempt_db_fallback_production_persistent_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Production-like persistent SQLite path logs fail-closed guidance."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///./prod_fallback.db")
        monkeypatch.setenv("ALLOW_DB_PERSISTENT_FALLBACK", "1")
        mock_err = Exception("Primary DB failed")

        with pytest.raises(Exception, match="Primary DB failed"):
            _attempt_db_fallback(
                env_name="production",
                is_production=True,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )
        assert "not an accepted production or staging baseline" in caplog.text

    def test_attempt_db_fallback_nonproduction_inmemory_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-production environment allows in-memory fallback."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.delenv("ALLOW_DB_INMEMORY_FALLBACK", raising=False)

        mock_err = OSError("Primary DB failed")

        with (
            patch("core.db_fallback.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            # Should not raise
            _attempt_db_fallback(
                env_name="local",
                is_production=False,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

            mock_create_engine.assert_called_once()

    def test_attempt_db_fallback_nonproduction_explicit_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-production with explicit ALLOW_DB_INMEMORY_FALLBACK=1."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.setenv("ALLOW_DB_INMEMORY_FALLBACK", "true")

        mock_err = Exception("Generic DB error")

        with (
            patch("core.db_fallback.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            _attempt_db_fallback(
                env_name="dev",
                is_production=False,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

            mock_create_engine.assert_called_once()

    def test_attempt_db_fallback_nonproduction_no_override_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-production without override and non-OSError should re-raise original error."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.delenv("ALLOW_DB_INMEMORY_FALLBACK", raising=False)
        mock_err = Exception("Primary DB failed")

        with pytest.raises(Exception, match="Primary DB failed"):
            _attempt_db_fallback(
                env_name="dev",
                is_production=False,
                db_err=mock_err,
                truthy=self.TRUTHY,
            )

    def test_configure_session_bindings_production_keeps_database_url_for_compatibility(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Coverage branch for _configure_session_bindings in production path (line 169-171)."""
        from core import db as core_db
        from core.db_fallback import _configure_session_bindings, reset_fallback_state
        from sqlalchemy import create_engine

        prev_session = core_db.SessionLocal
        prev_raw = core_db._RAW_ENGINE
        prev_engine = core_db.engine
        prev_db_health = os.environ.get("DB_HEALTH_DEGRADED")
        prev_fb_url = os.environ.get("DB_FALLBACK_URL")

        engine = create_engine("sqlite:///:memory:")
        monkeypatch.setenv("DATABASE_URL", "postgresql://canonical-db:5432/pulseplate")

        try:
            _configure_session_bindings(
                engine=engine,
                is_production=True,
                fallback_url="sqlite:///./prod-fallback.db",
                env_name="production",
            )

            assert core_db.SessionLocal is not None
            assert os.environ["DB_FALLBACK_URL"] == "sqlite:///./prod-fallback.db"
            assert os.environ["DATABASE_URL"] == "postgresql://canonical-db:5432/pulseplate"
        finally:
            core_db.SessionLocal = prev_session
            core_db._RAW_ENGINE = prev_raw
            core_db.engine = prev_engine
            reset_fallback_state()
            if prev_db_health is None:
                os.environ.pop("DB_HEALTH_DEGRADED", None)
            else:
                os.environ["DB_HEALTH_DEGRADED"] = prev_db_health
            if prev_fb_url is None:
                os.environ.pop("DB_FALLBACK_URL", None)
            else:
                os.environ["DB_FALLBACK_URL"] = prev_fb_url

    def test_fallback_state_helpers(self) -> None:
        """Cover fallback state helpers: set/clear/reset/is."""
        import core.db_fallback as fallback_mod

        fallback_mod.clear_fallback_active()
        assert fallback_mod.is_fallback_active() is False

        fallback_mod.set_fallback_active()
        assert fallback_mod.is_fallback_active() is True

        fallback_mod.reset_fallback_state()
        assert fallback_mod.is_fallback_active() is False

    @pytest.mark.parametrize(
        ("database_url", "expected"),
        [
            ("", "<empty-db-url>"),
            ("sqlite:///./fallback.db", "sqlite:///<redacted>"),
            (
                "postgresql+psycopg://db.example.invalid:5432/pulseplate",
                "<redacted-db-url>",
            ),
        ],
    )
    def test_redact_database_url_masks_non_memory_values(
        self, database_url: str, expected: str
    ) -> None:
        """Helper must redact empty, file SQLite, and external DSNs consistently."""
        from core.db_fallback import _redact_database_url

        assert _redact_database_url(database_url) == expected

    def test_attempt_db_fallback_fallback_init_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fallback DB initialization failure re-raises original error."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        mock_err = OSError("Primary DB failed")

        with patch("core.db_fallback.create_engine", side_effect=Exception("Fallback failed")):
            # Should raise original error when fallback fails
            with pytest.raises(OSError, match="Primary DB failed"):
                _attempt_db_fallback(
                    env_name="local",
                    is_production=False,
                    db_err=mock_err,
                    truthy=self.TRUTHY,
                )

    def test_check_production_constraints_inmemory_raises(self) -> None:
        """Production constraints fail closed for in-memory fallback."""
        from core.db_fallback import _check_production_constraints

        db_err = ValueError("test")
        with pytest.raises(ValueError, match="test"):
            _check_production_constraints(
                env_name="prod",
                fallback_url="sqlite:///:memory:",
                truthy={"1", "yes"},
                db_err=db_err,
            )

    def test_validate_fallback_url_rejects_production_inmemory(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Production validation rejects direct in-memory fallback URLs."""
        from core.db_fallback import _validate_fallback_url

        db_err = RuntimeError("primary unavailable")
        with pytest.raises(RuntimeError, match="primary unavailable"):
            _validate_fallback_url(
                env_name="production",
                is_production=True,
                fallback_url="sqlite:///:memory:",
                db_err=db_err,
            )

        assert "In-memory database fallback is not allowed" in caplog.text

    def test_check_production_constraints_persistent_logs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Production constraints reject persistent SQLite fallback too."""
        from core.db_fallback import _check_production_constraints

        with pytest.raises(Exception, match="x"):
            _check_production_constraints(
                env_name="production",
                fallback_url="sqlite:///./fallback.db",
                truthy=self.TRUTHY,
                db_err=Exception("x"),
            )
        assert "canonical Postgres DATABASE_URL" in caplog.text

    def test_configure_session_bindings_sessionlocal_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover _configure_session_bindings else branch (SessionLocal None, line 147)."""
        from core import db as core_db
        from core.db_fallback import _configure_session_bindings
        from sqlalchemy import create_engine

        engine = create_engine("sqlite:///:memory:")
        orig = getattr(core_db, "SessionLocal", None)
        try:
            monkeypatch.setattr(core_db, "SessionLocal", None)
            _configure_session_bindings(
                engine=engine,
                is_production=False,
                fallback_url="sqlite:///:memory:",
                env_name="test",
            )
            assert core_db.SessionLocal is not None
        finally:
            monkeypatch.setattr(core_db, "SessionLocal", orig, raising=False)

    def test_configure_session_bindings_configure_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover _configure_session_bindings except branch (lines 147, 150-151)."""
        from core import db as core_db
        from core.db_fallback import _configure_session_bindings
        from sqlalchemy import create_engine

        engine = create_engine("sqlite:///:memory:")
        mock_sl = MagicMock()
        mock_sl.configure.side_effect = RuntimeError("configure failed")
        orig = getattr(core_db, "SessionLocal", None)
        try:
            monkeypatch.setattr(core_db, "SessionLocal", mock_sl)
            _configure_session_bindings(
                engine=engine,
                is_production=False,
                fallback_url="sqlite:///:memory:",
                env_name="test",
            )
            assert core_db.SessionLocal is not None
        finally:
            monkeypatch.setattr(core_db, "SessionLocal", orig, raising=False)

    def test_attempt_db_fallback_via_configure_session_bindings_except(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Cover db_fallback lines 147, 150-151 via _attempt_db_fallback (SessionLocal.configure raises)."""
        from core import db as core_db
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        mock_sl = MagicMock()
        mock_sl.configure.side_effect = RuntimeError("configure failed")
        orig_sl = getattr(core_db, "SessionLocal", None)
        try:
            monkeypatch.setattr(core_db, "SessionLocal", mock_sl)
            with (
                patch("core.db_fallback.create_engine") as mock_create_engine,
                patch("core.models.Base"),
            ):
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine
                _attempt_db_fallback(
                    env_name="local",
                    is_production=False,
                    db_err=OSError("Primary DB failed"),
                    truthy=self.TRUTHY,
                )
            assert core_db.SessionLocal is not None
        finally:
            monkeypatch.setattr(core_db, "SessionLocal", orig_sl, raising=False)

    def test_attempt_db_fallback_nonproduction_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover non-production logger.warning (line 230) via explicit override."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.setenv("ALLOW_DB_INMEMORY_FALLBACK", "1")
        with (
            patch("core.db_fallback.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_create_engine.return_value = MagicMock()
            _attempt_db_fallback(
                env_name="dev",
                is_production=False,
                db_err=Exception("Generic"),
                truthy=self.TRUTHY,
            )
        assert "attempting fallback SQLite" in caplog.text

    def test_attempt_db_fallback_nonproduction_oserror_logs(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cover db_fallback line 230: non-production OSError path (fallback_exception) logs."""
        from core.db_fallback import _attempt_db_fallback

        monkeypatch.setenv("DB_FALLBACK_URL", "sqlite:///:memory:")
        monkeypatch.delenv("ALLOW_DB_INMEMORY_FALLBACK", raising=False)
        with (
            patch("core.db_fallback.create_engine") as mock_create_engine,
            patch("core.models.Base"),
            patch("core.db.SessionLocal"),
        ):
            mock_create_engine.return_value = MagicMock()
            _attempt_db_fallback(
                env_name="local",
                is_production=False,
                db_err=OSError("Primary DB failed"),
                truthy=self.TRUTHY,
            )
        assert "attempting fallback SQLite" in caplog.text
        assert "OSError" in caplog.text
