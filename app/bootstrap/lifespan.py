"""Canonical FastAPI startup and shutdown resource ownership."""

from __future__ import annotations

import asyncio
import logging
import math
import os
import threading
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from fastapi import FastAPI

from app.bootstrap.food_search import FoodSearchLifecycleLease
from core.food_apis.scheduler_runtime import SchedulerMode, resolve_scheduler_mode
from settings import get_runtime_env_name, is_production_like_env, is_truthy_env_var

if TYPE_CHECKING:
    from core.food_apis.unified_db import UnifiedFoodDatabase

logger = logging.getLogger(__name__)

DEFAULT_BACKGROUND_START_TIMEOUT_SECONDS = 10.0
MAX_BACKGROUND_START_TIMEOUT_SECONDS = 60.0
BACKGROUND_UPDATE_INTERVAL_HOURS = 24


class BackgroundUpdateStarter(Protocol):
    """Typed async scheduler startup boundary."""

    def __call__(
        self,
        update_interval_hours: int = BACKGROUND_UPDATE_INTERVAL_HOURS,
    ) -> Coroutine[Any, Any, None]: ...


BackgroundUpdateStopper = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class UnifiedFoodLifecycleLease:
    """Identity-bound ownership record for one unified-food lifespan acquisition."""

    instance: UnifiedFoodDatabase
    owns_instance: bool
    managed_lifetime: bool = field(default=False, repr=False)
    _released: bool = field(default=False, init=False, repr=False)


UnifiedFoodAcquirer = Callable[[], Awaitable[UnifiedFoodLifecycleLease]]
UnifiedFoodReleaser = Callable[[UnifiedFoodLifecycleLease], Awaitable[None]]

_managed_unified_food_instance: UnifiedFoodDatabase | None = None
_managed_unified_food_active_leases = 0
_managed_unified_food_lock = threading.Lock()


async def _close_unified_food_clients(instance: UnifiedFoodDatabase) -> None:
    """Close each initialized API client once while attempting every client."""

    first_ordinary_error: BaseException | None = None
    cancellation_error: asyncio.CancelledError | None = None
    closed_client_ids: set[int] = set()
    for attribute_name in ("usda_client", "off_client"):
        client = getattr(instance, attribute_name, None)
        if client is None or id(client) in closed_client_ids:
            continue
        closed_client_ids.add(id(client))
        close = getattr(client, "close", None)
        if not callable(close):
            continue
        try:
            await close()
        except asyncio.CancelledError as exc:
            if cancellation_error is None:
                cancellation_error = exc
        except BaseException as exc:
            if first_ordinary_error is None:
                first_ordinary_error = exc
    if cancellation_error is not None:
        if first_ordinary_error is not None:
            raise cancellation_error from first_ordinary_error
        raise cancellation_error
    if first_ordinary_error is not None:
        raise first_ordinary_error


async def _acquire_unified_food_database() -> UnifiedFoodLifecycleLease:
    """Initialize the process catalog without search, refresh, or cache writes."""

    global _managed_unified_food_active_leases, _managed_unified_food_instance

    import core.food_apis.unified_db as unified_db_module

    instance: UnifiedFoodDatabase
    initialization_error: BaseException | None = None
    replacement: UnifiedFoodDatabase | None = None
    with _managed_unified_food_lock:
        existing = unified_db_module._unified_db_instance
        if existing is _managed_unified_food_instance and existing is not None:
            _managed_unified_food_active_leases += 1
            return UnifiedFoodLifecycleLease(
                instance=existing,
                owns_instance=False,
                managed_lifetime=True,
            )
        if existing is not None:
            return UnifiedFoodLifecycleLease(instance=existing, owns_instance=False)

        instance = unified_db_module.UnifiedFoodDatabase.__new__(
            unified_db_module.UnifiedFoodDatabase
        )
        try:
            unified_db_module.UnifiedFoodDatabase.__init__(
                instance,
                create_cache_dir=False,
            )
        except BaseException as exc:
            initialization_error = exc
        else:
            replacement = unified_db_module._unified_db_instance
            if replacement is None:
                unified_db_module._unified_db_instance = instance
                _managed_unified_food_instance = instance
                _managed_unified_food_active_leases = 1
                return UnifiedFoodLifecycleLease(
                    instance=instance,
                    owns_instance=True,
                    managed_lifetime=True,
                )

    if initialization_error is not None:
        try:
            await _close_unified_food_clients(instance)
        except asyncio.CancelledError as cleanup_cancellation:
            raise cleanup_cancellation from initialization_error
        except BaseException:
            logger.error(
                "Error cleaning partially acquired unified-food resources",
                exc_info=True,
            )
        raise initialization_error.with_traceback(initialization_error.__traceback__)

    if replacement is not None:
        await _close_unified_food_clients(instance)
        with _managed_unified_food_lock:
            if replacement is _managed_unified_food_instance:
                _managed_unified_food_active_leases += 1
                return UnifiedFoodLifecycleLease(
                    instance=replacement,
                    owns_instance=False,
                    managed_lifetime=True,
                )
        return UnifiedFoodLifecycleLease(instance=replacement, owns_instance=False)

    raise RuntimeError("Unified-food acquisition produced no instance")


