from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from unittest.mock import MagicMock
from fastapi import FastAPI
import httpx
import pytest
from typing import Literal

import app.metrics as app_metrics
import app.bootstrap.food_search as food_search_module
from app.bootstrap.food_search import (
    FoodSearchLifecycleLease,
    _safe_index_name,
    _safe_show_performance_details,
    _safe_timeout_seconds,
    configure_food_search_backend,
    dispose_food_search_backend,
)
from app.services import food_store, search_meili as search_meili_module
from app.services.food_search_indexing import (
    build_swap_indexes_payload,
    canonicalize_food_document,
    content_hash,
    diff_emit,
)
from app.services.search_meili import (
    _default_transport,
    _numeric_field_or_default,
    _start_shadow_thread,
    build_meili_foods_search_headers,
    build_meili_foods_search_payload,
    build_meili_foods_search_url,
    make_pooled_httpx_transport,
    MeiliSearchBackend,
    MEILI_FOODS_ATTRIBUTES_TO_RETRIEVE,
    ShadowSearchBackend,
)


def test_meili_backend_falls_back_to_legacy_on_transport_error() -> None:
    class _FallbackBackend:
        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            self.calls.append((query, int(limit), int(offset)))
            return [{"id": "legacy"}]

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: (_ for _ in ()).throw(TimeoutError("boom")),
        fallback_backend=_FallbackBackend(),
    )

    rows = backend.search_foods("apple", limit=3, offset=1)

    assert rows == [{"id": "legacy"}]


def test_meili_backend_returns_empty_without_fallback_backend() -> None:
    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: (_ for _ in ()).throw(TimeoutError("boom")),
    )

    assert backend.search_foods("apple") == []


def test_meili_backend_validates_pagination_inputs() -> None:
    backend = MeiliSearchBackend(base_url="https://meili.example", index_name="foods")

    with pytest.raises(ValueError, match="limit and offset must be integers"):
        backend.search_foods("apple", limit="bad", offset=0)


def test_meili_backend_normalizes_missing_nutrient_fields() -> None:
    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: {
            "hits": [
                {
                    "id": "1",
                    "name": "Apple",
                    "source": "shadow",
                },
                "skip-me",
            ]
        },
    )

    rows = backend.search_foods("apple")

    assert rows == [
        {
            "id": "1",
            "canonical_name": "Apple",
            "kcal": 0,
            "protein_g": 0,
            "fat_g": 0,
            "carbs_g": 0,
            "source": "shadow",
            "content_hash": None,
        }
    ]


def test_meili_backend_falls_back_when_hits_is_not_a_list() -> None:
    class _FallbackBackend:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "legacy"}]

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: {"hits": "not-a-list"},
        fallback_backend=_FallbackBackend(),
    )

    assert backend.search_foods("apple") == [{"id": "legacy"}]


def test_meili_backend_falls_back_when_response_root_is_not_an_object() -> None:
    class _FallbackBackend:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "legacy"}]

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=lambda *_args: ["unexpected-root"],
        fallback_backend=_FallbackBackend(),
    )

    assert backend.search_foods("apple") == [{"id": "legacy"}]


def test_meili_backend_passes_authorization_header_to_transport() -> None:
    captured_headers: list[dict[str, str]] = []

    def _transport(
        url: str,
        payload: dict[str, object | int | str],
        headers: dict[str, str] | Mapping[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_headers.append(dict(headers))
        return {"hits": []}

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        api_key="x",  # pragma: allowlist secret
        transport=_transport,
    )

    assert backend.search_foods("apple") == []
    assert captured_headers == [{"Authorization": "Bearer x"}]


def test_meili_backend_omits_show_performance_details_when_disabled() -> None:
    captured_payloads: list[dict[str, object]] = []

    def _transport(
        url: str,
        payload: dict[str, object | int | str],
        headers: dict[str, str] | Mapping[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_payloads.append(dict(payload))
        return {"hits": []}

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        transport=_transport,
    )

    assert backend.search_foods("apple") == []
    assert "showPerformanceDetails" not in captured_payloads[0]


def test_meili_backend_includes_show_performance_details_when_enabled() -> None:
    captured_payloads: list[dict[str, object]] = []

    def _transport(
        url: str,
        payload: dict[str, object | int | str],
        headers: dict[str, str] | Mapping[str, str],
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_payloads.append(dict(payload))
        return {"hits": []}

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        show_performance_details=True,
        transport=_transport,
    )

    assert backend.search_foods("apple") == []
    assert captured_payloads[0]["showPerformanceDetails"] is True


def test_meili_backend_records_captured_performance_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_summaries: list[dict[str, object]] = []
    captured_stages: list[dict[str, object]] = []

    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_performance",
        lambda **kwargs: captured_summaries.append(kwargs),
    )
    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_stage_timing",
        lambda **kwargs: captured_stages.append(kwargs),
    )

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        show_performance_details=True,
        search_strategy_label="hybrid_shadow",
        transport=lambda *_args: {
            "hits": [
                {
                    "id": "1",
                    "name": "Apple",
                    "kcal": 52,
                    "protein_g": 0.3,
                    "fat_g": 0.2,
                    "carbs_g": 14,
                }
            ],
            "processingTimeMs": 42,
            "performanceDetails": {
                "wait for permit": "295.29µs",
                "search > tokenize": "436.67µs",
                "search": "3.56ms",
                "search > format": "288.54µs",
                "degraded": False,
            },
        },
    )

    rows = backend.search_foods("apple")

    assert rows[0]["id"] == "1"
    assert captured_summaries == [
        {
            "strategy": "hybrid_shadow",
            "perf_state": "captured",
            "degraded": "false",
            "processing_time_ms": 42.0,
        }
    ]
    assert [stage["strategy"] for stage in captured_stages] == [
        "hybrid_shadow",
        "hybrid_shadow",
        "hybrid_shadow",
        "hybrid_shadow",
    ]
    assert [stage["stage"] for stage in captured_stages] == [
        "authorization",
        "tokenization",
        "keyword_search",
        "formatting",
    ]
    assert [stage["duration_ms"] for stage in captured_stages] == pytest.approx(
        [0.29529, 0.43667, 3.56, 0.28854]
    )


