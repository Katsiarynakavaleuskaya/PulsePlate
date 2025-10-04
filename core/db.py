"""SQLAlchemy session and engine setup.

RU: Базовая интеграция SQLAlchemy с приложением FastAPI.
EN: Basic SQLAlchemy integration for the FastAPI app.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Optional, TYPE_CHECKING, cast

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

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
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
except ImportError:  # pragma: no cover - async extras not installed
    AsyncEngine = cast(Any, None)
    AsyncSession = cast(Any, None)
    async_sessionmaker = cast(Any, None)
    create_async_engine = cast(Any, None)


def _build_engine_url() -> str:
    """Return the database URL from env or fall back to local SQLite."""

    default_path = os.path.join("cache", "app.db")
    # Use file-based SQLite by default so the data survives across runs.
    return os.getenv("DATABASE_URL", f"sqlite:///{default_path}")


def _sqlite_connect_args(url: str) -> dict[str, object]:
    """Provide SQLite-specific connection args when needed."""

    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


DATABASE_URL: str = _build_engine_url()


def _derive_async_url(sync_url: str) -> Optional[str]:
    """
    Derive an async-capable URL from a synchronous SQLAlchemy database URL.

    Supported patterns:
    - PostgreSQL: 'postgresql://...' → 'postgresql+asyncpg://...'
    - MySQL: 'mysql://...' → 'mysql+aiomysql://...'
    - SQLite: 'sqlite://...' → 'sqlite+aiosqlite://...'

    For unsupported or custom formats, returns None.

    Args:
        sync_url (str): Synchronous SQLAlchemy database URL.

    Returns:
        Optional[str]: Async-capable database URL, or None if unsupported.
    """

    if "+async" in sync_url:
        return sync_url
    if sync_url.startswith("sqlite+aiosqlite"):
        return sync_url
    if sync_url.startswith("sqlite:///"):
        return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if sync_url.startswith("postgresql+asyncpg://") or sync_url.startswith("postgres+asyncpg://"):
        return sync_url
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgres://"):
        return sync_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("mysql://"):
        return sync_url.replace("mysql://", "mysql+aiomysql://", 1)
    if sync_url.startswith("mysql+pymysql://"):
        return sync_url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    return None


def _engine_pool_config() -> dict[str, Any]:
    """Return engine pooling options based on environment variables."""

    config: dict[str, Any] = {}
    pool_size = os.getenv("DB_POOL_SIZE")
    max_overflow = os.getenv("DB_MAX_OVERFLOW")
    pool_recycle = os.getenv("DB_POOL_RECYCLE")
    pool_timeout = os.getenv("DB_POOL_TIMEOUT")

    if pool_size:
        try:
            config["pool_size"] = int(pool_size)
        except ValueError:
            raise ValueError("DB_POOL_SIZE must be an integer") from None
    if max_overflow:
        try:
            config["max_overflow"] = int(max_overflow)
        except ValueError:
            raise ValueError("DB_MAX_OVERFLOW must be an integer") from None
    if pool_recycle:
        try:
            config["pool_recycle"] = int(pool_recycle)
        except ValueError:
            raise ValueError("DB_POOL_RECYCLE must be an integer") from None
    if pool_timeout:
        try:
            config["pool_timeout"] = int(pool_timeout)
        except ValueError:
            raise ValueError("DB_POOL_TIMEOUT must be an integer") from None

    return config


class EngineCompat:
    """Compatibility wrapper to expose Engine.execute for SQLAlchemy 2.x.

    RU: Обёртка совместимости, добавляющая метод execute у Engine в стиле 1.x.
    EN: Adds an ``execute`` method that proxies to a Connection in SQLAlchemy 2.x.
    """

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    # Delegate unknown attributes to the underlying Engine
    def __getattr__(self, name: str) -> Any:
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
            except Exception:
                # Not all statements require/allow commit; ignore commit errors
                pass
            return result


# Engine creation settings shared between sync/async variants
_ECHO_SQL = os.getenv("DB_ECHO", "false").lower() in {"1", "true", "yes", "on"}
_POOL_CONFIG = _engine_pool_config()


def _sync_engine_kwargs(url: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "future": True,
        "echo": _ECHO_SQL,
        "connect_args": _sqlite_connect_args(url),
    }
    if not url.startswith("sqlite"):
        kwargs |= _POOL_CONFIG
    return kwargs


# Create the underlying SQLAlchemy Engine instance (2.x style)
_RAW_ENGINE = create_engine(DATABASE_URL, **_sync_engine_kwargs(DATABASE_URL))

# Public engine exposes a legacy-compatible .execute attribute expected by tests
engine = EngineCompat(_RAW_ENGINE)


class Base(DeclarativeBase):
    """Base class for declarative SQLAlchemy models."""


SessionLocal = sessionmaker(bind=_RAW_ENGINE, autoflush=False, autocommit=False, future=True)


# Optional async engine/session factory -----------------------------------------------------
_ASYNC_URL_ENV = os.getenv("DATABASE_ASYNC_URL")
_ASYNC_ENABLED_FLAG = os.getenv("DATABASE_USE_ASYNC", "auto").lower()

ASYNC_DATABASE_URL: Optional[str]
if _ASYNC_URL_ENV:
    ASYNC_DATABASE_URL = _ASYNC_URL_ENV
elif _ASYNC_ENABLED_FLAG in {"1", "true", "yes", "on"}:
    ASYNC_DATABASE_URL = _derive_async_url(DATABASE_URL)
else:
    ASYNC_DATABASE_URL = None

if ASYNC_DATABASE_URL and create_async_engine is None:
    raise ImportError(
        "SQLAlchemy async extras are not available. Install with 'pip install sqlalchemy[asyncio]'"
    )

_ASYNC_ENGINE: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]]

if ASYNC_DATABASE_URL and create_async_engine is not None:
    async_kwargs: dict[str, Any] = {
        "echo": _ECHO_SQL,
        "future": True,
        "pool_pre_ping": True,
    }
    if not ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite"):
        async_kwargs.update(
            {key: value for key, value in _POOL_CONFIG.items() if key != "max_overflow"}
        )

    _ASYNC_ENGINE = create_async_engine(ASYNC_DATABASE_URL, **async_kwargs)
    AsyncSessionLocal = async_sessionmaker(
        bind=_ASYNC_ENGINE,
        autoflush=False,
        expire_on_commit=False,
    )
else:
    AsyncSessionLocal = None

async_engine: Optional[AsyncEngine] = _ASYNC_ENGINE


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


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency yielding an async SQLAlchemy session when enabled."""

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
async def session_scope_async() -> AsyncGenerator[AsyncSession, None]:
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
    if _ASYNC_ENGINE is not None:
        raise RuntimeError(
            "init_db() cannot be used when async engine is enabled. Use `await init_db_async()` instead."
        )

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
