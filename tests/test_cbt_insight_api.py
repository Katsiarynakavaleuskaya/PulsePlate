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
from sqlalchemy import text

from app.middleware.api_tiers import TEST_KEY_PRO
from app.security.llm_monthly_quota import llm_key_fingerprint, month_start_date_utc

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


def _seed_usage_row(
    db_module: object,
    *,
    key_fp: str,
    month_start: object,
    used_requests: int,
) -> None:
    session_scope = getattr(db_module, "session_scope")
    with session_scope() as session:
        session.execute(
            text("""
                DELETE FROM vip_llm_monthly_usage
                WHERE key_fingerprint = :fp AND month_start_date = :month_start
                """),
            {"fp": key_fp, "month_start": month_start},
        )
        session.execute(
            text("""
                INSERT INTO vip_llm_monthly_usage (key_fingerprint, month_start_date, used_requests)
                VALUES (:fp, :month_start, :used_requests)
                """),
            {"fp": key_fp, "month_start": month_start, "used_requests": used_requests},
        )


class TestCBTInsightTierGating:
    """Tests for PRO tier gating on CBT insight endpoint."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: object,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv(
            "AGENT_CONTROL_AUDIT_LOG_PATH",
            str(tmp_path / "cbt-agent-control.jsonl"),
        )

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
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert "rag_used" in data
        assert "sources" in data
        assert "confidence" in data
        assert data["quota_state"] == "consumed"
        assert data["mode"] == "auto-safe"
        assert "uncertainty" in data
        assert "warnings" in data

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
        tmp_path: object,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv(
            "AGENT_CONTROL_AUDIT_LOG_PATH",
            str(tmp_path / "cbt-agent-control.jsonl"),
        )

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
        tmp_path: object,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")
        self.monkeypatch.setenv(
            "AGENT_CONTROL_AUDIT_LOG_PATH",
            str(tmp_path / "cbt-agent-control.jsonl"),
        )

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
        tmp_path: object,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")
        self.monkeypatch.setenv(
            "AGENT_CONTROL_AUDIT_LOG_PATH",
            str(tmp_path / "cbt-agent-control.jsonl"),
        )

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
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert data["rag_used"] is True
        assert data["confidence"] == pytest.approx(0.88, 0.01)
        assert data["uncertainty"] == pytest.approx(0.12, 0.01)
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
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert data["rag_used"] is False
        assert data["sources"] == []
        assert data["confidence"] == 0.0
        assert data["uncertainty"] == 1.0

    def test_rag_retrieval_failure_falls_back_gracefully(self) -> None:
        """When RAG retrieval raises, endpoint continues without RAG context."""

        def mock_retrieve_error(*args: object, **kwargs: object) -> object:
            raise RuntimeError("RAG backend unavailable")

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve_error,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "Fallback CBT response"
        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )

        payload = {"query": "How to stay positive?"}
        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert data["rag_used"] is False
        assert data["insight"] == "Fallback CBT response"
        assert "rag_retrieval_failed" in data["warnings"]

    def test_rag_privileged_action_gate_failure_returns_503(self) -> None:
        """Permission/runtime failures in privileged RAG gate must fail closed."""

        self.monkeypatch.setattr(
            "app.routers.cbt_insight._persist_privileged_action_audit",
            lambda **kwargs: (_ for _ in ()).throw(PermissionError("denied")),
        )

        response = self.client.post(
            self.url,
            json={"query": "How to stay positive?"},
            headers=self.pro_headers,
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "rag_retrieval_unavailable"

    def test_response_redacts_pii_in_sources(self) -> None:
        """Source previews must redact common PII before returning to client."""
        from core.rag.contracts import RAGChunk

        mock_rag_ctx = _make_rag_context(
            chunks=[
                RAGChunk(
                    chunk_id="chunk-pii",
                    file="docs/cbt/private_note.md",
                    content="Reach me at test@example.com or 555-123-4567 for follow-up.",
                    score=0.93,
                )
            ],
            confidence=0.93,
        )

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            lambda *args, **kwargs: mock_rag_ctx,
        )

        mock_provider = MagicMock()
        mock_provider.generate.return_value = "CBT response with redacted context"
        self.monkeypatch.setattr("llm.get_provider", lambda: mock_provider)

        response = self.client.post(
            self.url,
            json={"query": "Need support"},
            headers=self.pro_headers,
        )

        data = response.json()
        assert response.status_code == 200
        assert "[EMAIL_REDACTED]" in data["sources"][0]["preview"]
        assert "[PHONE_REDACTED]" in data["sources"][0]["preview"]
        assert "source_content_redacted" in data["warnings"]


class TestCBTInsightLLMIntegration:
    """Tests for LLM generation integration."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        client: TestClient,
        pro_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: object,
    ) -> None:
        """Set up test client and headers."""
        self.client = client
        self.pro_headers = pro_headers
        self.monkeypatch = monkeypatch
        self.url = "/api/v1/pro/cbt/insight"
        self.monkeypatch.setenv("FEATURE_CBT_AGENT", "true")
        self.monkeypatch.setenv(
            "AGENT_CONTROL_AUDIT_LOG_PATH",
            str(tmp_path / "cbt-agent-control.jsonl"),
        )

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

    def test_execution_mode_blocked_returns_503(self) -> None:
        """Blocked execution mode must fail closed before privileged work."""
        self.monkeypatch.setenv("CBT_AGENT_EXECUTION_MODE", "blocked")
        response = self.client.post(
            self.url,
            json={"query": "Test query"},
            headers=self.pro_headers,
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "agent_execution_blocked"

    def test_pro_monthly_quota_returns_429_before_provider_call(
        self,
        configure_sqlite_database: object,
    ) -> None:
        """PRO monthly hard quota must stop the route before provider.generate()."""

        month_start = month_start_date_utc()
        key_fp = llm_key_fingerprint(TEST_KEY_PRO, tier="PRO")
        _seed_usage_row(
            configure_sqlite_database,
            key_fp=key_fp,
            month_start=month_start,
            used_requests=1,
        )
        self.monkeypatch.setenv("PRO_LLM_INSIGHT_REQUESTS_PER_MONTH", "1")

        mock_provider = MagicMock()
        self.monkeypatch.setattr("llm.get_provider", lambda: mock_provider)
        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            lambda *args, **kwargs: _make_rag_context(),
        )

        response = self.client.post(
            self.url,
            json={"query": "Need advice"},
            headers=self.pro_headers,
        )

        assert response.status_code == 429
        assert response.json() == {"detail": "quota_exceeded"}
        mock_provider.generate.assert_not_called()

    def test_llm_timeout_returns_504(self) -> None:
        """When LLM call times out, endpoint returns 504."""
        import asyncio

        def mock_retrieve(*args: object, **kwargs: object) -> object:
            return _make_rag_context()

        self.monkeypatch.setattr(
            "core.rag.vector_rag.retrieve_context_structured",
            mock_retrieve,
        )

        # Set a very short timeout for testing
        self.monkeypatch.setattr(
            "app.routers.cbt_insight.LLM_TIMEOUT_SECONDS",
            0.001,  # 1ms timeout
        )

        mock_provider = MagicMock()
        # Simulate slow LLM that takes longer than timeout
        import time

        def slow_generate(*args: object, **kwargs: object) -> str:
            time.sleep(0.1)  # 100ms - longer than 1ms timeout
            return "Response"

        mock_provider.generate.side_effect = slow_generate
        self.monkeypatch.setattr(
            "llm.get_provider",
            lambda: mock_provider,
        )

        payload = {"query": "Test query"}
        response = self.client.post(self.url, json=payload, headers=self.pro_headers)

        assert response.status_code == 504
        assert response.headers.get("content-type", "").startswith("application/json")
        assert "timed out" in response.json()["detail"].lower()
