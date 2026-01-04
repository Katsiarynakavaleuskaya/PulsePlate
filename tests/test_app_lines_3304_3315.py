"""Targeted tests for app.py lines 3304-3315 to reach 97% coverage.

Covers:
- /premium_bmr legacy endpoint exception paths
- ImportError handling
- ValueError handling
- Generic exception handling
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app


class TestAppLines3304_3315:
    """Tests for app.py lines 3304-3315 (premium_bmr legacy endpoint exceptions)."""

    def test_premium_bmr_legacy_import_error(self, client: TestClient) -> None:
        """/premium_bmr returns 503 when BMR calculation module unavailable."""

        # Patch wrapper to raise ImportError
        with patch.object(
            app, "_calculate_all_bmr_wrapper", side_effect=ImportError("Module missing")
        ):
            response = client.post(
                "/premium_bmr",
                json={
                    "weight_kg": 70.0,
                    "height_cm": 170.0,
                    "age": 30,
                    "sex": "male",
                    "activity": "moderate",
                    "lang": "en",
                },
            )
            assert response.status_code == 503
            data = response.json()
            assert "BMR calculation module not available" in data["detail"]

    def test_premium_bmr_legacy_value_error(self, client: TestClient) -> None:
        """/premium_bmr returns 400 for invalid input values."""

        # Patch wrapper to raise ValueError
        with patch.object(
            app, "_calculate_all_bmr_wrapper", side_effect=ValueError("Invalid weight")
        ):
            response = client.post(
                "/premium_bmr",
                json={
                    "weight_kg": 70.0,
                    "height_cm": 170.0,
                    "age": 30,
                    "sex": "male",
                    "activity": "moderate",
                    "lang": "en",
                },
            )
            assert response.status_code == 400
            data = response.json()
            assert "Invalid input" in data["detail"]
            assert "Invalid weight" in data["detail"]

    def test_premium_bmr_legacy_generic_exception(self, client: TestClient) -> None:
        """/premium_bmr returns 500 for unexpected errors."""

        # Patch wrapper to raise generic exception
        with patch.object(
            app,
            "_calculate_all_bmr_wrapper",
            side_effect=RuntimeError("Unexpected error"),
        ):
            response = client.post(
                "/premium_bmr",
                json={
                    "weight_kg": 70.0,
                    "height_cm": 170.0,
                    "age": 30,
                    "sex": "male",
                    "activity": "moderate",
                    "lang": "en",
                },
            )
            assert response.status_code == 500
            data = response.json()
            assert "BMR calculation failed" in data["detail"]

    def test_premium_bmr_legacy_success(self, client: TestClient) -> None:
        """/premium_bmr returns valid response for correct inputs.

        This is an integration test that verifies the actual implementation
        produces valid values, providing valuable coverage beyond mocked tests.
        """
        response = client.post(
            "/premium_bmr",
            json={
                "weight_kg": 70.0,
                "height_cm": 170.0,
                "age": 30,
                "sex": "male",
                "activity": "moderate",
                "lang": "en",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bmr" in data
        assert "tdee" in data
        assert "recommended_intake" in data

        # Basic sanity checks on values
        # BMR and TDEE are dicts with formula names as keys (e.g., {"mifflin": 1617.5})
        assert isinstance(data["bmr"], dict), "BMR should be a dict"
        assert isinstance(data["tdee"], dict), "TDEE should be a dict"
        assert len(data["bmr"]) > 0, "BMR dict should not be empty"
        assert len(data["tdee"]) > 0, "TDEE dict should not be empty"

        # Check that BMR values are positive
        for formula, value in data["bmr"].items():
            assert value > 0, f"BMR[{formula}] should be positive"

        # Check that TDEE values exceed corresponding BMR values
        for formula in data["bmr"]:
            if formula in data["tdee"]:
                assert data["tdee"][formula] > data["bmr"][formula], (
                    f"TDEE[{formula}] should exceed BMR[{formula}]"
                )

        assert isinstance(data["recommended_intake"], dict), "recommended_intake should be a dict"
