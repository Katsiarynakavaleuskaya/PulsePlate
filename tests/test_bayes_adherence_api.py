"""Tests for Bayesian adherence API endpoints.

RU: Тесты для API эндпоинтов байесовской модели adherence.
EN: Tests for Bayesian adherence API endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import app as fastapi_app
from app.middleware.api_tiers import get_pro_subject_id, require_pro_tier


def _allow_pro() -> None:
    """Override require_pro_tier dependency for tests."""
    pass


def _fake_subject_id() -> int:
    """Override get_pro_subject_id dependency for tests.

    Returns a stable test subject_id (1) for all tests.
    Real implementation derives this from API key hash.
    """
    return 1


class TestAdherenceAPI:
    """Test adherence event recording and risk retrieval."""

    def setup_method(self) -> None:
        """Setup test client with PRO tier and subject_id overrides."""
        fastapi_app.dependency_overrides[require_pro_tier] = _allow_pro
        fastapi_app.dependency_overrides[get_pro_subject_id] = _fake_subject_id
        self.client = TestClient(fastapi_app)

    def teardown_method(self) -> None:
        """Clean up dependency overrides and database state after each test."""
        # Clean up overrides
        fastapi_app.dependency_overrides.clear()

        # Clean up analyzer state for subject_id=1 to prevent test interference
        from core.db import SessionLocal
        from core.models import AnalyzerStateModel

        session = SessionLocal()
        try:
            session.query(AnalyzerStateModel).filter(AnalyzerStateModel.user_id == 1).delete()
            session.commit()
        finally:
            session.close()

    def test_record_meal_logged_event(self) -> None:
        """Test recording a successful meal_logged event."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert data["user_id"] == 1  # from _fake_subject_id
        assert data["analyzer_key"] == "v1:adherence"
        assert data["n"] == 1
        # Success event -> alpha should increase relative to beta
        assert data["alpha"] > data["beta"]
        assert 0.0 <= data["risk_slip"] <= 1.0
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["needs_more_data"] is True  # n=1 < 7

    def test_record_slip_event(self) -> None:
        """Test recording a slip event."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "slip",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == 1  # from _fake_subject_id
        assert data["n"] == 1
        # Slip event -> beta should increase relative to alpha
        assert data["beta"] > data["alpha"]
        assert data["risk_slip"] > 0.5  # beta > alpha -> higher risk
        assert data["needs_more_data"] is True

    def test_get_risk_for_new_user(self) -> None:
        """Test getting risk for user with no events (default state)."""
        response = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == 1  # from _fake_subject_id
        # Symmetric prior -> equal alpha/beta
        assert data["alpha"] == data["beta"]
        assert data["n"] == 0
        assert data["risk_slip"] == 0.5  # symmetric prior
        assert data["confidence"] < 0.5  # low confidence (n=0 < 7)
        assert data["needs_more_data"] is True

    def test_sequential_events_build_confidence(self) -> None:
        """Test that confidence threshold flips at n=7."""
        # All events use subject_id=1 from _fake_subject_id

        # Record 6 events (below threshold)
        for _ in range(6):
            response = self.client.post(
                "/api/v1/bayes/adherence/event",
                json={
                    "event_type": "meal_logged",
                    "weight": 1.0,
                    "analyzer_key": "v1:adherence",
                },
            )
            assert response.status_code == 200

        # Check state at n=6 (still needs data)
        response_6 = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
        )
        assert response_6.status_code == 200
        data_6 = response_6.json()
        assert data_6["n"] == 6
        assert data_6["needs_more_data"] is True
        assert data_6["confidence"] < 0.8  # Low confidence

        # Record 7th event (threshold)
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
        )
        assert response.status_code == 200

        # Check final state at n=7 (confidence flipped)
        response_7 = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
        )
        assert response_7.status_code == 200
        data_7 = response_7.json()
        assert data_7["n"] == 7
        assert data_7["needs_more_data"] is False
        assert data_7["confidence"] >= 0.8  # High confidence
        assert data_7["risk_slip"] < 0.2  # Low risk (many successes)

    def test_validation_invalid_event_type(self) -> None:
        """Test validation rejects invalid event_type."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "invalid_type",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_validation_weight_out_of_range(self) -> None:
        """Test validation rejects weight > 10.0."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 15.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_validation_weight_zero(self) -> None:
        """Test validation rejects weight = 0.0."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 0.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_custom_analyzer_key(self) -> None:
        """Test using custom analyzer key for isolation."""
        custom_key = "test:custom"

        # Record event with custom key
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": custom_key,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analyzer_key"] == custom_key

        # Verify default key is separate
        response_default = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
        )

        assert response_default.status_code == 200
        default_data = response_default.json()
        assert default_data["n"] == 0  # No events on default key