def test_meili_backend_treats_invalid_perf_details_as_observability_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_summaries: list[dict[str, object]] = []

    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_performance",
        lambda **kwargs: captured_summaries.append(kwargs),
    )
    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_stage_timing",
        lambda **kwargs: None,
    )

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        show_performance_details=True,
        transport=lambda *_args: {
            "hits": [{"id": "1", "name": "Apple"}],
            "processingTimeMs": 18,
            "performanceDetails": "bad-shape",
        },
    )

    rows = backend.search_foods("apple")

    assert rows == [
        {
            "id": "1",
            "canonical_name": "Apple",
            "kcal": 0,
            "protein_g": 0,
            "fat_g": 0,
            "carbs_g": 0,
            "source": None,
            "content_hash": None,
        }
    ]
    assert captured_summaries == [
        {
            "strategy": "meili",
            "perf_state": "invalid",
            "degraded": "unknown",
            "processing_time_ms": 18.0,
        }
    ]


def test_meili_backend_records_missing_perf_details_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_summaries: list[dict[str, object]] = []

    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_performance",
        lambda **kwargs: captured_summaries.append(kwargs),
    )
    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_stage_timing",
        lambda **kwargs: None,
    )

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        show_performance_details=True,
        transport=lambda *_args: {
            "hits": [{"id": "1", "name": "Apple"}],
            "processingTimeMs": 12,
        },
    )

    rows = backend.search_foods("apple")

    assert rows[0]["canonical_name"] == "Apple"
    assert captured_summaries == [
        {
            "strategy": "meili",
            "perf_state": "missing",
            "degraded": "unknown",
            "processing_time_ms": 12.0,
        }
    ]


def test_meili_backend_records_fallback_perf_state_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_summaries: list[dict[str, object]] = []

    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_performance",
        lambda **kwargs: captured_summaries.append(kwargs),
    )
    monkeypatch.setattr(
        search_meili_module,
        "record_food_search_meili_stage_timing",
        lambda **kwargs: None,
    )

    class _FallbackBackend:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "legacy"}]

    backend = MeiliSearchBackend(
        base_url="https://meili.example",
        index_name="foods",
        show_performance_details=True,
        transport=lambda *_args: (_ for _ in ()).throw(TimeoutError("boom")),
        fallback_backend=_FallbackBackend(),
    )

    assert backend.search_foods("apple") == [{"id": "legacy"}]
    assert captured_summaries == [
        {
            "strategy": "meili",
            "perf_state": "fallback",
            "degraded": "unknown",
            "processing_time_ms": None,
        }
    ]


def test_shadow_backend_returns_baseline_when_shadow_diverges() -> None:
    class _Baseline:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "baseline"}]

    class _Shadow:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "shadow"}]

    backend = ShadowSearchBackend(
        baseline_backend=_Baseline(),
        shadow_backend=_Shadow(),
        shadow_runner=lambda task: task(),
    )

    assert backend.search_foods("banana") == [{"id": "baseline"}]


def test_shadow_backend_does_not_block_on_shadow_query() -> None:
    class _Baseline:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "baseline"}]

    class _Shadow:
        def __init__(self) -> None:
            self.called = False

        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            self.called = True
            return [{"id": "shadow"}]

    scheduled_tasks: list[Callable[[], None]] = []
    shadow_backend = _Shadow()
    backend = ShadowSearchBackend(
        baseline_backend=_Baseline(),
        shadow_backend=shadow_backend,
        shadow_runner=scheduled_tasks.append,
    )

    assert backend.search_foods("banana") == [{"id": "baseline"}]
    assert shadow_backend.called is False
    assert len(scheduled_tasks) == 1

    scheduled_tasks[0]()
    assert shadow_backend.called is True


def test_start_shadow_thread_skips_when_capacity_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BusySlots:
        def acquire(self, *, blocking: bool) -> bool:
            assert blocking is False
            return False

        def release(self) -> None:
            raise AssertionError("release must not run for skipped tasks")

    def _unexpected_thread(**_kwargs: object) -> object:
        raise AssertionError("thread must not start when all shadow slots are busy")

    monkeypatch.setattr(search_meili_module, "_shadow_task_slots", _BusySlots())
    monkeypatch.setattr(search_meili_module.threading, "Thread", _unexpected_thread)

    _start_shadow_thread(lambda: None)


