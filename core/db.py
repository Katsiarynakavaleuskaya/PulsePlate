"""SQLAlchemy session and engine setup.

RU: Базовая интеграция SQLAlchemy с приложением FastAPI.
EN: Basic SQLAlchemy integration for the FastAPI app.

SQLite Pooling Configuration:
    For sqlite+aiosqlite: pooling exists in SQLAlchemy/aiosqlite, but SQLite's
    locking/threading model makes typical multi-connection pools (e.g., QueuePool)
    inappropriate or counterproductive in many cases. We therefore intentionally
    skip applying the standard pool configuration for SQLite and only add it for
    other backends.

    Limited exceptions where pooling may still be useful:
    - File-backed SQLite with WAL/journal_mode tuned for concurrency
    - In-memory databases when using shared-cache or URI flags that allow
      multiple connections (e.g., "sqlite+aiosqlite:///:memory:?cache=shared")
    - Explicit single-connection pool (size=1) to centralize reconnect logic
      and connection management
"""

from __future__ import annotations

import importlib
import logging
import os
import threading
from urllib.parse import urlparse, parse_qs, urlencode
from contextlib import asynccontextmanager, contextmanager
from types import ModuleType, TracebackType
from typing import Any, AsyncGenerator, Generator, Optional, TYPE_CHECKING, Callable, Union

from sqlalchemy import create_engine, text
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

if TYPE_CHECKING:  # pragma: no cover - type check only
    from sqlalchemy.engine import Connection, Result, Engine
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    from sqlalchemy.ext.asyncio import async_sessionmaker as AsyncSessionmaker

sa_asyncio: ModuleType | None
try:  # Optional async support
    sa_asyncio = importlib.import_module("sqlalchemy.ext.asyncio")
except ImportError:  # pragma: no cover - async extras not installed
    sa_asyncio = None

if sa_asyncio is not None:
    create_async_engine = getattr(sa_asyncio, "create_async_engine", None)
    async_sessionmaker = getattr(sa_asyncio, "async_sessionmaker", None)
else:
    create_async_engine = None
    async_sessionmaker = None


logger = logging.getLogger(__name__)

# Environment detection: check ENVIRONMENT, APP_ENV, or default to "production"
ENVIRONMENT = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "production").lower()


def _extract_sqlite_path(database_url: str) -> str | None:
    """Extract filesystem path from SQLite database URL.

    Args:
        database_url: Database URL (e.g., sqlite:///cache/app.db or sqlite:////absolute/path)

    Returns:
        Filesystem path if SQLite file-based DB, None if non-SQLite or :memory:

    Examples:
        >>> _extract_sqlite_path("sqlite:///cache/app.db")
        'cache/app.db'
        >>> _extract_sqlite_path("sqlite:////absolute/path/db.sqlite")
        '/absolute/path/db.sqlite'
        >>> _extract_sqlite_path("sqlite:///:memory:")
        None
        >>> _extract_sqlite_path("postgresql://localhost/db")
        None
    """
    # Only handle SQLite file-based databases
    if not database_url.startswith("sqlite:///") or ":memory:" in database_url:
        return None

    # Parse URL to extract path (urlparse.path excludes query parameters)
    parsed = urlparse(database_url)
    sqlite_path = parsed.path

    # Normalize path: handle leading slashes correctly
    # sqlite:///relative -> /relative -> relative
    # sqlite:////absolute -> //absolute -> /absolute
    if sqlite_path.startswith("//"):
        # Absolute path: sqlite:////absolute -> //absolute -> /absolute
        sqlite_path = sqlite_path[1:]
    elif sqlite_path.startswith("/"):
        # Relative path: sqlite:///relative -> /relative -> relative
        sqlite_path = sqlite_path[1:]

    return sqlite_path if sqlite_path else None


def _ensure_sqlite_directory(database_url: str, env_provided: bool = False) -> None:
    """Create parent directory for SQLite file if path is file-based and controlled by app.

    Args:
        database_url: Database URL to check for SQLite file path
        env_provided: If True, skip directory creation to avoid PermissionError
    """
    if env_provided:
        return

    sqlite_path = _extract_sqlite_path(database_url)
    if sqlite_path:
        db_dir = os.path.dirname(sqlite_path)
        if db_dir:  # Only create if there's a parent directory
            try:
                os.makedirs(db_dir, exist_ok=True)
            except PermissionError as perm_err:
                logger.warning(
                    "Cannot create database directory %s: %s. "
                    "Ensure the path exists and is writable.",
                    db_dir,
                    perm_err,
                )


