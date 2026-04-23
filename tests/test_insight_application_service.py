"""Unit tests for the shared insight application service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException, status

from app.services.insight_application_service import (
    INSIGHT_TEXT_MAX_LENGTH,
    execute_insight_request,
)
from core.ai.insight_runtime import InsightTransparencyNotice, RecursiveRolloutPolicy
from core.insight.philosophical_runtime import PhilosophyRolloutPolicy
from core.knowledge.policy import KnowledgePolicy
from core.insight.llm_provider_loader import LLMProvider
from core.verification.contracts import VerificationArtifact, VerificationBundle


class _FakeProvider:
    """Minimal provider stub matching the insight runtime protocol.

    RU: Минимальный provider stub для типобезопасного тестового seams.
    EN: Minimal provider stub for type-safe testing seams.
    """

    name: str = "fake-provider"

    def generate(self, prompt: str) -> Awaitable[str]:
        raise RuntimeError(f"Unexpected provider.generate call for prompt={prompt!r}")


def _knowledge_policy() -> KnowledgePolicy:
    return KnowledgePolicy(
        enabled=True,
        allow_reads=True,
        allow_promotion=False,
        min_confidence=0.7,
        require_rag_factual_route=True,
        deny_degraded_reasons=("retrieval_empty",),
        subject_scope_required=True,
        rail="product_ai_runtime",
    )


def _rollout_policy(
    *,
    router_enabled: bool = False,
    phase12_enabled: bool = False,
    linguistic_enabled: bool = False,
    pragmatic_enabled: bool = False,
) -> PhilosophyRolloutPolicy:
    return PhilosophyRolloutPolicy(
        router_enabled=router_enabled,
        phase12_enabled=phase12_enabled,
        linguistic_enabled=linguistic_enabled,
        pragmatic_enabled=pragmatic_enabled,
    )


def _verification_bundle(*, admission_allowed: bool = True) -> VerificationBundle:
    status = "pass" if admission_allowed else "fail"
    return VerificationBundle(
        artifacts=(
            VerificationArtifact(
                artifact_id=f"service-{status}",
                verifier_id="service_test_verifier",
                status=status,
                reason_codes=(
                    ("verification_checks_pass",) if admission_allowed else ("verification_failed",)
                ),
            ),
        ),
        overall_status=status,
        admission_allowed=admission_allowed,
        reason_codes=(
            ("verification_checks_pass",) if admission_allowed else ("verification_failed",)
        ),
    )


def _recursive_rollout_policy(
    *,
    use_rag: bool = False,
    recursive_rag_enabled: bool = False,
    recursive_rag_optimization_enabled: bool = False,
) -> RecursiveRolloutPolicy:
    return RecursiveRolloutPolicy(
        use_rag=use_rag,
        recursive_rag_enabled=recursive_rag_enabled,
        recursive_rag_optimization_enabled=recursive_rag_optimization_enabled,
    )


@pytest.mark.asyncio
async def test_execute_insight_request_uses_injected_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service must preserve injected patch-points and response mapping."""

    observed: dict[str, Any] = {}

    @dataclass
    class _Request:
        text: str

    def _input_guard(text: str) -> None:
        observed["guard_text"] = text

    def _provider_loader() -> LLMProvider:
        observed["provider_loader_called"] = True
        return _FakeProvider()

    def _transparency_loader() -> tuple[str, str]:
        observed["transparency_loader_called"] = True
        return ("ai_generated_insight", "Wellness only.")

    def _direct_provider_factory() -> LLMProvider:
        observed["direct_provider_factory_called"] = True
        return _FakeProvider()

    def _response_factory(**payload: object) -> dict[str, object]:
        observed["response_payload"] = payload
        return dict(payload)

    def _source_item_factory(**payload: object) -> dict[str, object]:
        return dict(payload)

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=object(),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
        rollout_policy=_rollout_policy(
            phase12_enabled=True,
            linguistic_enabled=True,
        ),
        recursive_rollout_policy=_recursive_rollout_policy(),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        observed["generate_kwargs"] = kwargs
        return SimpleNamespace(
            insight="generated insight",
            provider_name="fake-provider",
            source_dicts=[{"chunk_id": "c1", "file": "doc.md", "score": 0.9, "hop": 1}],
            confidence=0.9,
            rag_used=True,
            hops=1,
            latency_ms=12,
            knowledge_candidates=[],
            metadata=SimpleNamespace(
                route_type="deep_reasoning",
                depth_used=2,
                verification_rate=0.8,
                falsifiability_rate=0.7,
                contradiction_count=0,
                reason_codes=["legacy_path"],
                optimization_applied=False,
            ),
        )

    def _fake_prepare_insight_runtime(**kwargs: object) -> object:
        observed["prepare_kwargs"] = kwargs
        return prepared_runtime

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        _fake_prepare_insight_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_router_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_phase12_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_linguistic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_pragmatic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_optimization_enabled",
        lambda: False,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        subject_id=123,
        input_guard=_input_guard,
        provider_loader=_provider_loader,
        transparency_loader=_transparency_loader,
        direct_provider_factory=_direct_provider_factory,
        response_factory=_response_factory,
        source_item_factory=_source_item_factory,
    )

    assert observed["guard_text"] == "hello"
    assert observed["prepare_kwargs"] == {
        "text": "hello",
        "use_rag": False,
        "philosophy_router_enabled": False,
        "philosophy_phase12_enabled": False,
        "philosophy_linguistic_enabled": False,
        "philosophy_pragmatic_enabled": False,
        "recursive_rag_enabled": False,
        "recursive_rag_optimization_enabled": False,
        "provider_loader": _provider_loader,
        "transparency_loader": _transparency_loader,
        "direct_provider_factory": _direct_provider_factory,
    }
    assert observed["generate_kwargs"]["subject_id"] == 123
    assert observed["generate_kwargs"]["route_path"] == "/api/v1/insight"
    assert observed["generate_kwargs"]["knowledge_policy"] == prepared_runtime.knowledge_policy
    assert observed["generate_kwargs"]["rollout_policy"] is prepared_runtime.rollout_policy
    assert (
        observed["generate_kwargs"]["recursive_rollout_policy"]
        is prepared_runtime.recursive_rollout_policy
    )
    assert response["provider"] == "fake-provider"
    assert response["transparency_notice_id"] == "ai_generated_insight"
    assert response["sources"][0]["chunk_id"] == "c1"
    assert "rollout_policy" not in response