def test_start_shadow_thread_releases_capacity_after_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class _Slots:
        def acquire(self, *, blocking: bool) -> bool:
            assert blocking is False
            events.append("acquire")
            return True

        def release(self) -> None:
            events.append("release")

    class _Thread:
        def __init__(self, *, target: Callable[[], None], name: str, daemon: bool) -> None:
            self._target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            events.append("start")
            self._target()

    monkeypatch.setattr(search_meili_module, "_shadow_task_slots", _Slots())
    monkeypatch.setattr(search_meili_module.threading, "Thread", _Thread)

    _start_shadow_thread(lambda: events.append("task"))

    assert events == ["acquire", "start", "task", "release"]


def test_start_shadow_thread_releases_capacity_when_thread_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class _Slots:
        def acquire(self, *, blocking: bool) -> bool:
            assert blocking is False
            events.append("acquire")
            return True

        def release(self) -> None:
            events.append("release")

    class _Thread:
        def __init__(self, *, target: Callable[[], None], name: str, daemon: bool) -> None:
            self._target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            events.append("start")
            raise RuntimeError("thread-start-failed")

    monkeypatch.setattr(search_meili_module, "_shadow_task_slots", _Slots())
    monkeypatch.setattr(search_meili_module.threading, "Thread", _Thread)

    _start_shadow_thread(lambda: events.append("task"))

    assert events == ["acquire", "start", "release"]


def test_shadow_backend_returns_baseline_when_shadow_raises() -> None:
    class _Baseline:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "baseline"}]

    class _Shadow:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            raise RuntimeError("shadow down")

    backend = ShadowSearchBackend(
        baseline_backend=_Baseline(),
        shadow_backend=_Shadow(),
        shadow_runner=lambda task: task(),
    )

    assert backend.search_foods("banana") == [{"id": "baseline"}]


def test_strategy_backend_prefers_registered_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    class _StrategyBackend:
        def search_foods(
            self,
            query: str,
            limit: int | str = 20,
            offset: int | str = 0,
        ) -> list[dict[str, str]]:
            return [{"id": "meili"}]

    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    food_store.register_strategy_search_backend_adapter(_StrategyBackend())
    try:
        assert food_store.get_search_backend().search_foods("yogurt") == [{"id": "meili"}]
    finally:
        food_store.reset_strategy_search_backend_adapter()
        monkeypatch.delenv("FOOD_SEARCH_BACKEND_STRATEGY", raising=False)


def test_search_backend_strategy_invalid_value_falls_back_to_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "unsupported-shadow-mode")

    assert food_store.get_search_backend_strategy() == "baseline_fts"


def test_get_legacy_search_backend_exposes_legacy_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FEATURE_FOOD_SEARCH_COMPAT_ENABLED", raising=False)
    monkeypatch.delenv("FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED", raising=False)
    monkeypatch.delenv("FOOD_SEARCH_BACKEND_STRATEGY", raising=False)
    food_store.reset_search_backend_adapter()
    food_store.reset_strategy_search_backend_adapter()
    food_store.reset_semantic_search_backend_adapter()

    assert food_store.get_legacy_search_backend() is food_store.get_search_backend()


def test_configure_food_search_backend_falls_back_to_baseline_without_meili_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "hybrid_shadow")
    monkeypatch.delenv("MEILI_URL", raising=False)
    lease = configure_food_search_backend(app)
    try:
        assert app.state.food_search_strategy == "baseline_fts"
    finally:
        dispose_food_search_backend(app, lease)


def test_configure_food_search_backend_registers_meili_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "https://meili.example")
    monkeypatch.setenv("MEILI_FOODS_INDEX", "   ")
    monkeypatch.setenv("MEILI_TIMEOUT_SECONDS", "bad-timeout")
    monkeypatch.setenv("MEILI_SHOW_PERFORMANCE_DETAILS", "true")
    lease = configure_food_search_backend(app)
    try:
        assert app.state.food_search_strategy == "meili"
        backend = food_store.get_search_backend()
        assert isinstance(backend, MeiliSearchBackend)
        assert backend._index_name == "foods"
        assert backend._timeout_seconds == 2.0
        assert backend._show_performance_details is True
    finally:
        dispose_food_search_backend(app, lease)


def test_configure_food_search_backend_registers_shadow_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "hybrid_shadow")
    monkeypatch.setenv("MEILI_URL", "https://meili.example")
    lease = configure_food_search_backend(app)
    try:
        assert app.state.food_search_strategy == "hybrid_shadow"
        assert isinstance(food_store.get_search_backend(), ShadowSearchBackend)
    finally:
        dispose_food_search_backend(app, lease)


