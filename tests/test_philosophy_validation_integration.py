"""Integration tests for philosophy-agent RAG validation through HTTP endpoints.

Verifies that FEATURE_PHILOSOPHY_VALIDATION controls optional post-Stage-1
enrichment end-to-end while baseline Stage 1 remains mandatory on both routes.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, cast
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.rag.contracts import RAGChunk
from core.rag.philosophy_pipeline import PipelineResult, run_pipeline
from tests._client import disable_rate_limiting_for_test_app

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


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


def _rag_with_medical(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeCtx:
    """Fake RAG returning one medical chunk and one clean chunk."""
    del subject_id
    return _FakeCtx(
        query=query,
        refined_queries=[query],
        chunks=[
            _FakeChunk("med:1", "med.md", "You need a diagnosis from a doctor.", 0.90),
            _FakeChunk("clean:1", "well.md", "Balanced nutrition supports wellness.", 0.85),
        ],
        confidence=0.875,
        hops=1,
        latency_ms=10,
    )


def _rag_all_clean(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeCtx:
    """Fake RAG returning only clean chunks."""
    del subject_id
    return _FakeCtx(
        query=query,
        refined_queries=[query],
        chunks=[
            _FakeChunk("c:1", "a.md", "Hydration improves energy levels.", 0.88),
            _FakeChunk("c:2", "b.md", "Sleep quality affects metabolic health.", 0.82),
        ],
        confidence=0.85,
        hops=1,
        latency_ms=8,
    )


def _rag_all_invalid_scores(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeCtx:
    """Fake RAG returning only chunks with invalid runtime scores."""
    del subject_id
    return _FakeCtx(
        query=query,
        refined_queries=[query],
        chunks=[
            _FakeChunk(
                "invalid:true",
                "true-score.md",
                "True-scored evidence must not reach insight.",
                cast(float, True),
            ),
            _FakeChunk(
                "nonfinite:nan",
                "nan.md",
                "NaN-scored evidence must not reach insight.",
                math.nan,
            ),
            _FakeChunk(
                "nonfinite:positive-inf",
                "positive-inf.md",
                "Positive-infinity evidence must not reach insight.",
                math.inf,
            ),
            _FakeChunk(
                "nonfinite:negative-inf",
                "negative-inf.md",
                "Negative-infinity evidence must not reach insight.",
                -math.inf,
            ),
        ],
        confidence=0.99,
        hops=2,
        latency_ms=12,
    )


def _rag_mixed_safe_and_unrepresentable_int(
    query: str,
    max_chunks: int = 3,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> _FakeCtx:
    """Fake RAG returning one safe chunk and one unrepresentable integer score."""
    del subject_id
    return _FakeCtx(
        query=query,
        refined_queries=[query],
        chunks=[
            _FakeChunk(
                "safe:finite",
                "safe.md",
                "Safe finite evidence reaches insight.",
                0.75,
            ),
            _FakeChunk(
                "invalid:huge-int",
                "huge-int.md",
                "Huge integer evidence must not reach insight.",
                10**400,
            ),
        ],
        confidence=0.875,
        hops=2,
        latency_ms=13,
    )


class _EchoProvider:
    name = "echo"

    async def generate(self, text: str) -> str:
        return text


class _ExplodingProvider:
    name = "explode"

    async def generate(self, text: str) -> str:
        raise AssertionError(f"provider.generate must not be called: {text}")


class _StaticProvider:
    def __init__(self, response: str) -> None:
        self.name = "static"
        self._response = response

    async def generate(self, text: str) -> str:
        return self._response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_insight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable insight + RAG + configure echo provider."""
    import llm

    monkeypatch.setenv("FEATURE_INSIGHT", "true")
    monkeypatch.setenv("FEATURE_RAG", "true")
    monkeypatch.setattr(llm, "get_insight_provider", lambda: _EchoProvider(), raising=True)


