"""
Additional tests to improve coverage for app.py to reach 97%+.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app


class TestMissingCoverage:
    """Additional tests to improve coverage for app.py."""

    def setup_method(self):
        """Set up test environment."""
        # Set a test API key for testing
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        # Remove the test API key
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_bmi_endpoint_with_matplotlib_unavailable(self):
        """Test BMI endpoint when matplotlib is not available."""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "waist_cm": 85.0,
            "include_chart": True,
            "lang": "en"
        }

        # Mock matplotlib to be unavailable and generate_bmi_visualization to return unavailable
        with patch('app.MATPLOTLIB_AVAILABLE', False), \
             patch('app.generate_bmi_visualization') as mock_viz:
            mock_viz.return_value = {
                "available": False,
                "error": "Visualization not available - matplotlib not installed"
            }
            response = self.client.post("/bmi", json=data)
            assert response.status_code == 200

            result = response.json()
            assert "bmi" in result
            assert "category" in result
            # Should have visualization section with error
            if "visualization" in result:
                viz = result["visualization"]
                assert not viz.get("available", True)

    def test_bmi_visualize_endpoint_module_unavailable(self):
        """Test BMI visualize endpoint when module is not available."""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en"
        }

        # Mock generate_bmi_visualization to be None at app module level
        with patch('app.generate_bmi_visualization', None):
            response = self.client.post("/api/v1/bmi/visualize", json=data, headers={"X-API-Key": "test_key"})
            # The app raises HTTPException with status code 503 when module is not available
            assert response.status_code == 503
            assert "not available - module not found" in response.json()["detail"]

    def test_bmi_visualize_endpoint_matplotlib_unavailable(self):
        """Test BMI visualize endpoint when matplotlib is not available."""
        data = {
            "weight_kg": 70.0,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en"
        }

        # Mock matplotlib to be unavailable at app module level
        with patch('app.MATPLOTLIB_AVAILABLE', False):
            response = self.client.post("/api/v1/bmi/visualize", json=data, headers={"X-API-Key": "test_key"})
            # The app raises HTTPException with status code 503 when matplotlib is not available
            assert response.status_code == 503
            assert "not available - matplotlib not installed" in response.json()["detail"]

    def test_premium_bmr_modules_unavailable(self):
        """Test premium BMR endpoint when modules are not available."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "lang": "en"
        }

        # Mock calculate_all_bmr and calculate_all_tdee to be None at app module level
        with patch('app.calculate_all_bmr', None), \
             patch('app.calculate_all_tdee', None):
            response = self.client.post("/api/v1/premium/bmr", json=data, headers={"X-API-Key": "test_key"})
            # The app raises HTTPException with status code 503 when modules are not available
            assert response.status_code == 503
            assert "not available" in response.json()["detail"]

    def test_premium_bmr_general_exception(self):
        """Test premium BMR endpoint with general exception."""
        data = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "sex": "male",
            "activity": "moderate",
            "lang": "en"
        }

        # Mock calculate_all_bmr to raise an exception at app module level
        with patch('app.calculate_all_bmr') as mock_calc:
            mock_calc.side_effect = Exception("Test error")
            response = self.client.post("/api/v1/premium/bmr", json=data, headers={"X-API-Key": "test_key"})
            # The app catches the exception and raises HTTPException with status code 500
            assert response.status_code == 500
            assert "failed" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
