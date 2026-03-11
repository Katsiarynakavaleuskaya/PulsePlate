"""Deterministic tests for backend GenAI tracing."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import BaseRoute
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.bootstrap.tracing import register_tracing, tracing_middleware
from app.telemetry.genai import (
    COMPLETION_FINGERPRINT_ATTR,
    NULL_SPAN,
    OPENINFERENCE_KIND_AGENT,
    OPENINFERENCE_KIND_CHAIN,
    OPENINFERENCE_KIND_LLM,
    OPENINFERENCE_KIND_RETRIEVER,
    OPENINFERENCE_KIND_TOOL,
    OPENINFERENCE_SPAN_KIND,
    PROMPT_FINGERPRINT_ATTR,
    REQUEST_ID_ATTR,
    USER_TIER_ATTR,
    _sanitize_event_attrs,
    add_completion_event,
    add_prompt_event,
    safe_span,
    set_attributes,
    set_prompt_fingerprint,
    tool_span,
)
from app.telemetry.setup import install_test_exporter, reset_tracing_for_tests


@pytest.fixture
def tracing_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Install in-memory tracing exporter for deterministic span assertions."""

    exporter = InMemorySpanExporter()
    reset_tracing_for_tests()
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    monkeypatch.setenv("PULSE_OBS_HMAC_KEY", "test-genai-hmac-key")
    install_test_exporter(exporter)
    yield exporter
    reset_tracing_for_tests()


def _span_by_kind(spans: list[Any], kind: str) -> Any:
    for span in spans:
        if span.attributes.get(OPENINFERENCE_SPAN_KIND) == kind:
            return span
    raise AssertionError(f"Missing span with kind={kind!r}")


def test_register_tracing_is_idempotent() -> None:
    """Tracing bootstrap should not install duplicate middleware."""

    app = FastAPI()

    register_tracing(app)
    register_tracing(app)

    tracing_middleware_count = 0
    for middleware in app.user_middleware:
        dispatch = (
            getattr(middleware, "options", None) or getattr(middleware, "kwargs", None) or {}
        ).get("dispatch")
        if callable(dispatch) and getattr(dispatch, "__name__", "") == "tracing_middleware":
            tracing_middleware_count += 1

    assert tracing_middleware_count == 1


def test_register_tracing_marks_existing_middleware_state() -> None:
    """register_tracing should mark state when middleware already exists."""

    app = FastAPI()
    app.middleware("http")(tracing_middleware)

    register_tracing(app)

    assert getattr(app.state, "pulseplate_tracing_registered", False) is True


def test_safe_span_swallows_backend_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """GenAI span helpers must degrade to no-op if tracing backend fails."""

    def _raise(_name: str) -> Any:
        raise RuntimeError("otel backend unavailable")

    monkeypatch.setattr("app.telemetry.genai.get_tracer", _raise, raising=True)

    with safe_span("broken", tracer_name="test", kind="INTERNAL") as span:
        span.set_attribute("x", "y")
        span.add_event("evt", {"payload": "ignored"})


def test_safe_span_ignores_attribute_application_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Attribute-application failures should not break a safe span."""

    class _FailingSpan:
        def set_attribute(self, _key: str, _value: Any) -> None:
            raise RuntimeError("attribute failure")

    class _SpanContextManager:
        def __enter__(self) -> Any:
            return _FailingSpan()

        def __exit__(self, *_args: object) -> bool:
            return False

    class _Tracer:
        def start_as_current_span(self, *_args: object, **_kwargs: object) -> Any:
            return _SpanContextManager()

    monkeypatch.setattr("app.telemetry.genai.get_tracer", lambda _name: _Tracer(), raising=True)

    with safe_span(
        "attrs-fail",
        tracer_name="test",
        kind="INTERNAL",
        attrs={REQUEST_ID_ATTR: "req-1"},
    ) as span:
        assert span is not None


def test_null_span_and_attr_sanitizers_cover_noop_paths() -> None:
    """No-op span helpers and sanitizers should drop unsupported data."""

    NULL_SPAN.update_name("ignored")
    NULL_SPAN.record_exception(RuntimeError("ignored"))

    class _RecordingSpan:
        def __init__(self) -> None:
            self.attributes: dict[str, Any] = {}

        def set_attribute(self, key: str, value: Any) -> None:
            self.attributes[key] = value

    span = _RecordingSpan()
    set_attributes(
        span,
        **{
            REQUEST_ID_ATTR: "req-2",
            "unsupported.attr": "drop",
            USER_TIER_ATTR: None,
        },
    )

    assert span.attributes == {REQUEST_ID_ATTR: "req-2"}
    assert _sanitize_event_attrs(
        {
            "role": "user",
            "pulseplate.prompt.length": None,
            "unsupported.attr": "drop",
        }
    ) == {"role": "user"}


def test_prompt_fingerprint_skips_without_hmac_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fingerprint helpers should no-op when tracing is enabled without an HMAC key."""

    class _RecordingSpan:
        def __init__(self) -> None:
            self.attributes: dict[str, Any] = {}

        def set_attribute(self, key: str, value: Any) -> None:
            self.attributes[key] = value

    monkeypatch.setattr("app.telemetry.genai.tracing_is_enabled", lambda: True, raising=True)
    monkeypatch.delenv("PULSE_OBS_HMAC_KEY", raising=False)

    span = _RecordingSpan()
    set_prompt_fingerprint(span, "no fingerprint should be written")

    assert span.attributes == {}