@pytest.fixture(autouse=True)
def _disable_rate_limiting_for_insight_tests(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    """Keep insight integration tests deterministic outside dedicated 429 suites."""

    monkeypatch.delenv("RATE_LIMITING_IN_TESTS", raising=False)
    disable_rate_limiting_for_test_app(client.app)


# ---------------------------------------------------------------------------
# Tests: /api/v1/insight
# ---------------------------------------------------------------------------


class TestPhilosophyValidationV1:
    """Tests via /api/v1/insight endpoint."""

    def test_flag_off_still_enforces_stage1_filtering(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """The feature flag disables enrichment, never baseline validation."""
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "false")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_medical,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        chunk_ids = [s["chunk_id"] for s in data["sources"]]
        assert "med:1" not in chunk_ids
        assert "clean:1" in chunk_ids

    def test_flag_on_medical_filtered(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """When FEATURE_PHILOSOPHY_VALIDATION=true, medical chunks are removed."""
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_medical,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        chunk_ids = [s["chunk_id"] for s in data["sources"]]
        assert "med:1" not in chunk_ids
        assert "clean:1" in chunk_ids

    def test_flag_on_clean_chunks_pass(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Clean chunks pass through validation unchanged."""
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_all_clean,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sources"]) == 2

    def test_flag_on_confidence_recalculated(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """When medical chunks are filtered, confidence is recalculated from survivors."""
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_medical,
            raising=True,
        )

        resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        # Only clean:1 (score=0.85) survives → confidence = 0.85
        assert data["confidence"] == 0.85

    @pytest.mark.parametrize("path", ["/api/v1/insight", "/insight"])
    def test_enrichment_exception_preserves_baseline_route_response(
        self,
        path: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Both routes keep Stage-1 survivors without adding provider calls."""
        import llm

        provider = _EchoProvider()
        generate = AsyncMock(wraps=provider.generate)
        monkeypatch.setattr(provider, "generate", generate)
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(llm, "get_insight_provider", lambda: provider, raising=True)
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_medical,
            raising=True,
        )

        with patch(
            "core.rag.philosophy_pipeline._stage2_claim_classification",
            side_effect=RuntimeError("private enrichment failure"),
        ):
            resp = client.post(path, json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert [source["chunk_id"] for source in data["sources"]] == ["clean:1"]
        assert data["confidence"] == 0.85
        assert "Balanced nutrition supports wellness." in data["insight"]
        assert "You need a diagnosis from a doctor." not in data["insight"]
        generate.assert_awaited_once()

    @pytest.mark.parametrize("path", ["/api/v1/insight", "/insight"])
    def test_exact_compaction_preserves_route_contract_and_provider_count(
        self,
        path: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Both aliases expose one exact carrier and still call the provider once."""
        import llm

        provider = _EchoProvider()
        generate = AsyncMock(wraps=provider.generate)
        monkeypatch.setattr(provider, "generate", generate)
        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setenv("FEATURE_RAG_CONTEXT_COMPACTION", "true")
        monkeypatch.setattr(llm, "get_insight_provider", lambda: provider, raising=True)

        def _rag_with_exact_duplicate(
            query: str,
            max_chunks: int = 3,
            agent_id: str | None = None,
            user_tier: str | None = None,
            subject_id: int | None = None,
        ) -> _FakeCtx:
            del max_chunks, agent_id, user_tier, subject_id
            carrier = _FakeChunk(
                "exact:1",
                "wellness.md",
                "Balanced meals support everyday wellness.",
                0.85,
            )
            return _FakeCtx(
                query=query,
                refined_queries=[query],
                chunks=[carrier, _FakeChunk(**vars(carrier))],
                confidence=0.85,
                hops=1,
                latency_ms=7,
            )

        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_exact_duplicate,
            raising=True,
        )

        resp = client.post(path, json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["rag_used"] is True
        assert [source["chunk_id"] for source in data["sources"]] == ["exact:1"]
        assert data["confidence"] == 0.85
        assert "Balanced meals support everyday wellness." in data["insight"]
        generate.assert_awaited_once()

    @pytest.mark.parametrize("path", ["/api/v1/insight", "/insight"])
    def test_flag_on_validation_error_fails_closed(
        self,
        path: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """If canonical validation raises, both routes reject all RAG chunks."""
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_medical,
            raising=True,
        )

        with patch(
            "core.rag.validation._run_validation",
            side_effect=RuntimeError("internal"),
        ):
            resp = client.post(path, json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 1
        assert data["latency_ms"] == 10
        assert "You need a diagnosis from a doctor." not in data["insight"]
        assert "Balanced nutrition supports wellness." not in data["insight"]

    @pytest.mark.parametrize("path", ["/api/v1/insight", "/insight"])
    def test_flag_on_all_invalid_scores_degrades_without_rag(
        self,
        path: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Both routes exclude True and non-finite scores from all RAG output."""
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_all_invalid_scores,
            raising=True,
        )

        resp = client.post(path, json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] is None
        assert data["hops"] == 2
        assert data["latency_ms"] == 12
        for content in (
            "True-scored evidence must not reach insight.",
            "NaN-scored evidence must not reach insight.",
            "Positive-infinity evidence must not reach insight.",
            "Negative-infinity evidence must not reach insight.",
        ):
            assert content not in data["insight"]
        for provenance_value in (
            "invalid:true",
            "true-score.md",
            "nonfinite:nan",
            "nan.md",
            "nonfinite:positive-inf",
            "positive-inf.md",
            "nonfinite:negative-inf",
            "negative-inf.md",
        ):
            assert provenance_value not in resp.text

    @pytest.mark.parametrize("path", ["/api/v1/insight", "/insight"])
    def test_flag_on_mixed_safe_and_unrepresentable_int_uses_only_safe_rag(
        self,
        path: str,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """Both routes retain safe evidence while excluding unrepresentable scores."""
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_mixed_safe_and_unrepresentable_int,
            raising=True,
        )

        resp = client.post(path, json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["rag_used"] is True
        assert len(data["sources"]) == 1
        assert data["sources"][0]["chunk_id"] == "safe:finite"
        assert data["sources"][0]["file"] == "safe.md"
        assert data["sources"][0]["score"] == 0.75
        assert data["confidence"] == 0.75
        assert data["hops"] == 2
        assert data["latency_ms"] == 13
        assert "Safe finite evidence reaches insight." in data["insight"]
        assert "Huge integer evidence must not reach insight." not in data["insight"]
        for provenance_value in ("invalid:huge-int", "huge-int.md"):
            assert provenance_value not in resp.text


# ---------------------------------------------------------------------------
# Tests: /insight (legacy endpoint)
# ---------------------------------------------------------------------------


class TestPhilosophyValidationLegacy:
    """Tests via /insight legacy endpoint."""

    def test_legacy_flag_off_still_enforces_stage1_filtering(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "false")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_medical,
            raising=True,
        )

        resp = client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        chunk_ids = [s["chunk_id"] for s in data["sources"]]
        assert "med:1" not in chunk_ids
        assert "clean:1" in chunk_ids

    def test_legacy_flag_on_medical_filtered(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_with_medical,
            raising=True,
        )

        resp = client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        chunk_ids = [s["chunk_id"] for s in data["sources"]]
        assert "med:1" not in chunk_ids
        assert "clean:1" in chunk_ids

    def test_legacy_flag_on_clean_pass(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        _setup_insight(monkeypatch)
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", "true")
        monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            _rag_all_clean,
            raising=True,
        )

        resp = client.post("/insight", json={"text": "test"}, headers=vip_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert len(data["sources"]) == 2


# ---------------------------------------------------------------------------
# Feature flag unit test
# ---------------------------------------------------------------------------


class TestPhilosophyFlagUnit:
    """Unit tests for is_philosophy_validation_enabled() flag."""

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
        monkeypatch.setenv("FEATURE_PHILOSOPHY_VALIDATION", value)
        from app.utils.feature_flags import is_philosophy_validation_enabled

        assert is_philosophy_validation_enabled() is expected

    def test_flag_missing_defaults_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FEATURE_PHILOSOPHY_VALIDATION", raising=False)
        from app.utils.feature_flags import is_philosophy_validation_enabled

        assert is_philosophy_validation_enabled() is False


class TestPhilosophicalRuntimeIntegration:
    """Integration tests for new philosophical runtime metadata and routes."""

    def test_router_medical_query_returns_safe_disclaimer_without_provider_call(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_ROUTER", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_LINGUISTIC", "true")
        monkeypatch.setattr(llm, "get_insight_provider", lambda: _ExplodingProvider(), raising=True)

        resp = client.post(
            "/api/v1/insight",
            json={"text": "I have symptoms and need diagnosis advice."},
            headers=vip_headers,
        )

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["provider"] == "philosophical_runtime"
        assert data["route_type"] == "SAFE_WELLNESS_DISCLAIMER"
        assert data["depth_used"] == 1
        assert data["optimization_applied"] is True
        assert "medical diagnosis" in data["insight"]

    def test_router_definition_query_returns_local_direct_answer(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_ROUTER", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_LINGUISTIC", "true")
        monkeypatch.setattr(llm, "get_insight_provider", lambda: _ExplodingProvider(), raising=True)

        resp = client.post("/insight", json={"text": "What is BMI?"}, headers=vip_headers)

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["provider"] == "philosophical_runtime"
        assert data["route_type"] == "DIRECT_DEFINITION"
        assert data["depth_used"] == 1
        assert "BMI stands for body mass index" in data["insight"]

    def test_phase12_populates_runtime_metadata_for_factual_answer(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        import llm

        monkeypatch.setenv("FEATURE_INSIGHT", "true")
        monkeypatch.setenv("FEATURE_RAG", "false")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_ROUTER", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_LINGUISTIC", "true")
        monkeypatch.setenv("FEATURE_PHILOSOPHY_PHASE12", "true")
        monkeypatch.setattr(
            llm,
            "get_insight_provider",
            lambda: _StaticProvider(
                "According to WHO, 20-40 grams of protein per meal is a practical range for many adults."
            ),
            raising=True,
        )

        resp = client.post(
            "/api/v1/insight",
            json={"text": "How much protein should I eat for recovery?"},
            headers=vip_headers,
        )

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        assert data["route_type"] == "RAG_FACTUAL"
        assert data["verification_rate"] is not None
        assert data["falsifiability_rate"] is not None
        assert data["contradiction_count"] == 0
        assert isinstance(data["reason_codes"], list)
        assert "rollout_policy" not in data


class TestPhilosophicalRuntimeFlagUnit:
    """Unit tests for new philosophy runtime feature flags."""

    @pytest.mark.parametrize(
        "flag_name",
        [
            "FEATURE_PHILOSOPHY_ROUTER",
            "FEATURE_PHILOSOPHY_PHASE12",
            "FEATURE_PHILOSOPHY_LINGUISTIC",
            "FEATURE_PHILOSOPHY_PRAGMATIC",
        ],
    )
    def test_new_runtime_flags_parse_truthy(
        self,
        monkeypatch: pytest.MonkeyPatch,
        flag_name: str,
    ) -> None:
        monkeypatch.setenv(flag_name, "true")
        from app.utils import feature_flags

        flag_funcs = {
            "FEATURE_PHILOSOPHY_ROUTER": feature_flags.is_philosophy_router_enabled,
            "FEATURE_PHILOSOPHY_PHASE12": feature_flags.is_philosophy_phase12_enabled,
            "FEATURE_PHILOSOPHY_LINGUISTIC": feature_flags.is_philosophy_linguistic_enabled,
            "FEATURE_PHILOSOPHY_PRAGMATIC": feature_flags.is_philosophy_pragmatic_enabled,
        }
        assert flag_funcs[flag_name]() is True


# ===========================================================================
# Fail-closed boundary lines (diff-coverage sentinels)
# ===========================================================================


def _pipeline_chunk(
    chunk_id: str = "c1",
    content: str = "Some test content for chunk.",
    score: float = 0.85,
    file: str = "docs/test.md",
) -> RAGChunk:
    return RAGChunk(chunk_id=chunk_id, file=file, content=content, score=score)


class TestFailClosedBoundaryLines:
    """Focused coverage for the fail-closed and advisory boundary lines.

    Lives in this file because the CI contract/risk coverage suites select
    tests/test_philosophy_validation_integration.py for the insight_ai group.
    """

    def test_post_init_rejects_completed_enrichment_without_filtered_chunks(self) -> None:
        """Keyword construction of the impossible empty-and-complete state raises."""
        with pytest.raises(
            ValueError,
            match="post-Stage-1 enrichment cannot complete without filtered chunks",
        ):
            PipelineResult(
                filtered_chunks=[],
                stage_results=[],
                warnings=[],
                total_latency_ms=0.0,
                post_stage1_enrichment_completed=True,
            )

    def test_post_init_accepts_completed_enrichment_with_survivors(self) -> None:
        """Completed enrichment with survivors is the only valid completed state."""
        result = PipelineResult(
            filtered_chunks=[_pipeline_chunk()],
            stage_results=[],
            warnings=[],
            total_latency_ms=0.0,
            post_stage1_enrichment_completed=True,
        )

        assert result.post_stage1_enrichment_completed is True
        assert len(result.filtered_chunks) == 1

    def test_stage1_exception_returns_sanitized_fail_closed_result(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Stage-1 boundary exception rejects everything without leaking internals."""
        with (
            caplog.at_level(logging.WARNING, logger="core.rag.philosophy_pipeline"),
            patch(
                "core.rag.philosophy_pipeline._stage1_rule_validation",
                side_effect=RuntimeError("sentinel-stage1-exception"),
            ),
        ):
            result = run_pipeline([_pipeline_chunk()], "sentinel-stage1-query")

        assert result.filtered_chunks == []
        assert result.stage_results == []
        assert result.warnings == ["validation_error: internal failure, no chunks accepted"]
        assert result.post_stage1_enrichment_completed is False
        assert result.total_latency_ms >= 0
        assert "Stage-1 RAG validation failed; rejecting all chunks" in caplog.text
        assert "sentinel-stage1-exception" not in caplog.text
        assert "sentinel-stage1-query" not in caplog.text
        assert caplog.records
        assert all(record.exc_info is None for record in caplog.records)

    def test_alignment_mismatch_flagged_through_full_pipeline(self) -> None:
        """High-score short Stage-1 survivors are flagged by Stage 3 end-to-end."""
        chunks = [
            _pipeline_chunk("c1", "Short but valid.", 0.95, "a.md"),
            _pipeline_chunk(
                "c2",
                "A normal chunk with sufficiently long wellness content.",
                0.6,
                "b.md",
            ),
        ]
        result = run_pipeline(chunks, "wellness query")

        assert result.post_stage1_enrichment_completed is True
        stage3 = result.stage_results[2]
        assert stage3.stage_name == "source_alignment"
        assert stage3.metadata == {"flagged_count": 1}
        assert result.warnings == ["alignment_mismatch"]

    def test_numeric_contradiction_counted_through_full_pipeline(self) -> None:
        """Contradictory anchored ranges are counted by Stage 4 end-to-end."""
        chunks = [
            _pipeline_chunk("c1", "Normal BP range is 90-120 for adults.", 0.9, "a.md"),
            _pipeline_chunk("c2", "Normal BP range is 140-180 for adults.", 0.8, "b.md"),
        ]
        result = run_pipeline(chunks, "What BP range is normal?")

        assert result.post_stage1_enrichment_completed is True
        stage4 = result.stage_results[3]
        assert stage4.stage_name == "logical_consistency"
        assert stage4.metadata == {"unique_sources": 2, "contradiction_count": 1}
        assert result.warnings == ["numeric_contradiction"]
