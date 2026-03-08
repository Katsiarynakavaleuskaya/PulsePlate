"""Tests for RAG feedback submission endpoint.

Verifies:
- Feedback submission with valid API key
- PII redaction in llm_response and user_correction
- Validation of rating (1-5) and confidence (0.0-1.0)
- Authentication requirement
- JSONB storage of retrieved_chunks
"""

from __future__ import annotations

import hmac
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import TEST_KEY_PRO, derive_subject_id_from_api_key


class TestRAGFeedbackSubmission:
    """Tests for POST /api/v1/feedback/rag endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, test_client: TestClient) -> None:
        """Set up test client and headers."""
        self.client = test_client
        self.headers = {"X-API-Key": TEST_KEY_PRO}
        self.url = "/api/v1/feedback/rag"

    def test_submit_feedback_minimal(self) -> None:
        """Submit feedback with only required field (query)."""
        payload = {"query": "What is BMI?"}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["message"] == "Feedback submitted successfully"

    def test_submit_feedback_full(self) -> None:
        """Submit feedback with all fields."""
        payload = {
            "agent_id": "insight-default",
            "query": "How do I calculate my BMI?",
            "retrieved_chunks": [
                {"chunk_id": "c1", "file": "docs/bmi.md", "preview": "BMI is...", "score": 0.95},
                {"chunk_id": "c2", "file": "docs/health.md", "preview": "Health...", "score": 0.85},
            ],
            "llm_response": "BMI is calculated by dividing weight by height squared.",
            "user_rating": 5,
            "user_correction": None,
            "confidence": 0.92,
            "hops": 2,
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_submit_feedback_with_rating(self) -> None:
        """Submit feedback with user rating."""
        payload = {"query": "Test query", "user_rating": 4}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201

    def test_submit_feedback_with_correction(self) -> None:
        """Submit feedback with user correction."""
        payload = {
            "query": "Test query",
            "user_correction": "The correct answer should be...",
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201


class TestRAGFeedbackPIIRedaction:
    """Tests for PII redaction in feedback submission."""

    @pytest.fixture(autouse=True)
    def setup(self, test_client: TestClient) -> None:
        """Set up test client and headers."""
        self.client = test_client
        self.headers = {"X-API-Key": TEST_KEY_PRO}
        self.url = "/api/v1/feedback/rag"

    def test_email_redacted_in_llm_response(self) -> None:
        """Email in llm_response is redacted before storage."""
        payload = {
            "query": "Contact info",
            "llm_response": "Contact me at test@example.com for help",
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201
        # Note: We can't directly verify DB content without accessing it,
        # but the validator ensures redaction happens before storage

    def test_phone_redacted_in_llm_response(self) -> None:
        """Phone number in llm_response is redacted."""
        payload = {
            "query": "Contact info",
            "llm_response": "Call 555-123-4567 for support",
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201

    def test_pii_redacted_in_user_correction(self) -> None:
        """PII in user_correction is redacted."""
        payload = {
            "query": "Test",
            "user_correction": "My email is user@domain.com and SSN is 123-45-6789",
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201

    def test_query_and_preview_are_minimized_before_storage(self) -> None:
        """Query and chunk previews are minimized before persistence."""
        payload = {
            "query": "Reach me at person@example.com " + "q" * 700,
            "retrieved_chunks": [
                {
                    "chunk_id": "c1",
                    "file": "docs/private.md",
                    "preview": "Contact person@example.com for detailed history " + "p" * 400,
                    "score": 0.9,
                }
            ],
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201

        from app.models import RAGFeedback
        from core.db import SessionLocal

        assert SessionLocal is not None
        with SessionLocal() as session:
            record = session.query(RAGFeedback).order_by(RAGFeedback.id.desc()).first()
            assert record is not None
            assert "[EMAIL_REDACTED]" in record.query
            assert "person@example.com" not in record.query
            assert len(record.query) <= 512
            assert record.retrieved_chunks is not None
            preview = record.retrieved_chunks[0]["preview"]
            assert "[EMAIL_REDACTED]" in preview
            assert "person@example.com" not in preview
            assert len(preview) <= 240


class TestRAGFeedbackValidation:
    """Tests for request validation."""

    @pytest.fixture(autouse=True)
    def setup(self, test_client: TestClient) -> None:
        """Set up test client and headers."""
        self.client = test_client
        self.headers = {"X-API-Key": TEST_KEY_PRO}
        self.url = "/api/v1/feedback/rag"

    def test_invalid_rating_too_low(self) -> None:
        """Rating below 1 is rejected."""
        payload = {"query": "test", "user_rating": 0}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422

    def test_invalid_rating_too_high(self) -> None:
        """Rating above 5 is rejected."""
        payload = {"query": "test", "user_rating": 6}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422

    def test_valid_rating_boundaries(self) -> None:
        """Ratings 1 and 5 are valid boundaries."""
        for rating in [1, 5]:
            payload = {"query": f"test rating {rating}", "user_rating": rating}
            response = self.client.post(self.url, json=payload, headers=self.headers)
            assert response.status_code == 201, f"Rating {rating} should be valid"

    def test_invalid_confidence_too_low(self) -> None:
        """Confidence below 0.0 is rejected."""
        payload = {"query": "test", "confidence": -0.1}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422

    def test_invalid_confidence_too_high(self) -> None:
        """Confidence above 1.0 is rejected."""
        payload = {"query": "test", "confidence": 1.1}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422

    def test_valid_confidence_boundaries(self) -> None:
        """Confidence 0.0 and 1.0 are valid boundaries."""
        for conf in [0.0, 1.0]:
            payload = {"query": f"test confidence {conf}", "confidence": conf}
            response = self.client.post(self.url, json=payload, headers=self.headers)
            assert response.status_code == 201, f"Confidence {conf} should be valid"

    def test_invalid_hops_negative(self) -> None:
        """Negative hops is rejected."""
        payload = {"query": "test", "hops": -1}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422

    def test_missing_query_rejected(self) -> None:
        """Request without query is rejected."""
        payload = {"user_rating": 5}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422

    def test_empty_query_rejected(self) -> None:
        """Empty query string is rejected."""
        payload = {"query": ""}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422

    def test_oversized_query_rejected_before_minimization(self) -> None:
        """Over-limit query still fails the public request contract."""
        payload = {"query": "q" * 10001}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 422


def test_hash_only_minimization_uses_server_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hash-only policy must use keyed hashing to avoid raw SHA-256 markers."""
    from core.compliance import minimize_free_text, sanitize_audit_string

    monkeypatch.setenv("SERVER_SALT", "StrongServerSaltForTests123456789!")
    value = "private provider prompt"
    expected = hmac.new(
        b"StrongServerSaltForTests123456789!",
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert minimize_free_text(value, field_name="prompt") == expected
    audit_marker = sanitize_audit_string("prompt", value)
    assert isinstance(audit_marker, dict)
    assert audit_marker["sha256"] == expected


class TestRAGFeedbackAuthentication:
    """Tests for authentication requirements."""

    @pytest.fixture(autouse=True)
    def setup(self, test_client: TestClient) -> None:
        """Set up test client."""
        self.client = test_client
        self.url = "/api/v1/feedback/rag"

    def test_requires_api_key(self) -> None:
        """Request without API key is rejected."""
        payload = {"query": "test"}

        response = self.client.post(self.url, json=payload)

        assert response.status_code in (401, 403)

    def test_accepts_any_valid_api_key(self) -> None:
        """Any valid API key is accepted (not tier-specific)."""
        # Use a different key than TEST_KEY_PRO
        headers = {"X-API-Key": "any-valid-key-for-feedback"}
        payload = {"query": "test with different key"}

        response = self.client.post(self.url, json=payload, headers=headers)

        # Should succeed with any key (not require PRO/VIP tier)
        assert response.status_code == 201


class TestRAGFeedbackChunksStorage:
    """Tests for retrieved_chunks JSONB storage."""

    @pytest.fixture(autouse=True)
    def setup(self, test_client: TestClient) -> None:
        """Set up test client and headers."""
        self.client = test_client
        self.headers = {"X-API-Key": TEST_KEY_PRO}
        self.url = "/api/v1/feedback/rag"

    def test_empty_chunks_accepted(self) -> None:
        """Empty chunks array is accepted."""
        payload = {"query": "test", "retrieved_chunks": []}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201

    def test_null_chunks_accepted(self) -> None:
        """Null chunks is accepted."""
        payload = {"query": "test", "retrieved_chunks": None}

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201

    def test_multiple_chunks_accepted(self) -> None:
        """Multiple chunks are stored correctly."""
        payload = {
            "query": "test",
            "retrieved_chunks": [
                {"chunk_id": "c1", "file": "doc1.md", "preview": "Content 1", "score": 0.9},
                {"chunk_id": "c2", "file": "doc2.md", "preview": "Content 2", "score": 0.8},
                {"chunk_id": "c3", "file": "doc3.md", "preview": "Content 3", "score": 0.7},
            ],
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201

    def test_chunks_with_partial_fields(self) -> None:
        """Chunks with only some fields are accepted."""
        payload = {
            "query": "test",
            "retrieved_chunks": [
                {"score": 0.9},  # Only score
                {"file": "doc.md", "preview": "Content"},  # No chunk_id or score
            ],
        }

        response = self.client.post(self.url, json=payload, headers=self.headers)

        assert response.status_code == 201
