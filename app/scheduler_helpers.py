from __future__ import annotations

import asyncio
import importlib
import inspect
from contextlib import suppress
from typing import Any, Callable, Optional, cast


def resolve_app_package(pkg: Any, fallback_pkg: Any) -> Any:
    """Return the canonical app package when sys.modules churn leaves stale aliases."""
    for candidate in (pkg, fallback_pkg):
        if candidate is not None and getattr(candidate, "__path__", None):
            return candidate

    with suppress(Exception):
        imported_pkg = importlib.import_module("app")
        if getattr(imported_pkg, "__path__", None):
            return imported_pkg

    return pkg or fallback_pkg


def resolve_scheduler_starter(
    pkg: Any,
    alias_pkg: Any,
    globs: dict[str, Any],
    default_starter: Callable[[int], Any],
) -> Callable[[int], Any]:
    """Resolve the scheduler starter callable from package/module hierarchy.

    Returns the best available starter callable, falling back to default_starter.
    """
    pkg_appmod = getattr(pkg, "app_module", None) if pkg else None
    starter = (
        getattr(pkg, "_scheduler_start_background_updates", None)
        or (
            getattr(pkg_appmod, "_scheduler_start_background_updates", None) if pkg_appmod else None
        )
        or getattr(alias_pkg, "_scheduler_start_background_updates", None)
    )
    if callable(starter):
        resolved_starter = cast(Callable[[int], Any], starter)
        return resolved_starter

    starter = globs.get("_scheduler_start_background_updates", default_starter)
    if callable(starter) and starter is not default_starter:
        resolved_starter = cast(Callable[[int], Any], starter)
        return resolved_starter

    return default_starter


def resolve_stop_callable(
    pkg: Any,
    alias_pkg: Any,
    globs: dict[str, Any],
    default_stopper: Callable[[], Any],
) -> Callable[[], Any]:
    """Resolve the stop callable from package/module hierarchy.

    Returns the best available stopper callable, falling back to default_stopper.
    """
    pkg_appmod = getattr(pkg, "app_module", None) if pkg else None
    stopper = (
        getattr(pkg, "_scheduler_stop_background_updates", None)
        or (getattr(pkg_appmod, "_scheduler_stop_background_updates", None) if pkg_appmod else None)
        or getattr(alias_pkg, "_scheduler_stop_background_updates", None)
    )
    if callable(stopper):
        resolved_stopper = cast(Callable[[], Any], stopper)
        return resolved_stopper

    stopper = globs.get("_scheduler_stop_background_updates", default_stopper)
    if callable(stopper) and stopper is not default_stopper:
        resolved_stopper = cast(Callable[[], Any], stopper)
        return resolved_stopper

    return default_stopper


def handle_sync_test_mode(
    target: Callable[..., Any],
    update_interval_hours: Optional[int],
    caller_called: Optional[list[Any]],
) -> None:
    """Handle pytest sync mode by calling target and managing awaitables.

    Detects running loop and either schedules on it or runs in a new loop.
    Appends to caller_called list if provided.
    """
    # Call target with appropriate args
    if update_interval_hours is not None:
        res = target(update_interval_hours=update_interval_hours)
    else:
        res = target()

    if inspect.isawaitable(res):
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is not None:
            # Already inside event loop - schedule the coroutine
            asyncio.ensure_future(res)
        elif inspect.iscoroutine(res):
            asyncio.run(res)
        else:
            loop = asyncio.new_event_loop()
            try:
                _ = loop.run_until_complete(res)
            finally:
                loop.close()

    if caller_called is not None:
        with suppress(Exception):
            if update_interval_hours is not None:
                caller_called.append(update_interval_hours)
            else:
                caller_called.append("stop")


def execute_async_starter(
    starter: Callable[[int], Any], update_interval_hours: int, _asyncio: Any
) -> None:
    """Execute async starter in the current loop or create a new one.

    If a running loop exists, schedules starter as a task.
    Otherwise, runs starter using asyncio.run in a new loop.
    """
    loop: Optional[asyncio.AbstractEventLoop] = None
    try:
        loop = _asyncio.get_running_loop()
    except RuntimeError:
        pass

    if loop is None:
        asyncio.run(starter(update_interval_hours))
    else:
        loop.create_task(starter(update_interval_hours))


def safe_stop_with_cleanup(stopper: Callable[[], Any]) -> None:
    """Run stopper in a new event loop with proper cleanup and error suppression.

    Suppresses ResourceWarning and RuntimeWarning during cleanup.
    Catches and logs RuntimeError related to event loop closure.
    """
    try:
        # Suppress all warnings during event loop cleanup to avoid
        # ResourceWarning and RuntimeError from httpx/anyio cleanup
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            warnings.simplefilter("ignore", RuntimeWarning)

            result = stopper()
            if inspect.isawaitable(result):
                asyncio.run(result)  # type: ignore[arg-type]
    except RuntimeError as e:
        # Suppress "Event loop is closed" errors during cleanup
        error_msg = str(e)
        if "Event loop is closed" in error_msg or "loop" in error_msg.lower():
            # Log for debugging but don't propagate
            import logging

            logging.getLogger(__name__).debug(
                "Suppressed event loop cleanup error during scheduler stop: %s", error_msg
            )
        else:  # pragma: no cover - unexpected runtime error
            raise
