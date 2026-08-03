"""
Deterministic tests for RAG response fields in InsightResponse per RAG_CONTRACT.md §2.

Covers: sources[], confidence, rag_used, hops, latency_ms in both
/api/v1/insight and /insight endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generator, Optional
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.insight import philosophical_runtime as runtime_mod
from tests._client import (
    disable_rate_limiting_for_test_app,
    open_test_client,
    override_rate_limit_identity_for_test_app,
)
from tests.helpers.module_resolve import resolve_module

_INSIGHT_RESPONSE_FIELDS = {
    "provider",
    "insight",
    "sources",
    "confidence",
    "rag_used",
    "hops",
    "latency_ms",
    "route_type",
    "depth_used",
    "verification_rate",
    "falsifiability_rate",
    "contradiction_count",
    "reason_codes",
    "optimization_applied",
    "automated_analysis",
    "transparency_notice_id",
    "wellness_boundary",
}


@dataclass
class _FakeRAGChunk:
    chunk_id: str
    file: str
    content: str
    score: float
    hop: int = 1


@dataclass
class _FakeRAGContext:
    query: str
    refined_queries: list[str]
    chunks: list[_FakeRAGChunk]
    confidence: float
    hops: int
    latency_ms: int
    agent_id: Optional[str] = None
    user_tier: Optional[str] = None
    optimization_stats: dict[str, object] | None = None


def _make_fake_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeRAGContext:
    """Fake retrieve_context_structured that returns two chunks."""
    del subject_id
    chunks = [
        _FakeRAGChunk(
            chunk_id="readme.md:1",
            file="readme.md",
            content="BMI is body mass index.",
            score=0.85,
            hop=1,
        ),
        _FakeRAGChunk(
            chunk_id="faq.md:1",
            file="faq.md",
            content="# Source: internal.py (score=0.5)\nFrequently asked.",
            score=0.65,
            hop=1,
        ),
    ]
    return _FakeRAGContext(
        query=query,
        refined_queries=[query],
        chunks=chunks[:max_chunks],
        confidence=0.75,
        hops=1,
        latency_ms=42,
        agent_id=agent_id,
        user_tier=user_tier,
    )


def _make_empty_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeRAGContext:
    """Fake retrieve_context_structured that returns zero chunks."""
    del subject_id
    return _FakeRAGContext(
        query=query,
        refined_queries=[query],
        chunks=[],
        confidence=0.0,
        hops=1,
        latency_ms=5,
        agent_id=agent_id,
        user_tier=user_tier,
    )


def _make_boundary_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeRAGContext:
    """Return one rejected raw chunk and one valid baseline survivor."""
    del subject_id
    chunks = [
        _FakeRAGChunk(
            chunk_id="raw:rejected",
            file="raw.md",
            content="A diagnosis is required for this claim.",
            score=0.95,
        ),
        _FakeRAGChunk(
            chunk_id="baseline:survivor",
            file="wellness.md",
            content="Balanced meals support sustainable daily wellness.",
            score=0.85,
        ),
    ]
    return _FakeRAGContext(
        query=query,
        refined_queries=[query],
        chunks=chunks[:max_chunks],
        confidence=0.90,
        hops=1,
        latency_ms=17,
        agent_id=agent_id,
        user_tier=user_tier,
    )


def _make_fake_recursive_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
    philo_validation_enabled: bool = False,
    optimization_enabled: bool = False,
    optimization_hints: object | None = None,
) -> _FakeRAGContext:
    """Fake recursive retriever with deeper hops and refined query chain."""
    # Intentionally unused: keep signature parity with real recursive retriever.
    _ = (philo_validation_enabled, optimization_enabled, optimization_hints, subject_id)
    chunks = [
        _FakeRAGChunk(
            chunk_id="recursive.md:1",
            file="recursive.md",
            content="Recursive retrieval with deterministic verification.",
            score=0.82,
            hop=2,
        )
    ]
    return _FakeRAGContext(
        query=query,
        refined_queries=[query, f"{query} deterministic verification"],
        chunks=chunks[:max_chunks],
        confidence=0.82,
        hops=2,
        latency_ms=55,
        agent_id=agent_id,
        user_tier=user_tier,
        optimization_stats=(
            {
                "enabled": True,
                "cache_hits": 1,
                "refinement_cache_hits": 1,
                "verification_calls": 0,
                "stop_reason": "no_new_usable_chunks",
                "early_stop_no_query_change": False,
                "early_stop_no_new_chunks": True,
                "early_stop_low_confidence_gain": False,
                "early_stop_latency_budget": False,
            }
            if optimization_enabled
            else None
        ),
    )


def _make_stale_confidence_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeRAGContext:
    """Fake retriever output with stale aggregate confidence."""
    del subject_id
    chunks = [
        _FakeRAGChunk(
            chunk_id="readme.md:1",
            file="readme.md",
            content="BMI is body mass index.",
            score=0.9,
            hop=1,
        ),
        _FakeRAGChunk(
            chunk_id="faq.md:1",
            file="faq.md",
            content="Helpful wellness FAQ.",
            score=0.7,
            hop=1,
        ),
    ]
    return _FakeRAGContext(
        query=query,
        refined_queries=[query],
        chunks=chunks[:max_chunks],
        confidence=0.1,
        hops=1,
        latency_ms=24,
        agent_id=agent_id,
        user_tier=user_tier,
    )


class _EchoProvider:
    name = "echo"

    async def generate(self, text: str) -> str:
        return text


def _patch_insight_provider(
    monkeypatch: pytest.MonkeyPatch,
    provider: object | None = None,
) -> None:
    active_provider = _EchoProvider() if provider is None else provider
    insight_compat = resolve_module("app.services.insight_compat")
    monkeypatch.setattr(
        insight_compat,
        "_load_llm_get_provider",
        lambda: (lambda: active_provider),
        raising=True,
    )


@pytest.fixture
def rag_client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Use a unique client host per test to avoid shared rate-limit buckets."""
    with open_test_client(
        app,
        client=(f"rag-contract-{uuid4().hex}", 50000),
    ) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _disable_rate_limiting_for_rag_contracts(
    monkeypatch: pytest.MonkeyPatch,
    app: FastAPI,
) -> None:
    """RAG contract tests validate payload shape, not 429 behavior."""

    _ensure_rate_limiting_disabled(monkeypatch, app)
    _disable_vip_monthly_quota(monkeypatch)


