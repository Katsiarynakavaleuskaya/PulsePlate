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

# Canonical legacy nutrition alias route template (SoT for allowlist/tests).
# RU: Канонический route template для legacy nutrition alias (SoT для allowlist/тестов).
# EN: Canonical route template for legacy nutrition alias (SoT for allowlist/tests).
LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE = "/api/nutrition/{date_str}"

# Explicit allowlist for legacy alias routes (low cardinality).
# RU: Явный allowlist legacy-алиасов (низкая кардинальность).
# EN: Explicit allowlist for legacy aliases (low cardinality).
LEGACY_ALIAS_ROUTE_ALLOWLIST: set[str] = {
    LEGACY_NUTRITION_DATE_ROUTE_TEMPLATE,
}
MEILI_SEARCH_STRATEGY_ALLOWLIST: set[str] = {
    "meili",
    "hybrid_shadow",
    "baseline_fts",
    "unknown",
}
MEILI_PERF_STATE_ALLOWLIST: set[str] = {
    "disabled",
    "captured",
    "missing",
    "invalid",
    "fallback",
}
MEILI_DEGRADED_ALLOWLIST: set[str] = {
    "true",
    "false",
    "unknown",
}
MEILI_STAGE_ALLOWLIST: set[str] = {
    "authorization",
    "tokenization",
    "keyword_search",
    "filtering",
    "ranking",
    "formatting",
}


class _CounterChild(Protocol):
    def inc(self, amount: float = 1.0) -> None: ...


class _Counter(Protocol):
    def labels(self, *, alias_route: str) -> _CounterChild: ...


class _MeiliCounter(Protocol):
    def labels(self, *, strategy: str, perf_state: str, degraded: str) -> _CounterChild: ...


class _HistogramChild(Protocol):
    def observe(self, amount: float) -> None: ...


class _MeiliHistogram(Protocol):
    def labels(self, *, strategy: str, perf_state: str, degraded: str) -> _HistogramChild: ...


class _MeiliStageHistogram(Protocol):
    def labels(self, *, strategy: str, stage: str) -> _HistogramChild: ...


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


def _import_prometheus_histogram(importer: _Importer = import_module) -> Any:
    """Import prometheus_client.Histogram in a patchable way."""

    prometheus_client = importer("prometheus_client")
    return prometheus_client.Histogram


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


def _build_food_search_meili_perf_events_total() -> _MeiliCounter | None:
    """Initialize Meilisearch performance event counter."""

    try:
        Counter = _import_prometheus()
    except ImportError:
        return None

    try:
        meili_perf_events_total: _MeiliCounter = cast(
            _MeiliCounter,
            Counter(
                "food_search_meili_perf_events_total",
                "Total number of Meilisearch performance detail events",
                labelnames=("strategy", "perf_state", "degraded"),
            ),
        )
    except ValueError:
        logger.warning(
            "Duplicate prometheus metric registration for "
            "food_search_meili_perf_events_total (metric disabled)",
            exc_info=True,
        )
        return None

    return meili_perf_events_total


def _build_food_search_meili_processing_time_ms() -> _MeiliHistogram | None:
    """Initialize Meilisearch total processing time histogram."""

    try:
        Histogram = _import_prometheus_histogram()
    except ImportError:
        return None

    try:
        meili_processing_time_ms: _MeiliHistogram = cast(
            _MeiliHistogram,
            Histogram(
                "food_search_meili_processing_time_ms",
                "Meilisearch total processing time in milliseconds",
                labelnames=("strategy", "perf_state", "degraded"),
                buckets=(1, 5, 10, 20, 50, 100, 250, 500, 1000, 2500, 5000),
            ),
        )
    except ValueError:
        logger.warning(
            "Duplicate prometheus metric registration for "
            "food_search_meili_processing_time_ms (metric disabled)",
            exc_info=True,
        )
        return None

    return meili_processing_time_ms


