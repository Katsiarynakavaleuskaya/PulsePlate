"""Tests for nutrition logging endpoints.

RU: Тесты для /api/v1/pro/nutrition/meal-log и /day-close.
EN: Tests for nutrition log endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestNutritionLogAPI:
    client: TestClient
    pro_headers: dict[str, str]

    @pytest.fixture(autouse=True)
    def _bind_managed_resources(
        self,
        isolated_test_client: TestClient,
        pro_headers: dict[str, str],
    ) -> None:
        self.client = isolated_test_client
        self.pro_headers = pro_headers

    def test_meal_log_updates_adherence_state(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "meal_logged"},
            headers=self.pro_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert isinstance(data["user_id"], int)
        assert data["user_id"] > 0
        assert data["analyzer_key"] == "v1:adherence"
        assert data["n"] == 1
        assert data["alpha"] > data["beta"]
        assert data["alpha"] > 0
        assert data["beta"] > 0
        assert data["risk_slip"] < 0.5
        assert 0.0 <= data["confidence"] <= 1.0

        # Verify risk endpoint uses auth-derived identity (no user_id param)
        risk_resp = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
            headers=self.pro_headers,
        )
        assert risk_resp.status_code == 200
        assert risk_resp.headers["content-type"].startswith("application/json")
        risk = risk_resp.json()
        assert risk["user_id"] == data["user_id"]
        assert risk["analyzer_key"] == data["analyzer_key"]
        assert risk["n"] == 1
        assert 0.0 <= risk["risk_slip"] <= 1.0
        assert 0.0 <= risk["confidence"] <= 1.0
        assert risk == data

    def test_day_close_with_zero_score_increases_slip_risk(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/day-close",
            json={"day": "2025-01-01", "adherence_score": 0.0},
            headers=self.pro_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["n"] == 1
        assert data["beta"] > data["alpha"]
        assert data["risk_slip"] > 0.5

    def test_partial_meal_uses_weighted_slip(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "partial", "adherence_score": 0.8},
            headers=self.pro_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["n"] == 1
        assert data["alpha"] == pytest.approx(1.0)
        assert data["beta"] == pytest.approx(1.2)
        assert data["beta"] > data["alpha"]
        assert data["risk_slip"] == pytest.approx(1.2 / 2.2)

    def test_slip_meal_log_increases_beta(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "slip"},
            headers=self.pro_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["n"] == 1
        assert data["beta"] > data["alpha"]
        assert data["risk_slip"] > 0.5

    def test_day_close_high_score_maps_to_meal_logged(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/day-close",
            json={"day": "2025-01-02", "adherence_score": 1.0},
            headers=self.pro_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        data = response.json()
        assert data["n"] == 1
        # High score (1.0) should increase alpha relative to beta
        assert data["alpha"] > data["beta"]
        assert data["alpha"] > 0
        assert data["beta"] > 0
        assert data["risk_slip"] < 0.5

    def test_validation_of_adherence_score(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "partial", "adherence_score": 1.1},
            headers=self.pro_headers,
        )
        assert response.status_code == 422

    def test_partial_without_adherence_score_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "partial"},
            headers=self.pro_headers,
        )
        assert response.status_code == 422

    def test_nutrition_log_rejects_missing_api_key(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "meal_logged"},
        )
        assert response.status_code == 401

    def test_nutrition_log_rejects_invalid_api_key(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "meal_logged"},
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403

    def test_partial_meal_boundary_values(self) -> None:
        """Verify partial logs accept boundary adherence_score values (0.0, 1.0)."""
        for score, expected_n, expected_beta, expected_risk in (
            (0.0, 1, 2.0, 2.0 / 3.0),
            (1.0, 2, 2.01, 2.01 / 3.01),
        ):
            response = self.client.post(
                "/api/v1/pro/nutrition/meal-log",
                json={"log_type": "partial", "adherence_score": score},
                headers=self.pro_headers,
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            data = response.json()
            assert data["n"] == expected_n
            assert data["alpha"] == pytest.approx(1.0)
            assert data["beta"] == pytest.approx(expected_beta)
            assert data["beta"] > data["alpha"]
            assert data["risk_slip"] == pytest.approx(expected_risk)
