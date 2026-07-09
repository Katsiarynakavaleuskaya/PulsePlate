"""Guards for bounded BMI free-form query parsing (CodeQL ReDoS hardening)."""

from __future__ import annotations

from core.bmi.query import (
    _MAX_BMI_QUERY_CHARS,
    _MAX_FRACTION_DIGITS,
    _MAX_INTEGER_DIGITS,
    _parse_bounded_number,
    extract_bmi_inputs,
    render_bmi_query_answer,
)


def test_extract_bmi_inputs_accepts_normal_query() -> None:
    assert extract_bmi_inputs("Calculate BMI for 70kg and 175cm") == (70.0, 1.75)
    assert extract_bmi_inputs("70 кг и 1.75 м") == (70.0, 1.75)
    assert extract_bmi_inputs("70,5 кг и 175 см") == (70.5, 1.75)
    assert extract_bmi_inputs("70.25kg and 1.80m") == (70.25, 1.8)


def test_extract_bmi_inputs_skips_invalid_unit_token_then_matches() -> None:
    assert extract_bmi_inputs("I weigh about 3kgs but actually 70kg and 175cm") == (70.0, 1.75)
    assert extract_bmi_inputs("70kgx 175cm") is None


def test_extract_bmi_inputs_rejects_unicode_digits_fail_closed() -> None:
    # Unicode digits must not reach float() or raise; fail closed instead.
    assert extract_bmi_inputs("²kg 175cm") is None
    assert extract_bmi_inputs("70kg ¹⁷⁵cm") is None
    # Mixed Unicode+ASCII numeric tokens must also fail closed (not accept ASCII suffix).
    assert extract_bmi_inputs("¹70kg and 175cm") is None
    assert extract_bmi_inputs("70kg and ¹75cm") is None


def test_extract_bmi_inputs_rejects_overlong_query() -> None:
    payload = ("0" * (_MAX_BMI_QUERY_CHARS + 1)) + "70kg 175cm"
    assert extract_bmi_inputs(payload) is None


def test_extract_bmi_inputs_handles_repetitive_digits_without_match() -> None:
    # Pathological digit runs must fail closed quickly rather than hang.
    assert extract_bmi_inputs("0" * 200 + " kg") is None
    assert extract_bmi_inputs("70kg " + ("0" * 120) + "cm") is None


def test_extract_bmi_inputs_rejects_zero_weight_and_out_of_range_height() -> None:
    assert extract_bmi_inputs("0kg 175cm") is None
    assert extract_bmi_inputs("70kg 40cm") is None
    assert extract_bmi_inputs("70kg 400cm") is None
    assert extract_bmi_inputs("70kg only") is None


def test_parse_bounded_number_rejects_overflow_and_trailing_dot() -> None:
    too_many_int = "1" * (_MAX_INTEGER_DIGITS + 1)
    assert _parse_bounded_number(too_many_int, 0) is None
    too_many_frac = "1." + ("2" * (_MAX_FRACTION_DIGITS + 1))
    assert _parse_bounded_number(too_many_frac, 0) is None
    assert _parse_bounded_number("12.", 0) is None
    assert _parse_bounded_number("abc", 0) is None


def test_extract_bmi_inputs_prefers_earliest_valid_unit_across_aliases() -> None:
    # Both Latin and Cyrillic weight units present; earliest boundary-valid wins.
    assert extract_bmi_inputs("80кг then later 70kg and 175cm") == (80.0, 1.75)


def test_render_bmi_query_answer_missing_and_valid_inputs() -> None:
    assert "send both weight and height" in render_bmi_query_answer("only text", lang="en")
    answer = render_bmi_query_answer("70kg and 175cm", lang="en")
    assert "estimated BMI" in answer
    assert "22.9" in answer or "22." in answer
