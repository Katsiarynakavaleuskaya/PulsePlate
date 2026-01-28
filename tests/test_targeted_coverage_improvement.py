"""
Targeted tests to improve coverage for specific uncovered lines in main.py.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app from app.py file
from app import app

# Canonical imports for BMI helpers (replacing legacy app.* functions)
from core.bmi.risk import _waist_thresholds, get_waist_risk_note
from tests._helpers.bmi_flags import _normalize_flags_for_tests


class TestTargetedCoverageImprovement:
    """Targeted tests to improve coverage for uncovered lines."""

    def setup_method(self):
        """Set up test environment."""
        os.environ["API_KEY"] = "test-key"
        os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_normalize_flags_edge_cases(self) -> None:
        """Test edge cases for normalize_flags function."""
        # Test various gender inputs (note: these will be normalized by the model validator)
        # But we can test the function directly with lowercase inputs
        result = _normalize_flags_for_tests("male", "no", "no")
        assert result["gender_male"] is True

        result = _normalize_flags_for_tests("female", "no", "no")
        assert result["gender_male"] is False

        # Test various pregnant inputs
        result = _normalize_flags_for_tests("female", "да", "no")
        assert result["is_pregnant"] is True

        result = _normalize_flags_for_tests("female", "беременна", "no")
        assert result["is_pregnant"] is True

        result = _normalize_flags_for_tests("female", "pregnant", "no")
        assert result["is_pregnant"] is True

        result = _normalize_flags_for_tests("female", "yes", "no")
        assert result["is_pregnant"] is True

        result = _normalize_flags_for_tests("female", "y", "no")
        assert result["is_pregnant"] is True

        # Test that male can't be pregnant even with pregnant flags
        result = _normalize_flags_for_tests("male", "yes", "no")
        assert result["is_pregnant"] is False

        # Test various athlete inputs
        result = _normalize_flags_for_tests("male", "no", "спортсмен")
        assert result["is_athlete"] is True

        result = _normalize_flags_for_tests("male", "no", "да")
        assert result["is_athlete"] is True

        result = _normalize_flags_for_tests("male", "no", "yes")
        assert result["is_athlete"] is True

        result = _normalize_flags_for_tests("male", "no", "y")
        assert result["is_athlete"] is True

        result = _normalize_flags_for_tests("male", "no", "athlete")
        assert result["is_athlete"] is True

    @pytest.mark.parametrize("pregnant_value", ["pregnant", "беременна", "беременная"])
    def test_normalize_flags_pregnant_synonyms_are_true_for_female(
        self, pregnant_value: str
    ) -> None:
        """
        RU: Legacy public API: беременность должна распознаваться по строковым синонимам.
        EN: Legacy public API: pregnancy synonyms must be treated as true.
        """
        result = _normalize_flags_for_tests(gender="female", pregnant=pregnant_value, athlete="no")
        assert result["is_pregnant"] is True

    @pytest.mark.parametrize("bad_pregnant_value", ["athlete", "спортсмен"])
    def test_normalize_flags_pregnant_must_not_accept_athlete_keywords(
        self, bad_pregnant_value: str
    ) -> None:
        """
        RU: Athlete keywords MUST NOT imply pregnant=True.
        EN: Athlete keywords MUST NOT imply pregnant=True.
        """
        result = _normalize_flags_for_tests(
            gender="female", pregnant=bad_pregnant_value, athlete="no"
        )
        assert result["is_pregnant"] is False

    def test_waist_risk_edge_cases(self) -> None:
        """Test edge cases for waist_risk function."""
        # Get canonical thresholds (no hardcoded values)
        male_warn, male_high = _waist_thresholds("male")
        female_warn, female_high = _waist_thresholds("female")

        # Test male high risk boundary
        result = get_waist_risk_note(waist_cm=male_high, gender="male", lang="en")
        assert "High" in result

        result = get_waist_risk_note(waist_cm=male_high, gender="male", lang="ru")
        assert "Высокий" in result

        # Test male warning boundary
        result = get_waist_risk_note(waist_cm=male_warn, gender="male", lang="en")
        assert "Increased" in result

        result = get_waist_risk_note(waist_cm=male_warn, gender="male", lang="ru")
        assert "Повышенный" in result

        # Test female high risk boundary
        result = get_waist_risk_note(waist_cm=female_high, gender="female", lang="en")
        assert "High" in result

        result = get_waist_risk_note(waist_cm=female_high, gender="female", lang="ru")
        assert "Высокий" in result

        # Test female warning boundary
        result = get_waist_risk_note(waist_cm=female_warn, gender="female", lang="en")
        assert "Increased" in result

        result = get_waist_risk_note(waist_cm=female_warn, gender="female", lang="ru")
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
            "lang": "en",
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
            "height_m": 2.2,  # Very tall
            "age": 80,
            "gender": "female",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en",
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
            "include_chart": False,
        }

        response = self.client.post("/bmi", json=data)
        assert response.status_code == 200

        result = response.json()
        assert "bmi" in result
        assert "category" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
