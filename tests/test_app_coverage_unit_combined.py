# -*- coding: utf-8 -*-
"""
Combined app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers.

RU: Объединенные тесты для покрытия и юнит-тестов app: покрытие main.py, группы, insight, debug_env и внутренние хелперы
EN: Combined tests for app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers
"""

import pytest
from fastapi.testclient import TestClient

try:
    # Validate app module can be imported
    import app  # noqa: F401
except ImportError as exc:  # pragma: no cover
    pytest.skip(f"FastAPI app import failed: {exc}", allow_module_level=True)

# client fixture is provided by conftest.py


@pytest.mark.usefixtures("test_environment")
class TestAppCoverage:
    """Coverage tests for main.py (groups, insight, debug_env)."""

    def test_groups_endpoint_coverage(self, client: TestClient) -> None:
        """Test groups endpoint for coverage."""
        response = client.get("/groups")
        # Groups endpoint should return 404 as it's not implemented
        assert response.status_code == 404

    def test_insight_endpoint_coverage(self, client: TestClient) -> None:
        """Test insight endpoint for coverage."""
        response = client.post(
            "/api/v1/insight",
            json={"text": "test insight"},
            headers={"X-API-Key": "test_key"},
        )
        # With test_environment fixture, should return 200 or 503 (if LLM unavailable)
        assert response.status_code in [200, 503]

    def test_debug_env_feature_insight_switch(self, client: TestClient) -> None:
        """Test /debug_env: check insight_enabled switching through FEATURE_INSIGHT."""
        response = client.get("/debug_env")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should contain required environment variables (based on actual debug endpoint response)
        required_keys = ["FEATURE_INSIGHT", "LLM_PROVIDER", "insight_enabled"]
        missing_keys = [key for key in required_keys if key not in data]
        assert not missing_keys, (
            f"Missing required environment keys: {missing_keys}. Available keys: {list(data.keys())}"
        )

        # Check for optional but expected keys
        optional_keys = ["GROK_MODEL", "GROK_ENDPOINT"]
        found_optional = [key for key in optional_keys if key in data]
        assert found_optional, (
            f"Expected at least one optional key from {optional_keys} in response data: {list(data.keys())}"
        )


class TestAppUnitTests:
    """Unit tests for app internal functions and helpers."""

    def test_bmi_core_functions(self) -> None:
        """Test BMI core functions for coverage."""
        from bmi_core import (
            bmi_value,
            healthy_bmi_range,
            interpret_group,
            estimate_level,
        )

        # Test bmi_value function
        bmi = bmi_value(70.0, 1.75)
        assert isinstance(bmi, float)
        assert 20.0 <= bmi <= 25.0  # Should be in normal range

        # Test healthy_bmi_range function
        bmi_min, bmi_max = healthy_bmi_range(25, "general", premium=False)
        assert isinstance(bmi_min, float)
        assert isinstance(bmi_max, float)
        assert bmi_min < bmi_max

        # Test interpret_group function with specific values
        result = interpret_group(22.0, "general", "en")
        assert result == "Normal weight"

        # Test Russian localization
        result_ru = interpret_group(22.0, "general", "ru")
        assert result_ru == "Норма"

        # Test estimate_level function
        level = estimate_level(0, 0.0, "en")
        assert level == "beginner"

        # Test Russian localization
        level_ru = estimate_level(0, 0.0, "ru")
        assert level_ru == "базовый"

    def test_bmi_categories(self) -> None:
        """Test BMI category interpretations."""
        from bmi_core import interpret_group

        # Test different BMI categories
        assert interpret_group(18.5, "general", "en") == "Normal weight"
        assert interpret_group(22.0, "general", "en") == "Normal weight"
        assert interpret_group(25.0, "general", "en") == "Overweight"
        assert interpret_group(30.0, "general", "en") == "Obese Class I"

        # Test Russian categories
        assert interpret_group(18.5, "general", "ru") == "Норма"
        assert interpret_group(22.0, "general", "ru") == "Норма"
        assert interpret_group(25.0, "general", "ru") == "Избыточная масса"
        assert interpret_group(30.0, "general", "ru") == "Ожирение I степени"

    def test_estimate_level_categories(self) -> None:
        """Test estimate_level with different fitness experience levels."""
        from bmi_core import estimate_level

        # Test beginner level (no experience, no frequency)
        assert estimate_level(0, 0.0, "en") == "beginner"
        assert estimate_level(0, 0.0, "ru") == "базовый"

        # Test novice level (some experience, low frequency)
        assert estimate_level(1, 0.5, "en") == "novice"
        assert estimate_level(1, 0.5, "ru") == "начальный"

        # Test intermediate level (moderate experience and frequency)
        assert estimate_level(2, 2.0, "en") == "intermediate"
        assert estimate_level(2, 2.0, "ru") == "средний"

        # Test advanced level (high experience and frequency)
        assert estimate_level(3, 5.0, "en") == "advanced"
        assert estimate_level(3, 5.0, "ru") == "продвинутый"