def _build_food_search_meili_stage_processing_time_ms() -> _MeiliStageHistogram | None:
    """Initialize Meilisearch stage processing time histogram."""

    try:
        Histogram = _import_prometheus_histogram()
    except ImportError:
        return None

    try:
        meili_stage_processing_time_ms: _MeiliStageHistogram = cast(
            _MeiliStageHistogram,
            Histogram(
                "food_search_meili_stage_processing_time_ms",
                "Meilisearch stage processing time in milliseconds",
                labelnames=("strategy", "stage"),
                buckets=(1, 5, 10, 20, 50, 100, 250, 500, 1000, 2500, 5000),
            ),
        )
    except ValueError:
        logger.warning(
            "Duplicate prometheus metric registration for "
            "food_search_meili_stage_processing_time_ms (metric disabled)",
            exc_info=True,
        )
        return None

    return meili_stage_processing_time_ms


LEGACY_ALIAS_REQUESTS_TOTAL: _Counter | None = _build_legacy_alias_requests_total()
FOOD_SEARCH_MEILI_PERF_EVENTS_TOTAL: _MeiliCounter | None = (
    _build_food_search_meili_perf_events_total()
)
FOOD_SEARCH_MEILI_PROCESSING_TIME_MS: _MeiliHistogram | None = (
    _build_food_search_meili_processing_time_ms()
)
FOOD_SEARCH_MEILI_STAGE_PROCESSING_TIME_MS: _MeiliStageHistogram | None = (
    _build_food_search_meili_stage_processing_time_ms()
)


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
    except Exception:
        logger.debug("Failed to record legacy alias metric", exc_info=True)


def _normalize_label_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower()


def _normalize_meili_strategy(strategy: object) -> str:
    normalized = _normalize_label_value(strategy)
    if normalized is None:
        return "unknown"
    if normalized in MEILI_SEARCH_STRATEGY_ALLOWLIST:
        return normalized
    return "unknown"


def _normalize_meili_perf_state(perf_state: object) -> str:
    normalized = _normalize_label_value(perf_state)
    if normalized is None:
        return "invalid"
    if normalized in MEILI_PERF_STATE_ALLOWLIST:
        return normalized
    return "invalid"


def _normalize_meili_degraded(degraded: object) -> str:
    normalized = _normalize_label_value(degraded)
    if normalized is None:
        return "unknown"
    if normalized in MEILI_DEGRADED_ALLOWLIST:
        return normalized
    return "unknown"


def _normalize_meili_stage(stage: object) -> str | None:
    normalized = _normalize_label_value(stage)
    if normalized is None:
        return None
    if normalized in MEILI_STAGE_ALLOWLIST:
        return normalized
    return None


def record_food_search_meili_performance(
    *,
    strategy: object,
    perf_state: object,
    degraded: object,
    processing_time_ms: float | None,
) -> None:
    """Record best-effort Meilisearch performance summary metrics."""

    normalized_strategy = _normalize_meili_strategy(strategy)
    normalized_perf_state = _normalize_meili_perf_state(perf_state)
    normalized_degraded = _normalize_meili_degraded(degraded)

    counter = FOOD_SEARCH_MEILI_PERF_EVENTS_TOTAL
    if counter is not None:
        try:
            counter.labels(
                strategy=normalized_strategy,
                perf_state=normalized_perf_state,
                degraded=normalized_degraded,
            ).inc()
        except Exception:
            logger.debug("Failed to record Meilisearch performance counter", exc_info=True)

    if processing_time_ms is None:
        return

    histogram = FOOD_SEARCH_MEILI_PROCESSING_TIME_MS
    if histogram is None:
        return

    try:
        histogram.labels(
            strategy=normalized_strategy,
            perf_state=normalized_perf_state,
            degraded=normalized_degraded,
        ).observe(processing_time_ms)
    except Exception:
        logger.debug("Failed to record Meilisearch performance histogram", exc_info=True)


def record_food_search_meili_stage_timing(
    *,
    strategy: object,
    stage: object,
    duration_ms: float,
) -> None:
    """Record best-effort Meilisearch stage timing metrics."""

    normalized_stage = _normalize_meili_stage(stage)
    if normalized_stage is None:
        return

    histogram = FOOD_SEARCH_MEILI_STAGE_PROCESSING_TIME_MS
    if histogram is None:
        return

    try:
        histogram.labels(
            strategy=_normalize_meili_strategy(strategy),
            stage=normalized_stage,
        ).observe(duration_ms)
    except Exception:
        logger.debug("Failed to record Meilisearch stage timing histogram", exc_info=True)
