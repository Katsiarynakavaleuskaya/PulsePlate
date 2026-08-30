"""Tests for Bayesian adherence API endpoints.

RU: Тесты для API эндпоинтов байесовской модели adherence.
EN: Tests for Bayesian adherence API endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.middleware.api_tiers import derive_subject_id_from_api_key


class TestAdherenceAPI:
    """Test adherence event recording and risk retrieval."""

    def test_record_meal_logged_event(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test recording a successful meal_logged event."""
        user_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])

        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
            headers=pro_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        assert data["user_id"] == user_id
        assert data["analyzer_key"] == "v1:adherence"
        assert data["alpha"] == 2.0
        assert data["beta"] == 1.0
        assert data["n"] == 1
        assert data["risk_slip"] == pytest.approx(1 / 3)
        assert data["confidence"] == 0.35
        assert data["needs_more_data"] is True

    def test_record_slip_event(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test recording a slip event."""
        user_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])

        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "slip",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
            headers=pro_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        assert data["user_id"] == user_id
        assert data["analyzer_key"] == "v1:adherence"
        assert data["alpha"] == 1.0
        assert data["beta"] == 2.0
        assert data["n"] == 1
        assert data["risk_slip"] == pytest.approx(2 / 3)
        assert data["confidence"] == 0.35
        assert data["needs_more_data"] is True

    def test_get_risk_for_new_user(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test getting risk for user with no events (default state)."""
        user_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])

        response = isolated_test_client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
            headers=pro_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()

        assert data["user_id"] == user_id
        assert data["alpha"] == 1.0
        assert data["beta"] == 1.0
        assert data["n"] == 0
        assert data["risk_slip"] == 0.5
        assert data["confidence"] == 0.35
        assert data["needs_more_data"] is True

    def test_sequential_events_build_confidence(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test that confidence threshold flips at n=7."""
        user_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])

        for _ in range(6):
            response = isolated_test_client.post(
                "/api/v1/bayes/adherence/event",
                json={
                    "event_type": "meal_logged",
                    "weight": 1.0,
                    "analyzer_key": "v1:adherence",
                },
                headers=pro_headers,
            )
            assert response.status_code == 200

        response_6 = isolated_test_client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
            headers=pro_headers,
        )
        assert response_6.status_code == 200
        assert response_6.headers["content-type"].startswith("application/json")
        data_6 = response_6.json()
        assert data_6["user_id"] == user_id
        assert data_6["analyzer_key"] == "v1:adherence"
        assert data_6["alpha"] == 7.0
        assert data_6["beta"] == 1.0
        assert data_6["n"] == 6
        assert data_6["risk_slip"] == pytest.approx(1 / 8)
        assert data_6["confidence"] == 0.35
        assert data_6["needs_more_data"] is True

        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
            headers=pro_headers,
        )
        assert response.status_code == 200

        response_7 = isolated_test_client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
            headers=pro_headers,
        )
        assert response_7.status_code == 200
        assert response_7.headers["content-type"].startswith("application/json")
        data_7 = response_7.json()
        assert data_7["user_id"] == user_id
        assert data_7["analyzer_key"] == "v1:adherence"
        assert data_7["alpha"] == 8.0
        assert data_7["beta"] == 1.0
        assert data_7["n"] == 7
        assert data_7["risk_slip"] == pytest.approx(1 / 9)
        assert data_7["confidence"] == 0.85
        assert data_7["needs_more_data"] is False

    def test_validation_rejects_user_id_payload(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test validation rejects unexpected user_id payloads."""
        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "user_id": 1,
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
            headers=pro_headers,
        )

        assert response.status_code == 422

    def test_validation_invalid_event_type(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test validation rejects invalid event_type."""
        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "invalid_type",
                "weight": 1.0,
                "analyzer_key": "v1:adherence",
            },
            headers=pro_headers,
        )

        assert response.status_code == 422

    def test_validation_weight_out_of_range(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test validation rejects weight > 10.0."""
        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 15.0,
                "analyzer_key": "v1:adherence",
            },
            headers=pro_headers,
        )

        assert response.status_code == 422

    def test_validation_weight_zero(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test validation rejects weight = 0.0."""
        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 0.0,
                "analyzer_key": "v1:adherence",
            },
            headers=pro_headers,
        )

        assert response.status_code == 422

    def test_custom_analyzer_key(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        """Test using custom analyzer key for isolation."""
        user_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])
        custom_key = "test:custom"

        response = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={
                "event_type": "meal_logged",
                "weight": 1.0,
                "analyzer_key": custom_key,
            },
            headers=pro_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["user_id"] == user_id
        assert data["analyzer_key"] == custom_key
        assert data["alpha"] == 2.0
        assert data["beta"] == 1.0
        assert data["n"] == 1

        response_default = isolated_test_client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
            headers=pro_headers,
        )

        assert response_default.status_code == 200
        assert response_default.headers["content-type"].startswith("application/json")
        default_data = response_default.json()
        assert default_data["user_id"] == user_id
        assert default_data["analyzer_key"] == "v1:adherence"
        assert default_data["alpha"] == 1.0
        assert default_data["beta"] == 1.0
        assert default_data["n"] == 0

    def test_api_key_isolation(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
        vip_headers: dict[str, str],
    ) -> None:
        """Test that different API keys have isolated state."""
        pro_user_id = derive_subject_id_from_api_key(pro_headers["X-API-Key"])
        vip_user_id = derive_subject_id_from_api_key(vip_headers["X-API-Key"])
        assert pro_user_id != vip_user_id

        pro_write = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={"event_type": "meal_logged", "weight": 1.0},
            headers=pro_headers,
        )
        assert pro_write.status_code == 200
        assert pro_write.headers["content-type"].startswith("application/json")

        vip_write = isolated_test_client.post(
            "/api/v1/bayes/adherence/event",
            json={"event_type": "slip", "weight": 1.0},
            headers=vip_headers,
        )
        assert vip_write.status_code == 200
        assert vip_write.headers["content-type"].startswith("application/json")

        resp_pro = isolated_test_client.get(
            "/api/v1/bayes/adherence/risk",
            headers=pro_headers,
        )
        assert resp_pro.status_code == 200
        assert resp_pro.headers["content-type"].startswith("application/json")
        data_pro = resp_pro.json()
        assert data_pro["user_id"] == pro_user_id
        assert data_pro["alpha"] == 2.0
        assert data_pro["beta"] == 1.0
        assert data_pro["n"] == 1

        resp_vip = isolated_test_client.get(
            "/api/v1/bayes/adherence/risk",
            headers=vip_headers,
        )
        assert resp_vip.status_code == 200
        assert resp_vip.headers["content-type"].startswith("application/json")
        data_vip = resp_vip.json()
        assert data_vip["user_id"] == vip_user_id
        assert data_vip["alpha"] == 1.0
        assert data_vip["beta"] == 2.0
        assert data_vip["n"] == 1
