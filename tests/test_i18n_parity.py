"""
Tests for i18n Parity Across Languages

This test ensures that all translation keys are present in all languages
and that the i18n system works consistently across RU/EN/ES.
"""

import pytest

from core.i18n import TRANSLATIONS, t, validate_translation_key


class TestI18nParity:
    """Test i18n parity across all supported languages."""

    def test_all_languages_have_same_keys(self):
        """Test that all languages have the same translation keys."""
        languages = list(TRANSLATIONS.keys())
        assert len(languages) == 3, "Expected exactly 3 languages (ru, en, es)"

        # Get the set of keys for each language
        key_sets = [set(TRANSLATIONS[lang].keys()) for lang in languages]

        # Check that all key sets are identical
        for i in range(1, len(key_sets)):
            assert key_sets[0] == key_sets[i], f"Keys differ between {languages[0]} and {languages[i]}"

    def test_translation_function_works_for_all_languages(self):
        """Test that the translation function works for all languages."""
        # Test a few key translations
        test_keys = ["bmi_underweight", "form_weight", "risk_high_health"]

        for key in test_keys:
            # Test that each language has the key
            assert t("ru", key) is not None
            assert t("en", key) is not None
            assert t("es", key) is not None

    def test_validate_translation_key_function(self):
        """Test that validate_translation_key works correctly."""
        # Test with a valid key
        assert validate_translation_key("bmi_underweight")
        
        # Test with an invalid key
        assert not validate_translation_key("non_existent_key")

    def test_all_keys_present_in_all_languages(self):
        """Test that every key in one language is present in all others."""
        # Get all keys from the first language (Russian)
        ru_keys = set(TRANSLATIONS["ru"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())
        es_keys = set(TRANSLATIONS["es"].keys())

        # Check that all keys are present in all languages
        missing_in_en = ru_keys - en_keys
        missing_in_es = ru_keys - es_keys

        assert len(missing_in_en) == 0, f"Keys missing in English: {missing_in_en}"
        assert len(missing_in_es) == 0, f"Keys missing in Spanish: {missing_in_es}"

        # Also check the reverse - no extra keys in other languages
        extra_in_en = en_keys - ru_keys
        extra_in_es = es_keys - ru_keys

        assert len(extra_in_en) == 0, f"Extra keys in English: {extra_in_en}"
        assert len(extra_in_es) == 0, f"Extra keys in Spanish: {extra_in_es}"
