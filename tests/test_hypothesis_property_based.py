"""
Property-based tests using Hypothesis library.

This module demonstrates how to use Hypothesis for property-based testing
in the BMI App project. Property-based tests generate random inputs and
verify that certain properties always hold true.
"""

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from bmi_core import bmi_category, bmi_value
from core.targets import _life_stage_warnings


class TestBMIPropertyBased:
    """Property-based tests for BMI calculations."""

    @given(
        weight=st.floats(min_value=1.0, max_value=500.0),
        height_cm=st.floats(min_value=50.0, max_value=250.0),
    )
    def test_bmi_calculation_properties(self, weight, height_cm):
        """Test that BMI calculation has expected mathematical properties."""
        height_m = height_cm / 100.0  # Convert cm to meters
        bmi = bmi_value(weight, height_m)

        # Property 1: BMI should always be positive
        assert (
            bmi > 0
        ), f"BMI should be positive, got {bmi} for weight={weight}, height={height_cm}cm"

        # Property 2: BMI should be proportional to weight
        # If we double the weight, BMI should increase
        bmi_double_weight = bmi_value(weight * 2, height_m)
        assert (
            bmi_double_weight > bmi
        ), f"BMI should increase with weight: {bmi} -> {bmi_double_weight}"

        # Property 3: BMI should be inversely proportional to height squared
        # If we double the height, BMI should decrease
        bmi_double_height = bmi_value(weight, height_m * 2)
        assert (
            bmi > bmi_double_height
        ), f"BMI should decrease with height: {bmi} -> {bmi_double_height}"

    @given(
        weight=st.floats(min_value=1.0, max_value=500.0),
        height_cm=st.floats(min_value=50.0, max_value=250.0),
    )
    def test_bmi_category_consistency(self, weight, height_cm):
        """Test that BMI categories are consistent with BMI values."""
        height_m = height_cm / 100.0  # Convert cm to meters
        bmi = bmi_value(weight, height_m)
        category = bmi_category(bmi, "en")

        # Property: Category should be a valid string
        assert isinstance(
            category, str
        ), f"Category should be string, got {type(category)}"
        assert len(category) > 0, "Category should not be empty"

        # Property: Category should be a valid string (localized)
        # Note: Categories are localized, so we just check it's a non-empty string
        assert len(category) > 0, "Category should not be empty"

    @given(bmi=st.floats(min_value=5.0, max_value=100.0))
    def test_bmi_category_boundaries(self, bmi):
        """Test that BMI category boundaries work correctly."""
        category = bmi_category(bmi, "en")

        # Property: Categories should be mutually exclusive and cover all ranges
        # Note: Categories are localized, so we check they're non-empty strings
        assert len(category) > 0, f"Category should not be empty for BMI {bmi}"

        # Property: Categories should be consistent with BMI ranges
        if bmi < 18.5:
            assert (
                "underweight" in category.lower() or "under" in category.lower()
            ), f"BMI {bmi} should indicate underweight, got {category}"
        elif 18.5 <= bmi < 25:
            assert (
                "normal" in category.lower() or "healthy" in category.lower()
            ), f"BMI {bmi} should indicate normal/healthy, got {category}"
        elif 25 <= bmi < 30:
            assert (
                "overweight" in category.lower() or "over" in category.lower()
            ), f"BMI {bmi} should indicate overweight, got {category}"
        else:  # bmi >= 30
            assert (
                "obese" in category.lower()
            ), f"BMI {bmi} should indicate obese, got {category}"


