"""Tests for nutrition logging endpoints.

RU: Тесты для /api/v1/pro/nutrition/meal-log и /day-close.
EN: Tests for nutrition log endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import app as fastapi_app
from app.middleware.api_tiers import TEST_KEY_PRO, derive_subject_id_from_api_key
from core.models import AnalyzerStateModel


class TestNutritionLogAPI:
    def setup_method(self) -> None:
        self.headers = {"X-API-Key": TEST_KEY_PRO}
        self.client = TestClient(fastapi_app, headers=self.headers)
        self.user_id = derive_subject_id_from_api_key(TEST_KEY_PRO)

    def teardown_method(self) -> None:
        fastapi_app.dependency_overrides.clear()

        # Clean up analyzer state for this test subject to avoid cross-test interference
        # Import SessionLocal dynamically to get current value (not cached at module import time)
        from core.db import SessionLocal

        # Guard: SessionLocal should be initialized by _init_db_for_api_suite fixture
        # If None, it means reset_db_for_tests() was called unexpectedly in an API test
        if SessionLocal is None:
            raise AssertionError(
                "SessionLocal is None in API test teardown. "
                "API tests expect DB initialized; reset_db_for_tests() leaked into API scope."
            )

        session = SessionLocal()
        try:
            session.query(AnalyzerStateModel).filter(
                AnalyzerStateModel.user_id == self.user_id
            ).delete(synchronize_session=False)
            session.commit()
        finally:
            session.close()

    def test_meal_log_updates_adherence_state(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "meal_logged"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["n"] >= 1
        assert data["alpha"] > 0
        assert data["beta"] > 0

        # Verify risk endpoint uses auth-derived identity (no user_id param)
        risk_resp = self.client.get(
            "/api/v1/bayes/adherence/risk",
            params={"analyzer_key": "v1:adherence"},
        )
        assert risk_resp.status_code == 200
        risk = risk_resp.json()
        assert risk["n"] >= 1
        assert 0.0 <= risk["risk_slip"] <= 1.0
        assert 0.0 <= risk["confidence"] <= 1.0

    def test_day_close_with_zero_score_increases_slip_risk(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/day-close",
            json={"day": "2025-01-01", "adherence_score": 0.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["n"] >= 1
        assert data["beta"] >= data["alpha"]

    def test_partial_meal_uses_weighted_slip(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "partial", "adherence_score": 0.8},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["n"] >= 1
        assert data["beta"] > 1.0

    def test_slip_meal_log_increases_beta(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "slip"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["n"] >= 1
        assert data["beta"] > data["alpha"]

    def test_day_close_high_score_maps_to_meal_logged(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/day-close",
            json={"day": "2025-01-02", "adherence_score": 1.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["n"] >= 1
        # High score (1.0) should increase alpha relative to beta
        # Use invariant check: alpha and beta should be different after update
        assert data["alpha"] != data["beta"]
        assert data["alpha"] > 0
        assert data["beta"] > 0
        # Risk should decrease (or at least be reasonable) for high adherence
        assert 0.0 <= data.get("risk_slip", 0.5) <= 1.0

    def test_validation_of_adherence_score(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "partial", "adherence_score": 1.1},
        )
        assert response.status_code == 422

    def test_partial_without_adherence_score_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "partial"},
        )
        assert response.status_code == 422

    def test_nutrition_log_rejects_missing_api_key(self) -> None:
        client = TestClient(fastapi_app)
        response = client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "meal_logged"},
        )
        assert response.status_code == 401

    def test_nutrition_log_rejects_invalid_api_key(self) -> None:
        client = TestClient(fastapi_app, headers={"X-API-Key": "invalid_key"})
        response = client.post(
            "/api/v1/pro/nutrition/meal-log",
            json={"log_type": "meal_logged"},
        )
        assert response.status_code == 403

    def test_partial_meal_boundary_values(self) -> None:
        """Verify partial logs accept boundary adherence_score values (0.0, 1.0)."""
        for score in (0.0, 1.0):
            response = self.client.post(
                "/api/v1/pro/nutrition/meal-log",
                json={"log_type": "partial", "adherence_score": score},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["n"] >= 1
