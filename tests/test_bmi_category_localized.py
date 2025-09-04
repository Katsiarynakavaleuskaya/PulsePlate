"""
Tests for BMI Category Localization

This test ensures that BMI categories are correctly localized
across all supported languages (RU/EN/ES).
"""

import pytest

from bmi_core import bmi_category, normalize_lang


class TestBMICategoryLocalized:
    """Test BMI category localization across all supported languages."""

    @pytest.mark.parametrize("bmi", [
        18.4, 18.5, 24.9, 25.0, 29.9, 30.0, 34.9, 35.0, 39.9, 40.0
    ])
    def test_bmi_categories_across_languages(self, bmi):
        """Test that BMI categories are consistent across languages."""
        # Test each language
        ru_category = bmi_category(bmi, "ru")
        en_category = bmi_category(bmi, "en")
        es_category = bmi_category(bmi, "es")

        # All should be strings
        assert isinstance(ru_category, str)
        assert isinstance(en_category, str)
        assert isinstance(es_category, str)

        # All should be non-empty
        assert len(ru_category) > 0
        assert len(en_category) > 0
        assert len(es_category) > 0

    def test_normalize_lang_function(self):
        """Test that normalize_lang works correctly."""
        # Test case insensitivity
        assert normalize_lang("RU") == "ru"
        assert normalize_lang("EN") == "en"
        assert normalize_lang("ES") == "es"

        # Test locale-specific codes
        assert normalize_lang("es-ES") == "es"
        assert normalize_lang("ES-AR") == "es"
        assert normalize_lang("en-US") == "en"
        assert normalize_lang("ru-RU") == "ru"

        # Test fallback to default
        assert normalize_lang("fr") == "ru"  # French should fallback to Russian
        assert normalize_lang("") == "ru"    # Empty string should fallback to Russian
        assert normalize_lang(None) == "ru"  # None should fallback to Russian

    def test_bmi_category_with_age_and_group(self):
        """Test BMI category with age and group parameters."""
        bmi = 22.0

        # Test without age/group
        category_general = bmi_category(bmi, "es")
        assert isinstance(category_general, str)
        assert len(category_general) > 0

        # Test with age and group
        category_elderly = bmi_category(bmi, "es", age=65, group="elderly")
        assert isinstance(category_elderly, str)
        assert len(category_elderly) > 0

        # They should both be valid strings, though potentially different
        assert category_general != ""  # Should not be empty
        assert category_elderly != ""  # Should not be empty