def test_meili_foods_search_helpers_match_contract_shape() -> None:
    assert build_meili_foods_search_url("https://meili.example/", "foods_v2") == (
        "https://meili.example/indexes/foods_v2/search"
    )
    assert build_meili_foods_search_headers(None) == {}
    assert build_meili_foods_search_headers("") == {}
    assert build_meili_foods_search_headers("   ") == {}
    assert build_meili_foods_search_headers("k") == {"Authorization": "Bearer k"}
    payload = build_meili_foods_search_payload(
        query="x",
        limit=3,
        offset=1,
        show_performance_details=False,
    )
    assert payload["q"] == "x"
    assert payload["limit"] == 3
    assert payload["offset"] == 1
    assert payload["attributesToRetrieve"] == list(MEILI_FOODS_ATTRIBUTES_TO_RETRIEVE)
    assert "showPerformanceDetails" not in payload
    payload_perf = build_meili_foods_search_payload(
        query="x",
        limit=1,
        offset=0,
        show_performance_details=True,
    )
    assert payload_perf["showPerformanceDetails"] is True


def test_pooled_httpx_transport_reuses_single_client() -> None:
    request_count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={"hits": []})

    transport_layer = httpx.MockTransport(_handler)
    with httpx.Client(transport=transport_layer) as client:
        pooled = make_pooled_httpx_transport(client)
        assert pooled("http://testserver/indexes/i/search", {"q": "a"}, {}, 2.0) == {"hits": []}
        assert pooled("http://testserver/indexes/i/search", {"q": "b"}, {}, 2.0) == {"hits": []}
    assert request_count == 2


def test_pooled_httpx_transport_refuses_when_shutdown_event_set() -> None:
    request_count = 0

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={"hits": []})

    transport_layer = httpx.MockTransport(_handler)
    shutdown = threading.Event()
    with httpx.Client(transport=transport_layer) as client:
        pooled = make_pooled_httpx_transport(client, shutdown_event=shutdown)
        assert pooled("http://testserver/indexes/i/search", {"q": "a"}, {}, 2.0) == {"hits": []}
        assert request_count == 1
        shutdown.set()
        with pytest.raises(httpx.RequestError, match="shutting down"):
            pooled("http://testserver/indexes/i/search", {"q": "b"}, {}, 2.0)
        assert request_count == 1


def test_pooled_httpx_transport_maps_client_close_race_to_request_error() -> None:
    shutdown = threading.Event()
    client = MagicMock(spec=httpx.Client)
    client.is_closed = False

    def _race_with_shutdown(*_args: object, **_kwargs: object) -> None:
        shutdown.set()
        client.is_closed = True
        raise RuntimeError("connection pool closed during request")

    client.post.side_effect = _race_with_shutdown
    pooled = make_pooled_httpx_transport(client, shutdown_event=shutdown)

    with pytest.raises(httpx.RequestError, match="shut down during POST"):
        pooled("http://testserver/indexes/i/search", {"q": "a"}, {}, 2.0)


def test_pooled_httpx_transport_does_not_mask_unrelated_runtime_error() -> None:
    shutdown = threading.Event()
    client = MagicMock(spec=httpx.Client)
    client.is_closed = False
    client.post.side_effect = RuntimeError("unrelated transport bug")
    pooled = make_pooled_httpx_transport(client, shutdown_event=shutdown)

    with pytest.raises(RuntimeError, match="unrelated transport bug"):
        pooled("http://testserver/indexes/i/search", {"q": "a"}, {}, 2.0)


def test_pooled_httpx_transport_propagates_http_status_errors() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "server error"})

    transport_layer = httpx.MockTransport(_handler)
    with httpx.Client(transport=transport_layer) as client:
        pooled = make_pooled_httpx_transport(client)
        with pytest.raises(httpx.HTTPStatusError):
            pooled("http://testserver/indexes/i/search", {"q": "a"}, {}, 2.0)


def test_overlapping_food_search_acquisition_is_rejected_without_replacing_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_app = FastAPI()
    second_app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    lease = configure_food_search_backend(first_app)
    try:
        first = first_app.state.meili_http_client
        assert first is not None
        assert not first.is_closed
        with pytest.raises(RuntimeError, match="already active"):
            configure_food_search_backend(second_app)
        with pytest.raises(RuntimeError, match="already active"):
            configure_food_search_backend(first_app)
        assert first_app.state.meili_http_client is first
        assert not first.is_closed
    finally:
        dispose_food_search_backend(first_app, lease)


def test_stale_app_state_rejects_food_search_acquisition() -> None:
    app = FastAPI()
    app.state._food_search_lifecycle_lease = object()

    with pytest.raises(RuntimeError, match="already owns"):
        configure_food_search_backend(app)

    assert food_search_module._ACTIVE_FOOD_SEARCH_LIFECYCLE is None


def test_sequential_food_search_acquisition_uses_fresh_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    app = FastAPI()
    first_lease = configure_food_search_backend(app)
    first_client = app.state.meili_http_client
    dispose_food_search_backend(app, first_lease)
    assert first_client.is_closed

    second_lease = configure_food_search_backend(app)
    second_client = app.state.meili_http_client
    try:
        assert second_lease is not first_lease
        assert second_client is not first_client
        assert not second_client.is_closed
    finally:
        dispose_food_search_backend(app, second_lease)


def test_configure_food_search_does_not_mutate_lifespan_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    original_lifespan = app.router.lifespan_context
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "baseline_fts")
    lease = configure_food_search_backend(app)
    try:
        assert app.router.lifespan_context is original_lifespan
    finally:
        dispose_food_search_backend(app, lease)


