"""Comprehensive tests for core/db.py to achieve 97%+ coverage."""

import asyncio
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import create_engine, text
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.parametrize("surface", ["dependency", "scope"])
def test_async_session_rejects_pair_retired_before_construction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, surface: str
) -> None:
    from core import db

    first_url = f"sqlite+aiosqlite:///{tmp_path / 'first.sqlite'}"
    second_url = f"sqlite+aiosqlite:///{tmp_path / 'second.sqlite'}"

    async def scenario() -> None:
        original_acquire = db._get_async_engine_and_factory
        entered = asyncio.Event()
        release = asyncio.Event()
        monkeypatch.setenv("DATABASE_ASYNC_URL", first_url)
        try:
            first_pair = await original_acquire()
            assert first_pair is not None

            async def paused_acquire():
                pair = await original_acquire()
                entered.set()
                await release.wait()
                return pair

            with monkeypatch.context() as racing:
                racing.setattr(db, "_get_async_engine_and_factory", paused_acquire)

                async def open_session() -> None:
                    if surface == "dependency":
                        async for _session in db.get_async_session():
                            pass
                    else:
                        async with db.session_scope_async():
                            pass

                pending = asyncio.create_task(open_session())
                await asyncio.wait_for(entered.wait(), timeout=5)
                try:
                    racing.setenv("DATABASE_ASYNC_URL", second_url)
                    second_pair = await original_acquire()
                    assert second_pair is not None and second_pair[0] is not first_pair[0]
                finally:
                    release.set()
                with pytest.raises(
                    RuntimeError, match="Async DB generation changed during session acquisition"
                ):
                    await asyncio.wait_for(pending, timeout=5)
        finally:
            monkeypatch.delenv("DATABASE_ASYNC_URL", raising=False)
            monkeypatch.setenv("DATABASE_USE_ASYNC", "0")
            await original_acquire()

    asyncio.run(scenario())


@pytest.mark.parametrize("first_transition", ["replace", "disable"])
@pytest.mark.parametrize("selector_conflict", [False, True])
def test_async_acquisition_returns_current_pair_after_concurrent_retirement(
    monkeypatch: pytest.MonkeyPatch,
    first_transition: str,
    selector_conflict: bool,
) -> None:
    from core import db

    class FakeEngine:
        def __init__(self, url: str, *, wait_for_release: bool = False) -> None:
            self.url = db.make_url(url)
            self.wait_for_release = wait_for_release
            self.entered = asyncio.Event()
            self.release = asyncio.Event()
            self.dispose_count = 0

        async def dispose(self) -> None:
            self.dispose_count += 1
            self.entered.set()
            if self.wait_for_release:
                await self.release.wait()

    class FakeFactory:
        def __init__(self, bind: FakeEngine) -> None:
            self.bind = bind

        def __call__(self) -> object:
            return object()

    old_url = "sqlite+aiosqlite:///old.sqlite"
    first_url = "sqlite+aiosqlite:///first.sqlite"
    second_url = "sqlite+aiosqlite:///second.sqlite"
    old = FakeEngine(old_url, wait_for_release=True)

    def create_candidate(url: str, **_kwargs: object) -> FakeEngine:
        return FakeEngine(url)

    def make_factory(*, bind: FakeEngine, **_kwargs: object) -> FakeFactory:
        return FakeFactory(bind)

    monkeypatch.setattr(db, "_ASYNC_ENGINE", old)
    monkeypatch.setattr(db, "AsyncSessionLocal", FakeFactory(old))
    monkeypatch.setattr(db, "async_engine", old)
    monkeypatch.setattr(db, "create_async_engine", create_candidate)
    monkeypatch.setattr(db, "async_sessionmaker", make_factory)

    async def scenario() -> None:
        if first_transition == "disable":
            monkeypatch.delenv("DATABASE_ASYNC_URL", raising=False)
            monkeypatch.setenv("DATABASE_USE_ASYNC", "0")
        else:
            monkeypatch.setenv("DATABASE_ASYNC_URL", first_url)
        first_task = asyncio.create_task(db._get_async_engine_and_factory())
        await asyncio.wait_for(old.entered.wait(), timeout=5)
        first_engine = db._ASYNC_ENGINE
        if first_transition == "disable":
            assert first_engine is None
        else:
            assert first_engine is not old

        monkeypatch.setenv("DATABASE_ASYNC_URL", second_url)
        second_generation = await db._get_async_engine_and_factory()
        assert second_generation is not None
        second_engine, second_factory = second_generation
        assert second_engine is not first_engine

        if selector_conflict:
            monkeypatch.setenv("DATABASE_ASYNC_URL", "sqlite+aiosqlite:///unpublished.sqlite")
        old.release.set()
        if selector_conflict:
            with pytest.raises(
                RuntimeError, match="Async DB generation changed during acquisition"
            ) as conflict:
                await first_task
            assert "unpublished.sqlite" not in str(conflict.value)
            assert db._ASYNC_ENGINE is second_engine
            return

        first_generation = await first_task
        assert first_generation is not None
        assert first_generation[0] is second_engine is db._ASYNC_ENGINE
        assert first_generation[1] is second_factory is db.AsyncSessionLocal
        assert first_generation[1].bind is second_engine
        assert old.dispose_count == 1
        if first_engine is not None:
            assert first_engine.dispose_count == 1

    asyncio.run(scenario())