@pytest.mark.asyncio
async def test_execute_insight_request_rejects_oversized_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oversized prompt text must fail fast with 413 instead of silent truncation."""

    observed: dict[str, Any] = {}

    @dataclass
    class _Request:
        text: str

    def _input_guard(text: str) -> None:
        observed["guard_text"] = text

    def _provider_loader() -> LLMProvider:
        raise AssertionError("provider loader must not run for oversized prompts")

    def _transparency_loader() -> tuple[str, str]:
        raise AssertionError("transparency loader must not run for oversized prompts")

    def _response_factory(**payload: object) -> dict[str, object]:
        return dict(payload)

    def _source_item_factory(**payload: object) -> dict[str, object]:
        return dict(payload)

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: observed.setdefault("prepare_kwargs", kwargs),
        raising=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        await execute_insight_request(
            _Request(text="x" * (INSIGHT_TEXT_MAX_LENGTH + 1)),
            route_path="/api/v1/insight",
            user_tier="VIP",
            input_guard=_input_guard,
            provider_loader=_provider_loader,
            transparency_loader=_transparency_loader,
            response_factory=_response_factory,
            source_item_factory=_source_item_factory,
        )

    assert observed["guard_text"] == "x" * (INSIGHT_TEXT_MAX_LENGTH + 1)
    assert "prepare_kwargs" not in observed
    assert exc_info.value.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert exc_info.value.detail == "Prompt too long"


@pytest.mark.asyncio
async def test_execute_insight_request_uses_prepared_rollout_policy_as_execution_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepared rollout truth must flow downstream even if env-backed rollout readers disagree."""

    observed: dict[str, Any] = {}

    @dataclass
    class _Request:
        text: str

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=object(),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
        rollout_policy=_rollout_policy(
            router_enabled=True,
            phase12_enabled=True,
            linguistic_enabled=False,
            pragmatic_enabled=True,
        ),
        recursive_rollout_policy=_recursive_rollout_policy(
            use_rag=True,
            recursive_rag_enabled=True,
            recursive_rag_optimization_enabled=True,
        ),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        observed["generate_kwargs"] = kwargs
        return SimpleNamespace(
            insight="generated insight",
            provider_name="fake-provider",
            source_dicts=[],
            confidence=0.9,
            rag_used=False,
            hops=0,
            latency_ms=12,
            knowledge_candidates=[],
            metadata=SimpleNamespace(
                route_type="deep_reasoning",
                depth_used=2,
                verification_rate=0.8,
                falsifiability_rate=0.7,
                contradiction_count=0,
                reason_codes=["legacy_path"],
                optimization_applied=False,
            ),
        )

    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_router_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_phase12_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_linguistic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_pragmatic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_optimization_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["generate_kwargs"]["rollout_policy"] is prepared_runtime.rollout_policy
    assert (
        observed["generate_kwargs"]["recursive_rollout_policy"]
        is prepared_runtime.recursive_rollout_policy
    )
    assert observed["generate_kwargs"]["recursive_rag_enabled"] is True
    assert observed["generate_kwargs"]["recursive_rag_optimization_enabled"] is True
    assert response["route_type"] == "deep_reasoning"
    assert "rollout_policy" not in response


