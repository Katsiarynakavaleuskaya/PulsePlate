"""Runtime ownership and lease policy for food database updates."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import threading
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Protocol, TypeVar

from sqlalchemy import text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.orm import Session

from settings import (
    is_production_like_env,
    is_raw_explicit_developer_env,
    is_truthy_env_var,
)

logger = logging.getLogger(__name__)

FOOD_UPDATE_SCHEDULER_MODE_ENV = "FOOD_UPDATE_SCHEDULER_MODE"

# Stable signed PostgreSQL advisory-lock key for the ASCII label ``PULSEPLT``.
# This is repository-owned and must never be derived from Python hash(), input,
# source names, or environment text.
FOOD_UPDATE_ADVISORY_LOCK_KEY = 0x50554C5345504C54

_TRY_ADVISORY_LOCK_SQL = text("SELECT pg_try_advisory_lock(:lease_key)")
_ADVISORY_UNLOCK_SQL = text("SELECT pg_advisory_unlock(:lease_key)")
_LOCAL_UPDATE_LEASE = threading.Lock()

T = TypeVar("T")
VersionStateT = TypeVar("VersionStateT")
UpdateOperation = Callable[[], Awaitable[T]]
SessionFactory = Callable[[], Session]


class PersistedVersionStore(Protocol[VersionStateT]):
    """Version metadata surface that must be refreshed inside the update lease."""

    versions: VersionStateT

    def _load_versions(self) -> VersionStateT: ...


class SchedulerMode(str, Enum):
    """Configured owner of automatic food database update attempts."""

    EXTERNAL = "external"
    IN_PROCESS_DEV = "in_process_dev"
    DISABLED = "disabled"


class SchedulerConfigurationError(RuntimeError):
    """Scheduler ownership or database configuration is invalid."""


class UpdateLeaseError(RuntimeError):
    """Base class for update lease failures."""


class UpdateLeaseContended(UpdateLeaseError):
    """Another cooperating update path holds the shared lease."""

    def __init__(self) -> None:
        super().__init__("update_already_in_progress")


class UpdateLeaseAcquireError(UpdateLeaseError):
    """The lease acquisition result was unavailable or uncertain."""


class UpdateLeaseReleaseError(UpdateLeaseError):
    """The lease release result was unavailable or uncertain."""


def _is_explicit_development_or_test() -> bool:
    """Return whether process-local coordination is explicitly permitted."""

    explicit_developer = bool(is_raw_explicit_developer_env())
    explicit_testing = bool(is_truthy_env_var("TESTING"))
    explicit_ci = bool(is_truthy_env_var("CI"))
    return explicit_developer or explicit_testing or explicit_ci


def _database_backend_name() -> str | None:
    """Return the configured SQLAlchemy backend without exposing the URL."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None
    try:
        backend_name: str = make_url(database_url).get_backend_name()
        return backend_name
    except Exception as exc:
        raise SchedulerConfigurationError("invalid scheduler database configuration") from exc


def validate_scheduler_mode(mode: SchedulerMode) -> SchedulerMode:
    """Validate a resolved scheduler mode against runtime and database policy."""

    explicit_dev_test = _is_explicit_development_or_test()
    production_like = is_production_like_env()
    backend_name = _database_backend_name()

    if mode is SchedulerMode.IN_PROCESS_DEV and (production_like or not explicit_dev_test):
        raise SchedulerConfigurationError(
            "in_process_dev scheduler mode requires a non-production development or test runtime"
        )

    if mode is SchedulerMode.EXTERNAL and backend_name != "postgresql":
        raise SchedulerConfigurationError("external scheduler mode requires PostgreSQL")

    if mode is SchedulerMode.DISABLED and production_like and backend_name != "postgresql":
        raise SchedulerConfigurationError(
            "disabled scheduler mode requires PostgreSQL in production-like runtimes"
        )

    return mode


def resolve_scheduler_mode() -> SchedulerMode:
    """Resolve the exact scheduler mode at call time and fail closed on drift."""

    raw_mode = os.environ.get(FOOD_UPDATE_SCHEDULER_MODE_ENV)
    if raw_mode is None:
        mode = (
            SchedulerMode.IN_PROCESS_DEV
            if _is_explicit_development_or_test() and not is_production_like_env()
            else SchedulerMode.EXTERNAL
        )
    else:
        try:
            mode = SchedulerMode(raw_mode)
        except ValueError as exc:
            raise SchedulerConfigurationError(
                f"{FOOD_UPDATE_SCHEDULER_MODE_ENV} must be one of: "
                "external, in_process_dev, disabled"
            ) from exc
    return validate_scheduler_mode(mode)


def configured_periodic_owner(mode: SchedulerMode) -> str:
    """Return configuration intent without claiming live leadership or health."""

    if mode is SchedulerMode.EXTERNAL:
        return "worker"
    if mode is SchedulerMode.IN_PROCESS_DEV:
        return "api_process"
    return "none"


def refresh_update_version_state(
    update_manager: PersistedVersionStore[VersionStateT],
) -> None:
    """Reload shared version metadata after acquiring the cross-process lease.

    ``DatabaseUpdateManager`` persists all source versions as one JSON object.
    Long-lived API and worker processes therefore must replace their in-memory
    snapshot before any leased mutation, or a later writer can erase metadata
    saved by an earlier process even though their executions were serialized.
    """

    update_manager.versions = update_manager._load_versions()