async def _release_unified_food_database(lease: UnifiedFoodLifecycleLease) -> None:
    """Release an owned catalog once without disturbing borrowed or replacement state."""

    global _managed_unified_food_active_leases, _managed_unified_food_instance

    import core.food_apis.unified_db as unified_db_module

    with _managed_unified_food_lock:
        if lease._released:
            return
        lease._released = True
        if not lease.managed_lifetime:
            return
        if _managed_unified_food_instance is not lease.instance:
            return

        _managed_unified_food_active_leases -= 1
        if _managed_unified_food_active_leases > 0:
            return

        _managed_unified_food_active_leases = 0
        _managed_unified_food_instance = None
        if unified_db_module._unified_db_instance is lease.instance:
            unified_db_module._unified_db_instance = None

    await _close_unified_food_clients(lease.instance)


async def _unavailable_background_update_start(
    update_interval_hours: int = BACKGROUND_UPDATE_INTERVAL_HOURS,
) -> None:
    """Keep startup best-effort when the optional scheduler cannot import."""

    del update_interval_hours


async def _unavailable_background_update_stop() -> None:
    """No-op counterpart for an unavailable optional scheduler."""


def _import_background_update_hooks() -> tuple[
    BackgroundUpdateStarter,
    BackgroundUpdateStopper,
]:
    """Import the optional scheduler behind a narrow test seam."""

    from core.food_apis.scheduler import (
        start_background_updates,
        stop_background_updates,
    )

    return start_background_updates, stop_background_updates


def _load_background_update_hooks() -> tuple[BackgroundUpdateStarter, BackgroundUpdateStopper]:
    """Load optional scheduler hooks without making them a startup dependency."""

    try:
        return _import_background_update_hooks()
    except ImportError:
        logger.warning(
            "Background update scheduler is unavailable; continuing without it.",
            exc_info=True,
        )
        return _unavailable_background_update_start, _unavailable_background_update_stop


@dataclass(frozen=True, slots=True)
class LifespanHooks:
    """Explicit lifecycle dependencies for deterministic startup tests."""

    run_startup_guards: Callable[[FastAPI], None]
    initialize_database: Callable[[], object]
    clear_database_fallback: Callable[[], None]
    attempt_database_fallback: Callable[[str | None, bool, Exception], None]
    validate_templates: Callable[[], None]
    configure_food_search: Callable[[FastAPI], FoodSearchLifecycleLease]
    dispose_food_search: Callable[[FastAPI, FoodSearchLifecycleLease], None]
    start_background_updates: BackgroundUpdateStarter
    stop_background_updates: BackgroundUpdateStopper
    acquire_unified_food: UnifiedFoodAcquirer = _acquire_unified_food_database
    release_unified_food: UnifiedFoodReleaser = _release_unified_food_database


