"""
RU: Commit 3 tests — orchestrator calculate_bmi_result().
EN: Commit 3 tests — orchestrator calculate_bmi_result().
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import core.bmi.engine as eng


@dataclass(frozen=True)
class _FakeWaistRisk:
    """Fake WaistRiskResult for testing (isolates from real risk.py)."""

    risk_level: str
    notes: tuple[str, ...]
    wht_ratio: float | None = None


class TestCalculateBMIResultHappyPaths:
    """Happy path tests for orchestrator."""

    def test_calculate_bmi_result_adult_general_happy_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test adult general case with waist risk."""
        # Stub waist risk to keep test deterministic
        # Need to patch the actual import in core.bmi.risk module
        from core.bmi import risk

        def _fake_risk(**kwargs):
            return _FakeWaistRisk("low", ("note-a",), wht_ratio=0.47)

        monkeypatch.setattr(risk, "calculate_waist_risk", _fake_risk)

        res = eng.calculate_bmi_result(
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
        assert res.group == "general"
        assert res.category == "normal"
        assert res.group_display == "General"
        assert "normal" in res.interpretation
        assert res.wht_ratio == 0.47
        assert res.waist_risk is not None
        assert res.notes == ("note-a",)

    def test_calculate_bmi_result_teen_category_none(self) -> None:
        """Test teen group returns category=None."""
        res = eng.calculate_bmi_result(
            weight_kg=60.0,
            height_cm=170.0,
            age=19,
            gender="female",
            pregnant=False,
            athlete=False,
            waist_cm=None,
            hip_cm=None,
            lang="en",
        )
        assert res.group == "teen"
        assert res.category is None
        assert res.interpretation == ""

    def test_calculate_bmi_result_pregnant_female_group(self) -> None:
        """Test pregnant group returns category=None."""
        res = eng.calculate_bmi_result(
            weight_kg=65.0,
            height_cm=170.0,
            age=30,
            gender="female",
            pregnant=True,
            athlete=False,
            waist_cm=None,
            hip_cm=None,
            lang="en",
        )
        assert res.group == "pregnant"
        assert res.category is None

    def test_calculate_bmi_result_elderly_priority_over_pregnant(self) -> None:
        """Test age priority: elderly wins over pregnant."""
        res = eng.calculate_bmi_result(
            weight_kg=65.0,
            height_cm=170.0,
            age=65,
            gender="female",
            pregnant=True,
            athlete=True,
            waist_cm=None,
            hip_cm=None,
            lang="en",
        )
        assert res.group == "elderly"


class TestCalculateBMIResultValidation:
    """Input validation tests (fail-loud)."""

    def test_invalid_weight_raises(self) -> None:
        """Test ValueError for weight <= 0."""
        with pytest.raises(ValueError, match="weight_kg must be positive"):
            eng.calculate_bmi_result(
                weight_kg=0.0,
                height_cm=170.0,
                age=30,
                gender="male",
                pregnant=False,
                athlete=False,
                waist_cm=None,
                hip_cm=None,
                lang="en",
            )

    def test_invalid_height_raises(self) -> None:
        """Test ValueError for height <= 0."""
        with pytest.raises(ValueError, match="height_cm must be positive"):
            eng.calculate_bmi_result(
                weight_kg=70.0,
                height_cm=0.0,
                age=30,
                gender="male",
                pregnant=False,
                athlete=False,
                waist_cm=None,
                hip_cm=None,
                lang="en",
            )

    def test_invalid_age_raises(self) -> None:
        """Test ValueError for age out of bounds."""
        with pytest.raises(ValueError, match="age must be between 1 and 120"):
            eng.calculate_bmi_result(
                weight_kg=70.0,
                height_cm=170.0,
                age=0,
                gender="male",
                pregnant=False,
                athlete=False,
                waist_cm=None,
                hip_cm=None,
                lang="en",
            )

    def test_bmi_bounds_raises_low(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ValueError for BMI < 10."""
        monkeypatch.setattr(eng, "_compute_bmi", lambda w, h: 9.9)
        with pytest.raises(ValueError, match="BMI out of valid range"):
            eng.calculate_bmi_result(
                weight_kg=70.0,
                height_cm=170.0,
                age=30,
                gender="male",
                pregnant=False,
                athlete=False,
                waist_cm=None,
                hip_cm=None,
                lang="en",
            )

    def test_bmi_bounds_raises_high(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test ValueError for BMI > 100."""
        monkeypatch.setattr(eng, "_compute_bmi", lambda w, h: 100.1)
        with pytest.raises(ValueError, match="BMI out of valid range"):
            eng.calculate_bmi_result(
                weight_kg=70.0,
                height_cm=170.0,
                age=30,
                gender="male",
                pregnant=False,
                athlete=False,
                waist_cm=None,
                hip_cm=None,
                lang="en",
            )


class TestCalculateBMIResultWHtRAndRisk:
    """WHtR and waist risk integration tests (fail-soft)."""

    def test_wht_ratio_none_when_invalid_height(self) -> None:
        """Test WHtR returns None for invalid height (fail-soft)."""
        # height_m = 0.49 => _compute_wht_ratio returns None (fail-soft)
        res = eng.calculate_bmi_result(
            weight_kg=10.0,
            height_cm=49.0,
            age=30,
            gender="male",
            pregnant=False,
            athlete=False,
            waist_cm=80.0,
            hip_cm=None,
            lang="en",
        )
        assert res.wht_ratio is None

    def test_waist_risk_none_when_no_waist(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test waist_risk=None when waist_cm is None."""
        # Ensure even if calculate_waist_risk exists somewhere, it won't be called
        from core.bmi import risk

        called = {"n": 0}

        def _fake(**kwargs):
            called["n"] += 1
            return _FakeWaistRisk("low", ("x",))

        monkeypatch.setattr(risk, "calculate_waist_risk", _fake)

        res = eng.calculate_bmi_result(
            weight_kg=70.0,
            height_cm=170.0,
            age=30,
            gender="male",
            pregnant=False,
            athlete=False,
            waist_cm=None,
            hip_cm=None,
            lang="en",
        )
        assert res.waist_risk is None
        assert res.notes == ()
        assert called["n"] == 0

    def test_waist_risk_present_and_notes_propagate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test waist risk integration and notes propagation."""
        from core.bmi import risk

        monkeypatch.setattr(
            risk,
            "calculate_waist_risk",
            lambda **kwargs: _FakeWaistRisk("high", ("risk-note-1", "risk-note-2")),
        )

        res = eng.calculate_bmi_result(
            weight_kg=90.0,
            height_cm=180.0,
            age=30,
            gender="male",
            pregnant=False,
            athlete=False,
            waist_cm=95.0,
            hip_cm=None,
            lang="en",
        )
        assert res.waist_risk is not None
        assert res.notes == ("risk-note-1", "risk-note-2")
        assert "normal" in res.interpretation or "overweight" in res.interpretation

    def test_waist_risk_typeerror_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test TypeError fallback path for calculate_waist_risk (coverage line 437-443)."""
        from core.bmi import risk

        call_count = {"count": 0}

        def _type_error_first(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                # First call with keyword args raises TypeError
                raise TypeError("signature mismatch")
            # Second call with positional args succeeds
            return _FakeWaistRisk("low", ("fallback-note",))

        monkeypatch.setattr(risk, "calculate_waist_risk", _type_error_first)

        res = eng.calculate_bmi_result(
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
        # Should succeed on second try (positional args)
        assert res.waist_risk is not None
        assert call_count["count"] == 2

    def test_waist_risk_exception_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Exception fallback path for calculate_waist_risk (coverage line 445)."""
        from core.bmi import risk

        def _raise_exception(**kwargs):
            raise RuntimeError("risk calculation failed")

        monkeypatch.setattr(risk, "calculate_waist_risk", _raise_exception)

        res = eng.calculate_bmi_result(
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
        # Should fail-soft: waist_risk=None, but BMI calculation succeeds
        assert res.waist_risk is None
        assert res.bmi > 0  # BMI calculation succeeded
        assert res.notes == ()  # No notes when waist_risk fails

    def test_notes_aggregation_filters_non_strings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test notes aggregation filters non-strings (coverage line 452->457)."""
        from core.bmi import risk

        # Create fake risk with mixed notes (strings and non-strings)
        class _MixedNotesRisk:
            notes = ("valid-note", 123, "", "  ", "another-valid")

        monkeypatch.setattr(risk, "calculate_waist_risk", lambda **kwargs: _MixedNotesRisk())

        res = eng.calculate_bmi_result(
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
        # Should filter: only non-empty strings
        assert res.notes == ("valid-note", "another-valid")


class TestPipelineOrderingGuard:
    """Guard test to ensure pipeline ordering is preserved."""

    def test_pipeline_ordering_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that helper functions are called in canonical order."""
        calls: list[str] = []

        def _wrap(name: str, ret):
            def _inner(*args, **kwargs):
                calls.append(name)
                return ret(*args, **kwargs)

            return _inner

        # Wrap helpers to track ordering without changing behavior
        monkeypatch.setattr(eng, "_normalize_lang", _wrap("_normalize_lang", eng._normalize_lang))
        monkeypatch.setattr(
            eng, "_normalize_gender", _wrap("_normalize_gender", eng._normalize_gender)
        )
        monkeypatch.setattr(eng, "_compute_bmi", _wrap("_compute_bmi", eng._compute_bmi))
        monkeypatch.setattr(eng, "_age_band", _wrap("_age_band", eng._age_band))
        monkeypatch.setattr(eng, "_auto_group", _wrap("_auto_group", eng._auto_group))
        monkeypatch.setattr(eng, "_bmi_category", _wrap("_bmi_category", eng._bmi_category))
        monkeypatch.setattr(
            eng, "_group_display_name", _wrap("_group_display_name", eng._group_display_name)
        )
        monkeypatch.setattr(
            eng, "_compute_wht_ratio", _wrap("_compute_wht_ratio", eng._compute_wht_ratio)
        )
        from core.bmi import risk

        monkeypatch.setattr(
            risk,
            "calculate_waist_risk",
            lambda **kwargs: _FakeWaistRisk("low", ()),
        )

        _ = eng.calculate_bmi_result(
            weight_kg=70.0,
            height_cm=170.0,
            age=30,
            gender="male",
            pregnant=False,
            athlete=False,
            waist_cm=80.0,
            hip_cm=None,
            lang=None,
        )

        # Canonical ordering subset (we don't assert exact full list to avoid fragility)
        assert calls.index("_normalize_lang") < calls.index("_normalize_gender")
        assert calls.index("_normalize_gender") < calls.index("_compute_bmi")
        assert calls.index("_compute_bmi") < calls.index("_age_band")
        assert calls.index("_age_band") < calls.index("_auto_group")
        assert calls.index("_auto_group") < calls.index("_bmi_category")
        assert calls.index("_bmi_category") < calls.index("_group_display_name")
        assert calls.index("_group_display_name") < calls.index("_compute_wht_ratio")
