"""Unit tests for app-layer insight runtime tracing adapters."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.insight_runtime import (
    TracedInsightProvider,
    _traced_retrieve_and_validate_rag,
    generate_traced_insight,
)
from app.utils.feature_flags import is_rag_context_compaction_enabled
from core.ai.insight_runtime import RecursiveOptimizationHints, RecursiveRolloutPolicy


@pytest.mark.asyncio
async def test_traced_provider_updates_span_provider_name_after_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback winner must be reflected in tracing metadata and wrapper identity."""

    observed_attrs: dict[str, Any] = {}

    @contextmanager
    def _fake_llm_span(**_kwargs: object) -> Any:
        yield SimpleNamespace()

    async def _generate(_text: str) -> str:
        return "fallback response"

    provider = SimpleNamespace(
        name="perplexity",
        active_provider_name="stub",
        generate=_generate,
    )

    monkeypatch.setattr("app.services.insight_runtime.llm_span", _fake_llm_span, raising=True)
    monkeypatch.setattr(
        "app.services.insight_runtime.set_attributes",
        lambda _span, **attrs: observed_attrs.update(attrs),
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_runtime.finalize_llm_span",
        lambda _span, _result: None,
        raising=True,
    )

    traced = TracedInsightProvider(provider, user_tier="VIP", route="/api/v1/insight")

    result = await traced.generate("hello")

    assert result == "fallback response"
    assert traced.name == "stub"
    assert observed_attrs["gen_ai.provider.name"] == "stub"


@pytest.mark.asyncio
async def test_generate_traced_insight_forwards_prepared_recursive_optimization_hints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracing adapter must pass prepared recursive hints without recomputing them."""

    observed: dict[str, Any] = {}

    @contextmanager
    def _fake_chain_span(*_args: object, **_kwargs: object) -> Any:
        yield SimpleNamespace()

    @contextmanager
    def _fake_retrieval_span(*_args: object, **_kwargs: object) -> Any:
        yield SimpleNamespace()

    async def _fake_retrieve_and_validate_rag(*args: object, **kwargs: object) -> Any:
        observed["retrieve_args"] = args
        observed["retrieve_kwargs"] = kwargs
        return SimpleNamespace(hops=1)

    class _FakeRuntime:
        async def generate_insight(self, **kwargs: object) -> object:
            observed["runtime_kwargs"] = kwargs
            rag_retriever = kwargs["rag_retriever"]
            await rag_retriever(
                "hello",
                max_chunks=3,
                philo_validation_enabled=False,
                recursive_rag_enabled=True,
                subject_id=123,
                knowledge_policy={"enabled": True},
            )
            return SimpleNamespace(
                insight="ok",
                provider_name="provider",
                source_dicts=[],
                confidence=0.8,
                rag_used=True,
                hops=1,
                latency_ms=5,
                knowledge_candidates=[],
                metadata=SimpleNamespace(
                    route_type="deep_reasoning",
                    depth_used=2,
                    verification_rate=None,
                    falsifiability_rate=None,
                    contradiction_count=0,
                    reason_codes=["legacy_path"],
                    optimization_applied=False,
                ),
            )

    monkeypatch.setattr("app.services.insight_runtime.chain_span", _fake_chain_span, raising=True)
    monkeypatch.setattr(
        "app.services.insight_runtime.retrieval_span",
        _fake_retrieval_span,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_runtime.rag_orchestration.retrieve_and_validate_rag",
        _fake_retrieve_and_validate_rag,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_runtime.set_attributes",
        lambda *_args, **_kwargs: None,
        raising=True,
    )

    await generate_traced_insight(
        runtime=_FakeRuntime(),
        text="hello",
        lang=None,
        provider=SimpleNamespace(name="provider", generate=lambda text: text),
        use_rag=True,
        philo_validation_enabled=False,
        recursive_rag_enabled=True,
        recursive_rag_optimization_enabled=True,
        route_path="/api/v1/insight",
        route_type="deep_reasoning",
        user_tier="VIP",
        subject_id=123,
        knowledge_policy={"enabled": True},
        recursive_rollout_policy=RecursiveRolloutPolicy(
            use_rag=True,
            recursive_rag_enabled=True,
            recursive_rag_optimization_enabled=True,
            optimization_hints=RecursiveOptimizationHints(target_depth_cap=2),
        ),
    )

    assert observed["runtime_kwargs"]["recursive_rag_enabled"] is True
    assert observed["retrieve_kwargs"][
        "recursive_optimization_hints"
    ] == RecursiveOptimizationHints(target_depth_cap=2)


def test_request_time_context_compaction_flag_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The app layer must observe and forward the optional flag per request."""
    observed: dict[str, Any] = {}

    @contextmanager
    def _fake_retrieval_span(*_args: object, **_kwargs: object) -> Any:
        yield SimpleNamespace()

    async def _fake_retrieve_and_validate_rag(*args: object, **kwargs: object) -> Any:
        observed["args"] = args
        observed["kwargs"] = kwargs
        return SimpleNamespace(hops=1)

    monkeypatch.setattr(
        "app.services.insight_runtime.retrieval_span",
        _fake_retrieval_span,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_runtime.rag_orchestration.retrieve_and_validate_rag",
        _fake_retrieve_and_validate_rag,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_runtime.set_attributes",
        lambda *_args, **_kwargs: None,
        raising=True,
    )
    monkeypatch.delenv("FEATURE_RAG_CONTEXT_COMPACTION", raising=False)
    assert is_rag_context_compaction_enabled() is False
    monkeypatch.setenv("FEATURE_RAG_CONTEXT_COMPACTION", "true")

    asyncio.run(
        _traced_retrieve_and_validate_rag(
            "hello",
            max_chunks=3,
            philo_validation_enabled=True,
            recursive_rollout_policy=RecursiveRolloutPolicy(
                use_rag=True,
                recursive_rag_enabled=False,
                recursive_rag_optimization_enabled=False,
            ),
            subject_id=123,
            knowledge_policy={"enabled": True},
            user_tier="VIP",
            route_path="/api/v1/insight",
        )
    )

    assert observed["kwargs"]["context_compaction_enabled"] is True
    assert is_rag_context_compaction_enabled() is True

    monkeypatch.setenv("FEATURE_RAG_CONTEXT_COMPACTION", "false")
    asyncio.run(
        _traced_retrieve_and_validate_rag(
            "hello",
            max_chunks=3,
            philo_validation_enabled=True,
            recursive_rollout_policy=RecursiveRolloutPolicy(
                use_rag=True,
                recursive_rag_enabled=False,
                recursive_rag_optimization_enabled=False,
            ),
            subject_id=123,
            knowledge_policy={"enabled": True},
            user_tier="VIP",
            route_path="/api/v1/insight",
        )
    )

    assert observed["kwargs"]["context_compaction_enabled"] is False
    assert is_rag_context_compaction_enabled() is False
