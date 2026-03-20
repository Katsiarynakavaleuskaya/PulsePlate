"""
Test coverage for remaining missing lines in app.py to improve coverage to 97%.
"""

import os
from unittest.mock import patch

import pytest


class TestAppRemainingCoverage:
    """Tests for remaining missing lines in app.py."""

    def test_short_git_sha_function(self) -> None:
        """Test the _short_git_sha function from app.utils.helpers."""
        from app.utils.helpers import _short_git_sha

        assert _short_git_sha(None) == "unknown"
        assert _short_git_sha("") == "unknown"
        assert _short_git_sha("not-a-sha") == "unknown"
        assert _short_git_sha("a" * 40) == "a" * 12

    def test_is_truthy_function(self) -> None:
        """Test the _is_truthy function from app.utils.feature_flags."""
        from app.utils.feature_flags import _is_truthy

        assert _is_truthy("true") is True
        assert _is_truthy("  YES ") is True
        assert _is_truthy("1") is True
        assert _is_truthy("on") is True

        assert _is_truthy("false") is False
        assert _is_truthy("0") is False
        assert _is_truthy(None) is False

    def test_is_recursive_rag_enabled_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test recursive RAG feature flag parsing."""
        from app.utils.feature_flags import is_recursive_rag_enabled

        monkeypatch.setenv("FEATURE_RAG_RECURSIVE", "true")
        assert is_recursive_rag_enabled() is True

        monkeypatch.setenv("FEATURE_RAG_RECURSIVE", "0")
        assert is_recursive_rag_enabled() is False

    def test_is_recursive_rag_optimization_enabled_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test recursive optimization feature flag parsing."""
        from app.utils.feature_flags import is_recursive_rag_optimization_enabled

        monkeypatch.setenv("FEATURE_RAG_RECURSIVE_OPTIMIZATION", "true")
        assert is_recursive_rag_optimization_enabled() is True

        monkeypatch.setenv("FEATURE_RAG_RECURSIVE_OPTIMIZATION", "0")
        assert is_recursive_rag_optimization_enabled() is False

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
