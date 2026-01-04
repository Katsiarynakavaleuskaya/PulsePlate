"""
RU: Тесты для helper функций BMI engine (Commit 1).
EN: Tests for BMI engine helper functions (Commit 1).

PR-455: Helper functions parity tests.
"""

from __future__ import annotations

import pytest

from core.bmi.engine import (
    _age_band,
    _compute_bmi,
    _compute_wht_ratio,
    _group_display_name,
    _normalize_bool_flag,
    _normalize_gender,
    _normalize_lang,
    calculate_bmi_result,
)


class TestNormalizeGender:
    """Tests for _normalize_gender() with legacy parity."""

    def test_female_variants(self) -> None:
        """Test female gender normalization with startswith parity."""
        assert _normalize_gender("female") == "female"
        assert _normalize_gender("жен") == "female"
        assert _normalize_gender("женский") == "female"  # startswith parity
        assert _normalize_gender("женщина") == "female"  # startswith parity
        assert _normalize_gender("mujer") == "female"
        assert _normalize_gender("mujeres") == "female"  # startswith parity

    def test_male_variants(self) -> None:
        """Test male gender normalization."""
        assert _normalize_gender("male") == "male"
        assert _normalize_gender("муж") == "male"
        assert _normalize_gender("мужской") == "male"  # startswith parity
        assert _normalize_gender("hombre") == "male"  # ES startswith parity
        assert _normalize_gender("hombrecito") == "male"  # ES startswith parity

    def test_fallback_to_male(self) -> None:
        """Test fallback to 'male' for unknown values."""
        assert _normalize_gender("unknown") == "male"
        assert _normalize_gender("") == "male"
        assert _normalize_gender("   ") == "male"

    def test_none_input_handling(self) -> None:
        """Test None input handling (defensive helper)."""
        assert _normalize_gender(None) == "male"  # None → "" → "male"


class TestNormalizeBoolFlag:
    """Tests for _normalize_bool_flag() with default yes values."""

    def test_yes_values(self) -> None:
        """Test default yes values (no regex in Commit 1)."""
        assert _normalize_bool_flag("yes") is True
        assert _normalize_bool_flag("y") is True
        assert _normalize_bool_flag("true") is True
        assert _normalize_bool_flag("1") is True
        assert _normalize_bool_flag("да") is True
        assert _normalize_bool_flag("д") is True
        assert _normalize_bool_flag("истина") is True
        assert _normalize_bool_flag("si") is True
        assert _normalize_bool_flag("sí") is True

    def test_no_values(self) -> None:
        """Test no/false values."""
        assert _normalize_bool_flag("no") is False
        assert _normalize_bool_flag("false") is False
        assert _normalize_bool_flag("0") is False
        assert _normalize_bool_flag("") is False

    def test_bool_input(self) -> None:
        """Test bool input passthrough."""
        assert _normalize_bool_flag(True) is True
        assert _normalize_bool_flag(False) is False

    def test_non_string_non_bool_returns_false(self) -> None:
        """Test defensive behavior for non-str, non-bool inputs."""
        assert _normalize_bool_flag(None) is False  # type: ignore[arg-type]
        assert _normalize_bool_flag(123) is False  # type: ignore[arg-type]

    def test_custom_yes_values(self) -> None:
        """Test custom yes_values parameter."""
        custom = {"custom_yes", "ok"}
        assert _normalize_bool_flag("custom_yes", yes_values=custom) is True
        assert _normalize_bool_flag("yes", yes_values=custom) is False

    def test_whitespace_and_case_handling(self) -> None:
        """Test whitespace and case normalization."""
        # Whitespace trimming
        assert _normalize_bool_flag(" Yes ") is True
        assert _normalize_bool_flag(" TRUE ") is True
        assert _normalize_bool_flag(" Sí ") is True
        # Case insensitive
        assert _normalize_bool_flag("YES") is True
        assert _normalize_bool_flag("True") is True
        assert _normalize_bool_flag("ДА") is True
        # Custom yes_values with case
        custom = {"ok"}
        assert _normalize_bool_flag("OK", yes_values=custom) is True
        assert _normalize_bool_flag(" Ok ", yes_values=custom) is True


class TestNormalizeLang:
    """Tests for _normalize_lang() using core.i18n.normalize_lang()."""

    def test_base_languages(self) -> None:
        """Test base language codes."""
        assert _normalize_lang("ru") == "ru"
        assert _normalize_lang("en") == "en"
        assert _normalize_lang("es") == "es"

    def test_locale_fallbacks(self) -> None:
        """Test locale fallback logic (via core.i18n)."""
        assert _normalize_lang("en-US") == "en"
        assert _normalize_lang("es-MX") == "es"
        # es-ES → "en" per core/i18n.py LANG_ALIASES (market-based strategy)
        assert _normalize_lang("es-ES") == "en"

    def test_unknown_language_fallback(self) -> None:
        """Test fallback to 'en' for unknown languages."""
        assert _normalize_lang("fr") == "en"
        assert _normalize_lang("unknown") == "en"
        assert _normalize_lang("") == "en"

    def test_whitespace_and_case_handling(self) -> None:
        """Test whitespace and case normalization."""
        # Whitespace trimming (via core.i18n.normalize_lang)
        assert _normalize_lang(" EN-us ") == "en"
        assert _normalize_lang("Es-mx") == "es"
        assert _normalize_lang(" ru ") == "ru"
        # Case insensitive
        assert _normalize_lang("EN") == "en"
        assert _normalize_lang("ES") == "es"
        assert _normalize_lang("RU") == "ru"


