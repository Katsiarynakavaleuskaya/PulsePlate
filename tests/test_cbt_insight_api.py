"""Tests for CBT Insight API endpoint.

Verifies:
- PRO tier gating (FREE/PRO/VIP access patterns)
- Feature flag control (FEATURE_CBT_AGENT)
- RAG corpus filtering integration with agent_id="cbt-agent"
- LLM generation with CBT prompt
- Response schema validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from core.rag.contracts import RAGContext


def _make_rag_context(
    chunks: list | None = None,
    confidence: float = 0.0,
) -> "RAGContext":
    """Create RAGContext with all required fields for tests."""
    from core.rag.contracts import RAGContext

    return RAGContext(
        query="test",
        refined_queries=[],
        chunks=chunks or [],
        confidence=confidence,
        hops=1,
        latency_ms=10,
    )


class TestCBTInsightTierGating:
    """Tests for PRO tier gating on CBT insight endpoint."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"

    def test_free_tier_rejected(self) -> None:
        """FREE tier (no key) cannot access CBT insight endpoint."""
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")
        payload = {"query": "How do I handle negative thoughts?"}

        response = self.client.post(self.url, json=payload)

        assert response.status_code in (401, 403)

    def test_pro_tier_accepted_when_feature_enabled(self) -> None:
        """PRO tier can access CBT insight endpoint when feature enabled."""
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")
        self._mock_rag_and_llm()
        payload = {"query": "How do I handle negative thoughts?"}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 200
        data = response.json()
        assert "insight" in data
        assert "rag_used" in data
        assert "sources" in data
        assert "confidence" in data

    def test_pro_tier_rejected_when_feature_disabled(self) -> None:
        """PRO tier is rejected when feature flag is disabled."""
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "false")
        payload = {"query": "How do I handle negative thoughts?"}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 503
        assert "not enabled" in response.json().get("detail", "").lower()

    def _mock_rag_and_llm(self) -> None:
        """Mock RAG retrieval and LLM provider for deterministic tests."""
        from core.rag.contracts import RAGChunk

        mock_rag_ctx = _make_rag_context(
            chunks=[
                RAGChunk(
                    chunk_id="test-chunk-1",
                    file="docs/cbt/cognitive_restructuring.md",
                    content="Cognitive restructuring helps identify distorted thoughts.",
                    score=0.95,
                )
            ],
            confidence=0.95,
        )

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return mock_rag_ctx

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        # Mock LLM provider
        mock_provider = MagicMock()
        mock_provider.generate.return_value = (
            "Here is a CBT-informed response about managing thoughts."
        )

        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )


class TestCBTInsightFeatureFlag:
    """Tests for feature flag control of CBT insight endpoint."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"

    def test_feature_disabled_returns_503(self) -> None:
        """When FEATURE_CBT_AGENT=false, endpoint returns 503."""
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "false")
        payload = {"query": "Test query"}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 503
        assert "not enabled" in response.json()["detail"].lower()

    def test_feature_enabled_explicit_true(self) -> None:
        """FEATURE_CBT_AGENT=true enables endpoint."""
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")
        self._mock_rag_and_llm()
        payload = {"query": "Test query"}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 200

    def test_feature_enabled_numeric_1(self) -> None:
        """FEATURE_CBT_AGENT=1 enables endpoint."""
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "1")
        self._mock_rag_and_llm()
        payload = {"query": "Test query"}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 200

    def test_feature_disabled_explicit_false(self) -> None:
        """FEATURE_CBT_AGENT=false disables endpoint."""
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "false")
        payload = {"query": "Test query"}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 503

    def test_feature_disabled_by_default(self) -> None:
        """When FEATURE_CBT_AGENT is unset, endpoint is disabled."""
        self.monkeypatch.delenv("FEATURE_CBT_AGENT", raising=False)
        payload = {"query": "Test query"}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 503

    def _mock_rag_and_llm(self) -> None:
        """Mock RAG retrieval and LLM provider for deterministic tests."""
        mock_rag_ctx = _make_rag_context()

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return mock_rag_ctx

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "CBT response"

        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )


class TestCBTInsightValidation:
    """Tests for request validation."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")

    def test_empty_query_rejected(self) -> None:
        """Empty query string is rejected."""
        payload = {"query": ""}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 422

    def test_missing_query_rejected(self) -> None:
        """Request without query field is rejected."""
        payload = {}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 422

    def test_query_too_long_rejected(self) -> None:
        """Query exceeding 500 chars is rejected."""
        payload = {"query": "x" * 501}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 422

    def test_valid_query_boundaries(self) -> None:
        """Query at max length (500 chars) is accepted."""
        self._mock_rag_and_llm()
        payload = {"query": "x" * 500}

        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 200

    def _mock_rag_and_llm(self) -> None:
        """Mock RAG retrieval and LLM provider for deterministic tests."""
        mock_rag_ctx = _make_rag_context()

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return mock_rag_ctx

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "CBT response"

        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )


