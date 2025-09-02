"""
Targeted tests to improve coverage for specific uncovered lines in app.py.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app


class TestTargetedCoverageImprovement:
    """Targeted tests to improve coverage for uncovered lines."""

    def setup_method(self):
        """Set up test environment."""
        os.environ["API_KEY"] = "test-key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_normalize_flags_edge_cases(self):
        """Test edge cases for normalize_flags function."""
        from app import normalize_flags

        # Test various gender inputs (note: these will be normalized by the model validator)
        # But we can test the function directly with lowercase inputs
        result = normalize_flags("male", "no", "no")
        assert result["gender_male"] is True

        result = normalize_flags("female", "no", "no")
        assert result["gender_male"] is False

        # Test various pregnant inputs
        result = normalize_flags("female", "да", "no")
        assert result["is_pregnant"] is True

        result = normalize_flags("female", "беременна", "no")
        assert result["is_pregnant"] is True

        result = normalize_flags("female", "pregnant", "no")
        assert result["is_pregnant"] is True

        result = normalize_flags("female", "yes", "no")
        assert result["is_pregnant"] is True

        result = normalize_flags("female", "y", "no")
        assert result["is_pregnant"] is True

        # Test that male can't be pregnant even with pregnant flags
        result = normalize_flags("male", "yes", "no")
        assert result["is_pregnant"] is False

        # Test various athlete inputs
        result = normalize_flags("male", "no", "спортсмен")
        assert result["is_athlete"] is True

        result = normalize_flags("male", "no", "да")
        assert result["is_athlete"] is True

        result = normalize_flags("male", "no", "yes")
        assert result["is_athlete"] is True

        result = normalize_flags("male", "no", "y")
        assert result["is_athlete"] is True

        result = normalize_flags("male", "no", "athlete")
        assert result["is_athlete"] is True

    def test_waist_risk_edge_cases(self):
        """Test edge cases for waist_risk function."""
        from app import waist_risk

        # Test male high risk boundary
        result = waist_risk(102.0, True, "en")
        assert "High" in result

        result = waist_risk(102.0, True, "ru")
        assert "Высокий" in result

        # Test male warning boundary
        result = waist_risk(94.0, True, "en")
        assert "Increased" in result

        result = waist_risk(94.0, True, "ru")
        assert "Повышенный" in result

        # Test female high risk boundary
        result = waist_risk(88.0, False, "en")
        assert "High" in result

        result = waist_risk(88.0, False, "ru")
        assert "Высокий" in result

        # Test female warning boundary
        result = waist_risk(80.0, False, "en")
        assert "Increased" in result

        result = waist_risk(80.0, False, "ru")
        assert "Повышенный" in result

    def test_bmi_endpoint_pregnant_male(self):
        """Test BMI endpoint with pregnant male (should not be pregnant)."""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "yes",  # Male can't be pregnant
            "athlete": "no",
            "lang": "en"
        }

        response = self.client.post("/bmi", json=data)
        assert response.status_code == 200

        result = response.json()
        assert result["bmi"] is not None
        # Should not be marked as pregnant for male
        assert "not valid during pregnancy" not in result.get("note", "")

    def test_bmi_endpoint_extreme_values(self):
        """Test BMI endpoint with extreme but valid values."""
        data = {
            "weight_kg": 200.0,  # Very heavy
            "height_m": 2.2,     # Very tall
            "age": 80,
            "gender": "female",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en"
        }

        response = self.client.post("/bmi", json=data)
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "category" in result

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_favicon_endpoint(self):
        """Test favicon endpoint."""
        response = self.client.get("/favicon.ico")
        assert response.status_code == 204

    def test_health_endpoint(self):
        """Test health endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_bmi_endpoint_with_all_optional_fields(self):
        """Test BMI endpoint with all optional fields filled."""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "yes",
            "waist_cm": 85.0,
            "lang": "en",
            "premium": True,
            "include_chart": False
        }

        response = self.client.post("/bmi", json=data)
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "category" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
