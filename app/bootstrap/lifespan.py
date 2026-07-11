"""Canonical FastAPI startup and shutdown resource ownership."""

from __future__ import annotations

import asyncio
import logging
import math
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any, Protocol

from fastapi import FastAPI

from app.bootstrap.food_search import FoodSearchLifecycleLease
from settings import get_runtime_env_name, is_production_like_env, is_truthy_env_var

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


async def _unavailable_background_update_start(
    update_interval_hours: int = BACKGROUND_UPDATE_INTERVAL_HOURS,
) -> None:
    """Keep startup best-effort when the optional scheduler cannot import."""

    del update_interval_hours


async def _unavailable_background_update_stop() -> None:
    """No-op counterpart for an unavailable optional scheduler."""


def _load_background_update_hooks() -> tuple[BackgroundUpdateStarter, BackgroundUpdateStopper]:
    """Load optional scheduler hooks without making them a startup dependency."""

    try:
        from core.food_apis.scheduler import (
            start_background_updates,
            stop_background_updates,
        )
    except ImportError:
        logger.warning(
            "Background update scheduler is unavailable; continuing without it.",
            exc_info=True,
        )
        return _unavailable_background_update_start, _unavailable_background_update_stop
    return start_background_updates, stop_background_updates


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


def build_default_lifespan_hooks() -> LifespanHooks:
    """Resolve canonical lifecycle callables at each lifespan entry."""

    from app.bootstrap.food_search import (
        configure_food_search_backend,
        dispose_food_search_backend,
    )
    from app.bootstrap.startup_guards import run_startup_guards
    from app.dependencies import validate_template_dir
    from core.db import init_db
    from core.db_fallback import attempt_db_fallback, clear_fallback_active

    start_background_updates, stop_background_updates = _load_background_update_hooks()

    return LifespanHooks(
        run_startup_guards=run_startup_guards,
        initialize_database=init_db,
        clear_database_fallback=clear_fallback_active,
        attempt_database_fallback=attempt_db_fallback,
        validate_templates=validate_template_dir,
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
) -> None:
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
        return

    timeout = _background_start_timeout_seconds()
    task: asyncio.Task[None] = asyncio.create_task(
        starter(update_interval_hours=BACKGROUND_UPDATE_INTERVAL_HOURS),
        name="pulseplate-background-update-start",
    )
    try:
        await asyncio.wait_for(task, timeout=timeout)
    except TimeoutError:
        await _drain_cancelled_task(task)
        logger.error(
            "Background updates startup timed out after %.0f seconds",
            timeout,
        )
    except asyncio.CancelledError:
        await _drain_cancelled_task(task)
        raise
    except Exception:
        logger.error("Failed to start background updates", exc_info=True)
    else:
        logger.info("Started background database updates")


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


@asynccontextmanager
async def _application_lifespan_with_hooks(
    app: FastAPI,
    *,
    hooks: LifespanHooks,
) -> AsyncIterator[None]:
    """Run the canonical lifecycle with explicit dependencies."""

    async with AsyncExitStack() as stack:
        hooks.run_startup_guards(app)
        _initialize_database(hooks)
        hooks.validate_templates()

        food_search_lease = hooks.configure_food_search(app)
        stack.callback(
            _dispose_food_search_best_effort,
            app,
            food_search_lease,
            hooks.dispose_food_search,
        )
        stack.push_async_exit(_scheduler_stop_exit(hooks.stop_background_updates))

        await _start_background_updates_best_effort(hooks.start_background_updates)
        yield


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan entrypoint using canonical runtime dependencies."""

    async with _application_lifespan_with_hooks(
        app,
        hooks=build_default_lifespan_hooks(),
    ):
        yield
