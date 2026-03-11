"""
Deterministic tests for RAG response fields in InsightResponse per RAG_CONTRACT.md §2.

Covers: sources[], confidence, rag_used, hops, latency_ms in both
/api/v1/insight and /insight endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from core.insight import philosophical_runtime as runtime_mod


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


def _make_fake_recursive_structured(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
    philo_validation_enabled: bool = False,
) -> _FakeRAGContext:
    """Fake recursive retriever with deeper hops and refined query chain."""
    # Intentionally unused: keep signature parity with real recursive retriever.
    _ = (philo_validation_enabled, subject_id)
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
    )


class _EchoProvider:
    name = "echo"

    async def generate(self, text: str) -> str:
        return text


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
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers)
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
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_empty_structured,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
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

    def test_rag_disabled_returns_defaults(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
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
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """sources[].preview must not contain '# Source:' lines (redaction)."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        for src in data["sources"]:
            assert "# Source:" not in src["preview"]

    def test_recursive_rag_enabled_returns_recursive_metadata(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Recursive RAG mode returns same contract with deeper hops metadata."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_RAG_RECURSIVE", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
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

        resp = client.post("/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers)
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
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

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
        monkeypatch.setattr(llm, "get_provider", lambda: provider, raising=True)
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

        resp = client.post(
            "/api/v1/insight",
            json={"text": "How much protein should I eat for recovery?"},
            headers=vip_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert provider.calls == 2
        assert data["rag_used"] is True
        assert data["verification_rate"] == 0.8
        assert "rag_recursive_path" in data["reason_codes"]
        assert "verification_first_rewrite" in data["reason_codes"]
        assert "verification_first_fallback" not in data["reason_codes"]

    def test_insight_text_not_contaminated_by_source_headers(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """insight text (echoed prompt) must not leak internal file paths."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "What is BMI?"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert "Source:" not in data["insight"]


class TestInsightLegacyRAGFields:
    """RAG response fields on /insight (legacy path)."""

    def test_legacy_rag_enabled_returns_fields(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _make_fake_structured,
            raising=True,
        )

        resp = client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert len(data["sources"]) == 2
        assert data["confidence"] == 0.75
        assert data["hops"] == 1
        assert data["latency_ms"] == 42

    def test_legacy_rag_disabled_returns_defaults(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)

        resp = client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 0
        assert data["latency_ms"] == 0


class TestRAGSourceItemModel:
    """Unit tests for RAGSourceItem and InsightResponse Pydantic models."""

    def test_insight_response_backward_compat(self) -> None:
        """Old-style (provider + insight only) must still work."""
        from legacy_app import InsightResponse

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
        from legacy_app import RAGSourceItem

        item = RAGSourceItem(chunk_id="a:1", file="a.md", preview="text", score=0.77)
        assert item.chunk_id == "a:1"
        assert item.file == "a.md"
        assert item.preview == "text"
        assert item.score == 0.77