def test_prompt_and_completion_events_skip_when_not_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Event helpers should skip emission when event names are not allowlisted."""

    class _RecordingSpan:
        def __init__(self) -> None:
            self.events: list[tuple[str, dict[str, Any] | None]] = []

        def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
            self.events.append((name, attributes))

    monkeypatch.setattr("app.telemetry.genai.tracing_is_enabled", lambda: True, raising=True)
    monkeypatch.setattr("app.telemetry.genai._ALLOWED_EVENT_NAMES", frozenset(), raising=True)
    monkeypatch.setenv("PULSE_OBS_HMAC_KEY", "test-genai-hmac-key")

    span = _RecordingSpan()
    add_prompt_event(span, "hidden prompt", role="user")
    add_completion_event(span, "hidden completion")

    assert span.events == []


def test_tracing_middleware_handles_init_and_error_path_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracing middleware should survive init failures and error-path span failures."""

    class _ExplodingSpan:
        def update_name(self, _name: str) -> None:
            raise RuntimeError("update failed")

        def set_attribute(self, _key: str, _value: Any) -> None:
            raise RuntimeError("attr failed")

        def record_exception(self, _exc: BaseException) -> None:
            raise RuntimeError("record failed")

    @contextmanager
    def _broken_request_span(_method: str, _request_id: str) -> Any:
        yield _ExplodingSpan()

    app = FastAPI()
    register_tracing(app)

    @app.get("/boom")
    async def _boom() -> None:
        raise HTTPException(status_code=500, detail="boom")

    monkeypatch.setattr(
        "app.bootstrap.tracing.ensure_tracing_initialized",
        lambda: (_ for _ in ()).throw(RuntimeError("otel disabled")),
        raising=True,
    )
    monkeypatch.setattr(
        "app.bootstrap.tracing.request_span",
        _broken_request_span,
        raising=True,
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500


def test_tracing_middleware_handles_response_finalization_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracing middleware should survive response-path span finalization failures."""

    class _ExplodingSpan:
        def update_name(self, _name: str) -> None:
            raise RuntimeError("update failed")

        def set_attribute(self, _key: str, _value: Any) -> None:
            raise RuntimeError("attr failed")

    @contextmanager
    def _broken_request_span(_method: str, _request_id: str) -> Any:
        yield _ExplodingSpan()

    app = FastAPI()
    register_tracing(app)

    @app.get("/ok")
    async def _ok() -> JSONResponse:
        return JSONResponse({"ok": True})

    monkeypatch.setattr(
        "app.bootstrap.tracing.request_span",
        _broken_request_span,
        raising=True,
    )

    client = TestClient(app)
    response = client.get("/ok")

    assert response.status_code == 200


def test_insight_tracing_emits_chain_and_llm_spans(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tracing_exporter: InMemorySpanExporter,
    vip_headers: dict[str, str],
) -> None:
    """Insight path should emit CHAIN and LLM spans without raw prompt leakage."""

    import llm

    class AsyncStubProvider:
        name = "stub"

        async def generate(self, text: str) -> str:
            return "trace-safe insight"

    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setattr(llm, "get_provider", lambda: AsyncStubProvider(), raising=True)

    response = client.post(
        "/api/v1/insight",
        json={"text": "hello tracing world"},
        headers=vip_headers,
    )

    assert response.status_code == 200
    spans = tracing_exporter.get_finished_spans()
    chain = _span_by_kind(spans, OPENINFERENCE_KIND_CHAIN)
    llm_span = _span_by_kind(spans, OPENINFERENCE_KIND_LLM)

    assert chain.name == "insight chain"
    assert chain.attributes[USER_TIER_ATTR] == "VIP"
    assert llm_span.attributes["gen_ai.request.model"] == "stub"
    assert llm_span.attributes["gen_ai.usage.input_tokens"] >= 1
    assert llm_span.attributes["gen_ai.usage.output_tokens"] >= 1
    assert PROMPT_FINGERPRINT_ATTR in llm_span.attributes
    assert COMPLETION_FINGERPRINT_ATTR in llm_span.attributes
    assert "hello tracing world" not in str(llm_span.attributes)
    assert "trace-safe insight" not in str(llm_span.attributes)
    for event in llm_span.events:
        assert "hello tracing world" not in str(event.attributes)
        assert "trace-safe insight" not in str(event.attributes)


def test_insight_tracing_emits_retrieval_span_when_rag_enabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tracing_exporter: InMemorySpanExporter,
    vip_headers: dict[str, str],
) -> None:
    """Insight tracing should include retrieval span on the RAG path."""

    import llm

    class AsyncStubProvider:
        name = "stub"

        async def generate(self, text: str) -> str:
            return "rag traced insight"

    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("FEATURE_RAG", "true")
    monkeypatch.setattr(llm, "get_provider", lambda: AsyncStubProvider(), raising=True)

    async def _mock_retrieve_and_validate_rag(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            formatted_prompt="rag formatted prompt",
            confidence=0.92,
            rag_actually_used=True,
            hops=2,
            latency_ms=11,
            chunks=[],
        )

    monkeypatch.setattr(
        "core.rag.orchestration.retrieve_and_validate_rag",
        _mock_retrieve_and_validate_rag,
        raising=True,
    )

    response = client.post(
        "/insight",
        json={"text": "use rag please"},
        headers=vip_headers,
    )

    assert response.status_code == 200
    spans = tracing_exporter.get_finished_spans()
    retrieval = _span_by_kind(spans, OPENINFERENCE_KIND_RETRIEVER)

    assert retrieval.name == "retrieval query"
    assert retrieval.attributes["pulseplate.retrieval.max_chunks"] == 3
    assert retrieval.attributes["pulseplate.rag.hops"] == 2


def test_cbt_tracing_emits_agent_retriever_and_llm_spans(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tracing_exporter: InMemorySpanExporter,
    pro_headers: dict[str, str],
    tmp_path: Any,
) -> None:
    """CBT route should emit AGENT, RETRIEVER, and LLM spans."""

    from core.rag.contracts import RAGChunk, RAGContext

    @dataclass
    class SyncStubProvider:
        name: str = "stub"

        def generate(self, text: str) -> str:
            return "cbt trace-safe response"

    def _mock_retrieve(*args: object, **kwargs: object) -> RAGContext:
        return RAGContext(
            query="cbt",
            refined_queries=[],
            chunks=[
                RAGChunk(
                    chunk_id="cbt-1",
                    file="docs/cbt/intro.md",
                    content="Thought records can help spot patterns.",
                    score=0.88,
                )
            ],
            confidence=0.88,
            hops=1,
            latency_ms=9,
        )

    monkeypatch.setenv("FEATURE_CBT_AGENT", "true")
    monkeypatch.setenv("AGENT_CONTROL_AUDIT_LOG_PATH", str(tmp_path / "cbt-tracing-audit.jsonl"))
    monkeypatch.setattr(
        "core.rag.vector_rag.retrieve_context_structured", _mock_retrieve, raising=True
    )
    monkeypatch.setattr("llm.get_provider", lambda: SyncStubProvider(), raising=True)

    response = client.post(
        "/api/v1/pro/cbt/insight",
        json={"query": "How do I reframe a thought?"},
        headers=pro_headers,
    )

    assert response.status_code == 200
    spans = tracing_exporter.get_finished_spans()

    agent = _span_by_kind(spans, OPENINFERENCE_KIND_AGENT)
    retrieval = _span_by_kind(spans, OPENINFERENCE_KIND_RETRIEVER)
    llm_inference = _span_by_kind(spans, OPENINFERENCE_KIND_LLM)

    assert agent.name == "cbt insight agent"
    assert agent.attributes[USER_TIER_ATTR] == "PRO"
    assert retrieval.attributes["pulseplate.rag.agent_id"] == "cbt-agent"
    assert llm_inference.attributes["gen_ai.request.model"] == "stub"
    assert PROMPT_FINGERPRINT_ATTR in llm_inference.attributes
    assert "How do I reframe a thought?" not in str(llm_inference.attributes)


def test_tool_span_emits_tool_kind(tracing_exporter: InMemorySpanExporter) -> None:
    """Tool spans should emit deterministic TOOL metadata."""

    with tool_span(
        name="nutrition",
        tool_kind="http",
        user_tier="VIP",
        route="/api/v1/insight",
    ):
        pass

    tool = _span_by_kind(tracing_exporter.get_finished_spans(), OPENINFERENCE_KIND_TOOL)

    assert tool.name == "tool nutrition"
    assert tool.attributes["pulseplate.tool.kind"] == "http"
