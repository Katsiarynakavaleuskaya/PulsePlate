"""Application-level Prometheus metrics helpers.

RU: Хелперы Prometheus-метрик на уровне приложения.
EN: Prometheus metrics helpers at the application level.

Policy (hard):
- Only low-cardinality labels (explicit allowlist).
- Labels MUST use route templates (never raw paths, query params, user-correlated labels).
"""

from __future__ import annotations

import logging
from importlib import import_module
from typing import Any, Callable, Protocol, cast

logger = logging.getLogger(__name__)

# Explicit allowlist for legacy alias routes (low cardinality).
# RU: Явный allowlist legacy-алиасов (низкая кардинальность).
# EN: Explicit allowlist for legacy aliases (low cardinality).
LEGACY_ALIAS_ROUTE_ALLOWLIST: frozenset[str] = frozenset({"/api/nutrition/{date_str}"})


class _CounterChild(Protocol):
    def inc(self, amount: float = 1.0) -> None: ...


class _Counter(Protocol):
    def labels(self, *, alias_route: str) -> _CounterChild: ...


_Importer = Callable[[str], Any]


def _import_prometheus(importer: _Importer = import_module) -> Any:
    """Import prometheus_client.Counter in a patchable way.

    Returns:
        prometheus_client.Counter

    Raises:
        ImportError: If prometheus_client is not installed.
    """
    prometheus_client = importer("prometheus_client")
    return prometheus_client.Counter


def _build_legacy_alias_requests_total() -> _Counter | None:
    """Initialize legacy alias usage counter.

    Returns None if prometheus_client is unavailable OR metric registration fails
    (e.g., module reload causes duplicate names in the default registry).
    """
    try:
        Counter = _import_prometheus()
    except ImportError:
        return None

    try:
        legacy_alias_requests_total: _Counter = cast(
            _Counter,
            Counter(
                "legacy_alias_requests_total",
                "Total number of requests to deprecated legacy alias routes",
                labelnames=("alias_route",),
            ),
        )
    except ValueError:
        logger.warning(
            "Duplicate prometheus metric registration for legacy_alias_requests_total "
            "(metric disabled)",
            exc_info=True,
        )
        return None

    return legacy_alias_requests_total


LEGACY_ALIAS_REQUESTS_TOTAL: _Counter | None = _build_legacy_alias_requests_total()


def record_legacy_alias_hit(alias_route: str) -> None:
    """Record a hit to a deprecated legacy alias route (best-effort).

    RU: Зафиксировать обращение к legacy-алиасу (best-effort).
    EN: Record request to a legacy alias (best-effort).
    """
    if alias_route not in LEGACY_ALIAS_ROUTE_ALLOWLIST:
        return

    counter = LEGACY_ALIAS_REQUESTS_TOTAL
    if counter is None:
        return

    try:
        counter.labels(alias_route=alias_route).inc()
    except Exception:  # nosec B110 - metrics must never affect request handling
        pass
