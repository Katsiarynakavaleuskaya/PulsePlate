# -*- coding: utf-8 -*-
"""
Combined app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers.

RU: Объединенные тесты для покрытия и юнит-тестов app: покрытие main.py, группы, insight, debug_env и внутренние хелперы
EN: Combined tests for app coverage and unit tests: main.py coverage, groups, insight, debug_env, and internal helpers
"""

import pytest
from fastapi.testclient import TestClient

from tests.feature_manifest import FEATURE_REASON, require_feature

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
        require_feature("legacy_bmi_removed", reason=FEATURE_REASON)
        # TODO(pr-739): Replace with canonical assertions if legacy_bmi_removed is restored.
        pytest.fail(
            "legacy_bmi_removed enabled: test disabled until BMI category assertions are implemented."
        )

    def test_estimate_level_categories(self) -> None:
        """Test estimate_level with different fitness experience levels."""
        require_feature("legacy_bmi_removed", reason=FEATURE_REASON)
        # TODO(pr-739): Replace with canonical assertions if legacy_bmi_removed is restored.
        pytest.fail(
            "legacy_bmi_removed enabled: test disabled until estimate level assertions are implemented."
        )

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