def test_dispose_food_search_backend_is_idempotent_and_warns_when_close_raises(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = FastAPI()
    mock_client = MagicMock()
    mock_client.close.side_effect = RuntimeError("simulated close failure")
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    monkeypatch.setattr(
        "app.bootstrap.food_search._build_meili_http_client",
        lambda: mock_client,
    )
    lease = configure_food_search_backend(app)

    with caplog.at_level(logging.WARNING, logger="app.bootstrap.food_search"):
        dispose_food_search_backend(app, lease)
        dispose_food_search_backend(app, lease)

    assert "Meili HTTP client close failed" in caplog.text
    mock_client.close.assert_called_once_with()
    assert getattr(app.state, "meili_http_client", None) is None
    assert getattr(app.state, "meili_http_shutdown_event", None) is None


def test_foreign_lease_cannot_dispose_active_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = FastAPI()
    foreign = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "baseline_fts")
    lease = configure_food_search_backend(owner)
    try:
        with pytest.raises(RuntimeError, match="another application"):
            dispose_food_search_backend(foreign, FoodSearchLifecycleLease())
        assert owner.state._food_search_lifecycle_lease is lease
    finally:
        dispose_food_search_backend(owner, lease)


def test_failed_client_construction_releases_food_search_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    monkeypatch.setattr(
        "app.bootstrap.food_search._build_meili_http_client",
        lambda: (_ for _ in ()).throw(RuntimeError("client failed")),
    )
    with pytest.raises(RuntimeError, match="client failed"):
        configure_food_search_backend(FastAPI())

    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "baseline_fts")
    app = FastAPI()
    lease = configure_food_search_backend(app)
    dispose_food_search_backend(app, lease)


@pytest.mark.parametrize(
    "failing_resolver",
    [
        "get_search_backend_strategy",
        "get_registered_strategy_search_backend_adapter",
    ],
)
def test_failed_resolver_releases_food_search_reservation(
    monkeypatch: pytest.MonkeyPatch,
    failing_resolver: str,
) -> None:
    original = getattr(food_store, failing_resolver)
    monkeypatch.setattr(
        food_store,
        failing_resolver,
        lambda: (_ for _ in ()).throw(RuntimeError("resolver failed")),
    )

    with pytest.raises(RuntimeError, match="resolver failed"):
        configure_food_search_backend(FastAPI())

    assert food_search_module._ACTIVE_FOOD_SEARCH_LIFECYCLE is None
    monkeypatch.setattr(food_store, failing_resolver, original)
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "baseline_fts")
    app = FastAPI()
    lease = configure_food_search_backend(app)
    dispose_food_search_backend(app, lease)


def test_failed_adapter_commit_closes_candidate_and_releases_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    monkeypatch.setattr(food_search_module, "_build_meili_http_client", lambda: client)
    monkeypatch.setattr(
        food_store,
        "compare_and_swap_strategy_search_backend_adapter",
        lambda _expected, _replacement: False,
    )

    with pytest.raises(RuntimeError, match="ownership changed"):
        configure_food_search_backend(FastAPI())

    client.close.assert_called_once_with()
    assert food_search_module._ACTIVE_FOOD_SEARCH_LIFECYCLE is None


def test_failed_finalization_attempts_every_rollback_step(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = FastAPI()
    client = MagicMock()
    client.close.side_effect = RuntimeError("close failed")
    cas_calls = 0

    def _cas_then_lose_reservation(
        _expected: food_store.FoodSearchBackend | None,
        _replacement: food_store.FoodSearchBackend | None,
    ) -> bool:
        nonlocal cas_calls
        cas_calls += 1
        if cas_calls == 1:
            food_search_module._ACTIVE_FOOD_SEARCH_LIFECYCLE = None
            return True
        raise RuntimeError("adapter rollback failed")

    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "meili")
    monkeypatch.setenv("MEILI_URL", "http://127.0.0.1:7700")
    monkeypatch.setattr(food_search_module, "_build_meili_http_client", lambda: client)
    monkeypatch.setattr(
        food_store,
        "compare_and_swap_strategy_search_backend_adapter",
        _cas_then_lose_reservation,
    )
    monkeypatch.setattr(
        food_search_module,
        "_clear_owned_app_state",
        lambda _app, _lease: (_ for _ in ()).throw(RuntimeError("state cleanup failed")),
    )

    with caplog.at_level(logging.WARNING, logger="app.bootstrap.food_search"):
        with pytest.raises(RuntimeError, match="reservation was lost"):
            configure_food_search_backend(app)

    assert cas_calls == 2
    assert "rollback adapter reset failed" in caplog.text
    assert "rollback app-state cleanup failed" in caplog.text
    assert "rollback close failed" in caplog.text
    assert food_search_module._ACTIVE_FOOD_SEARCH_LIFECYCLE is None


def test_dispose_warns_when_adapter_ownership_changed(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "baseline_fts")
    lease = configure_food_search_backend(app)
    monkeypatch.setattr(
        food_store,
        "compare_and_swap_strategy_search_backend_adapter",
        lambda _expected, _replacement: False,
    )

    with caplog.at_level(logging.WARNING, logger="app.bootstrap.food_search"):
        dispose_food_search_backend(app, lease)

    assert "adapter ownership changed before shutdown" in caplog.text


