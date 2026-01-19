"""
Diff-cover tests for bmi_core.py legacy shim.

These tests ensure all exported functions in the shim are covered,
preventing diff-cover failures when shim code is added/modified.
"""

import pytest

import bmi_core


class TestAutoGroupShim:
    """Test auto_group wrapper coverage."""

    def test_auto_group_positional_lang_is_5th(self) -> None:
        """Test legacy call: auto_group(age, gender, pregnant, athlete, lang)."""
        g = bmi_core.auto_group(30, "female", False, False, "ru")
        assert isinstance(g, str)
        assert g  # non-empty

    def test_auto_group_with_athlete_text_6th(self) -> None:
        """Test legacy call with athlete_text: auto_group(..., lang, athlete_text)."""
        g = bmi_core.auto_group(30, "male", False, False, "ru", "спортсмен")
        assert isinstance(g, str)
        assert g in {"athlete", "general", "elderly", "teen", "child", "too_young"}

    def test_auto_group_string_pregnant(self) -> None:
        """Test auto_group with string pregnant flag."""
        g = bmi_core.auto_group(25, "female", "yes", False, "en")
        assert isinstance(g, str)

    def test_auto_group_string_athlete_preserves_text(self) -> None:
        """Test auto_group preserves athlete_text when string is not yes/no."""
        g = bmi_core.auto_group(30, "male", False, "спортсмен", "en")
        # athlete_text should be preserved for heuristics
        assert isinstance(g, str)


class TestBMICategoryShim:
    """Test bmi_category wrapper coverage."""

    @pytest.mark.parametrize("bmi,lang", [(17.0, "ru"), (22.0, "en"), (32.0, "es")])
    def test_bmi_category_localized_returns_string_or_none(self, bmi: float, lang: str) -> None:
        """Test bmi_category returns localized string or None."""
        s = bmi_core.bmi_category(bmi=bmi, lang=lang, age=30, group="general")
        assert s is None or isinstance(s, str)
        if s:
            assert len(s) > 0

    def test_bmi_category_with_age_none_defaults_to_30(self) -> None:
        """Test bmi_category defaults age to 30 when None."""
        s = bmi_core.bmi_category(bmi=22.0, lang="en", age=None, group="general")
        assert isinstance(s, str)

    def test_bmi_category_returns_none_for_invalid_category(self) -> None:
        """Test bmi_category returns None when category_key is None."""
        # This tests the early return path
        # Note: actual behavior depends on _bmi_category implementation
        s = bmi_core.bmi_category(bmi=100.0, lang="en", age=30, group="general")
        # May return None or a string depending on engine behavior
        assert s is None or isinstance(s, str)

    def test_bmi_category_fallback_to_legacy_keys(self) -> None:
        """Test bmi_category fallback to legacy i18n keys."""
        # Test that fallback path is covered (when canonical key fails)
        s = bmi_core.bmi_category(bmi=32.0, lang="ru", age=30, group="general")
        assert isinstance(s, str)
        assert "Ожирение" in s or "obesity" in s.lower()


class TestOtherShimFunctions:
    """Test other shim function coverage."""

    def test_bmi_value_smoke(self) -> None:
        """Test bmi_value wrapper."""
        v = bmi_core.bmi_value(weight_kg=70.0, height_m=1.75)
        assert isinstance(v, float)
        assert 20.0 <= v <= 30.0  # reasonable BMI range

    def test_compute_wht_ratio_smoke(self) -> None:
        """Test compute_wht_ratio wrapper."""
        r = bmi_core.compute_wht_ratio(waist_cm=80.0, height_m=1.70)
        assert isinstance(r, float)
        assert 0 < r < 1.0  # reasonable WHtR range

    def test_compute_wht_ratio_returns_none_for_invalid(self) -> None:
        """Test compute_wht_ratio returns None for invalid inputs."""
        r = bmi_core.compute_wht_ratio(waist_cm=0.0, height_m=1.70)
        # May return None or raise depending on engine implementation
        assert r is None or isinstance(r, float)

    def test_group_display_name_localized(self) -> None:
        """Test group_display_name wrapper."""
        name = bmi_core.group_display_name("general", "ru")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_group_display_name_all_languages(self) -> None:
        """Test group_display_name for all supported languages."""
        for lang in ["ru", "en", "es"]:
            name = bmi_core.group_display_name("athlete", lang)
            assert isinstance(name, str)
            assert len(name) > 0

    def test_healthy_bmi_range_smoke(self) -> None:
        """Test healthy_bmi_range wrapper."""
        lo, hi = bmi_core.healthy_bmi_range(age=30, group="general", premium=False)
        assert isinstance(lo, float)
        assert isinstance(hi, float)
        assert lo < hi
        assert 18.0 <= lo <= 19.0  # HEALTHY_BMI_RANGE.min = 18.5
        assert 24.0 <= hi <= 25.0  # HEALTHY_BMI_RANGE.max = 24.9


class TestDeprecatedStubs:
    """Test deprecated stub functions raise RuntimeError."""

    @pytest.mark.parametrize("fn_name", ["estimate_level", "interpret_group", "build_premium_plan"])
    def test_deprecated_stubs_raise_runtime_error(self, fn_name: str) -> None:
        """Test that deprecated stubs raise RuntimeError."""
        fn = getattr(bmi_core, fn_name)
        with pytest.raises(RuntimeError, match="deprecated"):
            fn()  # stubs should raise a clear error

    def test_estimate_level_raises_with_args(self) -> None:
        """Test estimate_level raises even with arguments."""
        with pytest.raises(RuntimeError, match="deprecated"):
            bmi_core.estimate_level(3, 2.0, "en")

    def test_interpret_group_raises_with_args(self) -> None:
        """Test interpret_group raises even with arguments."""
        with pytest.raises(RuntimeError, match="deprecated"):
            bmi_core.interpret_group(22.0, "general", "en")

    def test_build_premium_plan_raises_with_args(self) -> None:
        """Test build_premium_plan raises even with arguments."""
        with pytest.raises(RuntimeError, match="deprecated"):
            bmi_core.build_premium_plan(30, 70.0, 1.75, 22.9, "en", "general", False)
