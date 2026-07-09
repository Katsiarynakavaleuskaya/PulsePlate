"""Guards for bounded BMI free-form query parsing (CodeQL ReDoS hardening)."""

from __future__ import annotations

from core.bmi.query import _MAX_BMI_QUERY_CHARS, extract_bmi_inputs, render_bmi_query_answer


def test_extract_bmi_inputs_accepts_normal_query() -> None:
    assert extract_bmi_inputs("Calculate BMI for 70kg and 175cm") == (70.0, 1.75)
    assert extract_bmi_inputs("70 кг и 1.75 м") == (70.0, 1.75)


def test_extract_bmi_inputs_rejects_overlong_query() -> None:
    payload = ("0" * (_MAX_BMI_QUERY_CHARS + 1)) + "70kg 175cm"
    assert extract_bmi_inputs(payload) is None


def test_extract_bmi_inputs_handles_repetitive_digits_without_match() -> None:
    # Pathological digit runs must fail closed quickly rather than hang.
    assert extract_bmi_inputs("0" * 200 + " kg") is None
    assert extract_bmi_inputs("70kg " + ("0" * 120) + "cm") is None


def test_render_bmi_query_answer_missing_inputs() -> None:
    assert "send both weight and height" in render_bmi_query_answer("only text", lang="en")
