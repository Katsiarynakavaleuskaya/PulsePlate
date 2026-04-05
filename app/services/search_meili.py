"""Optional Meilisearch-backed search adapters with safe fallbacks."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
import logging
import math
import re
import threading
from typing import Any, Literal, TYPE_CHECKING

import httpx

from app.metrics import (
    record_food_search_meili_performance,
    record_food_search_meili_stage_timing,
)

if TYPE_CHECKING:
    from app.services.food_store import FoodSearchBackend

logger = logging.getLogger(__name__)

Transport = Callable[[str, dict[str, Any], Mapping[str, str], float], Any]
ShadowTaskRunner = Callable[[Callable[[], None]], None]
_MAX_CONCURRENT_SHADOW_TASKS = 4
_shadow_task_slots = threading.BoundedSemaphore(_MAX_CONCURRENT_SHADOW_TASKS)
_MAX_MEILI_DURATION_MS = 600_000.0
_PERF_DURATION_KEYS = (
    "durationMs",
    "elapsedMs",
    "processingTimeMs",
    "timeMs",
    "totalMs",
)
_TOTAL_DURATION_KEYS = (
    "processingTimeMs",
    "totalProcessingTimeMs",
    "totalMs",
    "search",
)
_STAGE_NAME_ALIASES = {
    "authorization": "authorization",
    "authorizationms": "authorization",
    "authorize": "authorization",
    "authorizems": "authorization",
    "waitforpermit": "authorization",
    "tokenization": "tokenization",
    "tokenizationms": "tokenization",
    "tokenize": "tokenization",
    "tokenizems": "tokenization",
    "searchtokenize": "tokenization",
    "keywordsearch": "keyword_search",
    "keywordsearchms": "keyword_search",
    "keywords": "keyword_search",
    "keywordms": "keyword_search",
    "search": "keyword_search",
    "searchms": "keyword_search",
    "filtering": "filtering",
    "filteringms": "filtering",
    "filters": "filtering",
    "filtersms": "filtering",
    "searchfilter": "filtering",
    "ranking": "ranking",
    "rankingms": "ranking",
    "searchranking": "ranking",
    "formatting": "formatting",
    "formattingms": "formatting",
    "format": "formatting",
    "formatms": "formatting",
    "searchformat": "formatting",
}
_DURATION_VALUE_RE = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ns|us|µs|μs|ms|s)\s*$",
    re.IGNORECASE,
)

# Single source of truth for foods index search request shape (contract-stable).
# RU: Единый SoT для формы запроса к индексу foods (стабильный контракт).
# EN: Single source of truth for foods index search request shape (stable contract).
MEILI_FOODS_ATTRIBUTES_TO_RETRIEVE: tuple[str, ...] = (
    "id",
    "canonical_name",
    "name",
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "source",
    "content_hash",
)


def build_meili_foods_search_url(base_url: str, index_name: str) -> str:
    """Return the Meilisearch search URL for a given index."""

    normalized_base = base_url.rstrip("/")
    return f"{normalized_base}/indexes/{index_name}/search"


def build_meili_foods_search_headers(api_key: str | None) -> dict[str, str]:
    """Return Authorization headers for Meilisearch or an empty dict."""

    cleaned = (api_key or "").strip()
    if not cleaned:
        return {}
    return {"Authorization": f"Bearer {cleaned}"}


def build_meili_foods_search_payload(
    *,
    query: str,
    limit: int,
    offset: int,
    show_performance_details: bool,
) -> dict[str, Any]:
    """Build the JSON body for a foods index search (attributes + optional perf flag)."""

    payload: dict[str, Any] = {
        "q": query,
        "limit": limit,
        "offset": offset,
        "attributesToRetrieve": list(MEILI_FOODS_ATTRIBUTES_TO_RETRIEVE),
    }
    if show_performance_details:
        payload["showPerformanceDetails"] = True
    return payload


@dataclass(frozen=True)
class NormalizedMeiliPerformanceDetails:
    """Sanitized Meilisearch performance summary for observability only."""

    state: Literal["disabled", "captured", "missing", "invalid", "fallback"]
    processing_time_ms: float | None
    degraded: Literal["true", "false", "unknown"]
    stage_timings_ms: dict[str, float]


def _numeric_field_or_default(hit: Mapping[str, Any], key: str) -> int | float:
    """Normalize optional numeric nutrient fields to deterministic defaults."""

    value = hit.get(key)
    if isinstance(value, bool):
        return 0
    return value if isinstance(value, (int, float)) else 0


def _normalize_degraded_flag(value: object) -> Literal["true", "false", "unknown"]:
    """Normalize degraded flag to a low-cardinality string."""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return "true"
        if normalized == "false":
            return "false"
    return "unknown"


def _coerce_non_negative_ms(value: object) -> float | None:
    """Return a bounded millisecond value or None."""

    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        match = _DURATION_VALUE_RE.match(value)
        if match is None:
            return None
        numeric_value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit == "ns":
            normalized = numeric_value / 1_000_000
        elif unit in {"us", "µs", "μs"}:
            normalized = numeric_value / 1_000
        elif unit == "ms":
            normalized = numeric_value
        else:
            normalized = numeric_value * 1_000
        if not math.isfinite(normalized):
            return None
        if normalized < 0 or normalized > _MAX_MEILI_DURATION_MS:
            return None
        return normalized
    if not isinstance(value, (int, float)):
        return None
    normalized = float(value)
    if not math.isfinite(normalized):
        return None
    if normalized < 0 or normalized > _MAX_MEILI_DURATION_MS:
        return None
    return normalized


def _normalize_stage_name(key: str) -> str | None:
    """Map vendor stage names to repo-owned labels."""

    normalized = (
        key.strip().lower().replace("-", "").replace("_", "").replace(">", "").replace(" ", "")
    )
    return _STAGE_NAME_ALIASES.get(normalized)


def _duration_from_candidate(value: object) -> float | None:
    """Extract a bounded duration value from a numeric or mapping candidate."""

    numeric_value = _coerce_non_negative_ms(value)
    if numeric_value is not None:
        return numeric_value
    if not isinstance(value, Mapping):
        return None
    for key in _PERF_DURATION_KEYS:
        duration = _coerce_non_negative_ms(value.get(key))
        if duration is not None:
            return duration
    return None


def _extract_stage_timings(details: Mapping[str, Any]) -> dict[str, float]:
    """Extract sanitized stage timings from vendor performance details."""

    stage_timings: dict[str, float] = {}
    for raw_key, raw_value in details.items():
        stage_name = _normalize_stage_name(raw_key)
        if stage_name is None or stage_name in stage_timings:
            continue
        duration_ms = _duration_from_candidate(raw_value)
        if duration_ms is not None:
            stage_timings[stage_name] = duration_ms
    return stage_timings


def _extract_processing_time_ms(
    response: Mapping[str, Any],
    details: Mapping[str, Any] | None,
    stage_timings: Mapping[str, float],
) -> float | None:
    """Extract total processing time from known safe fields."""

    processing_time_ms = _coerce_non_negative_ms(response.get("processingTimeMs"))
    if processing_time_ms is not None:
        return processing_time_ms
    if details is not None:
        for key in _TOTAL_DURATION_KEYS:
            processing_time_ms = _coerce_non_negative_ms(details.get(key))
            if processing_time_ms is not None:
                return processing_time_ms
    if stage_timings:
        total_stage_time_ms = sum(stage_timings.values())
        if total_stage_time_ms <= _MAX_MEILI_DURATION_MS:
            return total_stage_time_ms
    return None


def _normalize_performance_details(
    response: Mapping[str, Any],
    *,
    enabled: bool,
    fallback: bool = False,
) -> NormalizedMeiliPerformanceDetails:
    """Return a sanitized performance summary from a Meili response."""

    if fallback:
        return NormalizedMeiliPerformanceDetails(
            state="fallback",
            processing_time_ms=None,
            degraded="unknown",
            stage_timings_ms={},
        )
    if not enabled:
        return NormalizedMeiliPerformanceDetails(
            state="disabled",
            processing_time_ms=None,
            degraded="unknown",
            stage_timings_ms={},
        )

    raw_details = response.get("performanceDetails")
    if raw_details is None:
        return NormalizedMeiliPerformanceDetails(
            state="missing",
            processing_time_ms=_extract_processing_time_ms(response, None, {}),
            degraded=_normalize_degraded_flag(response.get("degraded")),
            stage_timings_ms={},
        )
    if not isinstance(raw_details, Mapping):
        return NormalizedMeiliPerformanceDetails(
            state="invalid",
            processing_time_ms=_extract_processing_time_ms(response, None, {}),
            degraded=_normalize_degraded_flag(response.get("degraded")),
            stage_timings_ms={},
        )

    stage_timings_ms = _extract_stage_timings(raw_details)
    processing_time_ms = _extract_processing_time_ms(response, raw_details, stage_timings_ms)
    degraded = _normalize_degraded_flag(raw_details.get("degraded", response.get("degraded")))
    if processing_time_ms is None and not stage_timings_ms and degraded == "unknown":
        state: Literal["captured", "invalid"] = "invalid"
    else:
        state = "captured"
    return NormalizedMeiliPerformanceDetails(
        state=state,
        processing_time_ms=processing_time_ms,
        degraded=degraded,
        stage_timings_ms=stage_timings_ms,
    )


def _default_transport(
    url: str,
    payload: dict[str, Any],
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> Any:
    """Execute a POST request against Meilisearch (one short-lived client per call)."""

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(url, json=payload, headers=dict(headers))
        response.raise_for_status()
        parsed_response: Any
        parsed_response = response.json()
        return parsed_response


def make_pooled_httpx_transport(
    client: httpx.Client,
    *,
    shutdown_event: threading.Event | None = None,
) -> Transport:
    """Bind POST semantics to a long-lived :class:`httpx.Client` for connection reuse.

    RU: Переиспользование соединений через общий клиент; закрытие — на стороне владельца.
    EN: Reuse connections via a shared client; the owner must close the client on shutdown.

    When ``shutdown_event`` is set before :meth:`httpx.Client.post`, callers get
    :class:`httpx.RequestError` so shadow threads avoid racing ``client.close()``.
    """

    def _transport(
        url: str,
        payload: dict[str, Any],
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> Any:
        if shutdown_event is not None and shutdown_event.is_set():
            raise httpx.RequestError(
                "Meilisearch HTTP client is shutting down",
                request=None,
            )
        response = client.post(
            url,
            json=payload,
            headers=dict(headers),
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    return _transport


def _start_shadow_thread(task: Callable[[], None]) -> None:
    """Run a best-effort shadow comparison off the request path."""

    if not _shadow_task_slots.acquire(blocking=False):
        logger.debug("Food search shadow task skipped; concurrency limit reached")
        return

    def _run_shadow_task() -> None:
        try:
            task()
        finally:
            _shadow_task_slots.release()

    try:
        thread = threading.Thread(
            target=_run_shadow_task,
            name="food-search-shadow",
            daemon=True,
        )
        thread.start()
    except RuntimeError:
        _shadow_task_slots.release()
        logger.debug("Food search shadow task skipped; failed to start thread", exc_info=True)


class MeiliSearchBackend:
    """Optional Meilisearch backend preserving the food-search contract."""

    def __init__(
        self,
        *,
        base_url: str,
        index_name: str,
        api_key: str | None = None,
        timeout_seconds: float = 2.0,
        show_performance_details: bool = False,
        search_strategy_label: str = "meili",
        transport: Transport = _default_transport,
        fallback_backend: "FoodSearchBackend | None" = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._index_name = index_name
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._show_performance_details = show_performance_details
        self._search_strategy_label = search_strategy_label
        self._transport = transport
        self._fallback_backend = fallback_backend

    def _record_performance_details(
        self,
        summary: NormalizedMeiliPerformanceDetails,
    ) -> None:
        """Emit best-effort observability for sanitized performance details."""

        record_food_search_meili_performance(
            strategy=self._search_strategy_label,
            perf_state=summary.state,
            degraded=summary.degraded,
            processing_time_ms=summary.processing_time_ms,
        )
        for stage_name, duration_ms in summary.stage_timings_ms.items():
            record_food_search_meili_stage_timing(
                strategy=self._search_strategy_label,
                stage=stage_name,
                duration_ms=duration_ms,
            )
        if summary.state in {"captured", "invalid", "missing"}:
            logger.debug(
                "Meilisearch performance details processed",
                extra={
                    "strategy": self._search_strategy_label,
                    "perf_state": summary.state,
                    "degraded": summary.degraded,
                    "processing_time_ms": summary.processing_time_ms,
                    "stage_timings_ms": dict(summary.stage_timings_ms),
                },
            )

    def _fallback_search(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> Sequence[Mapping[str, Any]]:
        """Return the baseline fallback rows or an empty result set."""

        if self._fallback_backend is not None:
            fallback_rows: Sequence[Mapping[str, Any]]
            fallback_rows = self._fallback_backend.search_foods(query, limit=limit, offset=offset)
            return fallback_rows
        return []

    def search_foods(
        self,
        query: str,
        limit: int | str = 20,
        offset: int | str = 0,
    ) -> Sequence[Mapping[str, Any]]:
        """Query Meilisearch and normalize hits to food contract fields."""

        try:
            normalized_limit = int(limit)
            normalized_offset = int(offset)
        except (TypeError, ValueError) as exc:
            raise ValueError("limit and offset must be integers") from exc

        search_url = build_meili_foods_search_url(self._base_url, self._index_name)
        headers = build_meili_foods_search_headers(self._api_key)
        payload = build_meili_foods_search_payload(
            query=query,
            limit=normalized_limit,
            offset=normalized_offset,
            show_performance_details=self._show_performance_details,
        )
        try:
            response = self._transport(search_url, payload, headers, self._timeout_seconds)
        except (
            httpx.HTTPError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ):
            logger.warning(
                "Meilisearch request failed; falling back to baseline backend", exc_info=True
            )
            self._record_performance_details(
                _normalize_performance_details(
                    {},
                    enabled=self._show_performance_details,
                    fallback=True,
                )
            )
            return self._fallback_search(
                query=query,
                limit=normalized_limit,
                offset=normalized_offset,
            )

        if not isinstance(response, Mapping):
            logger.warning("Meilisearch response root was not an object")
            self._record_performance_details(
                _normalize_performance_details(
                    {},
                    enabled=self._show_performance_details,
                    fallback=True,
                )
            )
            return self._fallback_search(
                query=query,
                limit=normalized_limit,
                offset=normalized_offset,
            )

        hits = response.get("hits", [])
        if not isinstance(hits, list):
            logger.warning("Meilisearch response missing hits list")
            self._record_performance_details(
                _normalize_performance_details(
                    response,
                    enabled=self._show_performance_details,
                    fallback=True,
                )
            )
            return self._fallback_search(
                query=query,
                limit=normalized_limit,
                offset=normalized_offset,
            )

        normalized_hits: list[Mapping[str, Any]] = []
        for hit in hits:
            if not isinstance(hit, Mapping):
                continue
            normalized_hits.append(
                {
                    "id": hit.get("id"),
                    "canonical_name": hit.get("canonical_name") or hit.get("name"),
                    "kcal": _numeric_field_or_default(hit, "kcal"),
                    "protein_g": _numeric_field_or_default(hit, "protein_g"),
                    "fat_g": _numeric_field_or_default(hit, "fat_g"),
                    "carbs_g": _numeric_field_or_default(hit, "carbs_g"),
                    "source": hit.get("source"),
                    "content_hash": hit.get("content_hash"),
                }
            )
        self._record_performance_details(
            _normalize_performance_details(
                response,
                enabled=self._show_performance_details,
            )
        )
        return normalized_hits


class ShadowSearchBackend:
    """Return baseline results while running a best-effort shadow query."""

    def __init__(
        self,
        *,
        baseline_backend: "FoodSearchBackend",
        shadow_backend: "FoodSearchBackend",
        shadow_runner: ShadowTaskRunner = _start_shadow_thread,
    ) -> None:
        self._baseline_backend = baseline_backend
        self._shadow_backend = shadow_backend
        self._shadow_runner = shadow_runner

    def search_foods(
        self,
        query: str,
        limit: int | str = 20,
        offset: int | str = 0,
    ) -> Sequence[Mapping[str, Any]]:
        """Serve baseline results and record shadow divergence in logs."""

        baseline_rows = list(self._baseline_backend.search_foods(query, limit=limit, offset=offset))
        baseline_ids = [str(row.get("id")) for row in baseline_rows]

        def _compare_shadow() -> None:
            try:
                shadow_rows = list(
                    self._shadow_backend.search_foods(query, limit=limit, offset=offset)
                )
                shadow_ids = [str(row.get("id")) for row in shadow_rows]
                if baseline_ids != shadow_ids:
                    logger.info(
                        "Food search shadow divergence detected",
                        extra={
                            "query": query,
                            "baseline_ids": baseline_ids,
                            "shadow_ids": shadow_ids,
                        },
                    )
            except Exception:
                logger.debug("Food search shadow query failed", exc_info=True)

        try:
            self._shadow_runner(_compare_shadow)
        except Exception:
            logger.debug("Food search shadow scheduling failed", exc_info=True)
        return baseline_rows