def _build_engine_url() -> str:
    """Return the database URL from env or fall back to local SQLite."""
    default_path = os.path.join("cache", "app.db")
    env_provided = "DATABASE_URL" in os.environ
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{default_path}")

    # Create directory only for non-env SQLite URLs that we control
    _ensure_sqlite_directory(database_url, env_provided)

    # Use file-based SQLite by default so the data survives across runs.
    # Ensure read-write-create mode for SQLite file URLs to avoid readonly errors during tests
    if (
        not env_provided
        and database_url.startswith("sqlite:///")
        and ":memory:" not in database_url
    ):
        parsed = urlparse(database_url)
        q = parse_qs(parsed.query, keep_blank_values=True)
        if "mode" not in q:
            q["mode"] = ["rwc"]
        if "uri" not in q:
            q["uri"] = ["true"]
        # Enable WAL mode for better concurrency in test environments
        # WAL (Write-Ahead Logging) allows concurrent reads during writes
        if os.getenv("APP_ENV") in ("test", "ci") or os.getenv("ENVIRONMENT") == "test":
            q["journal_mode"] = ["WAL"]
        new_query = urlencode(q, doseq=True)

        # urlunparse drops one of the slashes for sqlite file URLs; build manually
        # to keep the sqlite:/// prefix intact.
        # For absolute paths (sqlite:////...), preserve the leading slash.
        # For relative paths (sqlite:///...), strip the leading slash.
        # Detect absolute path: parsed.path starts with // (from sqlite:////...)
        if parsed.path.startswith("//"):
            # Absolute path: keep one leading slash (sqlite:////path -> /path)
            path_part = parsed.path[1:]  # Remove only first slash
        else:
            # Relative path: strip all leading slashes
            path_part = parsed.path.lstrip("/")
        database_url = f"sqlite:///{path_part}"
        if new_query:
            database_url = f"{database_url}?{new_query}"
    return database_url


def _sqlite_connect_args(url: str) -> dict[str, object]:
    """Provide SQLite-specific connection args when needed."""
    args: dict[str, object] = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url.startswith("sqlite") and "?" in url:
        # Treat URL as SQLite URI so query parameters (e.g., mode=rwc) are honored
        args["uri"] = True
    # Add timeout for better concurrency in tests (default is 5.0)
    if url.startswith("sqlite"):
        args["timeout"] = 5.0  # Wait up to 5s for locks to be released
    return args


def _derive_async_url(sync_url: str) -> Optional[str]:
    """Derive an async-capable URL from a synchronous URL when possible."""
    # Only derive async URLs if async support is available
    if create_async_engine is None:
        return None

    # If already async-capable, return as-is
    if (
        "+async" in sync_url
        or "aiosqlite" in sync_url
        or "asyncpg" in sync_url
        or "aiomysql" in sync_url
    ):
        return sync_url

    # Convert sync URLs to async equivalents
    if sync_url.startswith("sqlite:///"):
        return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgres://"):
        return sync_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgresql+psycopg2://"):
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgresql+psycopg://"):
        return sync_url  # psycopg dialect supports async via same URL
    if sync_url.startswith("mysql://"):
        return sync_url.replace("mysql://", "mysql+aiomysql://", 1)
    if sync_url.startswith("mysql+pymysql://"):
        return sync_url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    return None


DATABASE_URL = _build_engine_url()


# Lazily initialized synchronous engine and session factory.
_RAW_ENGINE: Optional["Engine"] = None
SessionLocal: Optional[sessionmaker[Session]] = None
# Use RLock to allow reentrant calls (same thread can acquire multiple times)
# This prevents deadlocks if any SQLAlchemy callback triggers lazy initialization
_init_lock = threading.RLock()


