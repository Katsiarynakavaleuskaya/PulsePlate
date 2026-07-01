"""
RU: Каноническая реализация DB fallback (TP2) для startup critical path.
EN: Canonical DB fallback implementation (TP2) for the startup critical path.

CRITICAL:
- Startup critical path.
- Production/staging fail closed; SQLite fallback is local/dev/test only.
- No OpenAPI / contract changes.

Location: core/db_fallback.py (flat module) to avoid core/db.py vs core/db/ package collision.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Module-level flag indicating fallback state
_db_fallback_active = False


def _redact_database_url(database_url: str) -> str:
    """Return a log-safe database URL label without credentials."""
    if not database_url:
        return "<empty-db-url>"

    if database_url.startswith("sqlite:///:memory:"):
        return "sqlite:///:memory:"
    if database_url.startswith("sqlite:///"):
        return "sqlite:///<redacted>"

    return "<redacted-db-url>"


def _validate_fallback_url(
    env_name: Optional[str],
    is_production: bool,
    fallback_url: str,
    db_err: Exception,
) -> None:
    """Validate fallback URL against production constraints.

    Production environments reject in-memory fallbacks.
    Raises db_err on validation failure.
    """
    # Check if fallback URL is in-memory SQLite
    is_in_memory = fallback_url.startswith("sqlite:///:memory:")

    # Production: reject in-memory fallbacks
    if is_production and is_in_memory:
        logger.error(
            "CRITICAL: In-memory database fallback is not allowed in production environment (%s). "
            "SQLite fallback is not an accepted production or staging baseline. "
            "Configure a canonical Postgres DATABASE_URL and recover the primary database.",
            env_name or "production",
        )
        raise db_err


def _check_production_constraints(
    env_name: Optional[str], fallback_url: str, truthy: set[str], db_err: Exception
) -> None:
    """Enforce production-specific fallback constraints.

    Production-like environments fail closed on DB init errors.
    Raises db_err after logging the canonical production contract.
    """
    del fallback_url, truthy
    logger.error(
        "CRITICAL: Database initialization failed in production-like environment (%s). "
        "SQLite fallback is not an accepted production or staging baseline. "
        "Configure a canonical Postgres DATABASE_URL and recover the primary database. "
        "Original error: %s",
        env_name or "production",
        db_err,
    )
    raise db_err


def _initialize_fallback_engine(fallback_url: str, db_err: Exception) -> Engine:
    """
    Create and initialize fallback SQLAlchemy engine.

    Creates engine with correct connect_args, runs Base.metadata.create_all.
    Returns the initialized engine or raises db_err on failure.
    """
    import core.models  # noqa: F401
    from core.models import Base

    try:
        # Create temporary engine with fallback URL
        # Use SQLite-specific connection args when needed
        connect_args = {"check_same_thread": False} if fallback_url.startswith("sqlite") else {}
        fallback_engine: Engine = create_engine(
            fallback_url, echo=False, future=True, connect_args=connect_args
        )

        # Initialize schema using the fallback engine
        Base.metadata.create_all(bind=fallback_engine)
        return fallback_engine
    except Exception as fallback_err:
        logger.error(
            "Fallback database init failed (url=%s): %s",
            _redact_database_url(fallback_url),
            fallback_err,
        )
        raise db_err from fallback_err


def _configure_session_bindings(
    engine: Engine, is_production: bool, fallback_url: str, env_name: Optional[str]
) -> None:
    """
    Configure core.db session bindings and environment variables.

    Sets SessionLocal (recreated sessionmaker, no .configure()), _RAW_ENGINE, engine wrapper,
    _db_fallback_active flag, and updates os.environ with appropriate markers.
    """
    # core.db is the module core/db.py (no package collision: we use core/db_fallback.py).
    from core import db as core_db

    # Always recreate sessionmaker; do not use SessionLocal.configure() (core/AGENTS.md).
    core_db.SessionLocal = core_db.sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    core_db._RAW_ENGINE = engine
    core_db.engine = core_db.EngineCompat(engine)
    set_fallback_active()
    os.environ["DB_HEALTH_DEGRADED"] = "1"

    # Emit an observability metric when DB fallback is activated so dashboards
    # can surface degraded states. This uses a lazy import and silently
    # no-ops if the metrics client is not available.
    is_in_memory = ":memory:" in (fallback_url or "")
    backend = "memory" if is_in_memory else "sqlite"
    env_label = (env_name or os.getenv("APP_ENV") or "unknown").strip() or "unknown"
    try:  # pragma: no cover - metrics instrumentation is optional
        from core import metrics as _metrics

        client = getattr(_metrics, "metrics_client", None)
        if client is not None:
            tags = [f"env:{env_label}", f"backend:{backend}"]
            try:
                client.increment("db_fallback_active", tags=tags)
            except Exception:
                logger.debug(
                    "Failed to increment DB fallback activation metric env=%s backend=%s",
                    env_label,
                    backend,
                    exc_info=True,
                )
    except Exception:  # pragma: no cover
        logger.debug(
            "Failed to emit DB fallback activation metric env=%s backend=%s",
            env_label,
            backend,
            exc_info=True,
        )
        # Metrics collection is non-critical; failures should not affect application startup

    # Set DB_FALLBACK_URL only if needed for external tools
    if not is_production:
        os.environ["DB_FALLBACK_URL"] = fallback_url
        os.environ["DATABASE_URL"] = fallback_url
        logger.warning(
            "Database initialized with fallback SQLite (env=%s, fallback_url=%s). "
            "os.environ['DATABASE_URL'] updated for compatibility.",
            env_name or "local",
            _redact_database_url(fallback_url),
        )
    else:
        # In production, only set DB_FALLBACK_URL for internal use
        os.environ["DB_FALLBACK_URL"] = fallback_url
        logger.warning(
            "Database initialized with fallback SQLite (env=%s, fallback_url=%s). "
            "Using module-level fallback variable only.",
            env_name or "local",
            _redact_database_url(fallback_url),
        )


def _attempt_db_fallback(
    env_name: Optional[str], is_production: bool, db_err: Exception, truthy: set[str]
) -> None:
    """Attempt to initialize database with fallback SQLite when primary DB fails.

    Production-like environments fail closed on primary DB errors.
    Non-production environments can use fallback SQLite when explicitly allowed.

    Raises:
        db_err: Original database error if fallback fails or is not allowed
    """
    if is_production:
        # Production/staging: fail closed, Postgres is the canonical baseline
        _check_production_constraints(
            env_name, (os.getenv("DB_FALLBACK_URL") or "").strip(), truthy, db_err
        )
    else:
        # Get fallback URL (prefer DB_FALLBACK_URL env var, otherwise use in-memory SQLite)
        fallback_url = (os.getenv("DB_FALLBACK_URL") or "").strip() or "sqlite:///:memory:"

        # Validate fallback URL against non-production constraints
        _validate_fallback_url(env_name, is_production, fallback_url, db_err)

        # Non-production: allow any fallback including in-memory
        explicit_override = (
            os.getenv("ALLOW_DB_INMEMORY_FALLBACK") or ""
        ).strip().lower() in truthy
        fallback_exception = isinstance(db_err, OSError)

        if not (explicit_override or fallback_exception):
            raise db_err

        logger.warning(
            "Database initialization failed (%s env: %s), attempting fallback SQLite: %s (explicit override: %s, IO error: %s)",
            type(db_err).__name__,
            env_name or "local",
            _redact_database_url(fallback_url),
            explicit_override,
            fallback_exception,
        )

    # Initialize fallback engine and configure bindings
    fallback_engine = _initialize_fallback_engine(fallback_url, db_err)
    _configure_session_bindings(fallback_engine, is_production, fallback_url, env_name)


# --- Public helpers (avoid cross-module writes to _db_fallback_active) ---


def set_fallback_active() -> None:
    """Mark DB fallback as active (public helper; avoids cross-module writes)."""
    global _db_fallback_active
    _db_fallback_active = True


def clear_fallback_active() -> None:
    """Clear DB fallback active marker (public helper; avoids cross-module writes)."""
    global _db_fallback_active
    _db_fallback_active = False


def reset_fallback_state() -> None:
    """Reset fallback global state for tests."""
    clear_fallback_active()


def is_fallback_active() -> bool:
    """
    Indicates whether a database fallback is currently active.

    Returns:
        `True` if a fallback is active, `False` otherwise.
    """
    return _db_fallback_active
