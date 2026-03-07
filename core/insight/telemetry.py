"""Best-effort insight telemetry for philosophical runtime.

RU: Телеметрия runtime не должна ломать обработку запросов.
EN: Runtime telemetry must never affect request handling.
"""

from __future__ import annotations

import logging
from importlib import import_module
from typing import Any, Callable, Protocol, cast

logger = logging.getLogger(__name__)

_Importer = Callable[[str], Any]


class _CounterChild(Protocol):
    def inc(self, amount: float = 1.0) -> None: ...


class _Counter(Protocol):
    def labels(self, *, route_type: str, fallback_reason: str) -> _CounterChild: ...


class _RewriteCounter(Protocol):
    def labels(self, *, route_type: str) -> _CounterChild: ...


class _HistogramChild(Protocol):
    def observe(self, amount: float) -> None: ...


class _Histogram(Protocol):
    def labels(self, *, route_type: str) -> _HistogramChild: ...


def _import_prometheus(importer: _Importer = import_module) -> Any:
    """Import prometheus_client in a patchable way."""
    return importer("prometheus_client")


def _build_metrics() -> (
    tuple[_Counter | None, _RewriteCounter | None, _Histogram | None, _Histogram | None]
):
    """Build best-effort metrics with duplicate-registration protection."""
    try:
        prometheus_client = _import_prometheus()
    except ImportError:
        return None, None, None, None

    try:
        runtime_total = cast(
            _Counter,
            prometheus_client.Counter(
                "insight_philosophical_runtime_total",
                "Insight runtime executions by route and fallback reason",
                labelnames=("route_type", "fallback_reason"),
            ),
        )
        rewrite_total = cast(
            _RewriteCounter,
            prometheus_client.Counter(
                "insight_philosophical_runtime_rewrites_total",
                "Insight runtime rewrite attempts by route",
                labelnames=("route_type",),
            ),
        )
        depth_histogram = cast(
            _Histogram,
            prometheus_client.Histogram(
                "insight_philosophical_runtime_depth",
                "Depth chosen by philosophical runtime",
                labelnames=("route_type",),
                buckets=(1, 2, 3, 4),
            ),
        )
        token_savings_histogram = cast(
            _Histogram,
            prometheus_client.Histogram(
                "insight_philosophical_tokens_saved_estimate",
                "Estimated prompt-token savings by route",
                labelnames=("route_type",),
                buckets=(0, 20, 50, 100, 200, 500, 1000),
            ),
        )
        return runtime_total, rewrite_total, depth_histogram, token_savings_histogram
    except ValueError:
        logger.warning(
            "Duplicate philosophical runtime metrics registration (disabled)", exc_info=True
        )
        return None, None, None, None


(
    _RUNTIME_TOTAL,
    _REWRITE_TOTAL,
    _DEPTH_HISTOGRAM,
    _TOKEN_SAVINGS_HISTOGRAM,
) = _build_metrics()


def record_runtime_metrics(
    *,
    route_type: str,
    depth_used: int,
    tokens_saved_estimate: int,
    rewrite_count: int,
    fallback_reason: str,
) -> None:
    """Record low-cardinality runtime metrics."""
    try:
        if _RUNTIME_TOTAL is not None:
            _RUNTIME_TOTAL.labels(route_type=route_type, fallback_reason=fallback_reason).inc()
        if _DEPTH_HISTOGRAM is not None:
            _DEPTH_HISTOGRAM.labels(route_type=route_type).observe(float(depth_used))
        if _TOKEN_SAVINGS_HISTOGRAM is not None:
            _TOKEN_SAVINGS_HISTOGRAM.labels(route_type=route_type).observe(
                float(max(tokens_saved_estimate, 0))
            )
        if _REWRITE_TOTAL is not None and rewrite_count > 0:
            _REWRITE_TOTAL.labels(route_type=route_type).inc(float(rewrite_count))
    except (
        Exception
    ):  # nosec B110: telemetry must never affect request handling (remove-by: 2026-06-30, ref: PR-philosophical-runtime-foundation)
        logger.debug("Philosophical runtime metrics failed", exc_info=True)


__all__ = ["record_runtime_metrics"]