def test_releasing_food_search_lifecycle_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "baseline_fts")
    lease = configure_food_search_backend(app)
    active = food_search_module._ACTIVE_FOOD_SEARCH_LIFECYCLE
    assert active is not None
    active.phase = food_search_module._FoodSearchLifecyclePhase.RELEASING

    dispose_food_search_backend(app, lease)
    assert food_search_module._ACTIVE_FOOD_SEARCH_LIFECYCLE is active

    active.phase = food_search_module._FoodSearchLifecyclePhase.ACTIVE
    dispose_food_search_backend(app, lease)


def test_strategy_adapter_compare_and_swap_rejects_stale_owner() -> None:
    food_store.reset_strategy_search_backend_adapter()
    stale_owner = MagicMock()

    assert food_store.compare_and_swap_strategy_search_backend_adapter(stale_owner, None) is False


def test_stale_disposal_cannot_change_newer_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FOOD_SEARCH_BACKEND_STRATEGY", "baseline_fts")
    first_app = FastAPI()
    first_lease = configure_food_search_backend(first_app)
    dispose_food_search_backend(first_app, first_lease)

    second_app = FastAPI()
    second_lease = configure_food_search_backend(second_app)
    try:
        with pytest.raises(RuntimeError, match="another application"):
            dispose_food_search_backend(first_app, first_lease)
        assert second_app.state._food_search_lifecycle_lease is second_lease
    finally:
        dispose_food_search_backend(second_app, second_lease)


def test_food_search_lease_repr_is_opaque() -> None:
    lease = FoodSearchLifecycleLease()

    assert repr(lease) == "<FoodSearchLifecycleLease>"
    assert not hasattr(lease, "_token")


def test_safe_timeout_and_index_helpers_use_fallbacks() -> None:
    assert _safe_timeout_seconds(None) == 2.0
    assert _safe_timeout_seconds("0") == 2.0
    assert _safe_timeout_seconds("-1") == 2.0
    assert _safe_timeout_seconds("1.5") == 1.5
    assert _safe_index_name(None) == "foods"
    assert _safe_index_name("   ") == "foods"
    assert _safe_index_name("foods_v2") == "foods_v2"
    assert _safe_show_performance_details(None) is False
    assert _safe_show_performance_details("false") is False
    assert _safe_show_performance_details("true") is True


