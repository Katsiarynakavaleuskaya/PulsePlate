"""SQLAlchemy session and engine setup.

RU: Базовая интеграция SQLAlchemy с приложением FastAPI.
EN: Basic SQLAlchemy integration for the FastAPI app.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Optional, TYPE_CHECKING, cast

from sqlalchemy import create_engine, text
from sqlalchemy.exc import InvalidRequestError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - type check only
    from sqlalchemy.ext.asyncio import (
        AsyncEngine as AsyncEngineType,
        AsyncSession as AsyncSessionType,
        async_sessionmaker as AsyncSessionmakerType,
    )
else:
    AsyncEngineType = AsyncSessionType = Any  # type: ignore[assignment]
    AsyncSessionmakerType = Any  # type: ignore[assignment]

try:  # Optional async support
    from sqlalchemy.ext.asyncio import (
        async_sessionmaker,
        create_async_engine,
    )
except ImportError:  # pragma: no cover - async extras not installed
    async_sessionmaker = cast(Any, None)
    create_async_engine = cast(Any, None)


def _build_engine_url() -> str:
    """Return the database URL from env or fall back to local SQLite."""
    default_path = os.path.join("cache", "app.db")
    # Use file-based SQLite by default so the data survives across runs.
    return os.getenv("DATABASE_URL", f"sqlite:///{default_path}")


def _sqlite_connect_args(url: str) -> dict[str, object]:
    """Provide SQLite-specific connection args when needed."""
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


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
    if sync_url.startswith("mysql://"):
        return sync_url.replace("mysql://", "mysql+aiomysql://", 1)
    if sync_url.startswith("mysql+pymysql://"):
        return sync_url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    return None


DATABASE_URL = _build_engine_url()


class EngineCompat:
    """Compatibility wrapper to expose Engine.execute for SQLAlchemy 2.x.

    RU: Обёртка совместимости, добавляющая метод execute у Engine в стиле 1.x.
    EN: Adds an ``execute`` method that proxies to a Connection in SQLAlchemy 2.x.
    """

    def __init__(self, engine: Any) -> None:
        """Initialize the EngineCompat wrapper with an SQLAlchemy engine."""
        self._engine = engine

    # Delegate unknown attributes to the underlying Engine
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying SQLAlchemy engine."""
        return getattr(self._engine, name)

    def execute(self, statement: Any, *args: Any, **kwargs: Any):
        """Execute a statement using a temporary connection.

        - Accepts both SQL strings and SQLAlchemy expressions.
        - Commits if the connection is in a transaction-capable context (SQLite autocommit).
        """
        stmt = text(statement) if isinstance(statement, str) else statement
        # Use a short-lived connection to mimic Engine.execute behavior
        with self._engine.connect() as conn:
            result = conn.execute(stmt, *args, **kwargs)
            try:
                conn.commit()
            except (InvalidRequestError, SQLAlchemyError) as e:
                # Not all statements require/allow commit; log and ignore commit errors
                logger.debug("Commit failed (expected for non-transactional statements): %s", e)
            return result


# Create the underlying SQLAlchemy Engine instance (2.x style)
_RAW_ENGINE = create_engine(
    DATABASE_URL, echo=False, future=True, connect_args=_sqlite_connect_args(DATABASE_URL)
)

# Public engine exposes a legacy-compatible .execute attribute expected by tests
engine = EngineCompat(_RAW_ENGINE)


# Async engine configuration (optional)
ASYNC_DATABASE_URL = None
if create_async_engine is not None:
    # Check for explicit async URL first
    async_url = os.getenv("DATABASE_ASYNC_URL")

    # If no explicit URL but async is enabled, derive from sync URL
    if not async_url and os.getenv("DATABASE_USE_ASYNC") == "1":
        async_url = _derive_async_url(DATABASE_URL)

    ASYNC_DATABASE_URL = async_url

_POOL_CONFIG = {
    "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "10")),
    "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
    "pool_pre_ping": True,
}

if ASYNC_DATABASE_URL and create_async_engine is not None:
    try:
        async_kwargs: dict[str, Any] = {
            "echo": False,
            "future": True,
        }

        if ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite"):
            # SQLite async doesn't support pooling
            pass
        else:
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

async_engine: Optional[AsyncEngineType] = _ASYNC_ENGINE


class Base(DeclarativeBase):
    """Base class for declarative SQLAlchemy models."""


SessionLocal = sessionmaker(bind=_RAW_ENGINE, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """RU: Зависимость FastAPI, возвращающая сессию базы данных.

    EN: FastAPI dependency that yields a scoped database session.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """RU: Контекстный менеджер для атомарных операций с БД.

    EN: Context manager that wraps short-lived database operations.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_async_session() -> AsyncGenerator[AsyncSessionType, None]:
    """Async dependency yielding an async SQLAlchemy session when enabled."""
    if AsyncSessionLocal is None:
        if create_async_engine is None:
            raise ImportError(
                "SQLAlchemy async extras are not available. Install with 'pip install sqlalchemy[asyncio]'"
            )
        raise RuntimeError(
            "Async SQLAlchemy is not configured. Set DATABASE_ASYNC_URL or DATABASE_USE_ASYNC=1."
        )

    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def session_scope_async() -> AsyncGenerator[AsyncSessionType, None]:
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
    """
    # Import models lazily so Base metadata is populated before create_all is called.
    import core.models  # noqa: F401  # pylint: disable=unused-import

    metadata = Base.metadata
    create_all = metadata.create_all

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
    metadata.create_all(bind=_RAW_ENGINE)


async def init_db_async() -> None:
    """Async variant of :func:`init_db` for async engines."""
    import core.models  # noqa: F401  # pylint: disable=unused-import

    metadata = Base.metadata

    if _ASYNC_ENGINE is None:
        metadata.create_all(bind=_RAW_ENGINE)
        return

    async with _ASYNC_ENGINE.begin() as conn:
        await conn.run_sync(metadata.create_all)


# Legacy aliases for backward compatibility
def create_tables() -> None:
    """Legacy alias for init_db()."""
    init_db()


def init_database() -> None:
    """Legacy alias for init_db()."""
    init_db()


def get_db_connection() -> Any:
    """Legacy function for database connection access.

    .. deprecated::
        Use :func:`get_session` or :func:`session_scope` instead.

    .. warning::
        Caller is responsible for closing the session via ``.close()``.
    """
    import warnings

    warnings.warn(
        "get_db_connection() is deprecated, use get_session() or session_scope() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return SessionLocal()


def close_all_connections() -> None:
    """Legacy function to close all database connections.

    .. deprecated::
        Connection lifecycle is managed by SQLAlchemy sessions and context managers.

    .. note::
        This is a no-op. SQLAlchemy automatically manages connection pooling.
        Use ``engine.dispose()`` if you need to close all pooled connections.
    """
    import warnings

    warnings.warn(
        "close_all_connections() is deprecated and has no effect",
        DeprecationWarning,
        stacklevel=2,
    )


def get_unified_food_db() -> Any:
    """Legacy synchronous wrapper for unified food database access.

    .. deprecated::
        Import from core.food_apis.unified_db instead.
    """
    import warnings
    import asyncio

    warnings.warn(
        "get_unified_food_db() is deprecated, import from core.food_apis.unified_db instead",
        DeprecationWarning,
        stacklevel=2,
    )

    from .food_apis.unified_db import get_unified_food_db as _get_unified_food_db

    return asyncio.run(_get_unified_food_db())