@pytest.mark.asyncio
async def test_execute_insight_request_uses_prepared_recursive_rollout_policy_as_execution_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepared recursive rollout truth must win over disagreeing env-backed readers."""

    observed: dict[str, Any] = {}

    @dataclass
    class _Request:
        text: str

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=object(),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
        rollout_policy=_rollout_policy(),
        recursive_rollout_policy=_recursive_rollout_policy(
            use_rag=True,
            recursive_rag_enabled=True,
            recursive_rag_optimization_enabled=False,
        ),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        observed["generate_kwargs"] = kwargs
        return SimpleNamespace(
            insight="generated insight",
            provider_name="fake-provider",
            source_dicts=[],
            confidence=0.9,
            rag_used=True,
            hops=1,
            latency_ms=12,
            knowledge_candidates=[],
            metadata=SimpleNamespace(
                route_type="deep_reasoning",
                depth_used=2,
                verification_rate=0.8,
                falsifiability_rate=0.7,
                contradiction_count=0,
                reason_codes=["legacy_path"],
                optimization_applied=False,
            ),
        )

    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_router_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_phase12_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_linguistic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_pragmatic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_optimization_enabled",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["generate_kwargs"]["recursive_rollout_policy"] is (
        prepared_runtime.recursive_rollout_policy
    )
    assert observed["generate_kwargs"]["use_rag"] is True
    assert observed["generate_kwargs"]["recursive_rag_enabled"] is True
    assert observed["generate_kwargs"]["recursive_rag_optimization_enabled"] is False
    assert response["rag_used"] is True
    assert "recursive_rollout_policy" not in response


@pytest.mark.asyncio
async def test_execute_insight_request_does_not_build_legacy_recursive_policy_when_prepared_policy_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepared recursive rollout policy must not trigger the legacy fallback path."""

    observed: dict[str, Any] = {}

    @dataclass
    class _Request:
        text: str

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=object(),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
        rollout_policy=_rollout_policy(),
        recursive_rollout_policy=_recursive_rollout_policy(),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        observed["generate_kwargs"] = kwargs
        return SimpleNamespace(
            insight="generated insight",
            provider_name="fake-provider",
            source_dicts=[],
            confidence=0.9,
            rag_used=True,
            hops=1,
            latency_ms=12,
            knowledge_candidates=[],
            metadata=SimpleNamespace(
                route_type="deep_reasoning",
                depth_used=2,
                verification_rate=0.8,
                falsifiability_rate=0.7,
                contradiction_count=0,
                reason_codes=["prepared_policy"],
                optimization_applied=True,
            ),
        )

    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_router_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_phase12_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_linguistic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_philosophy_pragmatic_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_enabled",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_optimization_enabled",
        lambda: False,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    def _unexpected_legacy_policy(**kwargs: object) -> RecursiveRolloutPolicy:
        raise AssertionError("legacy recursive rollout helper should not run")

    monkeypatch.setattr(
        "app.services.insight_application_service._legacy_recursive_rollout_policy",
        _unexpected_legacy_policy,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["generate_kwargs"]["recursive_rollout_policy"] is (
        prepared_runtime.recursive_rollout_policy
    )
    assert (
        observed["generate_kwargs"]["use_rag"] is prepared_runtime.recursive_rollout_policy.use_rag
    )
    assert response["rag_used"] is True


@pytest.mark.asyncio
async def test_execute_insight_request_clamps_legacy_recursive_fallback_when_rag_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy prepared-runtime doubles must stay fail-closed when request RAG is off."""

    observed: dict[str, Any] = {}

    @dataclass
    class _Request:
        text: str

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=object(),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
        rollout_policy=_rollout_policy(),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        observed["generate_kwargs"] = kwargs
        return SimpleNamespace(
            insight="generated insight",
            provider_name="fake-provider",
            source_dicts=[],
            confidence=0.9,
            rag_used=False,
            hops=0,
            latency_ms=12,
            knowledge_candidates=[],
            metadata=SimpleNamespace(
                route_type="deep_reasoning",
                depth_used=2,
                verification_rate=0.8,
                falsifiability_rate=0.7,
                contradiction_count=0,
                reason_codes=["legacy_path"],
                optimization_applied=False,
            ),
        )

    monkeypatch.setenv("FEATURE_RAG", "false")
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_enabled",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.is_recursive_rag_optimization_enabled",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["generate_kwargs"]["use_rag"] is False
    assert observed["generate_kwargs"]["recursive_rag_enabled"] is False
    assert observed["generate_kwargs"]["recursive_rag_optimization_enabled"] is False
    assert response["rag_used"] is False
    assert "recursive_rollout_policy" not in response


@pytest.mark.asyncio
async def test_execute_insight_request_prefers_active_fallback_provider_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Service response must expose the actual fallback winner, not wrapper metadata."""

    @dataclass
    class _Request:
        text: str

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=SimpleNamespace(active_provider_name="stub"),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="deep_reasoning")),
        rollout_policy=_rollout_policy(),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        return SimpleNamespace(
            insight="generated insight",
            provider_name="perplexity",
            source_dicts=[],
            confidence=0.9,
            rag_used=False,
            hops=0,
            latency_ms=5,
            knowledge_candidates=[],
            metadata=SimpleNamespace(
                route_type="deep_reasoning",
                depth_used=1,
                verification_rate=0.0,
                falsifiability_rate=0.0,
                contradiction_count=0,
                reason_codes=[],
                optimization_applied=False,
            ),
        )

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert response["provider"] == "stub"


