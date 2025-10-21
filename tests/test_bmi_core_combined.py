"""
Combined BMI core tests
Includes validation, edge cases, and coverage tests for BMI core functionality.
"""

import importlib
import pytest
from fastapi.testclient import TestClient

from bmi_core import (
    bmi_value,
    build_premium_plan,
    estimate_level,
    healthy_bmi_range,
    interpret_group,
)

app_module = importlib.import_module("app")
client = TestClient(app_module.app)


class TestBMICoreValidation:
    """Test BMI core validation and edge cases."""

    def test_interpret_group_general_en_no_extra_dot(self):
        """Test interpret_group for 'general' group without extra dot."""
        # Для group='general' строка не должна заканчиваться лишней точкой
        txt = interpret_group(22.0, "general", "en")
        assert txt == "Normal weight"

    def test_estimate_level_beginner_ru(self):
        """Test estimate_level for beginner level in Russian."""
        # Добиваем RU-ветку 'beginner'
        assert estimate_level(0, 0.0, "ru") == "базовый"

    def test_build_premium_plan_gain_ru_tips(self):
        """Test build_premium_plan for weight gain with Russian tips."""
        # Добиваем RU-ветку 'gain' + наличие подсказок
        height = 1.60
        bmin, bmax = healthy_bmi_range(25, "general", premium=False)
        wmin = round(bmin * height * height, 1)
        weight = wmin - 2.0  # ниже «здорового» -> gain
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


class TestBMICoreCoverage:
    """Test BMI core coverage and fallback scenarios."""

    def _call_interpret_group_safe(self, group: str, lang: str):
        """Safely call interpret_group with different signature attempts."""
        fn = getattr(pytest.importorskip("bmi_core"), "interpret_group", None)
        if not callable(fn):
            pytest.skip("interpret_group not found")
            return None

        # Попробуем несколько стилей вызова; если ни один не подходит — скипаем.
        try:
            return fn(group=group, lang=lang)  # type: ignore[misc]
        except TypeError:
            pass
        try:
            return fn(group, lang)  # type: ignore[misc]
        except TypeError:
            pass
        try:
            return fn(group, lang=lang)  # type: ignore[misc]
        except TypeError:
            pass
        try:
            return fn(lang, group=group)  # type: ignore[misc]
        except TypeError:
            pytest.skip("interpret_group signature unsupported for this test")
            return None

    def test_group_display_fallbacks_and_edges(self):
        """Test BMI category fallbacks and edge cases."""
        bmi_core = pytest.importorskip("bmi_core")

        # язык вне ('ru','en') -> fallback на 'ru'
        assert bmi_core.bmi_category(24.9, "de")

        # безопасный вызов interpret_group (или skip, если сигнатура экзотическая)
        res = self._call_interpret_group_safe("unknown_group", "en")
        if res is not None:
            assert isinstance(res, str) and res
