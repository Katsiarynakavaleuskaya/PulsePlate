"""Test-only helpers that mirror the legacy plate patching utilities from app.py.

These helpers intentionally live under tests/ to avoid importing heavy snapshot logic
in production code paths while still exercising the behaviors through unit tests.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import contextmanager
from functools import wraps
from typing import Any, Awaitable, Callable, Iterable, Iterator, ParamSpec, TypeVar, cast

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

_PATCHED_ATTRS: list[str] = [
    "build_nutrition_targets",
    "make_plate",
    "api_premium_plate",
    "_aggregate_day_micronutrients",
]
_SNAPSHOT_SENTINEL: object = object()
_PATCH_SOURCE_IDS: dict[str, int | None] = {attr: None for attr in _PATCHED_ATTRS}

__all__ = [
    "_PATCHED_ATTRS",
    "_propagate_app_patches",
    "_sync_app_attr_sources",
    "_plate_env_snapshot",
    "_with_plate_env_snapshot",
]


def _propagate_app_patches(source: object | None, target: object | None) -> object | None:
    """Copy patched attributes from a source module to the target module."""
    if source is None or target is None:
        return None

    for attr in _PATCHED_ATTRS:
        if not hasattr(source, attr):
            continue
        value = getattr(source, attr)
        try:
            setattr(target, attr, value)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("_propagate_app_patches failed for %s: %s", attr, exc)
    return target


def _sync_app_attr_sources(alias_module: object, sources: Iterable[object]) -> object | None:
    """Best-effort synchronization of exported attributes across modules."""
    if alias_module is None or not sources:
        return alias_module

    for source in sources:
        if source is None:
            continue
        try:
            attributes = dir(source)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("_sync_app_attr_sources: dir() failed for %r: %s", source, exc)
            continue

        for attr_name in attributes:
            if attr_name.startswith("_") or attr_name not in _PATCHED_ATTRS:
                continue
            try:
                value = getattr(source, attr_name)
            except AttributeError:
                continue
            current_value = getattr(alias_module, attr_name, None)
            if current_value is value:
                continue
            source_id = id(value)
            if _PATCH_SOURCE_IDS.get(attr_name) == source_id:
                continue
            try:
                setattr(alias_module, attr_name, value)
                _PATCH_SOURCE_IDS[attr_name] = source_id
            except Exception as exc:  # pragma: no cover - ignore setattr failures
                logger.debug(
                    "_sync_app_attr_sources: setattr failed for alias=%r attr=%s err=%s",
                    alias_module,
                    attr_name,
                    exc,
                )
    return alias_module


@contextmanager
def _plate_env_snapshot() -> Iterator[None]:
    """Capture and restore selected module attributes after temporary patching."""
    snapshot: list[tuple[object, dict[str, object]]] = []
    try:
        modules = list(sys.modules.values())
    except Exception:  # pragma: no cover
        modules = []

    for module in modules:
        if module is None or not hasattr(module, "__dict__"):
            continue
        stored: dict[str, Any] = {}
        for attr_name in _PATCHED_ATTRS:
            if hasattr(module, attr_name):
                stored[attr_name] = getattr(module, attr_name)
            else:
                stored[attr_name] = _SNAPSHOT_SENTINEL
        if stored:
            snapshot.append((module, stored))

    env_snapshot = dict(os.environ)

    try:
        yield
    finally:
        # Restore environment variables
        current_keys = set(os.environ.keys())
        original_keys = set(env_snapshot.keys())
        for key in current_keys - original_keys:
            os.environ.pop(key, None)
        for key, value in env_snapshot.items():
            os.environ[key] = value

        for module, attrs in snapshot:
            for attr_name, original_value in attrs.items():
                try:
                    if original_value is _SNAPSHOT_SENTINEL:
                        if hasattr(module, attr_name):
                            delattr(module, attr_name)
                    else:
                        setattr(module, attr_name, original_value)
                except Exception as exc:  # pragma: no cover
                    logger.debug(
                        "_plate_env_snapshot: failed to restore %s on %r: %s",
                        attr_name,
                        module,
                        exc,
                    )


def _with_plate_env_snapshot(
    func: Callable[P, Awaitable[T]] | Callable[P, T],
) -> Callable[P, Awaitable[T]] | Callable[P, T]:
    """Decorator that wraps execution with _plate_env_snapshot."""

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with _plate_env_snapshot():
                return await cast(Callable[P, Awaitable[T]], func)(*args, **kwargs)

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with _plate_env_snapshot():
            return cast(Callable[P, T], func)(*args, **kwargs)

    return sync_wrapper