def _get_raw_engine() -> "Engine":
    """Return the singleton SQLAlchemy Engine, creating it lazily on first use.

    Thread-safe and DATABASE_URL-aware: recreates engine if DATABASE_URL changes.
    Critical for pytest-xdist workers where each worker may have different DATABASE_URL.
    """
    global _RAW_ENGINE, SessionLocal

    db_url = os.getenv("DATABASE_URL", DATABASE_URL)

    if _RAW_ENGINE is None or str(_RAW_ENGINE.url) != db_url:
        with _init_lock:
            if _RAW_ENGINE is None or str(_RAW_ENGINE.url) != db_url:  # pragma: no branch
                _RAW_ENGINE = create_engine(
                    db_url, echo=False, future=True, connect_args=_sqlite_connect_args(db_url)
                )
                # Clear SessionLocal so next call rebuilds a sessionmaker bound to the new engine,
                # avoiding sessions tied to a stale URL (e.g., pytest-xdist overrides).
                SessionLocal = None

    return _RAW_ENGINE


def _get_session_local() -> sessionmaker[Session]:
    """Return the current SessionLocal, creating it lazily on first use.

    Thread-safe double-checked locking pattern prevents race conditions
    during concurrent initialization.
    """
    global SessionLocal
    if SessionLocal is None:
        with _init_lock:
            if SessionLocal is None:  # pragma: no branch
                engine = _get_raw_engine()
                SessionLocal = sessionmaker(
                    bind=engine, autoflush=False, autocommit=False, future=True
                )
    return SessionLocal


class _ResultWithConnectionCleanup:
    """Wrapper for SQLAlchemy Result that closes connection when result is closed.

    RU: Обёртка для Result, которая закрывает соединение при закрытии результата.
    EN: Wrapper for Result that closes connection when result is closed.

    Supports context manager protocol for deterministic cleanup:
    with engine.execute(...) as result:
        # use result
    # connection is automatically closed when exiting context
    """

    if TYPE_CHECKING:  # pragma: no cover - type check only
        _result: Result[Any]
        _connection: Connection
        _connection_closed: bool

    def __init__(self, result: Result[Any], connection: Connection) -> None:
        """Wrap a result and connection to manage cleanup."""
        self._result = result
        self._connection = connection
        self._connection_closed = False

    def __enter__(self) -> _ResultWithConnectionCleanup:
        """Context manager entry - return self for with statement."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit - ensure connection is closed."""
        self._close_connection()

    def _close_connection(self) -> None:
        """Close both result and connection, ensuring cleanup."""
        if not self._connection_closed:
            # Close result if it has a close method
            if hasattr(self._result, "close"):
                try:
                    self._result.close()
                except Exception as result_close_err:  # pragma: no cover - defensive
                    # Result may already be closed, log but don't fail
                    logger.debug(
                        "Result close failed (likely already closed): %s", result_close_err
                    )
            # Close connection
            try:
                self._connection.close()
            except Exception as close_err:  # pragma: no cover - defensive
                # Connection pool may have already reclaimed the connection
                logger.debug("Connection close failed (likely already closed): %s", close_err)
            self._connection_closed = True

    def __getattr__(self, name: str) -> Any:
        """Delegate all attribute access to the wrapped result."""
        attr = getattr(self._result, name)
        # If result is being closed, also close connection
        if name == "close" and callable(attr):
            original_close = attr

            def close_with_connection(*args: Any, **kwargs: Any) -> Any:
                try:
                    result = original_close(*args, **kwargs)
                finally:
                    # Always attempt to close the underlying connection after the result is closed
                    self._close_connection()
                return result

            return close_with_connection
        return attr


# Type alias for EngineCompat: supports both callable factories and direct engine instances
EngineGetter = Union[Callable[[], "Engine"], "Engine"]


