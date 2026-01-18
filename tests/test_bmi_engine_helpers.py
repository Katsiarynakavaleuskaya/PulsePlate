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
    _compute_whr,
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
        # Product policy: ES locales normalize to "es"
        assert _normalize_lang("es-ES") == "es"

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

    def test_overflow_returns_none(self) -> None:
        """
        RU: Controlled overflow в Decimal ratio → None (fail-soft).
        EN: Controlled overflow in Decimal ratio → None (fail-soft).

        Deterministic strategy: local Decimal context with small Emax/Emin and Overflow trap.
        Guaranteed overflow: Decimal("1e10") / Decimal("1e-10") = 1e20 > Emax=9.

        Test verifies:
        1. Context is explicitly set (Emax=9, Emin=-9, traps[Overflow]=True)
        2. Direct division raises Overflow in this context (deterministic)
        3. Helper catches overflow and returns None (fail-soft)
        """
        import decimal
        from decimal import Decimal

        import core.bmi.engine as engine

        # Explicit context setup: small Emax ensures deterministic overflow
        with decimal.localcontext() as ctx:
            ctx.Emax = 9
            ctx.Emin = -9
            ctx.traps[decimal.Overflow] = True

            # Verify context is active: direct division should raise Overflow
            numer = Decimal("1e10")
            denom = Decimal("1e-10")
            # This division in this context will overflow: 1e20 > Emax=9
            # If traps[Overflow] = True, this raises; helper catches it
            with pytest.raises(decimal.Overflow):
                _ = numer / denom  # Direct division should overflow in this context

            # Now test helper: should catch overflow and return None
            result = engine._safe_ratio_decimal(numer=numer, denom=denom)

        assert result is None

    def test_safe_ratio_decimal_zero_denom_returns_none(self) -> None:
        """
        RU: Zero denominator в _safe_ratio_decimal → None (covers line 192).
        EN: Zero denominator in _safe_ratio_decimal → None (covers line 192).
        """
        from decimal import Decimal

        import core.bmi.engine as engine

        result = engine._safe_ratio_decimal(numer=Decimal("10"), denom=Decimal("0"))
        assert result is None

    def test_safe_ratio_decimal_non_finite_returns_none(self) -> None:
        """
        RU: Non-finite Decimal result → None (covers lines 194-196).
        EN: Non-finite Decimal result → None (covers lines 194-196).

        Test strategy: Create non-finite Decimal via division that produces inf/nan.
        """
        from decimal import Decimal

        import core.bmi.engine as engine

        # Division that produces inf (large numerator, small denominator)
        # Note: Decimal("inf") / Decimal("1") = Decimal("Infinity")
        numer = Decimal("inf")
        denom = Decimal("1")
        result = engine._safe_ratio_decimal(numer=numer, denom=denom)
        assert result is None

        # NaN case
        numer_nan = Decimal("nan")
        result_nan = engine._safe_ratio_decimal(numer=numer_nan, denom=denom)
        assert result_nan is None

    def test_fail_soft_waist_validation(self) -> None:
        """Test fail-soft behavior for invalid waist (legacy parity)."""
        assert _compute_wht_ratio(0.0, 1.70) is None  # <= 0
        assert _compute_wht_ratio(-1.0, 1.70) is None  # < 0
        assert _compute_wht_ratio(300.0, 1.70) == 1.76  # boundary (300/100/1.70 = 1.764... → 1.76)
        assert _compute_wht_ratio(301.0, 1.70) is None  # > 300.0

    def test_normal_case_smoke(self) -> None:
        """Test normal WHtR scenario returns rounded ratio."""
        assert _compute_wht_ratio(1.0, 1.0) == 0.01

    def test_non_finite_ratio_returns_none(self) -> None:
        """
        RU: Non-finite ratio (inf/nan) → None (fail-soft).
        EN: Non-finite ratio (inf/nan) → None (fail-soft).

        Test strategy: Create non-finite ratio via inputs (waist_cm=inf/nan),
        not by patching builtins (forbidden in Py3.13+).
        This covers line 203 in core/bmi/engine.py.
        """
        import math

        # INF ratio: waist is +inf, height finite positive
        assert _compute_wht_ratio(waist_cm=math.inf, height_m=1.70) is None

        # NAN ratio: waist is NaN, height finite positive
        assert _compute_wht_ratio(waist_cm=math.nan, height_m=1.70) is None

    def test_wht_ratio_exception_handling_returns_none(self) -> None:
        """
        RU: Exception handling в _compute_wht_ratio → None (covers lines 227, 230).
        EN: Exception handling in _compute_wht_ratio → None (covers lines 227, 230).

        Test strategy: Use an input object that raises OverflowError during division
        (no monkeypatching builtins or core compute functions).
        """
        from typing import cast

        import core.bmi.engine as engine

        class _ExplodingWaist:
            def __le__(self, other: object) -> bool:
                return False

            def __gt__(self, other: object) -> bool:
                return False

            def __truediv__(self, other: object) -> float:
                raise OverflowError("overflow")

        result = engine._compute_wht_ratio(waist_cm=cast(float, _ExplodingWaist()), height_m=1.70)
        assert result is None


