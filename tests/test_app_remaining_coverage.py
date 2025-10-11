"""
Test coverage for remaining missing lines in main.py to improve coverage to 97%.
"""

import os
from unittest.mock import patch

import pytest


class TestAppRemainingCoverage:
    """Tests for remaining missing lines in main.py."""

    def test_calc_bmi_function(self):
        """Test the calc_bmi function."""
        from app import calc_bmi

        # Test normal calculation
        result = calc_bmi(70.0, 1.75)
        assert result == 22.9

        # Test with different values
        result = calc_bmi(80.0, 1.80)
        assert result == 24.7

    def test_normalize_flags_function(self):
        """Test the normalize_flags function."""
        from app import normalize_flags

        # Test male gender normalization
        result = normalize_flags("male", "no", "no")
        assert result["gender_male"] is True
        assert result["is_pregnant"] is False
        assert result["is_athlete"] is False

        # Test female gender normalization
        result = normalize_flags("female", "yes", "yes")
        assert result["gender_male"] is False
        assert result["is_pregnant"] is True
        assert result["is_athlete"] is True

        # Test various string synonyms
        result = normalize_flags("муж", "нет", "нет")
        assert result["gender_male"] is True

        result = normalize_flags("жен", "да", "да")
        assert result["gender_male"] is False
        assert result["is_pregnant"] is True
        assert result["is_athlete"] is True

    def test_waist_risk_function(self):
        """Test the waist_risk function."""
        from app import waist_risk

        # Test male waist risk levels
        result = waist_risk(90.0, True, "en")
        assert result == ""

        result = waist_risk(95.0, True, "en")
        assert "Increased" in result

        result = waist_risk(105.0, True, "en")
        assert "High" in result

        # Test female waist risk levels
        result = waist_risk(75.0, False, "en")
        assert result == ""

        result = waist_risk(85.0, False, "en")
        assert "Increased" in result

        result = waist_risk(95.0, False, "en")
        assert "High" in result

        # Test Russian language
        result = waist_risk(95.0, True, "ru")
        assert "Повышенный" in result or "Высокий" in result

    def test_add_visualization_if_requested_function(self, test_client):
        """Test the add_visualization_if_requested function."""
        from app import BMIRequest, add_visualization_if_requested

        # Test when include_chart is False
        result = {"bmi": 22.5}
        req = BMIRequest(weight_kg=70.0, height_m=1.75, age=30, gender="male", include_chart=False)
        add_visualization_if_requested(result, req)
        # Should not add visualization when include_chart is False
        assert "visualization" not in result

    def test_bmi_endpoint_with_visualization(self, test_client):
        """Test BMI endpoint with visualization request."""
        client = test_client

        # Test BMI endpoint with visualization
        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.75,
                "age": 30,
                "gender": "male",
                "include_chart": True,
            },
        )
        assert response.status_code == 200
        # Visualization may or may not be available depending on matplotlib

    def test_bmi_endpoint_pregnant_female(self, test_client):
        """Test BMI endpoint with pregnant female."""
        client = test_client

        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.75,
                "age": 30,
                "gender": "female",
                "pregnant": "yes",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] is None
        assert (
            "pregnancy" in data["note"].lower()
            or "беременности" in data["note"].lower()
            or data["note"] == ""
        )

    def test_bmi_endpoint_athlete(self, test_client):
        """Test BMI endpoint with athlete flag."""
        client = test_client

        response = client.post(
            "/bmi",
            json={
                "weight_kg": 70.0,
                "height_m": 1.75,
                "age": 30,
                "gender": "male",
                "athlete": "yes",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["athlete"] is True

    def test_plan_endpoint(self, test_client):
        """Test plan endpoint."""
        client = test_client

        response = client.post(
            "/plan", json={"weight_kg": 70.0, "height_m": 1.75, "age": 30, "gender": "male"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "next_steps" in data

    def test_plan_endpoint_premium(self, test_client):
        """Test plan endpoint with premium flag."""
        client = test_client

        response = client.post(
            "/plan",
            json={
                "weight_kg": 70.0,
                "height_m": 1.75,
                "age": 30,
                "gender": "male",
                "premium": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["premium"] is True

    def test_insight_endpoint_disabled(self, test_client):
        """Test insight endpoint when feature is disabled."""
        client = test_client

        # Test when FEATURE_INSIGHT is disabled
        with patch.dict(os.environ, {"FEATURE_INSIGHT": "false"}):
            response = client.post("/insight", json={"text": "test"})
            # Should return 503 when feature is disabled
            assert response.status_code in [503, 403, 422]

    def test_debug_env_endpoint(self, test_client):
        """Test debug environment endpoint."""
        client = test_client

        response = client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_health_endpoints(self, test_client):
        """Test health endpoints."""
        client = test_client

        # Test basic health endpoint
        response = client.get("/health")
        assert response.status_code == 200

        # Test API v1 health endpoint
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_favicon_endpoint(self, test_client):
        """Test favicon endpoint."""
        client = test_client

        response = client.get("/favicon.ico")
        assert response.status_code == 204

    def test_privacy_endpoint(self, test_client):
        """Test privacy endpoint."""
        client = test_client

        response = client.get("/privacy")
        assert response.status_code == 200
        data = response.json()
        assert "privacy_policy" in data

    def test_metrics_endpoint(self, test_client):
        """Test metrics endpoint."""
        client = test_client

        response = client.get("/metrics")
        assert response.status_code == 200
        # Will return error if prometheus is not available


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
