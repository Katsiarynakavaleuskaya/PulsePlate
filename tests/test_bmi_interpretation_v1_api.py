# -*- coding: utf-8 -*-
"""
Tests for BMI interpretation_v1 API integration.

RU: Тесты интеграции interpretation_v1 в API.
EN: Tests for interpretation_v1 API integration.
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import app


@pytest.fixture()
def client() -> TestClient:
    """TestClient fixture for BMI API tests."""
    return TestClient(app)


class TestInterpretationV1API:
    """Tests for interpretation_v1 field in BMI calculate response."""

    def test_general_returns_interpretation_v1_not_null(self, client: TestClient) -> None:
        """Test that general group returns interpretation_v1 (not null)."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": False,
            "athlete": False,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "interpretation_v1" in data
        assert data["interpretation_v1"] is not None
        assert "goal_direction" in data["interpretation_v1"]
        assert data["interpretation_v1"]["goal_direction"] in {"maintain", "reduce", "increase", "medical_review"}

    def test_pregnant_female_no_athlete_returns_interpretation_v1(self, client: TestClient) -> None:
        """Test that pregnant (female, pregnant=yes, athlete=no) returns interpretation_v1 (not null)."""
        payload = {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "age": 28,
            "gender": "female",
            "pregnant": True,
            "athlete": False,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "interpretation_v1" in data
        assert data["interpretation_v1"] is not None
        assert data["interpretation_v1"]["goal_direction"] == "medical_review"
        assert data["interpretation_v1"]["target_range"] == "prenatal_guidelines"
        disclaimers = data["interpretation_v1"]["disclaimers"]
        assert isinstance(disclaimers, list)
        disclaimer_keys = [d for d in disclaimers if isinstance(d, str)]
        assert any("pregnancy" in k.lower() for k in disclaimer_keys)
        # Should NOT have athlete disclaimer
        assert not any("athlete" in k.lower() for k in disclaimer_keys)

    def test_pregnant_athlete_returns_interpretation_v1_not_null(self, client: TestClient) -> None:
        """Test that pregnant+athlete (female, pregnant=yes, athlete=yes) returns interpretation_v1 not null."""
        payload = {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "age": 28,
            "gender": "female",
            "pregnant": True,
            "athlete": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "interpretation_v1" in data
        assert data["interpretation_v1"] is not None
        assert "goal_direction" in data["interpretation_v1"]
        assert data["interpretation_v1"]["goal_direction"] == "medical_review"
        assert "disclaimers" in data["interpretation_v1"]
        # Check that both pregnancy and athlete disclaimers are present
        disclaimers = data["interpretation_v1"]["disclaimers"]
        assert isinstance(disclaimers, list)
        disclaimer_keys = [d for d in disclaimers if isinstance(d, str)]
        assert any("pregnancy" in k.lower() for k in disclaimer_keys)
        assert any("athlete" in k.lower() for k in disclaimer_keys)

    def test_all_interpretation_v1_fields_are_i18n_keys(self, client: TestClient) -> None:
        """Guard: all text fields in interpretation_v1 must be i18n keys (strings), not translated text."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": False,
            "athlete": False,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        interp = data.get("interpretation_v1")
        assert interp is not None

        # All fields must be strings (i18n keys)
        assert isinstance(interp["risk_flags"], list)
        for flag in interp["risk_flags"]:
            assert isinstance(flag, str)
            assert "." in flag or flag in {"age_appropriate_growth", "prenatal_guidelines"}

        assert isinstance(interp["priority_notes"], list)
        for note in interp["priority_notes"]:
            assert isinstance(note, str)
            assert "." in note

        assert isinstance(interp["disclaimers"], list)
        for disclaimer in interp["disclaimers"]:
            assert isinstance(disclaimer, str)
            assert "." in disclaimer

    def test_male_pregnant_still_returns_422(self, client: TestClient) -> None:
        """Regression: male+pregnant must still return 422 (validation contract)."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": True,
            "athlete": False,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        body = resp.json()
        detail = body.get("detail", [])
        if isinstance(detail, list) and len(detail) > 0:
            msg = str(detail[0].get("msg", ""))
        else:
            msg = str(body)
        assert "only applicable to females" in msg.lower()

    def test_athlete_returns_interpretation_v1(self, client: TestClient) -> None:
        """Test that athlete group returns interpretation_v1."""
        payload = {
            "weight_kg": 75.0,
            "height_cm": 180.0,
            "age": 25,
            "gender": "male",
            "pregnant": False,
            "athlete": True,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["group"] == "athlete"
        assert "interpretation_v1" in data
        assert data["interpretation_v1"] is not None
        assert "athlete" in str(data["interpretation_v1"]["disclaimers"]).lower()

    def test_elderly_returns_interpretation_v1(self, client: TestClient) -> None:
        """Test that elderly group returns interpretation_v1."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "age": 65,
            "gender": "male",
            "pregnant": False,
            "athlete": False,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["group"] == "elderly"
        assert "interpretation_v1" in data
        assert data["interpretation_v1"] is not None
        assert "stability" in str(data["interpretation_v1"]["priority_notes"]).lower()

    def test_legacy_interpretation_field_still_present(self, client: TestClient) -> None:
        """Guard: legacy interpretation field must still be present (backward compatibility)."""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": False,
            "athlete": False,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "interpretation" in data
        assert isinstance(data["interpretation"], str)
        # interpretation_v1 is separate field
        assert "interpretation_v1" in data

    def test_fail_soft_on_interpretation_builder_failure(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Guard: if build_interpretation_v1 fails, endpoint still returns 200 with interpretation_v1 null."""
        # Monkeypatch to simulate builder failure
        def failing_builder(*args: object, **kwargs: object) -> None:  # noqa: ARG001
            raise RuntimeError("Simulated builder failure")

        monkeypatch.setattr("core.bmi.interpretation_rules.build_interpretation_v1", failing_builder)

        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": False,
            "athlete": False,
            "lang": "en",
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        # Endpoint must still return 200 (fail-soft)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # interpretation_v1 should be null on failure
        assert data.get("interpretation_v1") is None
        # Legacy interpretation should still be present
        assert "interpretation" in data
        assert isinstance(data["interpretation"], str)
