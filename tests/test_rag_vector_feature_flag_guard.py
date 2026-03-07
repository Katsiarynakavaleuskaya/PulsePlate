"""Guard tests for FEATURE_RAG_VECTOR feature flag behavior.

Ensures:
- Flag off → Jaccard path only
- Flag on → vector path attempted
- Vector failure → graceful fallback to Jaccard (no 500)
- FEATURE_RAG=false → no RAG at all (unchanged behavior)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_VIP, derive_subject_id_from_api_key
from core.rag.orchestration import RAGOrchestrationResult


@dataclass
class _FakeChunk:
    chunk_id: str
    file: str
    content: str
    score: float
    hop: int = 1


@dataclass
class _FakeCtx:
    query: str
    refined_queries: list[str]
    chunks: list[_FakeChunk]
    confidence: float
    hops: int
    latency_ms: int
    agent_id: Optional[str] = None
    user_tier: Optional[str] = None


def _vector_fake(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeCtx:
    """Fake that simulates vector retrieval (distinct chunk_id prefix)."""
    return _FakeCtx(
        query=query,
        refined_queries=[query],
        chunks=[_FakeChunk("vec:1", "vector.md", "vector result", 0.92)],
        confidence=0.92,
        hops=1,
        latency_ms=15,
        agent_id=agent_id,
        user_tier=user_tier,
    )


class _EchoProvider:
    name = "echo"

    async def generate(self, text: str) -> str:
        return text


class TestFeatureFlagUnit:
    """Unit tests for is_rag_vector_enabled() flag helper."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("TRUE", True),
            ("1", True),
            ("on", True),
            ("yes", True),
            ("false", False),
            ("0", False),
            ("off", False),
            ("", False),
            ("no", False),
        ],
    )
    def test_flag_parsing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        value: str,
        expected: bool,
    ) -> None:
        monkeypatch.setenv("FEATURE_RAG_VECTOR", value)
        from app.utils.feature_flags import is_rag_vector_enabled

        assert is_rag_vector_enabled() is expected

    def test_flag_missing_defaults_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FEATURE_RAG_VECTOR", raising=False)
        from app.utils.feature_flags import is_rag_vector_enabled

        assert is_rag_vector_enabled() is False


class TestFeatureFlagIntegration:
    """Integration tests: feature flag controls which RAG path is used."""

    def test_rag_disabled_returns_no_rag(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """FEATURE_RAG=false → no RAG at all, regardless of vector flag."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        monkeypatch.setenv("FEATURE_RAG_VECTOR", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []

    def test_vector_flag_on_uses_vector_module(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """FEATURE_RAG=true + FEATURE_RAG_VECTOR=true → vector_rag module called."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_RAG_VECTOR", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _vector_fake,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert data["confidence"] == 0.92
        assert data["latency_ms"] == 15
        assert len(data["sources"]) == 1
        assert data["sources"][0]["chunk_id"] == "vec:1"

    def test_vector_flag_off_uses_jaccard_via_vector_module(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """FEATURE_RAG=true + FEATURE_RAG_VECTOR=false → vector_rag still called,
        but internally delegates to Jaccard."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_RAG_VECTOR", "false")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)

        # Patch vector_rag.retrieve_context_structured (the entry point in legacy_app)
        # to simulate Jaccard fallback path
        def _jaccard_fallback(
            query: str,
            max_chunks: int = 3,
            agent_id: str | None = None,
            user_tier: str | None = None,
            subject_id: int | None = None,
        ) -> _FakeCtx:
            return _FakeCtx(
                query=query,
                refined_queries=[query],
                chunks=[_FakeChunk("j:1", "doc.md", "jaccard", 0.45)],
                confidence=0.45,
                hops=1,
                latency_ms=3,
            )

        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _jaccard_fallback,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert data["sources"][0]["chunk_id"] == "j:1"

    def test_api_v1_insight_passes_authenticated_subject_id(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Authenticated /api/v1/insight propagates derived subject_id into RAG orchestration."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        rag_result = AsyncMock()
        rag_result.return_value = RAGOrchestrationResult(
            chunks=[],
            formatted_prompt="test",
            rag_actually_used=False,
            confidence=None,
            hops=0,
            latency_ms=0,
        )
        monkeypatch.setattr(
            "core.rag.orchestration.retrieve_and_validate_rag",
            rag_result,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        assert rag_result.await_args.kwargs["subject_id"] == derive_subject_id_from_api_key(
            TEST_KEY_VIP
        )

    def test_legacy_insight_uses_safe_fallback_without_subject_id(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Legacy /insight keeps vector user corpus disabled by omitting subject_id."""
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)
        rag_result = AsyncMock()
        rag_result.return_value = RAGOrchestrationResult(
            chunks=[],
            formatted_prompt="test",
            rag_actually_used=False,
            confidence=None,
            hops=0,
            latency_ms=0,
        )
        monkeypatch.setattr(
            "core.rag.orchestration.retrieve_and_validate_rag",
            rag_result,
            raising=True,
        )

        resp = client.post("/insight", json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        assert rag_result.await_args.kwargs["subject_id"] is None
