# -*- coding: utf-8 -*-
"""
Combined app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers.

RU: Объединенные тесты для покрытия и юнит-тестов app: покрытие main.py, группы, insight, debug_env и внутренние хелперы
EN: Combined tests for app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers
"""

import pytest
from fastapi.testclient import TestClient

from tests.feature_manifest import FEATURE_REASON, fail_feature_gated_test, require_feature

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

    def test_insight_endpoint_coverage(
        self, client: TestClient, vip_headers: dict[str, str]
    ) -> None:
        """Test insight endpoint for coverage."""
        response = client.post(
            "/api/v1/insight",
            json={"text": "test insight"},
            headers=vip_headers,
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
        assert (
            not missing_keys
        ), f"Missing required environment keys: {missing_keys}. Available keys: {list(data.keys())}"

        # Check for optional but expected keys
        optional_keys = ["GROK_MODEL", "GROK_ENDPOINT"]
        found_optional = [key for key in optional_keys if key in data]
        assert (
            found_optional
        ), f"Expected at least one optional key from {optional_keys} in response data: {list(data.keys())}"


class TestAppUnitTests:
    """Unit tests for app internal functions and helpers."""

    def test_bmi_core_functions(self) -> None:
        """Test BMI core functions for coverage (canonical equivalents)."""
        from core.bmi.engine import _compute_bmi, HEALTHY_BMI_RANGE

        # Test bmi_value function (canonical: _compute_bmi)
        bmi = _compute_bmi(weight_kg=70.0, height_m=1.75)
        assert isinstance(bmi, float)
        assert 20.0 <= bmi <= 25.0  # Should be in normal range

        # Test healthy_bmi_range (canonical: HEALTHY_BMI_RANGE constant)
        bmi_min = HEALTHY_BMI_RANGE.min
        bmi_max = HEALTHY_BMI_RANGE.max
        assert isinstance(bmi_min, float)
        assert isinstance(bmi_max, float)
        assert bmi_min < bmi_max

    def test_bmi_categories(self) -> None:
        """Test BMI category interpretations."""
        from core.bmi.engine import _bmi_category

        # Test general adult categories
        assert _bmi_category(bmi=17.0, age=30, group="general") == "underweight"
        assert _bmi_category(bmi=22.0, age=30, group="general") == "normal"
        assert _bmi_category(bmi=27.0, age=30, group="general") == "overweight"
        assert _bmi_category(bmi=32.0, age=30, group="general") == "obesity_1"
        assert _bmi_category(bmi=37.0, age=30, group="general") == "obesity_2"
        assert _bmi_category(bmi=42.0, age=30, group="general") == "obesity_3"

        # Test athlete thresholds (higher normal upper bound)
        assert _bmi_category(bmi=26.0, age=30, group="athlete") == "normal"
        assert _bmi_category(bmi=28.0, age=30, group="athlete") == "overweight"

        # Test elderly thresholds (adjusted)
        assert _bmi_category(bmi=17.0, age=65, group="general") == "underweight"
        assert _bmi_category(bmi=25.0, age=65, group="general") == "normal"

        # Test no-category groups
        assert _bmi_category(bmi=22.0, age=10, group="too_young") is None
        assert _bmi_category(bmi=22.0, age=12, group="child") is None
        assert _bmi_category(bmi=22.0, age=15, group="teen") is None
        assert _bmi_category(bmi=22.0, age=30, group="pregnant") is None

    def test_estimate_level_categories(self) -> None:
        """Test estimate_level with different fitness experience levels."""
        from core.bmi.engine import estimate_level

        # Test beginner (default, low experience)
        assert estimate_level(freq_per_week=0, years=0.0) == "beginner"
        assert estimate_level(freq_per_week=1, years=0.3) == "beginner"

        # Test novice (>= 0.5 years AND >= 1 session/week)
        assert estimate_level(freq_per_week=1, years=0.5) == "novice"
        assert estimate_level(freq_per_week=2, years=1.0) == "novice"

        # Test intermediate (>= 2 years AND >= 2 sessions/week)
        assert estimate_level(freq_per_week=2, years=2.0) == "intermediate"
        assert estimate_level(freq_per_week=3, years=4.0) == "intermediate"

        # Test advanced (>= 5 years AND >= 3 sessions/week)
        assert estimate_level(freq_per_week=3, years=5.0) == "advanced"
        assert estimate_level(freq_per_week=5, years=10.0) == "advanced"

        # Test edge cases: missing one criterion stays at lower level
        assert estimate_level(freq_per_week=3, years=4.0) == "intermediate"  # < 5 years
        assert estimate_level(freq_per_week=2, years=5.0) == "intermediate"  # < 3 freq

        # Test with lang parameter (reserved for future localization)
        assert estimate_level(freq_per_week=3, years=5.0, lang="ru") == "advanced"
        assert estimate_level(freq_per_week=3, years=5.0, lang="en") == "advanced"

    def test_get_api_key_requires_exact_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """API key matching should be strict by default."""
        from fastapi import HTTPException

        from app import get_api_key

        monkeypatch.setenv("API_KEY", "abc_def")
        monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")
        monkeypatch.setenv("ALLOW_DEV_API_KEY_NORMALIZE", "false")

        with pytest.raises(HTTPException):
            get_api_key(api_key="abc-def")

        assert get_api_key(api_key="abc_def") == "abc_def"

    def test_get_api_key_dev_normalize_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Optional dev-only normalization can be enabled explicitly."""
        from app import get_api_key

        monkeypatch.setenv("API_KEY", "abc_def")
        monkeypatch.setenv("ALLOW_DEV_API_KEY", "true")
        monkeypatch.setenv("ALLOW_DEV_API_KEY_NORMALIZE", "true")

        assert get_api_key(api_key="abc-def") == "abc_def"