class TestCBTInsightRAGIntegration:
    """Tests for RAG corpus filtering integration."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")

    def test_rag_called_with_cbt_agent_id(self) -> None:
        """RAG retrieval is called with agent_id='cbt-agent'."""
        captured_kwargs: dict[str, object] = {}

        def capture_rag(*args: object, **kwargs: object) -> object:
            captured_kwargs.update(kwargs)
            return _make_rag_context()

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            capture_rag,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "CBT response"
        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )

        payload = {"query": "Test query"}
        self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert captured_kwargs.get("agent_id") == "cbt-agent"

    def test_response_includes_sources_when_rag_returns_chunks(self) -> None:
        """Response includes sources extracted from RAG chunks."""
        from core.rag.contracts import RAGChunk

        mock_chunks = [
            RAGChunk(
                chunk_id="chunk-1",
                file="docs/cbt/cognitive_restructuring.md",
                content="Content about cognitive restructuring techniques.",
                score=0.92,
            ),
            RAGChunk(
                chunk_id="chunk-2",
                file="docs/psychology/motivation_theories.md",
                content="Self-determination theory explains motivation.",
                score=0.85,
            ),
        ]
        mock_rag_ctx = _make_rag_context(chunks=mock_chunks, confidence=0.88)

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return mock_rag_ctx

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "CBT response with context"
        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )

        payload = {"query": "How do I stay motivated?"}
        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["rag_used"] is True
        assert data["confidence"] == pytest.approx(0.88, 0.01)
        assert len(data["sources"]) == 2
        assert data["sources"][0]["file"] == "docs/cbt/cognitive_restructuring.md"
        assert data["sources"][1]["file"] == "docs/psychology/motivation_theories.md"

    def test_response_without_rag_chunks(self) -> None:
        """Response handles empty RAG results gracefully."""
        mock_rag_ctx = _make_rag_context()

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return mock_rag_ctx

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "CBT response without RAG"
        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )

        payload = {"query": "Random question"}
        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] == 0.0


class TestCBTInsightLLMIntegration:
    """Tests for LLM generation integration."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")

    def test_llm_provider_unavailable_returns_503(self) -> None:
        """When LLM provider is unavailable, endpoint returns 503."""

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return _make_rag_context()

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        # Simulate ImportError for LLM provider
        def raise_import_error() -> None:
            raise ImportError("LLM provider not available")

        self.monkeypatch.setattr(
            "llm.get_provider",
            raise_import_error,
        )

        payload = {"query": "Test query"}
        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 503
        assert "not available" in response.json()["detail"].lower()

    def test_llm_empty_response_returns_503(self) -> None:
        """When LLM returns empty response, endpoint returns 503."""

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return _make_rag_context()

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = ""  # Empty response
        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )

        payload = {"query": "Test query"}
        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 503
        # Empty LLM response triggers 503 with "empty response" or "failed" in message
        detail = response.json()["detail"].lower()
        assert "empty response" in detail or "failed" in detail

    def test_llm_generation_failure_returns_503(self) -> None:
        """When LLM generation fails, endpoint returns 503."""

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return _make_rag_context()

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        mock_provider = MagicMock()
        mock_provider.generate.side_effect = RuntimeError("LLM API error")
        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )

        payload = {"query": "Test query"}
        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 503
        assert "failed" in response.json()["detail"].lower()
