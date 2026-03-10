"""Deterministic tests for backend GenAI tracing."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import BaseRoute
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.bootstrap.tracing import register_tracing
from app.telemetry.genai import (
    COMPLETION_FINGERPRINT_ATTR,
    OPENINFERENCE_KIND_AGENT,
    OPENINFERENCE_KIND_CHAIN,
    OPENINFERENCE_KIND_LLM,
    OPENINFERENCE_KIND_RETRIEVER,
    OPENINFERENCE_SPAN_KIND,
    PROMPT_FINGERPRINT_ATTR,
    USER_TIER_ATTR,
    safe_span,
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


def test_safe_span_swallows_backend_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """GenAI span helpers must degrade to no-op if tracing backend fails."""

    def _raise(_name: str) -> Any:
        raise RuntimeError("otel backend unavailable")

    monkeypatch.setattr("app.telemetry.genai.get_tracer", _raise, raising=True)

    with safe_span("broken", tracer_name="test", kind="INTERNAL") as span:
        span.set_attribute("x", "y")
        span.add_event("evt", {"payload": "ignored"})


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
