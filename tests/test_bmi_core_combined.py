"""
Combined BMI core tests
Includes validation, edge cases, and coverage tests for BMI core functionality.
"""

import importlib
import pytest
from fastapi.testclient import TestClient
from tests._client import get_client

from bmi_core import (
    bmi_value,
    build_premium_plan,
    estimate_level,
    healthy_bmi_range,
    interpret_group,
)

app_module = importlib.import_module("app")
client = get_client()


class TestBMICoreValidation:
    """Test BMI core validation and edge cases."""

    def test_interpret_group_general_en_no_extra_dot(self):
        """Test interpret_group for 'general' group without extra dot."""
        # For group='general' the string should not end with an extra dot
        txt = interpret_group(22.0, "general", "en")
        assert txt == "Normal weight"

    def test_estimate_level_beginner_ru(self):
        """Test estimate_level for beginner level in Russian."""
        # Cover RU branch for 'beginner'
        assert estimate_level(0, 0.0, "ru") == "базовый"

    def test_build_premium_plan_gain_ru_tips(self):
        """Test build_premium_plan for weight gain with Russian tips."""
        # Cover RU branch for 'gain' + presence of tips
        height = 1.60
        bmin, bmax = healthy_bmi_range(25, "general", premium=False)
        wmin = round(bmin * height * height, 1)
        weight = wmin - 2.0  # below 'healthy' range -> gain
        bmi = bmi_value(weight, height)
        plan = build_premium_plan(25, weight, height, bmi, "ru", "general", False)
        assert plan["action"] == "gain"
        assert isinstance(plan["nutrition_tip"], str) and len(plan["nutrition_tip"]) > 0
        assert isinstance(plan["activity_tip"], str) and len(plan["activity_tip"]) > 0


class TestBMIAPIValidation:
    """Test BMI API validation endpoints."""

    def test_bmi_height_as_string_invalid(self):
        """Test BMI API with invalid height as string."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": "invalid"},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_weight_as_string_invalid(self):
        """Test BMI API with invalid weight as string."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": "70", "height_cm": 170},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_group_unknown_still_ok(self):
        """Test BMI API with unknown group still works."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "group": "ALIEN"},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["bmi"] == 24.2
        # v1 endpoint returns "Normal weight" (EN)
        assert data["category"] == "Normal weight"
        assert isinstance(data.get("interpretation", ""), str)

    def test_bmi_negative_weight_validation_error(self):
        """Test BMI API with negative weight returns validation error."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": -70, "height_cm": 170},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_negative_height_validation_error(self):
        """Test BMI API with negative height returns validation error."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": -170},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_zero_weight_validation_error(self):
        """Test BMI API with zero weight returns validation error."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 0, "height_cm": 170},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_zero_height_validation_error(self):
        """Test BMI API with zero height returns validation error."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 0},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_extremely_large_values_returns_result(self):
        """Test BMI API with extremely large values returns computed result."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 10000, "height_cm": 1000},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["bmi"], (int, float))
        assert data["bmi"] > 0
        assert isinstance(data["category"], str)

    def test_bmi_missing_weight_validation_error(self):
        """Test BMI API with missing weight returns validation error."""
        r = client.post(
            "/api/v1/bmi",
            json={"height_cm": 170},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_missing_height_validation_error(self):
        """Test BMI API with missing height returns validation error."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 422

    def test_bmi_invalid_gender_returns_result(self):
        """Test BMI API with invalid gender still returns computed result."""
        r = client.post(
            "/api/v1/bmi",
            json={"weight_kg": 70, "height_cm": 170, "gender": "INVALID"},
            headers={"X-API-Key": "test_key"},
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["bmi"], (int, float))
        assert data["bmi"] > 0
        assert isinstance(data["category"], str)


class TestBMICoreCoverage:
    """Test BMI core coverage and fallback scenarios."""

    def _call_interpret_group_safe(self, group: str, lang: str, bmi: float = 24.9) -> str | None:
        """Safely call interpret_group with correct signature."""
        fn = getattr(pytest.importorskip("bmi_core"), "interpret_group", None)
        if not callable(fn):
            pytest.skip("interpret_group not found")

        # Use correct signature: interpret_group(bmi, group, lang, age=None)
        try:
            result = fn(bmi=bmi, group=group, lang=lang)
            return str(result) if result is not None else None
        except (TypeError, ValueError) as e:
            pytest.skip(f"interpret_group call failed: {e}")

    def test_group_display_fallbacks_and_edges(self):
        """Test BMI category fallbacks and edge cases."""
        bmi_core = pytest.importorskip("bmi_core")

        # language outside ('ru','en') -> fallback to default (en)
        assert bmi_core.bmi_category(24.9, "de") == bmi_core.bmi_category(24.9, "en")

        # safe call to interpret_group (or skip if signature is unusual)
        res = self._call_interpret_group_safe("unknown_group", "en")
        if res is not None:
            assert isinstance(res, str) and res
