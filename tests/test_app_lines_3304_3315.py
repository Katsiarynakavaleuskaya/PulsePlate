"""
Targeted tests for app.py lines 3364-3370 to reach 97% coverage.

Covers:
- /premium_bmr legacy endpoint exception paths
- ImportError handling (line 3364-3365)
- ValueError handling (line 3366-3367)
- Generic exception handling (line 3368-3370)
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
        """/premium_bmr returns valid response for correct inputs."""
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