def _current_session_factory() -> SessionFactory:
    """Resolve the public DB session factory lazily without creating an engine."""

    from core.db import get_session_factory

    session_factory: SessionFactory = get_session_factory()
    return session_factory


def _invalidate_connection(connection: Connection | None) -> None:
    """Discard a connection whose advisory-lock session state is uncertain."""

    if connection is None:
        return
    try:
        connection.invalidate()
    except Exception:
        logger.error("Could not invalidate uncertain update-lease connection", exc_info=True)


def _close_session(session: Session) -> None:
    """Close the dedicated lease session without masking the primary result."""

    try:
        session.close()
    except Exception:
        logger.error("Could not close update-lease session", exc_info=True)


async def _run_lease_io(
    executor: ThreadPoolExecutor,
    operation: Callable[[], T],
) -> T:
    """Run synchronous lease I/O on the invocation's single worker thread."""

    loop = asyncio.get_running_loop()
    result: T = await loop.run_in_executor(executor, operation)
    return result


async def _run_with_postgresql_lease(
    operation: UpdateOperation[T],
    *,
    session_factory: SessionFactory,
) -> T:
    """Run an operation while one PostgreSQL session holds the advisory lease."""

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="food-update-lease")
    session: Session | None = None
    connection: Connection | None = None
    acquired = False
    body_error: BaseException | None = None
    try:
        try:
            created_session = await _run_lease_io(executor, session_factory)
            session = created_session
            lease_connection = await _run_lease_io(executor, created_session.connection)
            connection = lease_connection
            acquire_result = await _run_lease_io(
                executor,
                lambda: lease_connection.execute(
                    _TRY_ADVISORY_LOCK_SQL,
                    {"lease_key": FOOD_UPDATE_ADVISORY_LOCK_KEY},
                ).scalar_one_or_none(),
            )
        except BaseException as exc:
            await _run_lease_io(executor, lambda: _invalidate_connection(connection))
            if not isinstance(exc, Exception):
                raise
            raise UpdateLeaseAcquireError("update lease acquisition failed") from exc

        if acquire_result is False:
            raise UpdateLeaseContended()
        if acquire_result is not True:
            await _run_lease_io(executor, lambda: _invalidate_connection(connection))
            raise UpdateLeaseAcquireError("update lease acquisition was uncertain")
        acquired = True

        try:
            return await operation()
        except BaseException as exc:
            body_error = exc
            raise
        finally:
            if acquired and connection is not None:
                lease_connection = connection
                release_error: BaseException | None = None
                try:
                    release_result = await _run_lease_io(
                        executor,
                        lambda: lease_connection.execute(
                            _ADVISORY_UNLOCK_SQL,
                            {"lease_key": FOOD_UPDATE_ADVISORY_LOCK_KEY},
                        ).scalar_one_or_none(),
                    )
                    if release_result is not True:
                        raise UpdateLeaseReleaseError("update lease release was uncertain")
                except BaseException as exc:
                    release_error = exc
                    await _run_lease_io(
                        executor,
                        lambda: _invalidate_connection(lease_connection),
                    )

                if release_error is not None:
                    if body_error is None:
                        if not isinstance(release_error, Exception):
                            raise release_error
                        if isinstance(release_error, UpdateLeaseReleaseError):
                            raise release_error
                        raise UpdateLeaseReleaseError(
                            "update lease release failed"
                        ) from release_error
                    logger.error(
                        "Update lease release was uncertain after a primary operation failure; "
                        "the primary failure is preserved"
                    )
    finally:
        try:
            if session is not None:
                lease_session = session
                await _run_lease_io(executor, lambda: _close_session(lease_session))
        finally:
            executor.shutdown(wait=False, cancel_futures=True)


async def _run_with_local_lease(operation: UpdateOperation[T]) -> T:
    """Run an operation under the explicit development/test process lease."""

    if not _LOCAL_UPDATE_LEASE.acquire(blocking=False):
        raise UpdateLeaseContended()
    try:
        return await operation()
    finally:
        _LOCAL_UPDATE_LEASE.release()


async def run_with_update_lease(
    operation: UpdateOperation[T],
    *,
    mode: SchedulerMode | None = None,
    session_factory: SessionFactory | None = None,
) -> T:
    """Run one update attempt through the canonical coordination boundary."""

    if mode is None:
        resolve_scheduler_mode()
    else:
        validate_scheduler_mode(mode)
    backend_name = _database_backend_name()

    if backend_name == "postgresql":
        return await _run_with_postgresql_lease(
            operation,
            session_factory=session_factory or _current_session_factory(),
        )

    if not _is_explicit_development_or_test():
        raise SchedulerConfigurationError(
            "process-local update lease requires an explicit development or test runtime"
        )

    return await _run_with_local_lease(operation)


__all__ = [
    "FOOD_UPDATE_ADVISORY_LOCK_KEY",
    "FOOD_UPDATE_SCHEDULER_MODE_ENV",
    "SchedulerConfigurationError",
    "SchedulerMode",
    "SessionFactory",
    "PersistedVersionStore",
    "UpdateLeaseAcquireError",
    "UpdateLeaseContended",
    "UpdateLeaseError",
    "UpdateLeaseReleaseError",
    "configured_periodic_owner",
    "refresh_update_version_state",
    "resolve_scheduler_mode",
    "run_with_update_lease",
    "validate_scheduler_mode",
]