def build_default_lifespan_hooks(
    *,
    scheduler_mode: SchedulerMode | None = None,
) -> LifespanHooks:
    """Resolve canonical lifecycle callables at each lifespan entry."""

    from app.bootstrap.food_search import (
        configure_food_search_backend,
        dispose_food_search_backend,
    )
    from app.bootstrap.startup_guards import run_startup_guards
    from app.dependencies import validate_template_dir
    from core.db import init_db
    from core.db_fallback import attempt_db_fallback, clear_fallback_active

    if scheduler_mode is SchedulerMode.IN_PROCESS_DEV:
        start_background_updates, stop_background_updates = _load_background_update_hooks()
    else:
        start_background_updates = _unavailable_background_update_start
        stop_background_updates = _unavailable_background_update_stop

    return LifespanHooks(
        run_startup_guards=run_startup_guards,
        initialize_database=init_db,
        clear_database_fallback=clear_fallback_active,
        attempt_database_fallback=attempt_db_fallback,
        validate_templates=validate_template_dir,
        acquire_unified_food=_acquire_unified_food_database,
        release_unified_food=_release_unified_food_database,
        configure_food_search=configure_food_search_backend,
        dispose_food_search=dispose_food_search_backend,
        start_background_updates=start_background_updates,
        stop_background_updates=stop_background_updates,
    )


def _background_start_timeout_seconds() -> float:
    raw_value = os.getenv("BACKGROUND_START_TIMEOUT_SEC")
    try:
        timeout = float(
            raw_value if raw_value is not None else DEFAULT_BACKGROUND_START_TIMEOUT_SECONDS
        )
    except (TypeError, ValueError):
        timeout = DEFAULT_BACKGROUND_START_TIMEOUT_SECONDS
    if not math.isfinite(timeout) or not 0 < timeout <= MAX_BACKGROUND_START_TIMEOUT_SECONDS:
        logger.warning("Invalid BACKGROUND_START_TIMEOUT_SEC; using the safe default.")
        return DEFAULT_BACKGROUND_START_TIMEOUT_SECONDS
    return timeout


def _initialize_database(hooks: LifespanHooks) -> None:
    env_name = get_runtime_env_name()
    is_production = is_production_like_env()
    try:
        hooks.initialize_database()
    except Exception as db_err:
        hooks.attempt_database_fallback(env_name, is_production, db_err)
    else:
        hooks.clear_database_fallback()
        os.environ.pop("DB_HEALTH_DEGRADED", None)
        logger.info("Database schema initialized")


async def _drain_cancelled_task(task: asyncio.Task[None]) -> None:
    if not task.done():
        task.cancel()
    with suppress(asyncio.CancelledError, Exception):
        await task


async def _start_background_updates_best_effort(
    starter: BackgroundUpdateStarter,
    *,
    failed_start_stopper: BackgroundUpdateStopper | None = None,
) -> bool:
    testing_mode = is_truthy_env_var("TESTING") or is_truthy_env_var("CI")
    force_background = is_truthy_env_var("FORCE_BACKGROUND_UPDATES")
    disable_background = is_truthy_env_var("DISABLE_BACKGROUND_UPDATES")
    env_name = get_runtime_env_name()
    if disable_background or (testing_mode and not force_background):
        logger.info(
            "Skipping background database updates (env=%s, testing=%s, forced=%s, disabled=%s)",
            env_name or "unknown",
            testing_mode,
            force_background,
            disable_background,
        )
        return False

    timeout = _background_start_timeout_seconds()
    task: asyncio.Task[None] = asyncio.create_task(
        starter(update_interval_hours=BACKGROUND_UPDATE_INTERVAL_HOURS),
        name="pulseplate-background-update-start",
    )
    try:
        await asyncio.wait_for(task, timeout=timeout)
    except TimeoutError:
        await _drain_cancelled_task(task)
        if failed_start_stopper is not None:
            await _stop_after_failed_background_start(failed_start_stopper)
        logger.error(
            "Background updates startup timed out after %.0f seconds",
            timeout,
        )
        return False
    except asyncio.CancelledError:
        await _drain_cancelled_task(task)
        if failed_start_stopper is not None:
            await _stop_after_failed_background_start(failed_start_stopper)
        raise
    except Exception:
        if failed_start_stopper is not None:
            await _stop_after_failed_background_start(failed_start_stopper)
        logger.error("Failed to start background updates", exc_info=True)
        return False
    else:
        logger.info("Started background database updates")
        return True