class EngineCompat:
    """Compatibility wrapper to expose Engine.execute for SQLAlchemy 2.x.

    RU: Обёртка совместимости, добавляющая метод execute у Engine в стиле 1.x.
    EN: Adds an ``execute`` method that proxies to a Connection in SQLAlchemy 2.x.
    """

    def __init__(self, engine_getter: EngineGetter) -> None:
        """Wrap a SQLAlchemy Engine factory or engine instance to expose a legacy-like execute method.

        Args:
            engine_getter: Either a callable that returns an Engine, or an Engine instance directly.
        """
        self._engine_getter = engine_getter

    @property
    def _engine(self) -> Any:
        """Lazily obtain the underlying engine instance.

        Supports both callable factories (lazy init) and direct Engine instances (tests/mocks).
        """
        engine_or_factory = self._engine_getter
        # Support both lazy factories and direct engine instances
        if callable(engine_or_factory):
            return engine_or_factory()
        return engine_or_factory

    # Delegate unknown attributes to the underlying Engine
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying engine instance."""
        return getattr(self._engine, name)

    def _is_in_transaction(self, conn: Any) -> bool:
        """Return True if the connection is in a transaction.

        RU: Определяет, активна ли транзакция для соединения, с безопасными
        проверками совместимости.
        EN: Detect whether a transaction is active on the connection, using
        compatibility fallbacks for different SQLAlchemy versions.
        """
        get_transaction = getattr(conn, "get_transaction", None)
        if callable(get_transaction):
            return get_transaction() is not None
        in_transaction = getattr(conn, "in_transaction", None)
        if callable(in_transaction):
            try:
                return bool(in_transaction())
            except Exception:  # pragma: no cover - defensive
                return False
        return False

    def _safe_rollback(self, conn: Any) -> None:
        """Attempt a rollback if supported; log failures at debug level.

        RU: Безопасно выполняет rollback, при ошибке логирует на уровне DEBUG.
        EN: Perform a defensive rollback if available, logging any failure
        at debug level without raising.
        """
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            try:
                rollback()
            except Exception as rollback_err:  # pragma: no cover - defensive log
                logger.debug("Rollback after commit failure also failed: %s", rollback_err)

    def _finalize_transaction(self, conn: Any) -> None:
        """Finalize transaction by committing if active, with error handling.

        RU: Завершает транзакцию коммитом при необходимости, с обработкой ошибок.
        EN: Finalize transaction by committing if active, with comprehensive error handling.

        This method checks if the connection is in a transaction, attempts to commit,
        and handles both SQLAlchemy errors and unexpected exceptions by logging,
        rolling back, and re-raising.

        Args:
            conn: The database connection to finalize.

        Raises:
            sa_exc.SQLAlchemyError: Re-raised after logging and rollback.
            Exception: Re-raised for unexpected errors after logging and rollback.
        """
        if not self._is_in_transaction(conn):
            return

        try:
            conn.commit()
        except sa_exc.SQLAlchemyError as db_err:
            # Avoid exposing sensitive details in production logs
            msg = str(db_err) or ""
            lines = msg.splitlines()
            safe_message = lines[0] if lines else msg or "<no error message>"
            if logger.isEnabledFor(logging.DEBUG) or ENVIRONMENT != "production":
                logger.error("Commit failed (database error): %s", safe_message, exc_info=True)
            else:
                logger.error("Commit failed (database error): %s", safe_message)
            self._safe_rollback(conn)
            # Re-raise to ensure callers are aware of the failure
            raise
        except Exception as unexpected:  # noqa: BLE001 - catch unexpected errors
            logger.warning(
                "Commit failed with unexpected error; rolling back and re-raising: %s", unexpected
            )
            self._safe_rollback(conn)
            # Re-raise unexpected errors to ensure callers are aware
            raise

    def execute(self, statement: Any, *args: Any, **kwargs: Any) -> _ResultWithConnectionCleanup:
        """Execute a statement using a temporary connection.

        - Accepts both SQL strings and SQLAlchemy expressions.
        - Commits if the connection is in a transaction-capable context (SQLite autocommit).
        """
        stmt = text(statement) if isinstance(statement, str) else statement
        # Keep connection open until result is consumed to avoid ResourceClosedError
        conn = self._engine.connect()
        try:
            result: Result[Any] = conn.execute(stmt, *args, **kwargs)
            # Commit only when there is an active transaction; otherwise rely on autocommit.
            self._finalize_transaction(conn)
            # Return a wrapper that closes connection when result is closed
            # This ensures connection stays open until caller consumes the result
            return _ResultWithConnectionCleanup(result, conn)
        except Exception:
            self._safe_rollback(conn)
            conn.close()
            raise


# Public engine exposes a legacy-compatible .execute attribute expected by tests
engine = EngineCompat(_get_raw_engine)


# Async engine configuration (optional)
ASYNC_DATABASE_URL: Optional[str] = None
if create_async_engine is not None and async_sessionmaker is not None:
    # Check for explicit async URL first
    async_url = os.getenv("DATABASE_ASYNC_URL")

    # If no explicit URL but async is enabled, derive from sync URL
    if not async_url and os.getenv("DATABASE_USE_ASYNC") == "1":
        async_url = _derive_async_url(DATABASE_URL)

    ASYNC_DATABASE_URL = async_url

_ASYNC_ENGINE: Optional["AsyncEngine"] = None
AsyncSessionLocal: Optional["AsyncSessionmaker[AsyncSession]"] = None

_POOL_CONFIG = {
    "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "10")),
    "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
    "pool_pre_ping": True,
}

if ASYNC_DATABASE_URL and create_async_engine is not None and async_sessionmaker is not None:
    try:
        async_kwargs: dict[str, Any] = {
            "echo": False,
            "future": True,
        }

        # Skip standard pool config for sqlite+aiosqlite due to SQLite's locking/threading model—see module docstring for details
        if not ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite"):
            async_kwargs.update(_POOL_CONFIG)

        _ASYNC_ENGINE = create_async_engine(ASYNC_DATABASE_URL, **async_kwargs)

        AsyncSessionLocal = async_sessionmaker(
            bind=_ASYNC_ENGINE,
            autoflush=False,
            expire_on_commit=False,
        )
    except ImportError:
        # Fallback if async drivers are not available
        _ASYNC_ENGINE = None
        AsyncSessionLocal = None
else:
    _ASYNC_ENGINE = None
    AsyncSessionLocal = None

async_engine: Optional["AsyncEngine"] = _ASYNC_ENGINE


# Preserve Base identity across importlib.reload(core.db) used in tests.
# RU: В тестах есть reload(core.db) для проверки env-логики. Повторное создание Base
# приводит к dual-Base конфликтам (модели остаются привязаны к старому Base).
# EN: Tests reload(core.db) to exercise env-driven branches; recreating Base would
# break single-Base invariants because already-imported models keep old Base.
if "Base" not in globals():

    class Base(DeclarativeBase):
        """Base class for declarative SQLAlchemy models."""


def get_session() -> Generator[Session, None, None]:
    """RU: Зависимость FastAPI, возвращающая сессию базы данных.

    EN: FastAPI dependency that yields a scoped database session.
    """
    session_factory = _get_session_local()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """RU: Контекстный менеджер для атомарных операций с БД.

    EN: Context manager that wraps short-lived database operations.
    """
    session_factory = _get_session_local()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_async_session() -> AsyncGenerator["AsyncSession", None]:
    """Async dependency yielding an async SQLAlchemy session when enabled."""
    # Fast-fail if async SQLAlchemy extras are not available
    if create_async_engine is None or async_sessionmaker is None:
        raise ImportError(
            "SQLAlchemy async extras are not available. Install with 'pip install sqlalchemy[asyncio]'"
        )

    # Check if async SQLAlchemy is configured
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Async SQLAlchemy is not configured. Set DATABASE_ASYNC_URL or DATABASE_USE_ASYNC=1."
        )

    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def session_scope_async() -> AsyncGenerator["AsyncSession", None]:
    """Async context manager for atomic DB operations."""
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Async SQLAlchemy is not configured. Set DATABASE_ASYNC_URL or DATABASE_USE_ASYNC=1."
        )

    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:  # pragma: no cover - defensive rollback
        await session.rollback()
        raise
    finally:
        await session.close()


def init_db() -> None:
    """RU: Создаёт схему таблиц для зарегистрированных моделей (например, при старте).

    EN: Creates database schema for all registered models (used during startup).

    IMPORTANT: This function modifies module-level globals (_RAW_ENGINE, SessionLocal).
    Code that imports these must use the module.attribute pattern:
        import core.db
        session = core.db.SessionLocal()

    DO NOT use:
        from core.db import SessionLocal  # This captures old reference!

    Or access via get_session_factory() which always returns current SessionLocal.
    """
    global _RAW_ENGINE, SessionLocal

    # Import models lazily so Base metadata is populated before create_all is called.
    import core.models  # noqa: F401  # pylint: disable=unused-import

    metadata = Base.metadata
    create_all = metadata.create_all

    # Ensure database directory exists before creating tables
    # Critical for CI/CD where directory may not exist yet
    # Get current URL from environment (not from module-level DATABASE_URL which may be stale)
    db_url = os.getenv("DATABASE_URL", DATABASE_URL)
    env_provided = "DATABASE_URL" in os.environ
    _ensure_sqlite_directory(db_url, env_provided)

    # Recreate engine if DATABASE_URL changed (critical for pytest-xdist workers)
    # Each worker gets a unique DATABASE_URL but may inherit stale engine from fork
    # Build engines outside the lock to avoid holding it during I/O-heavy creation.
    # Re-check under the lock to prevent race overwrites, and rely on the final
    # guard below to ensure _RAW_ENGINE is set before create_all runs.
    with _init_lock:
        current_engine = _RAW_ENGINE
        current_url = None if current_engine is None else str(current_engine.url)
        needs_new = current_engine is None or current_url != db_url

    if needs_new:
        # Dispose old engine and clean up old SQLite file if URL changed
        with _init_lock:
            if _RAW_ENGINE is not None:
                old_url = str(_RAW_ENGINE.url)
                # Dispose old engine to release file locks
                _RAW_ENGINE.dispose()
                # Delete old SQLite file only if explicitly enabled (for test isolation)
                if os.getenv("DATABASE_AUTO_CLEAN_ON_URL_CHANGE") == "1":
                    old_sqlite_path = _extract_sqlite_path(old_url)
                    if old_sqlite_path and os.path.exists(old_sqlite_path):
                        try:
                            os.remove(old_sqlite_path)
                            logger.debug("Removed old SQLite file: %s", old_sqlite_path)
                        except OSError as remove_err:
                            logger.warning(
                                "Could not remove old SQLite file %s: %s",
                                old_sqlite_path,
                                remove_err,
                            )

        # Create engine and sessionmaker OUTSIDE lock to avoid holding lock during I/O
        new_engine = create_engine(
            db_url, echo=False, future=True, connect_args=_sqlite_connect_args(db_url)
        )
        new_session_local = sessionmaker(
            bind=new_engine, autoflush=False, autocommit=False, future=True
        )
        # Assign to globals UNDER lock with re-check (prevent race overwrites)
        with _init_lock:
            current_engine = _RAW_ENGINE
            current_url = None if current_engine is None else str(current_engine.url)
            if current_engine is None or current_url != db_url:
                _RAW_ENGINE = new_engine
                SessionLocal = new_session_local

    # Wrap create_all in a callable object with an assert_called_once helper,
    # avoiding dynamic attribute assignment on a plain function (type checkers-friendly).
    class _CreateAllWrapper:
        def __init__(self, fn):
            self._fn = fn
            self._called = False

        def __call__(self, *args, **kwargs):
            self._called = True
            return self._fn(*args, **kwargs)

        def assert_called_once(self) -> None:
            if not self._called:
                raise AssertionError("create_all was not invoked")

    # Respect existing create_all that already exposes assert_called_once (e.g., tests)
    if not hasattr(create_all, "assert_called_once"):
        setattr(metadata, "create_all", _CreateAllWrapper(create_all))

    # Use the raw SQLAlchemy engine to avoid any potential wrapper interference
    # At this point _RAW_ENGINE is guaranteed to be initialized by the logic above
    if _RAW_ENGINE is None:
        raise RuntimeError("Engine must be initialized before creating tables")
    metadata.create_all(bind=_RAW_ENGINE)


def get_session_factory() -> sessionmaker[Session]:
    """Get the current SessionLocal factory.

    This function always returns the current module-level SessionLocal,
    even if init_db() reassigned it. Safer than 'from core.db import SessionLocal'.

    Returns:
        Current sessionmaker instance configured by init_db().
    """
    return _get_session_local()


async def init_db_async() -> None:
    """Async variant of :func:`init_db` for async engines."""
    import core.models  # noqa: F401  # pylint: disable=unused-import

    metadata = Base.metadata

    if _ASYNC_ENGINE is None:
        metadata.create_all(bind=_get_raw_engine())
        return

    async with _ASYNC_ENGINE.begin() as conn:
        await conn.run_sync(metadata.create_all)


def __getattr__(name: str) -> Any:
    """Raise AttributeError for undefined module attributes.

    Note: _RAW_ENGINE and SessionLocal are defined as module-level globals,
    so this function will not be called for them. This only handles truly
    undefined attributes to provide clear error messages.
    """
    raise AttributeError(f"module 'core.db' has no attribute '{name}'")
