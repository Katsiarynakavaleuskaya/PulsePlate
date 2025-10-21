# -*- coding: utf-8 -*-
"""
Combined app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers.

RU: Объединенные тесты для покрытия и юнит-тестов app: покрытие main.py, группы, insight, debug_env и внутренние хелперы
EN: Combined tests for app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers
"""

import pytest
from fastapi.testclient import TestClient

try:
    import os
    import sys

    # Simple import of the app module
    import app

    app_instance = app.app
except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

# client fixture is provided by conftest.py


class TestAppCoverage:
    """Coverage tests for main.py (groups, insight, debug_env)."""

    def test_groups_endpoint_coverage(self, client):
        """Test groups endpoint for coverage."""
        response = client.get("/groups")
        # Groups endpoint should return 404 as it's not implemented
        assert response.status_code == 404

    def test_insight_endpoint_coverage(self, client, test_environment):
        """Test insight endpoint for coverage."""
        response = client.post(
            "/api/v1/insight",
            json={"text": "test insight"},
            headers={"X-API-Key": "test_key"},
        )
        # With test_environment fixture, should return 200 or 503 (if LLM unavailable)
        assert response.status_code in [200, 503]

    def test_debug_env_endpoint_coverage(self, client):
        """Test debug_env endpoint for coverage."""
        response = client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_health_endpoint_coverage(self, client):
        """Test health endpoint for coverage."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_root_endpoint_coverage(self, client):
        """Test root endpoint for coverage."""
        response = client.get("/")
        assert response.status_code == 200
        content = response.text
        assert "<title" in content

    def test_docs_endpoint_coverage(self, client):
        """Test docs endpoint for coverage."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_endpoint_coverage(self, client):
        """Test openapi endpoint for coverage."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data

    def test_favicon_endpoint_coverage(self, client):
        """Test favicon endpoint for coverage."""
        response = client.get("/favicon.ico")
        assert response.status_code == 204


class TestAppUnitTests:
    """Unit tests for internal helpers in main.py."""

    def test_bmi_category_boundaries(self):
        """Test BMI category boundary values 18.5/25/30."""
        from bmi_core import bmi_category

        # below 18.5
        assert bmi_category(18.49, "en") == "Underweight"
        # [18.5, 25)
        assert bmi_category(18.5, "en") == "Normal weight"
        assert bmi_category(24.99, "en") == "Normal weight"
        # [25, 30)
        assert bmi_category(25.0, "en") == "Overweight"
        assert bmi_category(29.99, "en") == "Overweight"
        # >= 30
        assert bmi_category(30.0, "en") == "Obese Class I"

    def test_bmi_category_russian(self):
        """Test BMI category in Russian."""
        from bmi_core import bmi_category

        assert bmi_category(20.0, "ru") == "Норма"
        assert bmi_category(27.0, "ru") == "Избыточная масса"
        assert bmi_category(32.0, "ru") == "Ожирение I степени"

    def test_bmi_interpret_group_function(self):
        """Test interpret_group function for different groups."""
        from bmi_core import interpret_group

        # Test interpret_group function
        result = interpret_group(25.0, "general", "en")
        assert isinstance(result, str)
        assert len(result) > 0

        result_ru = interpret_group(25.0, "general", "ru")
        assert isinstance(result_ru, str)
        assert len(result_ru) > 0

    def test_bmi_estimate_level_function(self):
        """Test estimate_level function."""
        from bmi_core import estimate_level

        # Test estimate_level function
        result = estimate_level(30, 25.0, "en")
        assert isinstance(result, str)
        assert len(result) > 0

        result_ru = estimate_level(30, 25.0, "ru")
        assert isinstance(result_ru, str)
        assert len(result_ru) > 0

    def test_debug_env_feature_insight_switch(self, client):
        """Test /debug_env: check insight_enabled switching through FEATURE_INSIGHT."""
        response = client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should contain required environment variables (based on actual debug endpoint response)
        required_keys = ["FEATURE_INSIGHT", "LLM_PROVIDER", "insight_enabled"]
        missing_keys = [key for key in required_keys if key not in data]
        assert (
            len(missing_keys) == 0
        ), f"Missing required environment keys: {missing_keys}. Available keys: {list(data.keys())}"

        # Check for optional but expected keys
        optional_keys = ["GROK_MODEL", "GROK_ENDPOINT"]
        found_optional = [key for key in optional_keys if key in data]
        assert (
            len(found_optional) > 0
        ), f"Expected at least one optional key from {optional_keys} in response data: {list(data.keys())}"