def test_default_transport_posts_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object], dict[str, str], float]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"hits": []}

    class _Client:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, exc_type, exc, tb) -> Literal[False]:
            return False

        def post(
            self,
            url: str,
            *,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> _Response:
            calls.append((url, json, headers, self.timeout))
            return _Response()

    monkeypatch.setattr(httpx, "Client", _Client)

    response = _default_transport(
        "https://meili.example/indexes/foods/search",
        {"q": "apple"},
        {"Authorization": "Bearer token"},
        1.25,
    )

    assert response == {"hits": []}
    assert calls == [
        (
            "https://meili.example/indexes/foods/search",
            {"q": "apple"},
            {"Authorization": "Bearer token"},
            1.25,
        )
    ]


def test_content_hash_is_stable_for_semantically_equal_documents() -> None:
    first = {"id": "1", "aliases": ["banana", "apple"], "source": "usda"}
    second = {"source": "usda", "aliases": ["apple", "banana"], "id": "1"}

    assert content_hash(first) == content_hash(second)


def test_canonicalize_food_document_ignores_existing_content_hash() -> None:
    document = {
        "id": "1",
        "aliases": ["banana", "apple"],
        "content_hash": "stale",
    }

    assert canonicalize_food_document(document) == {
        "aliases": ["apple", "banana"],
        "id": "1",
    }


def test_diff_emit_returns_only_changed_documents() -> None:
    documents = [
        {"id": "1", "canonical_name": "Apple", "aliases": ["apple"]},
        {"id": "2", "canonical_name": "Banana", "aliases": ["banana"]},
    ]
    cache = {"1": content_hash(documents[0])}

    changed = diff_emit(documents, cache)

    assert changed == [
        {
            "id": "2",
            "canonical_name": "Banana",
            "aliases": ["banana"],
            "content_hash": content_hash(documents[1]),
        }
    ]


def test_diff_emit_ignores_existing_content_hash_in_hash_input() -> None:
    document = {
        "id": "1",
        "canonical_name": "Apple",
        "aliases": ["apple"],
        "content_hash": "stale",
    }
    cache = {"1": content_hash(document)}

    assert diff_emit([document], cache) == []


def test_diff_emit_raises_clear_error_when_id_field_is_missing() -> None:
    with pytest.raises(ValueError, match="Document missing required field 'id'"):
        diff_emit([{"canonical_name": "Apple"}], {})


def test_build_swap_indexes_payload_is_atomic_pair_list() -> None:
    assert build_swap_indexes_payload([("foods", "foods_v2"), ("recipes", "recipes_v2")]) == [
        {"indexes": ["foods", "foods_v2"]},
        {"indexes": ["recipes", "recipes_v2"]},
    ]


def test_numeric_field_or_default_returns_zero_for_missing_values() -> None:
    hit = {"protein_g": None, "fat_g": "bad", "carbs_g": 3, "kcal": True}

    assert _numeric_field_or_default(hit, "protein_g") == 0
    assert _numeric_field_or_default(hit, "fat_g") == 0
    assert _numeric_field_or_default(hit, "carbs_g") == 3
    assert _numeric_field_or_default(hit, "kcal") == 0


def test_coerce_non_negative_ms_rejects_nan() -> None:
    assert search_meili_module._coerce_non_negative_ms(float("nan")) is None


def test_search_meili_helper_sanitizers_cover_edge_branches() -> None:
    assert search_meili_module._normalize_degraded_flag(True) == "true"
    assert search_meili_module._normalize_degraded_flag("true") == "true"
    assert search_meili_module._normalize_degraded_flag("false") == "false"
    assert search_meili_module._normalize_degraded_flag("maybe") == "unknown"
    assert search_meili_module._coerce_non_negative_ms(True) is None
    assert search_meili_module._coerce_non_negative_ms("5") is None
    assert search_meili_module._coerce_non_negative_ms("12ns") == 12e-6
    assert search_meili_module._coerce_non_negative_ms("250us") == 0.25
    assert search_meili_module._coerce_non_negative_ms("7ms") == 7.0
    assert search_meili_module._coerce_non_negative_ms("2s") == 2000.0
    assert search_meili_module._coerce_non_negative_ms("700000ms") is None
    assert search_meili_module._coerce_non_negative_ms("9" * 400 + "ms") is None
    assert search_meili_module._coerce_non_negative_ms(-1) is None
    assert search_meili_module._coerce_non_negative_ms(700_000) is None
    assert search_meili_module._normalize_stage_name("keywordSearch") == "keyword_search"
    assert search_meili_module._normalize_stage_name("search > tokenize") == "tokenization"
    assert search_meili_module._normalize_stage_name("wait for permit") == "authorization"
    assert search_meili_module._normalize_stage_name("unknown-stage") is None
    assert search_meili_module._duration_from_candidate(7) == 7.0
    assert search_meili_module._duration_from_candidate({"durationMs": 9}) == 9.0
    assert search_meili_module._duration_from_candidate({"durationMs": "bad"}) is None
    assert search_meili_module._duration_from_candidate("bad") is None


def test_extract_processing_time_ms_uses_details_or_stage_sum() -> None:
    assert (
        search_meili_module._extract_processing_time_ms(
            {},
            {"totalProcessingTimeMs": 23},
            {},
        )
        == 23.0
    )
    assert (
        search_meili_module._extract_processing_time_ms(
            {},
            None,
            {"tokenization": 2.0, "ranking": 4.0},
        )
        == 6.0
    )


def test_normalize_performance_details_marks_invalid_when_payload_has_no_safe_fields() -> None:
    summary = search_meili_module._normalize_performance_details(
        {"performanceDetails": {"unknown": {"durationMs": "bad"}}},
        enabled=True,
    )

    assert summary.state == "invalid"
    assert summary.processing_time_ms is None
    assert summary.stage_timings_ms == {}


def test_app_metrics_build_food_search_meili_perf_events_total_returns_none_on_importerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_metrics,
        "_import_prometheus",
        lambda: (_ for _ in ()).throw(ImportError("boom")),
    )
    assert app_metrics._build_food_search_meili_perf_events_total() is None


def test_app_metrics_build_food_search_meili_processing_time_ms_returns_none_on_importerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_metrics,
        "_import_prometheus_histogram",
        lambda: (_ for _ in ()).throw(ImportError("boom")),
    )
    assert app_metrics._build_food_search_meili_processing_time_ms() is None
    assert app_metrics._build_food_search_meili_stage_processing_time_ms() is None


def test_app_metrics_build_food_search_meili_metrics_return_none_on_duplicate_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _bad_counter(*_args: object, **_kwargs: object) -> object:
        raise ValueError("duplicate metric name")

    def _bad_histogram(*_args: object, **_kwargs: object) -> object:
        raise ValueError("duplicate metric name")

    monkeypatch.setattr(app_metrics, "_import_prometheus", lambda: _bad_counter)
    monkeypatch.setattr(app_metrics, "_import_prometheus_histogram", lambda: _bad_histogram)

    assert app_metrics._build_food_search_meili_perf_events_total() is None
    assert app_metrics._build_food_search_meili_processing_time_ms() is None
    assert app_metrics._build_food_search_meili_stage_processing_time_ms() is None


def test_record_food_search_meili_performance_normalizes_labels_and_observes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_labels: list[dict[str, str]] = []
    captured_observations: list[float] = []

    class _CounterChild:
        def inc(self, amount: float = 1.0) -> None:
            captured_observations.append(amount)

    class _Counter:
        def labels(self, *, strategy: str, perf_state: str, degraded: str) -> _CounterChild:
            captured_labels.append(
                {
                    "strategy": strategy,
                    "perf_state": perf_state,
                    "degraded": degraded,
                }
            )
            return _CounterChild()

    class _HistogramChild:
        def observe(self, amount: float) -> None:
            captured_observations.append(amount)

    class _Histogram:
        def labels(self, *, strategy: str, perf_state: str, degraded: str) -> _HistogramChild:
            captured_labels.append(
                {
                    "strategy": strategy,
                    "perf_state": perf_state,
                    "degraded": degraded,
                }
            )
            return _HistogramChild()

    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PERF_EVENTS_TOTAL", _Counter())
    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PROCESSING_TIME_MS", _Histogram())

    app_metrics.record_food_search_meili_performance(
        strategy="unexpected",
        perf_state="captured",
        degraded="maybe",
        processing_time_ms=33.0,
    )

    assert captured_labels == [
        {"strategy": "unknown", "perf_state": "captured", "degraded": "unknown"},
        {"strategy": "unknown", "perf_state": "captured", "degraded": "unknown"},
    ]
    assert captured_observations == [1.0, 33.0]


