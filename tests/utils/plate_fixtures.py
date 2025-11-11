"""Test utilities for plate environment isolation.

RU: Утилиты для изоляции окружения premium plate в тестах.
EN: Utilities for isolating premium plate environment in tests.

WARNING: NOT THREAD-SAFE - do not use with concurrent threads.
"""

from __future__ import annotations

import os
import sys
import threading
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator

# Attributes that are patched in tests and need snapshotting
_PATCHED_ATTRS = (
    "make_plate",
    "calculate_all_bmr",
    "calculate_all_tdee",
    "_aggregate_day_micronutrients",
    "build_nutrition_targets",
)


# WARNING: NOT THREAD-SAFE - do not use with concurrent threads
@contextmanager
def plate_env_snapshot() -> Generator[None, None, None]:
    """WARNING: NOT THREAD-SAFE - Isolate premium plate globals/env for each request/test run.

    DANGER: This context manager is NOT thread-safe and is intended ONLY for
    single-threaded test/request isolation. It modifies module attributes via
    setattr/delattr which can cause race conditions in concurrent execution.

    Do NOT use this in production with concurrent requests. It is designed for:
    - Single-threaded test isolation (pytest with -n 0 or function-scoped fixtures)
    - Development/debugging scenarios where thread safety is not required

    The restoration logic uses setattr/delattr on module objects (sys.modules[__name__])
    instead of direct globals() mutation to maintain cleaner module state management,
    but this is still not atomic and not thread-safe.

    Raises:
        RuntimeError: If called in a multithreaded context (threading.active_count() > 1)
    """
    # Runtime guard: fail-fast if used in multithreaded context
    if threading.active_count() > 1:
        raise RuntimeError(
            f"plate_env_snapshot() is not thread-safe and cannot be used with "
            f"concurrent threads. Current thread count: {threading.active_count()}. "
            f"Use single-threaded test execution (pytest -n 0) or function-scoped fixtures."
        )

    sentinel = object()
    env_snapshot = os.environ.get("FEATURE_PREMIUM_NUTRITION", sentinel)
    module_snapshots: list[tuple[object, dict[str, Any]]] = []

    def _capture(module: object | None) -> None:
        if module is None:
            return
        for existing, _ in module_snapshots:
            if existing is module:
                return
        module_snapshots.append(
            (
                module,
                {attr: getattr(module, attr, sentinel) for attr in _PATCHED_ATTRS},
            )
        )

    _capture(sys.modules.get(__name__))
    _capture(sys.modules.get("app"))
    _capture(sys.modules.get("app_module"))
    _capture(sys.modules.get("_app_top_module"))

    try:
        yield
    finally:
        # Restore patched attributes using module setattr/delattr
        # This avoids direct globals() mutation but is still not thread-safe
        for module, snapshot in module_snapshots:
            for attr, original in snapshot.items():
                if original is sentinel:
                    # Attribute didn't exist originally, remove it
                    try:
                        delattr(module, attr)
                    except AttributeError:
                        pass
                else:
                    # Restore original value using module setattr
                    setattr(module, attr, original)
        # Restore environment variable
        if env_snapshot is sentinel:
            os.environ.pop("FEATURE_PREMIUM_NUTRITION", None)
        else:
            os.environ["FEATURE_PREMIUM_NUTRITION"] = str(env_snapshot)


def with_plate_env_snapshot(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to run a function within an isolated plate environment snapshot.

    Supports both sync and async callables.
    """
    import asyncio

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def _async_wrapped(*args: Any, **kwargs: Any) -> Any:
            with plate_env_snapshot():
                return await func(*args, **kwargs)

        return _async_wrapped

    @wraps(func)
    def _sync_wrapped(*args: Any, **kwargs: Any) -> Any:
        with plate_env_snapshot():
            return func(*args, **kwargs)

    return _sync_wrapped
