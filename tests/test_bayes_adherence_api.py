"""Tests for Bayesian adherence API endpoints.

RU: Тесты для API эндпоинтов байесовской модели adherence.
EN: Tests for Bayesian adherence API endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import app as fastapi_app
from app.middleware.api_tiers import require_pro_tier


def _allow_pro() -> None:
    """Override require_pro_tier dependency for tests."""
    pass


class TestAdherenceAPI:
    """Test adherence event recording and risk retrieval."""

    def setup_method(self) -> None:
        """Setup test client with PRO tier override."""
        fastapi_app.dependency_overrides[require_pro_tier] = _allow_pro
        self.client = TestClient(fastapi_app)

    def teardown_method(self) -> None:
        """Clean up dependency overrides."""
        fastapi_app.dependency_overrides.clear()

    def test_record_meal_logged_event(self) -> None:
        """Test recording a successful meal_logged event."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "user_id": 1,
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert data["user_id"] == 1
        assert data["analyzer_key"] == "v1:adherence"
        assert data["alpha"] == 2.0  # 1.0 prior + 1.0 event
        assert data["beta"] == 1.0  # unchanged
        assert data["n"] == 1
        assert 0.0 <= data["risk_slip"] <= 1.0
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["needs_more_data"] is True  # n=1 < 7

    def test_record_slip_event(self) -> None:
        """Test recording a slip event."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "user_id": 2,
                "event_type": "slip",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == 2
        assert data["alpha"] == 1.0  # unchanged
        assert data["beta"] == 2.0  # 1.0 prior + 1.0 event
        assert data["n"] == 1
        assert data["risk_slip"] > 0.5  # beta > alpha -> higher risk
        assert data["needs_more_data"] is True

    def test_get_risk_for_new_user(self) -> None:
        """Test getting risk for user with no events (default state)."""
        response = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"user_id": 999, "analyzer_key": "v1:adherence"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == 999
        assert data["alpha"] == 1.0  # default prior
        assert data["beta"] == 1.0  # default prior
        assert data["n"] == 0
        assert data["risk_slip"] == 0.5  # symmetric prior
        assert data["confidence"] == 0.35  # low confidence (n=0 < 7)
        assert data["needs_more_data"] is True

    def test_sequential_events_build_confidence(self) -> None:
        """Test that multiple events increase confidence."""
        user_id = 100

        # Record 7 successful events (threshold for confidence)
        for i in range(7):
            response = self.client.post(
                "/api/v1/bayes/adherence/event",
                json={
                    "user_id": user_id,
                    "event_type": "meal_logged",
                    "weight": 1.0,
                    "analyzer_key": "v1:adherence",
                },
            )
            assert response.status_code == 200

        # Check final state
        response = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"user_id": user_id, "analyzer_key": "v1:adherence"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["n"] == 7
        assert data["alpha"] == 8.0  # 1.0 prior + 7 events
        assert data["beta"] == 1.0  # no slips
        assert data["risk_slip"] < 0.2  # low risk (many successes)
        assert data["confidence"] == 0.85  # high confidence (n >= 7)
        assert data["needs_more_data"] is False

    def test_validation_negative_user_id(self) -> None:
        """Test validation rejects negative user_id."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "user_id": -1,
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_validation_invalid_event_type(self) -> None:
        """Test validation rejects invalid event_type."""
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "user_id": 1,
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
                "user_id": 1,
                "event_type": "meal_logged",
                "weight": 15.0,
                "analyzer_key": "v1:adherence",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_custom_analyzer_key(self) -> None:
        """Test using custom analyzer key for isolation."""
        user_id = 200
        custom_key = "test:custom"

        # Record event with custom key
        response = self.client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "user_id": user_id,
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
            params={"user_id": user_id, "analyzer_key": "v1:adherence"},
        )

        assert response_default.status_code == 200
        default_data = response_default.json()
        assert default_data["n"] == 0  # No events on default key

    def test_user_isolation(self) -> None:
        """Test that different users have isolated state."""
        # User 1: record meal_logged
        self.client.post(
            "/api/v1/bayes/adherence/event",
            json={"user_id": 301, "event_type": "meal_logged", "weight": 1.0},
        )

        # User 2: record slip
        self.client.post(
            "/api/v1/bayes/adherence/event",
            json={"user_id": 302, "event_type": "slip", "weight": 1.0},
        )

        # Check User 1 state
        resp1 = self.client.get("/api/v1/bayes/adherence/risk", params={"user_id": 301})
        data1 = resp1.json()
        assert data1["alpha"] == 2.0
        assert data1["beta"] == 1.0

        # Check User 2 state
        resp2 = self.client.get("/api/v1/bayes/adherence/risk", params={"user_id": 302})
        data2 = resp2.json()
        assert data2["alpha"] == 1.0
        assert data2["beta"] == 2.0
