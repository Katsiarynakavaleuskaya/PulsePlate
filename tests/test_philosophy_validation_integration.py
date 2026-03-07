"""Integration tests for philosophy-agent RAG validation through HTTP endpoints.

Verifies that FEATURE_PHILOSOPHY_VALIDATION flag controls validation behavior
end-to-end via /api/v1/insight and /insight endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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
) -> _FakeCtx:
    """Fake RAG returning one medical chunk and one clean chunk."""
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
) -> _FakeCtx:
    """Fake RAG returning only clean chunks."""
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
    monkeypatch.setattr(llm, "get_provider", lambda: _EchoProvider(), raising=True)


# ---------------------------------------------------------------------------
# Tests: /api/v1/insight
# ---------------------------------------------------------------------------


class TestPhilosophyValidationV1:
    """Tests via /api/v1/insight endpoint."""

    def test_flag_off_no_filtering(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """When FEATURE_PHILOSOPHY_VALIDATION=false, medical chunks are NOT filtered."""
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
        # Medical chunk should still be present (validation off)
        chunk_ids = [s["chunk_id"] for s in data["sources"]]
        assert "med:1" in chunk_ids
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

    def test_flag_on_validation_error_failsafe(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        vip_headers: dict[str, str],
    ) -> None:
        """If validation raises, original chunks are returned (fail-safe)."""
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
            resp = client.post("/api/v1/insight", json={"text": "test"}, headers=vip_headers)

        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("application/json")
        data = resp.json()
        # Fail-safe: both chunks should be present
        chunk_ids = [s["chunk_id"] for s in data["sources"]]
        assert "med:1" in chunk_ids
        assert "clean:1" in chunk_ids


# ---------------------------------------------------------------------------
# Tests: /insight (legacy endpoint)
# ---------------------------------------------------------------------------


class TestPhilosophyValidationLegacy:
    """Tests via /insight legacy endpoint."""

    def test_legacy_flag_off_no_filtering(
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
        assert "med:1" in chunk_ids

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
        monkeypatch.setattr(llm, "get_provider", lambda: _ExplodingProvider(), raising=True)

        resp = client.post(
            "/api/v1/insight",
            json={"text": "I have symptoms and need diagnosis advice."},
            headers=vip_headers,
        )

        assert resp.status_code == 200
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
        monkeypatch.setattr(llm, "get_provider", lambda: _ExplodingProvider(), raising=True)

        resp = client.post("/insight", json={"text": "What is BMI?"}, headers=vip_headers)

        assert resp.status_code == 200
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
            "get_provider",
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
        data = resp.json()
        assert data["route_type"] == "RAG_FACTUAL"
        assert data["verification_rate"] is not None
        assert data["falsifiability_rate"] is not None
        assert data["contradiction_count"] == 0
        assert isinstance(data["reason_codes"], list)


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