class TestAgeBand:
    """Tests for _age_band() with boundary parity."""

    def test_too_young(self) -> None:
        """Test too_young band (age < 12)."""
        assert _age_band(0) == "too_young"
        assert _age_band(11) == "too_young"

    def test_child(self) -> None:
        """Test child band (12 <= age < 13)."""
        assert _age_band(12) == "child"

    def test_teen(self) -> None:
        """Test teen band (13 <= age <= 19), age 19 inclusive."""
        assert _age_band(13) == "teen"
        assert _age_band(16) == "teen"
        assert _age_band(19) == "teen"  # Critical: 19 is teen, not adult

    def test_adult(self) -> None:
        """Test adult band (19 < age < 60), starts at 20."""
        assert _age_band(20) == "adult"
        assert _age_band(30) == "adult"
        assert _age_band(59) == "adult"

    def test_elderly(self) -> None:
        """Test elderly band (age >= 60)."""
        assert _age_band(60) == "elderly"
        assert _age_band(65) == "elderly"
        assert _age_band(120) == "elderly"


class TestComputeBMI:
    """Tests for _compute_bmi() with rounding parity."""

    def test_basic_calculation(self) -> None:
        """Test basic BMI calculation."""
        assert _compute_bmi(70.0, 1.70) == 24.2
        assert _compute_bmi(80.0, 1.80) == 24.7

    def test_rounding_to_one_decimal(self) -> None:
        """Test rounding to 1 decimal place (legacy parity)."""
        # 70 / (1.70 ** 2) = 24.221453287197235 → 24.2
        assert _compute_bmi(70.0, 1.70) == 24.2
        # 75 / (1.75 ** 2) = 24.489795918367346 → 24.5
        assert _compute_bmi(75.0, 1.75) == 24.5

    def test_validation_raises_valueerror(self) -> None:
        """Test validation raises ValueError for invalid inputs."""
        with pytest.raises(ValueError, match="weight_kg must be positive"):
            _compute_bmi(0.0, 1.70)
        with pytest.raises(ValueError, match="weight_kg must be positive"):
            _compute_bmi(-1.0, 1.70)
        with pytest.raises(ValueError, match="height_m must be positive"):
            _compute_bmi(70.0, 0.0)
        with pytest.raises(ValueError, match="height_m must be positive"):
            _compute_bmi(70.0, -1.0)


class TestComputeWhtRatio:
    """Tests for _compute_wht_ratio() with fail-soft parity."""

    def test_basic_calculation(self) -> None:
        """Test basic WHtR calculation."""
        # 80 / 100 / 1.70 = 0.470588... → 0.47
        assert _compute_wht_ratio(80.0, 1.70) == 0.47
        # 90 / 100 / 1.80 = 0.5 → 0.5
        assert _compute_wht_ratio(90.0, 1.80) == 0.5

    def test_rounding_to_two_decimals(self) -> None:
        """Test rounding to 2 decimal places."""
        # 85 / 100 / 1.75 = 0.485714... → 0.49
        assert _compute_wht_ratio(85.0, 1.75) == 0.49

    def test_none_for_none_waist(self) -> None:
        """Test None return for None waist_cm."""
        assert _compute_wht_ratio(None, 1.70) is None

    def test_fail_soft_height_validation(self) -> None:
        """Test fail-soft behavior for invalid height (legacy parity)."""
        assert _compute_wht_ratio(80.0, 0.49) is None  # < 0.5
        assert _compute_wht_ratio(80.0, 0.5) is None  # <= 0.5 (boundary excluded)
        assert _compute_wht_ratio(80.0, 0.51) == 1.57  # > 0.5, valid
        assert _compute_wht_ratio(80.0, 3.0) == 0.27  # <= 3.0, valid
        assert _compute_wht_ratio(80.0, 3.01) is None  # > 3.0

    def test_overflow_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        RU: OverflowError при приведении очень большого int к float → None (fail-soft).
        EN: OverflowError during huge int→float conversion → None (fail-soft).
        """
        import core.bmi.engine as engine

        monkeypatch.setattr(engine, "_MAX_WAIST_CM", 10**2000)
        assert engine._compute_wht_ratio(10**1000, 1.0) is None  # type: ignore[arg-type]

    def test_fail_soft_waist_validation(self) -> None:
        """Test fail-soft behavior for invalid waist (legacy parity)."""
        assert _compute_wht_ratio(0.0, 1.70) is None  # <= 0
        assert _compute_wht_ratio(-1.0, 1.70) is None  # < 0
        assert _compute_wht_ratio(300.0, 1.70) == 1.76  # boundary
        assert _compute_wht_ratio(301.0, 1.70) is None  # > 300.0

    def test_normal_case_smoke(self) -> None:
        """Test normal WHtR scenario returns rounded ratio."""
        assert _compute_wht_ratio(1.0, 1.0) == 0.01


def test_group_display_name_fallback_for_unknown_group() -> None:
    """Verify unknown group names are returned unchanged."""
    assert _group_display_name("not_a_real_group", "en") == "not_a_real_group"  # type: ignore[arg-type]


def test_waist_risk_fallback_signature_drift_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _legacy_calculate_waist_risk(a: float, b: float, c: str, d: str) -> object:
        raise RuntimeError("legacy signature failure")

    import core.bmi.risk as risk

    monkeypatch.setattr(risk, "calculate_waist_risk", _legacy_calculate_waist_risk, raising=True)

    result = calculate_bmi_result(
        weight_kg=70.0,
        height_cm=170.0,
        age=30,
        gender="male",
        pregnant=False,
        athlete=False,
        waist_cm=80.0,
        lang="en",
    )

    assert result.waist_risk is None
    assert result.notes == ()