def test_record_food_search_meili_performance_handles_non_string_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_labels: list[dict[str, str]] = []

    class _CounterChild:
        def inc(self, amount: float = 1.0) -> None:
            return None

    class _Counter:
        def labels(self, *, strategy: str, perf_state: str, degraded: str) -> _CounterChild:
            captured_labels.append(
                {
                    "strategy": strategy,
                    "perf_state": perf_state,
                    "degraded": degraded,
                }
            )
            return _CounterChild()

    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PERF_EVENTS_TOTAL", _Counter())
    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PROCESSING_TIME_MS", None)

    app_metrics.record_food_search_meili_performance(
        strategy=None,
        perf_state=None,
        degraded=None,
        processing_time_ms=None,
    )

    assert captured_labels == [
        {"strategy": "unknown", "perf_state": "invalid", "degraded": "unknown"}
    ]


def test_record_food_search_meili_performance_swallows_counter_and_histogram_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BadCounterChild:
        def inc(self, amount: float = 1.0) -> None:
            raise RuntimeError("boom")

    class _BadCounter:
        def labels(self, *, strategy: str, perf_state: str, degraded: str) -> _BadCounterChild:
            return _BadCounterChild()

    class _BadHistogramChild:
        def observe(self, amount: float) -> None:
            raise RuntimeError("boom")

    class _BadHistogram:
        def labels(self, *, strategy: str, perf_state: str, degraded: str) -> _BadHistogramChild:
            return _BadHistogramChild()

    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PERF_EVENTS_TOTAL", _BadCounter())
    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PROCESSING_TIME_MS", _BadHistogram())

    app_metrics.record_food_search_meili_performance(
        strategy="meili",
        perf_state="captured",
        degraded="false",
        processing_time_ms=10.0,
    )


def test_record_food_search_meili_performance_noops_when_histogram_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PERF_EVENTS_TOTAL", None)
    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_PROCESSING_TIME_MS", None)

    app_metrics.record_food_search_meili_performance(
        strategy="meili",
        perf_state="weird-state",
        degraded="false",
        processing_time_ms=10.0,
    )


def test_record_food_search_meili_stage_timing_filters_unknown_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class _HistogramChild:
        def observe(self, amount: float) -> None:
            calls.append({"kind": "observe", "amount": amount})

    class _Histogram:
        def labels(self, *, strategy: str, stage: str) -> _HistogramChild:
            calls.append({"kind": "labels", "strategy": strategy, "stage": stage})
            return _HistogramChild()

    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_STAGE_PROCESSING_TIME_MS", _Histogram())

    app_metrics.record_food_search_meili_stage_timing(
        strategy="hybrid_shadow",
        stage="authorization",
        duration_ms=5.0,
    )
    app_metrics.record_food_search_meili_stage_timing(
        strategy="hybrid_shadow",
        stage="unbounded-stage",
        duration_ms=9.0,
    )

    assert calls == [
        {"kind": "labels", "strategy": "hybrid_shadow", "stage": "authorization"},
        {"kind": "observe", "amount": 5.0},
    ]


def test_record_food_search_meili_stage_timing_noops_when_stage_not_normalizable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class _HistogramChild:
        def observe(self, amount: float) -> None:
            calls.append({"kind": "observe", "amount": amount})

    class _Histogram:
        def labels(self, *, strategy: str, stage: str) -> _HistogramChild:
            calls.append({"kind": "labels", "strategy": strategy, "stage": stage})
            return _HistogramChild()

    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_STAGE_PROCESSING_TIME_MS", _Histogram())

    app_metrics.record_food_search_meili_stage_timing(
        strategy="meili",
        stage=42,
        duration_ms=1.0,
    )

    assert calls == []


def test_record_food_search_meili_stage_timing_noops_and_swallows_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BadHistogramChild:
        def observe(self, amount: float) -> None:
            raise RuntimeError("boom")

    class _BadHistogram:
        def labels(self, *, strategy: str, stage: str) -> _BadHistogramChild:
            return _BadHistogramChild()

    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_STAGE_PROCESSING_TIME_MS", None)
    app_metrics.record_food_search_meili_stage_timing(
        strategy="meili",
        stage="authorization",
        duration_ms=5.0,
    )

    monkeypatch.setattr(app_metrics, "FOOD_SEARCH_MEILI_STAGE_PROCESSING_TIME_MS", _BadHistogram())
    app_metrics.record_food_search_meili_stage_timing(
        strategy="meili",
        stage="authorization",
        duration_ms=5.0,
    )