class TestComputeWhr:
    """Tests for _compute_whr() with fail-soft parity."""

    def test_basic_calculation(self) -> None:
        """Test basic WHR calculation."""
        # 80 / 100 = 0.8
        assert _compute_whr(80.0, 100.0) == 0.8
        # 90 / 95 = 0.947... → 0.95 (rounded)
        assert _compute_whr(90.0, 95.0) == 0.95

    def test_rounding_to_two_decimals(self) -> None:
        """Test rounding to 2 decimal places."""
        # 85 / 100 = 0.85
        assert _compute_whr(85.0, 100.0) == 0.85
        # 75 / 100 = 0.75
        assert _compute_whr(75.0, 100.0) == 0.75

    def test_none_for_missing_inputs(self) -> None:
        """Test None return for missing waist or hip."""
        assert _compute_whr(None, 100.0) is None
        assert _compute_whr(80.0, None) is None
        assert _compute_whr(None, None) is None

    def test_fail_soft_validation(self) -> None:
        """Test fail-soft behavior for invalid values."""
        assert _compute_whr(0.0, 100.0) is None  # waist <= 0
        assert _compute_whr(-1.0, 100.0) is None  # waist < 0
        assert _compute_whr(80.0, 0.0) is None  # hip <= 0
        assert _compute_whr(80.0, -1.0) is None  # hip < 0

    def test_zero_division_handling(self) -> None:
        """Test that zero division is handled gracefully."""
        # hip_cm > 0 is validated by Pydantic, but guard remains for safety
        assert _compute_whr(80.0, 0.0) is None

    def test_overflow_handling(self) -> None:
        """Test that OverflowError is handled gracefully."""
        from typing import cast

        import core.bmi.engine as engine

        class _ExplodingWaist:
            def __le__(self, other: object) -> bool:
                return False

            def __truediv__(self, other: object) -> float:
                raise OverflowError("overflow")

        result = engine._compute_whr(cast(float, _ExplodingWaist()), 100.0)
        assert result is None


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
        hip_cm=None,
        lang="en",
    )

    assert result.waist_risk is None
    assert result.notes == ()


class TestBMIBreakpointsFallback:
    """
    RU: Тесты для fallback-логики _get_bmi_breakpoints (defensive branches).
    EN: Tests for _get_bmi_breakpoints fallback logic (defensive branches).

    These tests cover defensive fallback branches that ensure robustness
    when registry lookups fail (missing age_band/group combinations).
    """

    def test_fallback_to_age_band_general(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        RU: Покрывает ветку fallback (age_band, "general") в _get_bmi_breakpoints().
        EN: Covers (age_band, "general") fallback branch in _get_bmi_breakpoints().

        Test strategy:
        - Inject synthetic age_band "adult2" with only ("adult2", "general") in registry
        - Request ("adult2", "athlete") which doesn't exist
        - Should fallback to ("adult2", "general") → covers line 258
        """
        from typing import Any

        import core.bmi.engine as eng

        # Copy current registry and inject a synthetic age_band
        patched: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined, unused-ignore]

        # Provide only (adult2, general), but request (adult2, athlete)
        patched[("adult2", "general")] = patched[("adult", "general")]
        monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", patched)

        bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]  # Synthetic age_band for test
        assert bp == patched[("adult", "general")]
        assert len(bp) == 6

    def test_final_fallback_to_adult_general(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        RU: Покрывает финальный fallback ("adult","general") в _get_bmi_breakpoints().
        EN: Covers final ("adult","general") fallback branch in _get_bmi_breakpoints().

        Test strategy:
        - Use synthetic age_band "adult2" with NO entries in registry
        - Request ("adult2", "athlete") which doesn't exist
        - Should fallback to ("adult2", "general") which also doesn't exist
        - Should use final fallback ("adult", "general") → covers line 261
        """
        from typing import Any

        import core.bmi.engine as eng

        # Copy registry, but DO NOT define (adult2, general)
        patched: dict[tuple[Any, Any], Any] = dict(eng._BMI_BREAKPOINTS)  # type: ignore[attr-defined, unused-ignore]
        monkeypatch.setattr(eng, "_BMI_BREAKPOINTS", patched)

        bp = eng._get_bmi_breakpoints("adult2", "athlete")  # type: ignore[arg-type]  # Synthetic age_band for test
        assert bp == patched[("adult", "general")]
        assert len(bp) == 6
        # Verify it's actually adult/general thresholds (25.0 normal_max)
        assert bp[1][0] == 25.0  # adult normal_max


class TestBMIUpperFor:
    """
    RU: Тесты для _upper_for() (извлечение верхних границ из breakpoints).
    EN: Tests for _upper_for() (extracting upper bounds from breakpoints).
    """

    def test_raises_when_missing_category(self) -> None:
        """
        RU: Покрывает raise ValueError в _upper_for() когда категория отсутствует.
        EN: Covers raise ValueError in _upper_for() when category is missing.

        Test strategy:
        - Provide breakpoints without "normal" category
        - Request "normal" → should raise ValueError → covers line 361
        """
        from core.bmi.engine import _upper_for

        breakpoints = [
            (18.5, "underweight"),
            (25.0, "overweight"),  # intentionally missing "normal"
            (float("inf"), "obesity_3"),
        ]
        with pytest.raises(ValueError, match="Missing breakpoint"):
            _upper_for(breakpoints, "normal")  # type: ignore[arg-type]  # Intentionally missing category for test