@pytest.mark.asyncio
async def test_execute_insight_request_hands_internal_candidates_to_store_without_payload_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Thin service may promote internal candidates without changing public payload."""

    observed: dict[str, Any] = {}

    @dataclass
    class _Request:
        text: str

    candidate = SimpleNamespace(fact_key="fact-1")
    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=SimpleNamespace(active_provider_name="stub"),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="rag_factual")),
        rollout_policy=_rollout_policy(
            router_enabled=True,
            phase12_enabled=True,
            linguistic_enabled=True,
        ),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        observed["generate_kwargs"] = kwargs
        return SimpleNamespace(
            insight="generated insight",
            provider_name="stub",
            source_dicts=[],
            confidence=0.92,
            rag_used=True,
            hops=1,
            latency_ms=8,
            knowledge_candidates=[candidate],
            verification_bundle=_verification_bundle(),
            metadata=SimpleNamespace(
                route_type="rag_factual",
                depth_used=1,
                verification_rate=1.0,
                falsifiability_rate=1.0,
                contradiction_count=0,
                reason_codes=["rag_factual"],
                optimization_applied=False,
            ),
        )

    class _Store:
        def promote(self, candidates: list[object]) -> list[object]:
            observed["promoted"] = candidates
            return candidates

        def read(
            self, *, subject: str, predicate: str, access_scope: str, rail: str
        ) -> list[object]:
            del subject, predicate, access_scope, rail
            return []

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        subject_id=42,
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        knowledge_store=_Store(),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["promoted"] == [candidate]
    assert response["provider"] == "stub"
    assert "knowledge_candidates" not in response


@pytest.mark.asyncio
async def test_execute_insight_request_skips_store_when_no_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty candidate handoff must not touch the store seam."""

    observed: dict[str, Any] = {"promote_called": False}

    @dataclass
    class _Request:
        text: str

    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=SimpleNamespace(active_provider_name="stub"),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="rag_factual")),
        rollout_policy=_rollout_policy(
            router_enabled=True,
            phase12_enabled=True,
            linguistic_enabled=True,
        ),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        return SimpleNamespace(
            insight="generated insight",
            provider_name="stub",
            source_dicts=[],
            confidence=0.92,
            rag_used=True,
            hops=1,
            latency_ms=8,
            knowledge_candidates=[],
            metadata=SimpleNamespace(
                route_type="rag_factual",
                depth_used=1,
                verification_rate=1.0,
                falsifiability_rate=1.0,
                contradiction_count=0,
                reason_codes=["rag_factual"],
                optimization_applied=False,
            ),
        )

    class _Store:
        def promote(self, candidates: list[object]) -> list[object]:
            observed["promote_called"] = True
            return candidates

        def read(
            self, *, subject: str, predicate: str, access_scope: str, rail: str
        ) -> list[object]:
            del subject, predicate, access_scope, rail
            return []

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        subject_id=42,
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        knowledge_store=_Store(),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["promote_called"] is False
    assert response["provider"] == "stub"