async def _stop_after_failed_background_start(stopper: BackgroundUpdateStopper) -> None:
    """Clean possible partial scheduler ownership without masking startup failure."""

    try:
        await stopper()
    except asyncio.CancelledError:
        task = asyncio.current_task()
        if task is not None and task.cancelling():
            raise
        logger.error("Error cleaning up a failed background scheduler start", exc_info=True)
    except BaseException:
        logger.error("Error cleaning up a failed background scheduler start", exc_info=True)


def _scheduler_stop_exit(
    stopper: BackgroundUpdateStopper,
) -> Callable[
    [type[BaseException] | None, BaseException | None, object | None],
    Awaitable[bool],
]:
    async def _stop(
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> bool:
        del exc_type, traceback
        try:
            await stopper()
        except asyncio.CancelledError:
            if exc is None:
                raise
            logger.error("Scheduler shutdown was cancelled during exception cleanup")
        except Exception:
            logger.error("Error stopping background updates", exc_info=True)
        else:
            logger.info("Stopped background database updates")
        return False

    return _stop


def _dispose_food_search_best_effort(
    app: FastAPI,
    lease: FoodSearchLifecycleLease,
    disposer: Callable[[FastAPI, FoodSearchLifecycleLease], None],
) -> None:
    try:
        disposer(app, lease)
    except Exception:
        logger.error("Error disposing food search resources", exc_info=True)


def _unified_food_release_exit(
    lease: UnifiedFoodLifecycleLease,
    releaser: UnifiedFoodReleaser,
) -> Callable[
    [type[BaseException] | None, BaseException | None, object | None],
    Awaitable[bool],
]:
    """Adapt unified-food release to the canonical exception-preserving exit contract."""

    async def _release(
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> bool:
        del exc_type, traceback
        try:
            await releaser(lease)
        except asyncio.CancelledError:
            if exc is None:
                raise
            logger.error("Unified-food shutdown was cancelled during exception cleanup")
        except Exception:
            logger.error("Error releasing unified-food resources", exc_info=True)
        return False

    return _release


@asynccontextmanager
async def _application_lifespan_with_hooks(
    app: FastAPI,
    *,
    hooks: LifespanHooks,
    scheduler_mode: SchedulerMode | None = None,
    deferred_background_update_hooks: (
        Callable[[], tuple[BackgroundUpdateStarter, BackgroundUpdateStopper]] | None
    ) = None,
) -> AsyncIterator[None]:
    """Run the canonical lifecycle with explicit dependencies."""

    async with AsyncExitStack() as stack:
        hooks.run_startup_guards(app)
        resolved_mode = scheduler_mode if scheduler_mode is not None else resolve_scheduler_mode()
        _initialize_database(hooks)
        hooks.validate_templates()

        unified_food_lease = await hooks.acquire_unified_food()
        stack.push_async_exit(
            _unified_food_release_exit(
                unified_food_lease,
                hooks.release_unified_food,
            )
        )

        food_search_lease = hooks.configure_food_search(app)
        stack.callback(
            _dispose_food_search_best_effort,
            app,
            food_search_lease,
            hooks.dispose_food_search,
        )

        if resolved_mode is SchedulerMode.IN_PROCESS_DEV:
            starter = hooks.start_background_updates
            stopper = hooks.stop_background_updates
            if deferred_background_update_hooks is not None:
                starter, stopper = deferred_background_update_hooks()
            started = await _start_background_updates_best_effort(
                starter,
                failed_start_stopper=stopper,
            )
            if started:
                stack.push_async_exit(_scheduler_stop_exit(stopper))
        yield


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan entrypoint using canonical runtime dependencies."""

    async with _application_lifespan_with_hooks(
        app,
        hooks=build_default_lifespan_hooks(),
        deferred_background_update_hooks=_load_background_update_hooks,
    ):
        yield
