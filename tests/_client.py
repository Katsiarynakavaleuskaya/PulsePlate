"""Canonical TestClient factory for tests.

Ensures all tests use app.main:app (canonical entrypoint with observability bootstrap).
Prevents bypassing /metrics registration, middleware, and lifespan wiring.
"""

from __future__ import annotations

import inspect
import os
from contextlib import contextmanager
from types import TracebackType
from typing import TYPE_CHECKING, Any, Iterator, NoReturn

from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from httpx2 import Request, Response
else:
    try:
        from httpx2 import Request, Response
    except ModuleNotFoundError:
        from httpx import Request, Response

from app.effective_routes import (
    is_api_route_candidate,
    iter_effective_route_candidates,
    route_endpoint,
)

_LIMITER_OWNED_ATTRIBUTES = (
    "enabled",
    "_key_func",
    "_auto_check",
    "_check_request_limit",
)
_CapturedError = tuple[BaseException, TracebackType | None]


def _rate_limiting_opted_in() -> bool:
    """Return whether a dedicated test suite explicitly owns limiter behavior."""

    return os.getenv("RATE_LIMITING_IN_TESTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _iter_test_limiters(app_instance: FastAPI) -> Iterator[Any]:
    """Yield the finite canonical SlowAPI limiter surface for one test app."""

    try:
        from slowapi import Limiter
    except ImportError:  # pragma: no cover - optional dependency
        return

    from app.security import rate_limit as rate_limit_mod

    seen_limiters: set[int] = set()
    candidates: list[object | None] = [
        getattr(rate_limit_mod, "limiter", None),
        getattr(app_instance.state, "limiter", None),
    ]

    for route in iter_effective_route_candidates(app_instance.routes):
        if not is_api_route_candidate(route):
            continue
        endpoint = route_endpoint(route)
        if endpoint is None or not callable(endpoint):
            continue
        try:
            candidates.extend(inspect.getclosurevars(endpoint).nonlocals.values())
        except TypeError:
            continue

    for candidate in candidates:
        if not isinstance(candidate, Limiter):
            continue
        limiter_id = id(candidate)
        if limiter_id in seen_limiters:
            continue
        seen_limiters.add(limiter_id)
        yield candidate


def _snapshot_limiter_attributes(limiter_instance: Any) -> dict[str, tuple[bool, Any]]:
    """Capture exact instance ownership for the finite limiter policy attributes."""

    namespace = vars(limiter_instance)
    return {name: (name in namespace, namespace.get(name)) for name in _LIMITER_OWNED_ATTRIBUTES}


def _restore_limiter_attributes(
    limiter_instance: Any,
    snapshot: dict[str, tuple[bool, Any]],
) -> None:
    """Restore limiter attributes without leaving new instance-owned shadows."""

    namespace = vars(limiter_instance)
    for name, (was_owned, value) in snapshot.items():
        if was_owned:
            setattr(limiter_instance, name, value)
        elif name in namespace:
            delattr(limiter_instance, name)


def _reset_and_disable_limiter(limiter_instance: Any) -> None:
    """Clear counters and disable one verified SlowAPI limiter."""

    limiter_instance.reset()
    limiter_instance.enabled = False


def _cleanup_error_context(errors: list[_CapturedError]) -> BaseException:
    """Build one ordered context without changing the primary failure."""

    prepared = [error.with_traceback(traceback) for error, traceback in errors]
    if len(prepared) == 1:
        return prepared[0]
    return BaseExceptionGroup("open_test_client cleanup failures", prepared)


def _raise_after_cleanup(
    primary_error: _CapturedError | None,
    cleanup_errors: list[_CapturedError],
) -> NoReturn:
    """Raise the primary failure, or the first cleanup failure after restore-all."""

    if primary_error is not None:
        error, traceback = primary_error
        if cleanup_errors:
            error.add_note(f"open_test_client cleanup encountered {len(cleanup_errors)} failure(s)")
            raise error.with_traceback(traceback) from _cleanup_error_context(cleanup_errors)
        raise error.with_traceback(traceback)

    first_error, *remaining_errors = cleanup_errors
    error, traceback = first_error
    if remaining_errors:
        error.add_note(
            "open_test_client preserved the first cleanup failure after "
            f"{len(remaining_errors)} additional failure(s)"
        )
        raise error.with_traceback(traceback) from _cleanup_error_context(remaining_errors)
    raise error.with_traceback(traceback)


def disable_rate_limiting_for_test_app(app_instance: FastAPI) -> None:
    """Deprecated compatibility helper; prefer ``open_test_client``."""

    if _rate_limiting_opted_in():
        return

    for limiter_instance in _iter_test_limiters(app_instance):
        _reset_and_disable_limiter(limiter_instance)


def override_rate_limit_identity_for_test_app(
    app_instance: FastAPI,
    *,
    limiter_key: str,
    monkeypatch: Any,
) -> None:
    """Pin route-level limiter identity to a deterministic key for one test app.

    RU: Принудительно задаёт единый limiter key и отключает auto-check для теста.
    EN: Forces a stable limiter key and disables auto-check for deterministic tests.
    """

    for limiter in _iter_test_limiters(app_instance):
        monkeypatch.setattr(
            limiter,
            "_key_func",
            lambda request, key=limiter_key: key,
            raising=False,
        )
        monkeypatch.setattr(limiter, "_auto_check", False, raising=False)
        monkeypatch.setattr(
            limiter,
            "_check_request_limit",
            lambda *args, **kwargs: None,
            raising=False,
        )


class MetricsAwareTestClient(TestClient):
    """TestClient that auto-adds the test API key for implicit `/metrics` probes."""

    auto_metrics_api_key = True

    def send(self, request: Request, **kwargs: Any) -> Response:
        has_explicit_auth_header = "x-api-key" in request.headers
        if (
            getattr(self, "auto_metrics_api_key", True)
            and request.url.path == "/metrics"
            and not has_explicit_auth_header
        ):
            request.headers["X-API-Key"] = os.getenv("API_KEY", "test_key")
        return super().send(request, **kwargs)


def make_test_client(app_instance: FastAPI, **kwargs: Any) -> MetricsAwareTestClient:
    """Deprecated raw constructor retained for TC2 compatibility only."""

    return MetricsAwareTestClient(app_instance, **kwargs)


@contextmanager
def open_test_client(
    app_instance: FastAPI | None = None,
    **kwargs: Any,
) -> Iterator[MetricsAwareTestClient]:
    """Open one canonical client and restore app-owned mutable test state."""

    if app_instance is None:
        import app.main

        app_instance = app.main.app

    overrides_owner = app_instance.dependency_overrides
    overrides_snapshot = dict(overrides_owner)
    limiter_snapshots: list[tuple[Any, dict[str, tuple[bool, Any]]]] = []
    limiter_opt_in = _rate_limiting_opted_in()
    primary_error: _CapturedError | None = None
    cleanup_errors: list[_CapturedError] = []

    try:
        if not limiter_opt_in:
            for limiter_instance in _iter_test_limiters(app_instance):
                limiter_snapshots.append(
                    (
                        limiter_instance,
                        _snapshot_limiter_attributes(limiter_instance),
                    )
                )
            for limiter_instance, _snapshot in limiter_snapshots:
                _reset_and_disable_limiter(limiter_instance)

        with make_test_client(app_instance, **kwargs) as client:
            try:
                yield client
            except BaseException as error:
                primary_error = (error, error.__traceback__)
    except BaseException as error:
        lifecycle_error = (error, error.__traceback__)
        if primary_error is None:
            primary_error = lifecycle_error
        else:
            cleanup_errors.append(lifecycle_error)
    finally:
        try:
            if app_instance.dependency_overrides is not overrides_owner:
                app_instance.dependency_overrides = overrides_owner
        except BaseException as error:
            cleanup_errors.append((error, error.__traceback__))
        try:
            overrides_owner.clear()
        except BaseException as error:
            cleanup_errors.append((error, error.__traceback__))
        try:
            overrides_owner.update(overrides_snapshot)
        except BaseException as error:
            cleanup_errors.append((error, error.__traceback__))

        if not limiter_opt_in:
            for limiter_instance, snapshot in limiter_snapshots:
                try:
                    limiter_instance.reset()
                except BaseException as error:
                    cleanup_errors.append((error, error.__traceback__))
                try:
                    _restore_limiter_attributes(limiter_instance, snapshot)
                except BaseException as error:
                    cleanup_errors.append((error, error.__traceback__))

    if primary_error is not None or cleanup_errors:
        _raise_after_cleanup(primary_error, cleanup_errors)


def get_client(**kwargs: Any) -> TestClient:
    """Deprecated raw client factory retained for TC2 compatibility.

    Always uses app.main.app (bootstrap-enabled) to ensure:
    - /metrics endpoint is registered
    - Observability middleware is active
    - Lifespan events are properly wired

    Args:
        **kwargs: Pass-through arguments to TestClient
                  (e.g., raise_server_exceptions=False, headers={...})

    Returns:
        TestClient instance configured with canonical entrypoint.

    Example:
        >>> client = get_client()
        >>> response = client.get("/metrics")
        >>> assert response.status_code == 200

    IMPORTANT: Import app.main inside function (not module-level) to ensure
    pytest_configure sets TESTING=true before app initialization.
    """
    # Import inside function to respect pytest_configure TESTING env setup
    import app.main

    disable_rate_limiting_for_test_app(app.main.app)
    return make_test_client(app.main.app, **kwargs)