@pytest.mark.asyncio
async def test_execute_insight_request_survives_store_promotion_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Knowledge promotion errors must not fail an otherwise valid response."""

    @dataclass
    class _Request:
        text: str

    candidate = SimpleNamespace(fact_key="fact-1")
    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=SimpleNamespace(active_provider_name="stub"),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="rag_factual")),
        rollout_policy=_rollout_policy(
            router_enabled=True,
            phase12_enabled=True,
            linguistic_enabled=True,
        ),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        return SimpleNamespace(
            insight="generated insight",
            provider_name="stub",
            source_dicts=[],
            confidence=0.92,
            rag_used=True,
            hops=1,
            latency_ms=8,
            knowledge_candidates=[candidate],
            verification_bundle=_verification_bundle(),
            metadata=SimpleNamespace(
                route_type="rag_factual",
                depth_used=1,
                verification_rate=1.0,
                falsifiability_rate=1.0,
                contradiction_count=0,
                reason_codes=["rag_factual"],
                optimization_applied=False,
            ),
        )

    class _AsyncFailingStore:
        async def promote(self, candidates: list[object]) -> list[object]:
            del candidates
            raise RuntimeError("store unavailable")

        def read(
            self, *, subject: str, predicate: str, access_scope: str, rail: str
        ) -> list[object]:
            del subject, predicate, access_scope, rail
            return []

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        subject_id=42,
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        knowledge_store=_AsyncFailingStore(),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert response["provider"] == "stub"


@pytest.mark.asyncio
async def test_execute_insight_request_skips_store_when_bundle_denies_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Denied admission bundle must block persistence without changing the response."""

    observed: dict[str, Any] = {"promote_called": False}

    @dataclass
    class _Request:
        text: str

    candidate = SimpleNamespace(fact_key="fact-1")
    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=SimpleNamespace(active_provider_name="stub"),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="rag_factual")),
        rollout_policy=_rollout_policy(
            router_enabled=True,
            phase12_enabled=True,
            linguistic_enabled=True,
        ),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        return SimpleNamespace(
            insight="generated insight",
            provider_name="stub",
            source_dicts=[],
            confidence=0.92,
            rag_used=True,
            hops=1,
            latency_ms=8,
            knowledge_candidates=[candidate],
            verification_bundle=_verification_bundle(admission_allowed=False),
            metadata=SimpleNamespace(
                route_type="rag_factual",
                depth_used=1,
                verification_rate=1.0,
                falsifiability_rate=1.0,
                contradiction_count=0,
                reason_codes=["rag_factual"],
                optimization_applied=False,
            ),
        )

    class _Store:
        def promote(self, candidates: list[object]) -> list[object]:
            observed["promote_called"] = True
            return candidates

        def read(
            self, *, subject: str, predicate: str, access_scope: str, rail: str
        ) -> list[object]:
            del subject, predicate, access_scope, rail
            return []

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        subject_id=42,
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        knowledge_store=_Store(),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["promote_called"] is False
    assert response["provider"] == "stub"


