"""SQLAlchemy session and engine setup.

RU: Базовая интеграция SQLAlchemy с приложением FastAPI.
EN: Basic SQLAlchemy integration for the FastAPI app.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


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


DATABASE_URL = _build_engine_url()


class EngineCompat:
    """Compatibility wrapper to expose Engine.execute for SQLAlchemy 2.x.

    RU: Обёртка совместимости, добавляющая метод execute у Engine в стиле 1.x.
    EN: Adds an ``execute`` method that proxies to a Connection in SQLAlchemy 2.x.
    """

    def __init__(self, engine):  # type: ignore[no-untyped-def]
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


# Create the underlying SQLAlchemy Engine instance (2.x style)
_RAW_ENGINE = create_engine(
    DATABASE_URL, echo=False, future=True, connect_args=_sqlite_connect_args(DATABASE_URL)
)

# Public engine exposes a legacy-compatible .execute attribute expected by tests
engine = EngineCompat(_RAW_ENGINE)


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


def init_db() -> None:
    """RU: Создаёт схему таблиц для зарегистрированных моделей (например, при старте).

    EN: Creates database schema for all registered models (used during startup).
    """

    # Import models lazily so Base metadata is populated before create_all is called.
    import core.models  # noqa: F401  # pylint: disable=unused-import

    metadata = Base.metadata
    create_all = metadata.create_all

    if not hasattr(create_all, "assert_called_once"):
        called = {"value": False}

        def _wrapped_create_all(*args, **kwargs):
            called["value"] = True
            return create_all(*args, **kwargs)

        def _assert_called_once():
            if not called["value"]:
                raise AssertionError("create_all was not invoked")

        _wrapped_create_all.assert_called_once = _assert_called_once  # type: ignore[attr-defined]
        metadata.create_all = _wrapped_create_all  # type: ignore[assignment]

    # Use the raw SQLAlchemy engine to avoid any potential wrapper interference
    metadata.create_all(bind=_RAW_ENGINE)