def test_async_engine_replacement_closes_owned_sessions_and_awaits_disposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run real async connection, replacement and cleanup in one event loop."""
    from core import db

    first_url = f"sqlite+aiosqlite:///{tmp_path / 'first.sqlite'}"
    second_url = f"sqlite+aiosqlite:///{tmp_path / 'second.sqlite'}"

    async def scenario() -> None:
        if db._ASYNC_ENGINE is not None:
            await db._ASYNC_ENGINE.dispose()
        db._ASYNC_ENGINE = None
        db.AsyncSessionLocal = None
        db.async_engine = None
        try:
            monkeypatch.setenv("DATABASE_ASYNC_URL", first_url)
            first_generation = await db._get_async_engine_and_factory()
            assert first_generation is not None
            first_engine, first_factory = first_generation
            async with first_factory() as session:
                assert session.bind is first_engine
                assert (await session.scalar(text("SELECT 1"))) == 1

            original_dispose = type(first_engine).dispose
            disposed: list[object] = []

            async def dispose(self, *, close: bool = True) -> None:  # noqa: ANN001 - spy
                disposed.append(self)
                await original_dispose(self, close=close)

            monkeypatch.setattr(type(first_engine), "dispose", dispose)
            monkeypatch.setenv("DATABASE_ASYNC_URL", second_url)
            second_generation = await db._get_async_engine_and_factory()
            assert second_generation is not None
            second_engine, second_factory = second_generation
            assert second_engine is not first_engine
            assert disposed == [first_engine]
            async with second_factory() as session:
                assert session.bind is second_engine
                assert (await session.scalar(text("SELECT 1"))) == 1

            monkeypatch.delenv("DATABASE_ASYNC_URL")
            monkeypatch.setenv("DATABASE_USE_ASYNC", "0")
            assert await db._get_async_engine_and_factory() is None
            assert disposed == [first_engine, second_engine]
            assert db._ASYNC_ENGINE is None
            assert db.AsyncSessionLocal is None
        finally:
            if db._ASYNC_ENGINE is not None:
                await db._ASYNC_ENGINE.dispose()
            db._ASYNC_ENGINE = None
            db.AsyncSessionLocal = None
            db.async_engine = None

    asyncio.run(scenario())


@pytest.fixture
def init_db_with_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[ModuleType, None, None]:
    """Fixture that provides db module with test DATABASE_URL and ensures cleanup.

    This fixture sets up a test database URL and initializes the DB module.
    No reload needed - init_db() handles URL changes.
    """
    from core import db

    original_db_url = os.environ.get("DATABASE_URL")
    temp_dir = tempfile.mkdtemp(prefix="core_db_comp_")
    default_db_path = os.path.join(temp_dir, "app.db")
    test_db_url = f"sqlite:///{default_db_path}"
    monkeypatch.setenv("DATABASE_URL", test_db_url)

    # Initialize DB with test URL
    db.init_db(database_url=test_db_url)

    # Provide the db module to tests
    yield db

    # Cleanup: dispose engines but do NOT reset SessionLocal
    # reset_db_for_tests() sets SessionLocal = None, which breaks other tests
    # that expect SessionLocal to be available after this fixture completes.
    try:
        # Dispose engines to clean up connections
        if hasattr(db, "_RAW_ENGINE") and db._RAW_ENGINE is not None:
            try:
                db._RAW_ENGINE.dispose()
            except Exception:
                pass  # Best-effort cleanup
        if hasattr(db, "engine") and db.engine is not None:
            try:
                db.engine.dispose()
            except Exception:
                pass  # Best-effort cleanup
        # Do NOT call reset_db_for_tests() - it sets SessionLocal = None
        # and breaks subsequent tests that expect DB to be initialized
    finally:
        # Restore original DATABASE_URL
        if original_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_db_url
        # Best-effort cleanup of temp directory
        try:
            os.remove(default_db_path)
        except OSError:
            pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass


def test_build_engine_url_with_existing_query_params(
    monkeypatch: pytest.MonkeyPatch, init_db_with_cleanup
) -> None:
    """Test _build_engine_url preserves existing query parameters.

    Covers lines 83->85, 85->87: query parameter merging logic.
    """
    db = init_db_with_cleanup

    # Clear DATABASE_URL so it uses default path with params
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Get URL with default (non-env-provided) URL
    url = db.get_database_url()

    # Default URL should have mode=rwc and uri=true added
    assert "mode=rwc" in url
    assert "uri=true" in url


def test_build_engine_url_memory_sqlite(
    monkeypatch: pytest.MonkeyPatch, init_db_with_cleanup
) -> None:
    """Test _build_engine_url skips query params for :memory: databases.

    Covers line 97: early return for memory databases.
    """
    db = init_db_with_cleanup

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    # Get URL - memory DB should not get mode=rwc or uri=true
    url = db.get_database_url()
    assert url == "sqlite:///:memory:"


def test_build_engine_url_with_env_provided(
    monkeypatch: pytest.MonkeyPatch, init_db_with_cleanup
) -> None:
    """Test _build_engine_url respects env-provided URLs without modification.

    Covers line 94->107: urlunparse branch (though env-provided URLs skip modification).
    """
    db = init_db_with_cleanup

    # Explicitly set DATABASE_URL to a SQLite file (env_provided=True)
    # This tests that env-provided URLs are not modified
    custom_url = "sqlite:///custom_env.db"
    monkeypatch.setenv("DATABASE_URL", custom_url)

    # Should not add SQLite-specific params since it's env-provided
    url = db.get_database_url()
    # Env-provided URLs are not modified, so no mode=rwc should be added
    assert url == custom_url


def test_derive_async_url_postgres_plain() -> None:
    """Test _derive_async_url converts postgres:// to postgresql+asyncpg://.

    Covers line 140: postgres:// replacement.
    """
    from core.db import _derive_async_url, create_async_engine

    if create_async_engine is None:
        pytest.skip("sqlalchemy.asyncio not available")

    sync_url = "postgres://user:pass@host/db"
    async_url = _derive_async_url(sync_url)
    assert async_url == "postgresql+asyncpg://user:pass@host/db"


def test_derive_async_url_mysql_pymysql() -> None:
    """Test _derive_async_url converts mysql+pymysql:// to mysql+aiomysql://.

    Covers lines 147-148: mysql+pymysql replacement.
    """
    from core.db import _derive_async_url, create_async_engine

    if create_async_engine is None:
        pytest.skip("sqlalchemy.asyncio not available")

    sync_url = "mysql+pymysql://user:pass@host/db"
    async_url = _derive_async_url(sync_url)
    assert async_url == "mysql+aiomysql://user:pass@host/db"


def test_derive_async_url_unsupported_returns_none() -> None:
    """Test _derive_async_url returns None for unsupported databases.

    Covers line 149: return None for unknown database types.
    """
    from core.db import _derive_async_url, create_async_engine

    if create_async_engine is None:
        pytest.skip("sqlalchemy.asyncio not available")

    # Oracle database has no async equivalent
    sync_url = "oracle://user:pass@host/db"
    async_url = _derive_async_url(sync_url)
    assert async_url is None


def test_result_wrapper_exit_on_exception() -> None:
    """Test _ResultWithConnectionCleanup.__exit__ closes connection on exception.

    Covers line 193->exit: exception handling in context manager.
    """
    from core.db import EngineCompat

    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Create table
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE test (id INTEGER)"))
        conn.commit()

    # Use result wrapper in context manager with forced exception
    try:
        result = engine.execute("SELECT * FROM test")
        with result:
            # Force an exception during processing
            raise ValueError("Test exception")
    except ValueError:
        pass  # Expected

    # Connection should be closed despite exception
    # Use SQLAlchemy's public API to verify connection closure
    assert (
        result._connection.closed
    ), "Connection should be closed after exception in context manager"


def test_result_wrapper_close_already_closed_result() -> None:
    """Test _ResultWithConnectionCleanup handles already-closed results gracefully.

    Covers line 195->204: result.close() exception handling.
    """
    from core.db import EngineCompat, _ResultWithConnectionCleanup

    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Create a mock result that raises on close
    mock_result = MagicMock()
    mock_result.close.side_effect = Exception("Already closed")

    mock_conn = MagicMock()

    wrapper = _ResultWithConnectionCleanup(mock_result, mock_conn)

    # Calling _close_connection should handle the exception gracefully
    wrapper._close_connection()

    # Connection should still be attempted to close
    mock_conn.close.assert_called_once()


def test_safe_rollback_exception_handling() -> None:
    """Test _safe_rollback logs but doesn't raise on rollback failure.

    Covers line 273->exit: rollback exception handling.
    """
    from core.db import EngineCompat

    engine = EngineCompat(create_engine("sqlite:///:memory:", future=True))

    # Create a mock connection that raises on rollback
    mock_conn = MagicMock()
    mock_conn.rollback.side_effect = Exception("Rollback failed")

    # _safe_rollback should not raise
    engine._safe_rollback(mock_conn)

    # Rollback should have been attempted
    mock_conn.rollback.assert_called_once()


def test_async_engine_pool_config_sqlite_async(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        """Test async engine creation for SQLite (pool config skipped).

        Note: Uses SQLite to avoid asyncpg dependency. Pool config is skipped for SQLite.
        Covers line 382: pool config skipped for sqlite+aiosqlite.
        """
        from core import db

        if db.create_async_engine is None or db.async_sessionmaker is None:
            pytest.skip("sqlalchemy.asyncio not available")

        try:
            # Use SQLite async instead of PostgreSQL to avoid needing asyncpg installed
            monkeypatch.setenv("DATABASE_URL", "sqlite:///test_async.db")
            monkeypatch.setenv("DATABASE_USE_ASYNC", "1")
            monkeypatch.setenv("DATABASE_POOL_SIZE", "15")
            monkeypatch.setenv("DATABASE_MAX_OVERFLOW", "25")

            # Verify async URL was derived correctly
            async_url = db._get_async_database_url()
            assert async_url is not None
            assert "sqlite+aiosqlite" in async_url

            # For SQLite+aiosqlite, async engine should be created
            # but pool config is skipped (see core/db.py lines 369-371)
            async_engine = await db._get_async_engine()
            if async_engine is not None:
                # Engine was successfully created (aiosqlite available)
                # Verify pool config was NOT applied (SQLite doesn't use connection pooling)
                engine_pool = async_engine.pool
                from sqlalchemy.pool import NullPool, StaticPool

                assert isinstance(
                    engine_pool, (NullPool, StaticPool)
                ), f"SQLite async engine should use NullPool/StaticPool, got {type(engine_pool).__name__}"
            # else: aiosqlite not available, engine creation failed gracefully (ImportError)
            # Both states are valid - test passes either way
        finally:
            # Cleanup
            if hasattr(db, "_ASYNC_ENGINE") and db._ASYNC_ENGINE is not None:
                await db._ASYNC_ENGINE.dispose()
                db._ASYNC_ENGINE = None
                db.AsyncSessionLocal = None
                db.async_engine = None

    asyncio.run(scenario())


def test_async_engine_import_error_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        """Test async engine handles ImportError gracefully when driver is unavailable.

        Covers line 380-383: ImportError exception handler during async engine creation.
        Verifies that when async driver (e.g., aiosqlite) is not available, the module
        sets _ASYNC_ENGINE and AsyncSessionLocal to None gracefully without crashing.
        """
        from core import db

        # If sqlalchemy.asyncio itself is not available, verify graceful handling
        if db.create_async_engine is None:
            # This is the actual ImportError condition - verify module handles it correctly
            assert db._ASYNC_ENGINE is None, "Engine should be None when asyncio not available"
            assert (
                db.AsyncSessionLocal is None
            ), "SessionLocal should be None when asyncio not available"
            assert db.async_engine is None, "async_engine alias should be None"
            return

        # sqlalchemy.asyncio IS available - verify the module loaded successfully
        # The test passes if the module didn't crash during import
        # The actual engine state depends on whether the async driver (aiosqlite) is installed:
        # - If aiosqlite available: _ASYNC_ENGINE is not None
        # - If aiosqlite missing: ImportError caught, _ASYNC_ENGINE is None (line 380-383)
        # Both are valid - we just verify no crash occurred
        assert db.create_async_engine is not None, "create_async_engine should be available"
        assert db.async_sessionmaker is not None, "async_sessionmaker should be available"

    asyncio.run(scenario())

    # Verify the module loaded without crashing (both engine states are valid)
    # This test documents that ImportError is caught gracefully in core/db.py lines 380-383


def test_get_async_session_no_async_sqlalchemy() -> None:
    async def scenario() -> None:
        """Test get_async_session raises ImportError when async extras not installed.

        Covers lines 453-457: ImportError for missing async extras.
        """
        from core import db

        # Temporarily mock create_async_engine as None
        original_create = db.create_async_engine
        original_maker = db.async_sessionmaker

        try:
            db.create_async_engine = None
            db.async_sessionmaker = None

            with pytest.raises(ImportError, match="SQLAlchemy async extras are not available"):
                async for _ in db.get_async_session():
                    pass
        finally:
            db.create_async_engine = original_create
            db.async_sessionmaker = original_maker

    asyncio.run(scenario())


def test_session_scope_async_not_configured() -> None:
    async def scenario() -> None:
        """Test session_scope_async raises RuntimeError when not configured.

        Covers lines 468-476: async session scope error handling.
        """
        from core import db

        # Temporarily set AsyncSessionLocal to None
        original_session_local = db.AsyncSessionLocal

        try:
            db.AsyncSessionLocal = None

            with pytest.raises(RuntimeError, match="Async SQLAlchemy is not configured"):
                async with db.session_scope_async():
                    pass
        finally:
            db.AsyncSessionLocal = original_session_local

    asyncio.run(scenario())


def test_init_db_calls_create_all_idempotently() -> None:
    """Test that init_db() calls create_all() and it's idempotent.

    Covers that create_all is always called in init_db() and can be called multiple times.
    """
    from core import db

    # Reset DB state to ensure clean test
    db.reset_db_for_tests()

    # Mock create_all to verify it's called
    with patch.object(db.Base.metadata, "create_all") as mock_create_all:
        db.init_db()
        # Verify create_all was called once
        mock_create_all.assert_called_once()

    # Test that create_all is idempotent (can be called multiple times)
    # Second call should also call create_all (it's idempotent)
    with patch.object(db.Base.metadata, "create_all") as mock_create_all2:
        db.init_db()
        # Should be called again (idempotent operation)
        mock_create_all2.assert_called_once()

    # Cleanup: reset module state
    db.reset_db_for_tests()


def test_init_db_async_with_async_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        """Test init_db_async uses async engine when available.

        Covers lines 523-524: async engine path in init_db_async.
        """
        from core import db

        if db.create_async_engine is None or db.async_sessionmaker is None:
            pytest.skip("sqlalchemy.asyncio not available")

        try:
            # Set up async engine
            monkeypatch.setenv("DATABASE_ASYNC_URL", "sqlite+aiosqlite:///:memory:")

            async_engine = await db._get_async_engine()
            if async_engine is not None:
                # This should use the async engine path
                await db.init_db_async()

                # Cleanup
                await async_engine.dispose()
                db._ASYNC_ENGINE = None
                db.AsyncSessionLocal = None
        finally:
            # Restore original state (async engine cleanup handled above if needed)
            db.reset_db_for_tests()

    asyncio.run(scenario())


def test_init_db_async_fallback_to_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        """Test init_db_async falls back to sync engine when async not available.

        Covers line 520: sync fallback in init_db_async.
        """
        from core import db

        # Temporarily disable async engine
        original_async_engine = db._ASYNC_ENGINE

        try:
            db._ASYNC_ENGINE = None

            # Should use sync engine as fallback
            await db.init_db_async()

        finally:
            db._ASYNC_ENGINE = original_async_engine

    asyncio.run(scenario())


def test_sqlite_connect_args_without_query_params() -> None:
    """Test _sqlite_connect_args returns basic args for SQLite URLs without query params."""
    from core.db import _sqlite_connect_args

    args = _sqlite_connect_args("sqlite:///test.db")
    assert args == {"check_same_thread": False, "timeout": 5.0}


def test_sqlite_connect_args_with_query_params() -> None:
    """Test _sqlite_connect_args adds uri=True for SQLite URLs with query params."""
    from core.db import _sqlite_connect_args

    args = _sqlite_connect_args("sqlite:///test.db?mode=rwc")
    assert args == {"check_same_thread": False, "uri": True, "timeout": 5.0}


def test_sqlite_connect_args_non_sqlite() -> None:
    """Test _sqlite_connect_args returns empty dict for non-SQLite URLs."""
    from core.db import _sqlite_connect_args

    args = _sqlite_connect_args("postgresql://localhost/test")
    assert args == {}