@pytest.mark.asyncio
async def test_execute_insight_request_skips_store_when_bundle_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing admission bundle must fail closed before persistence."""

    observed: dict[str, Any] = {"promote_called": False}

    @dataclass
    class _Request:
        text: str

    candidate = SimpleNamespace(fact_key="fact-1")
    prepared_runtime = SimpleNamespace(
        runtime=object(),
        provider=SimpleNamespace(active_provider_name="stub"),
        decision=SimpleNamespace(route_type=SimpleNamespace(value="rag_factual")),
        rollout_policy=_rollout_policy(
            router_enabled=True,
            phase12_enabled=True,
            linguistic_enabled=True,
        ),
        transparency_notice=InsightTransparencyNotice(
            surface_id="ai_generated_insight",
            wellness_boundary="Wellness only.",
        ),
        knowledge_policy=_knowledge_policy(),
    )

    async def _fake_generate_traced_insight(**kwargs: object) -> object:
        return SimpleNamespace(
            insight="generated insight",
            provider_name="stub",
            source_dicts=[],
            confidence=0.92,
            rag_used=True,
            hops=1,
            latency_ms=8,
            knowledge_candidates=[candidate],
            verification_bundle=None,
            metadata=SimpleNamespace(
                route_type="rag_factual",
                depth_used=1,
                verification_rate=1.0,
                falsifiability_rate=1.0,
                contradiction_count=0,
                reason_codes=["rag_factual"],
                optimization_applied=False,
            ),
        )

    class _Store:
        def promote(self, candidates: list[object]) -> list[object]:
            observed["promote_called"] = True
            return candidates

        def read(
            self, *, subject: str, predicate: str, access_scope: str, rail: str
        ) -> list[object]:
            del subject, predicate, access_scope, rail
            return []

    monkeypatch.setattr(
        "app.services.insight_application_service.prepare_insight_runtime",
        lambda **kwargs: prepared_runtime,
        raising=True,
    )
    monkeypatch.setattr(
        "app.services.insight_application_service.generate_traced_insight",
        _fake_generate_traced_insight,
        raising=True,
    )

    response = await execute_insight_request(
        _Request(text="hello"),
        route_path="/api/v1/insight",
        user_tier="VIP",
        subject_id=42,
        input_guard=lambda text: None,
        provider_loader=lambda: _FakeProvider(),
        transparency_loader=lambda: ("ai_generated_insight", "Wellness only."),
        knowledge_store=_Store(),
        response_factory=lambda **payload: dict(payload),
        source_item_factory=lambda **payload: dict(payload),
    )

    assert observed["promote_called"] is False
    assert response["provider"] == "stub"