def _ensure_rate_limiting_disabled(
    monkeypatch: pytest.MonkeyPatch,
    app_instance: FastAPI,
) -> None:
    """Keep RAG contract tests isolated from dedicated 429 suites."""
    monkeypatch.delenv("RATE_LIMITING_IN_TESTS", raising=False)
    disable_rate_limiting_for_test_app(app_instance)

    limiter_key = f"rag-contract-{uuid4()}"
    override_rate_limit_identity_for_test_app(
        app_instance,
        limiter_key=limiter_key,
        monkeypatch=monkeypatch,
    )


def _disable_vip_monthly_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep RAG contract tests focused on response schema, not quota state."""
    insight_compat = resolve_module("app.services.insight_compat")

    # RU: В этом файле проверяем контракт RAG-ответа, а не месячную VIP-квоту.
    # EN: This file validates the RAG response contract, not VIP monthly quota enforcement.
    monkeypatch.setattr(
        insight_compat,
        "_enforce_vip_llm_monthly_quota",
        lambda *_args, **_kwargs: None,
        raising=True,
    )


@dataclass
class _SequenceEchoProvider:
    responses: list[str]
    name: str = "echo-seq"
    calls: int = 0

    async def generate(self, text: str) -> str:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return self.responses[index]


class TestInsightV1RAGFields:
    """RAG response fields on /api/v1/insight."""

    def test_rag_enabled_returns_sources_and_metadata(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert data["hops"] == 1
        assert data["latency_ms"] == 42
        assert data["confidence"] == 0.75

        sources = data["sources"]
        assert len(sources) == 2
        assert sources[0]["chunk_id"] == "readme.md:1"
        assert sources[0]["file"] == "readme.md"
        assert sources[0]["score"] == 0.85
        # preview exists and is a string
        assert isinstance(sources[0]["preview"], str)

    def test_rag_enabled_empty_chunks_returns_zero_sources(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_empty_structured,
            raising=True,
        )

        resp = rag_client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        # rag_used is False when no chunks contribute to prompt (empty RAG result)
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        # hops and latency_ms reflect the RAG call metadata even when chunks are empty
        assert data["hops"] == 1
        assert data["latency_ms"] == 5

    def test_rag_late_context_collapse_returns_non_rag_contract(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Late formatting collapse must keep the additive non-RAG response contract."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )
        monkeypatch.setattr(
            "core.rag.formatting.format_rag_chunks_for_prompt",
            lambda chunks: "   ",
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight",
            json={"text": "What is BMI?"},
            headers=vip_headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 1
        assert data["latency_ms"] == 42

    def test_rag_late_redaction_collapse_returns_non_rag_contract(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Late redaction collapse must keep the additive non-RAG response contract."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )
        monkeypatch.setattr(
            "core.insight.safety.redact_rag_context_for_insight",
            lambda context: "",
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight",
            json={"text": "What is BMI?"},
            headers=vip_headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 1
        assert data["latency_ms"] == 42

    def test_rag_response_confidence_uses_active_output_chunks(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """API confidence should be recomputed from returned chunks, not stale retriever metadata."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_stale_confidence_structured,
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert data["confidence"] == 0.8
        assert len(data["sources"]) == 2

    def test_rag_response_confidence_uses_filtered_subset_chunks(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Endpoint confidence should follow the filtered subset that survives validation."""
        from core.rag.philosophy_pipeline import PipelineResult

        rag_ctx = _make_stale_confidence_structured("What is BMI?")
        filtered_subset = [rag_ctx.chunks[0]]
        pipeline_result = PipelineResult(
            filtered_chunks=filtered_subset,
            stage_results=[],
            warnings=["medical_boundary: chunk faq.md:1 rejected"],
            total_latency_ms=1.0,
            post_stage1_enrichment_completed=True,
        )

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            lambda *args, **kwargs: rag_ctx,
            raising=True,
        )
        monkeypatch.setattr(
            "core.rag.philosophy_pipeline.run_pipeline",
            lambda chunks, query, *, enrichment_enabled=True: pipeline_result,
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert data["confidence"] == 0.9
        assert len(data["sources"]) == 1
        assert data["sources"][0]["chunk_id"] == "readme.md:1"
        assert data["sources"][0]["score"] == 0.9

    def test_rag_disabled_returns_defaults(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        _patch_insight_provider(monkeypatch)

        resp = rag_client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 0
        assert data["latency_ms"] == 0

    def test_rag_source_preview_redacts_internal_metadata(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """sources[].preview must not contain '# Source:' lines (redaction)."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = rag_client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        for src in data["sources"]:
            assert "# Source:" not in src["preview"]

    def test_recursive_rag_enabled_returns_recursive_metadata(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Recursive RAG mode returns same contract with deeper hops metadata."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_RAG_RECURSIVE", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.recursive_retrieval.retrieve_recursive_context_structured",
            _make_fake_recursive_structured,
            raising=True,
        )

        def _vector_must_not_be_used(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("vector retriever must not be used in recursive mode")

        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _vector_must_not_be_used,
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert data["hops"] == 2
        assert data["latency_ms"] == 55
        assert data["confidence"] == 0.82
        assert len(data["sources"]) == 1

    def test_recursive_verification_reason_codes_surface_in_response(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        provider = _SequenceEchoProvider(
            responses=[
                "Draft answer with weak evidence.",
                "Rewritten answer with stronger evidence.",
            ]
        )
        verification_reports = iter([0.6, 0.8])

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_RAG_RECURSIVE", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_ROUTER", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_PHASE12", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_LINGUISTIC", "true")
        _patch_insight_provider(monkeypatch, provider)
        monkeypatch.setattr(
            "core.rag.recursive_retrieval.retrieve_recursive_context_structured",
            _make_fake_recursive_structured,
            raising=True,
        )
        monkeypatch.setattr(
            "core.insight.philosophical_runtime.VerificationEnforcer.validate",
            lambda self, answer, citations: runtime_mod.VerificationReport(
                verification_rate=next(verification_reports),
                unverified_claims=[],
            ),
            raising=True,
        )
        monkeypatch.setattr(
            "core.insight.philosophical_runtime.FalsificationChecker.validate",
            lambda self, answer: runtime_mod.FalsificationReport(
                falsifiability_rate=0.9,
                unfalsifiable_claims=[],
            ),
            raising=True,
        )
        monkeypatch.setattr(
            "core.insight.philosophical_runtime.NonContradictionChecker.count",
            lambda self, answer: 0,
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight",
            json={"text": "How much protein should I eat for recovery?"},
            headers=vip_headers,
        )

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert provider.calls == 2
        assert data["rag_used"] is True
        assert data["verification_rate"] == 0.8
        assert "rag_recursive_path" in data["reason_codes"]
        assert "verification_first_fallback" not in data["reason_codes"]
        assert "verification_first_rewrite" in data["reason_codes"]

    def test_recursive_optimization_enabled_preserves_recursive_api_contract(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Recursive optimization must preserve the existing public response fields."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_RAG_RECURSIVE", "true")
        monkeypatch.setenv("FEATURE_RAG_RECURSIVE_OPTIMIZATION", "true")
        _patch_insight_provider(monkeypatch)

        seen_optimization_enabled: list[bool] = []

        def _tracked_recursive_structured(*args: Any, **kwargs: Any) -> _FakeRAGContext:
            seen_optimization_enabled.append(bool(kwargs.get("optimization_enabled")))
            return _make_fake_recursive_structured(*args, **kwargs)

        monkeypatch.setattr(
            "core.rag.recursive_retrieval.retrieve_recursive_context_structured",
            _tracked_recursive_structured,
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers
        )

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert seen_optimization_enabled == [True]
        assert "optimization_stats" not in data
        assert data["rag_used"] is True
        assert data["hops"] == 2
        assert data["latency_ms"] == 55
        assert data["confidence"] == 0.82
        assert isinstance(data["sources"], list)
        assert data["contradiction_count"] == 0
        assert "verification_first_fallback" not in data["reason_codes"]

    def test_insight_text_not_contaminated_by_source_headers(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """insight text (echoed prompt) must not leak internal file paths."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = rag_client.post(
            "/api/v1/insight",
            json={"text": "What is BMI?"},
            headers=vip_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert "Source:" not in data["insight"]


class TestInsightLegacyRAGFields:
    """RAG response fields on /insight (legacy path)."""

    def test_legacy_rag_enabled_returns_fields(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = rag_client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert len(data["sources"]) == 2
        assert data["confidence"] == 0.75
        assert data["hops"] == 1
        assert data["latency_ms"] == 42

    def test_legacy_rag_late_redaction_collapse_returns_non_rag_contract(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Legacy /insight must match non-RAG-safe contract on late redaction collapse."""
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        _patch_insight_provider(monkeypatch)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )
        monkeypatch.setattr(
            "core.insight.safety.redact_rag_context_for_insight",
            lambda context: "",
            raising=True,
        )

        resp = rag_client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()

        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 1
        assert data["latency_ms"] == 42

    def test_legacy_rag_disabled_returns_defaults(
        self,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        _patch_insight_provider(monkeypatch)

        resp = rag_client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 0
        assert data["latency_ms"] == 0


class TestMandatoryStage1HTTPBoundary:
    """Both retained routes expose the same fail-closed Stage-1 contract."""

    @pytest.mark.parametrize("path", ["/api/v1/insight", "/insight"])
    @pytest.mark.parametrize(
        "scenario",
        [
            "stage1_empty",
            "stage1_exception",
            "enrichment_disabled",
            "enrichment_exception",
        ],
    )
    def test_route_matrix_preserves_baseline_response_boundary(
        self,
        path: str,
        scenario: str,
        rag_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Stage-1 truth controls response fields independently of enrichment."""
        prompt = "How do balanced meals support sustainable daily wellness?"
        provider = _SequenceEchoProvider(responses=["Available wellness response."])
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        for disabled_flag in (
            "FEATURE_RAG_RECURSIVE",
            "FEATURE_RAG_RECURSIVE_OPTIMIZATION",
            "FEATURE_PHILOSOPHY_ROUTER",
            "FEATURE_PHILOSOPHY_PHASE12",
            "FEATURE_PHILOSOPHY_LINGUISTIC",
            "FEATURE_PHILOSOPHY_PRAGMATIC",
        ):
            monkeypatch.setenv(disabled_flag, "false")
        monkeypatch.setenv(
            "FEATURE_PHILOSOPHY_VALIDATION",
            "false" if scenario == "enrichment_disabled" else "true",
        )
        _patch_insight_provider(monkeypatch, provider)

        guard_calls: list[str] = []
        agent_input_guard = resolve_module("app.security.agent_input_guard")
        monkeypatch.setattr(
            agent_input_guard,
            "require_safe_ai_agent_input",
            lambda text: guard_calls.append(text),
            raising=True,
        )

        vector_rag = resolve_module("core.rag.vector_rag")

        def _retrieve_boundary(*args: Any, **kwargs: Any) -> _FakeRAGContext:
            """Return scenario-specific retrieval chunks for the route matrix."""
            context = _make_boundary_structured(*args, **kwargs)
            if scenario == "stage1_empty":
                context.chunks = context.chunks[:1]
            return context

        monkeypatch.setattr(
            vector_rag,
            "retrieve_context_structured",
            _retrieve_boundary,
            raising=True,
        )

        philosophy_pipeline = resolve_module("core.rag.philosophy_pipeline")

        def _raise_private_failure(*_args: object, **_kwargs: object) -> None:
            """Simulate a private validation-stage failure without leaking details."""
            raise RuntimeError("private boundary failure")

        failure_stage = {
            "stage1_exception": "_stage1_rule_validation",
            "enrichment_exception": "_stage2_claim_classification",
        }.get(scenario)
        if failure_stage is not None:
            monkeypatch.setattr(
                philosophy_pipeline,
                failure_stage,
                _raise_private_failure,
                raising=True,
            )

        promotion_observer = AsyncMock()
        if scenario == "enrichment_exception":
            application_service = resolve_module("app.services.insight_application_service")
            monkeypatch.setattr(
                application_service,
                "_maybe_promote_knowledge_candidates",
                promotion_observer,
                raising=True,
            )

        response = rag_client.post(path, json={"text": prompt}, headers=vip_headers)

        assert response.status_code == 200, response.text
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert set(data) == _INSIGHT_RESPONSE_FIELDS
        assert data["provider"] == provider.name
        assert data["insight"] == "Available wellness response."
        assert provider.calls == 1
        assert guard_calls == [prompt]

        if scenario in {"stage1_empty", "stage1_exception"}:
            assert data["rag_used"] is False
            assert data["sources"] == []
            assert data["confidence"] is None
        else:
            assert data["rag_used"] is True
            assert [source["chunk_id"] for source in data["sources"]] == ["baseline:survivor"]
            assert data["confidence"] == 0.85

        assert "raw:rejected" not in response.text
        assert "A diagnosis is required" not in response.text
        if scenario in {"stage1_exception", "enrichment_exception"}:
            assert "private boundary failure" not in response.text

        if scenario == "enrichment_exception":
            promotion_observer.assert_awaited_once()
            promotion_inputs = promotion_observer.await_args.kwargs
            assert promotion_inputs["candidates"] == []
            assert promotion_inputs["verification_bundle"].admission_allowed is False


class TestRAGSourceItemModel:
    """Unit tests for RAGSourceItem and InsightResponse Pydantic models."""

    def test_insight_response_backward_compat(self) -> None:
        """Old-style (provider + insight only) must still work."""
        from app.schemas.insight import InsightResponse

        r = InsightResponse(provider="test", insight="hello")
        d = r.model_dump()
        assert d["sources"] == []
        assert d["confidence"] is None
        assert d["rag_used"] is False
        assert d["hops"] == 0
        assert d["latency_ms"] == 0
        assert d["route_type"] is None
        assert d["depth_used"] == 0
        assert d["verification_rate"] is None
        assert d["falsifiability_rate"] is None
        assert d["contradiction_count"] == 0
        assert d["reason_codes"] == []
        assert d["optimization_applied"] is False

    def test_rag_source_item_fields(self) -> None:
        from app.schemas.insight import RAGSourceItem

        item = RAGSourceItem(chunk_id="a:1", file="a.md", preview="text", score=0.77)
        assert item.chunk_id == "a:1"
        assert item.file == "a.md"
        assert item.preview == "text"
        assert item.score == 0.77