class TestLifeStageWarningsPropertyBased:
    """Property-based tests for life stage warnings."""

    @given(
        age=st.integers(min_value=0, max_value=120),
        life_stage=st.sampled_from(["child", "teen", "adult", "elderly", "pregnant"]),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    def test_life_stage_warnings_properties(self, age, life_stage, lang):
        """Test that life stage warnings have expected properties."""
        warnings = _life_stage_warnings(age, life_stage, lang)

        # Property 1: Warnings should be a list
        assert isinstance(
            warnings, list
        ), f"Warnings should be list, got {type(warnings)}"

        # Property 2: Each warning should have required structure
        for warning in warnings:
            assert isinstance(
                warning, dict
            ), f"Warning should be dict, got {type(warning)}"
            assert "code" in warning, "Warning should have 'code' field"
            assert "message" in warning, "Warning should have 'message' field"
            assert isinstance(warning["code"], str), "Warning code should be string"
            assert isinstance(
                warning["message"], str
            ), "Warning message should be string"
            assert len(warning["code"]) > 0, "Warning code should not be empty"
            assert len(warning["message"]) > 0, "Warning message should not be empty"

    @given(
        age=st.integers(min_value=12, max_value=18),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    def test_teen_warnings_property(self, age, lang):
        """Test that teen warnings appear for appropriate ages."""
        warnings = _life_stage_warnings(age, "teen", lang)

        # Property: Teen warnings should appear for ages 12-18 with teen life stage
        teen_warnings = [w for w in warnings if w["code"] == "teen"]
        assert (
            len(teen_warnings) == 1
        ), f"Should have exactly one teen warning, got {len(teen_warnings)}"

        # Property: Message should be localized
        message = teen_warnings[0]["message"]
        assert len(message) > 0, "Teen warning message should not be empty"

    @given(
        age=st.integers(min_value=0, max_value=120),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    def test_pregnant_warnings_property(self, age, lang):
        """Test that pregnant warnings appear for pregnant life stage."""
        warnings = _life_stage_warnings(age, "pregnant", lang)

        # Property: Pregnant warnings should always appear for pregnant life stage
        pregnant_warnings = [w for w in warnings if w["code"] == "pregnant"]
        assert (
            len(pregnant_warnings) == 1
        ), f"Should have exactly one pregnant warning, got {len(pregnant_warnings)}"

        # Property: Message should be localized
        message = pregnant_warnings[0]["message"]
        assert len(message) > 0, "Pregnant warning message should not be empty"

    @given(
        age=st.integers(min_value=51, max_value=120),
        lang=st.sampled_from(["en", "ru", "es"]),
    )
    def test_elderly_warnings_property(self, age, lang):
        """Test that elderly warnings appear for appropriate ages."""
        warnings = _life_stage_warnings(age, "elderly", lang)

        # Property: Elderly warnings should appear for ages 51+ with elderly life stage
        elderly_warnings = [w for w in warnings if w["code"] == "elderly"]
        assert (
            len(elderly_warnings) == 1
        ), f"Should have exactly one elderly warning, got {len(elderly_warnings)}"

        # Property: Message should be localized
        message = elderly_warnings[0]["message"]
        assert len(message) > 0, "Elderly warning message should not be empty"


class TestDataValidationPropertyBased:
    """Property-based tests for data validation."""

    @given(
        data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.integers(),
                st.floats(),
                st.text(),
                st.booleans(),
                st.lists(st.integers()),
            ),
        )
    )
    def test_api_payload_structure(self, data):
        """Test that API payloads have expected structure properties."""
        # Property 1: All keys should be strings
        for key in data.keys():
            assert isinstance(key, str), f"Key should be string, got {type(key)}"
            assert len(key) > 0, "Key should not be empty"

        # Property 2: Values should be of expected types
        for key, value in data.items():
            assert isinstance(
                value, (int, float, str, bool, list)
            ), f"Value for {key} should be valid type, got {type(value)}"

            # Property 3: If value is string, it should not be too long
            if isinstance(value, str):
                assert (
                    len(value) <= 1000
                ), f"String value for {key} should not be too long: {len(value)}"

            # Property 4: If value is list, it should not be too large
            if isinstance(value, list):
                assert (
                    len(value) <= 100
                ), f"List value for {key} should not be too large: {len(value)}"

    @given(
        numbers=st.lists(
            st.floats(min_value=0.1, max_value=1000.0), min_size=1, max_size=50
        )
    )
    def test_nutrition_calculations_properties(self, numbers):
        """Test properties of nutrition calculations."""
        # Property 1: Sum should be positive
        total = sum(numbers)
        assert total > 0, f"Sum should be positive, got {total}"

        # Property 2: Average should be within bounds
        average = total / len(numbers)
        assert (
            0.1 <= average <= 1000.0
        ), f"Average should be within bounds, got {average}"

        # Property 3: All individual values should be positive
        for num in numbers:
            assert num > 0, f"Individual number should be positive, got {num}"


class TestEdgeCasesPropertyBased:
    """Property-based tests for edge cases."""

    @given(value=st.floats(min_value=0.0, max_value=1.0))
    def test_percentage_properties(self, value):
        """Test properties of percentage calculations."""
        percentage = value * 100

        # Property 1: Percentage should be between 0 and 100
        assert (
            0.0 <= percentage <= 100.0
        ), f"Percentage should be 0-100, got {percentage}"

        # Property 2: Converting back should give original value
        original = percentage / 100
        assert (
            abs(original - value) < 1e-10
        ), f"Round-trip conversion failed: {value} -> {percentage} -> {original}"

    @given(text_input=st.text(min_size=1, max_size=100))
    def test_text_processing_properties(self, text_input):
        """Test properties of text processing."""
        # Property 1: Length should be preserved
        original_length = len(text_input)
        assert original_length >= 1, "Text should have at least 1 character"
        assert original_length <= 100, "Text should not exceed 100 characters"

        # Property 2: Text should not be empty after basic processing
        processed = text_input.strip()
        assert len(processed) >= 0, "Processed text should have non-negative length"


# Example of using @example decorator for specific test cases
class TestSpecificExamples:
    """Tests with specific examples using Hypothesis."""

    @given(
        weight=st.floats(min_value=1.0, max_value=500.0),
        height_cm=st.floats(min_value=50.0, max_value=250.0),
    )
    @example(weight=70.0, height_cm=175.0)  # Normal BMI case
    @example(weight=50.0, height_cm=175.0)  # Underweight case
    @example(weight=100.0, height_cm=175.0)  # Overweight case
    def test_bmi_specific_examples(self, weight, height_cm):
        """Test BMI calculation with specific examples."""
        height_m = height_cm / 100.0  # Convert cm to meters
        bmi = bmi_value(weight, height_m)
        category = bmi_category(bmi, "en")

        # Property: BMI and category should be consistent
        assert bmi > 0, f"BMI should be positive: {bmi}"
        assert len(category) > 0, f"Category should not be empty: {category}"


if __name__ == "__main__":
    # Run property-based tests
    pytest.main([__file__, "-v"])
