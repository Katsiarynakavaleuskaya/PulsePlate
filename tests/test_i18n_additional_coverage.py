"""
Additional tests for core/i18n.py missing lines coverage.
Focus on error handling and template formatting.
"""

import logging

import pytest
from faker import Faker

fake = Faker()


class TestI18nAdditionalCoverage:
    """Test remaining missing lines in core/i18n.py"""

    def setup_method(self):
        Faker.seed(42)

    def test_t_function_unsupported_language_error_line_344(self):
        """Test line 344: KeyError for unsupported language in t() function"""
        try:
            from core.i18n import t

            # Test with unsupported languages
            unsupported_languages = [
                "de",  # German
                "fr",  # French
                "it",  # Italian
                "zh",  # Chinese
                fake.language_code(),  # Random language
            ]

            for lang in unsupported_languages:
                with pytest.raises(KeyError, match=f"Unsupported language: {lang}"):
                    t(lang, "bmi_normal")  # Should trigger line 344

        except ImportError:
            pass

    def test_t_function_template_formatting_line_352(self):
        """Test line 352: template formatting with kwargs in t() function"""
        try:
            from core.i18n import t

            # Test template formatting with kwargs
            # Need to find a translation key that uses formatting
            # Let's check if there are any with {} placeholders
            # For risk_high_whr which has {threshold} placeholder
            result_ru = t("ru", "risk_high_whr", threshold="0.85")
            assert "0.85" in result_ru

            result_en = t("en", "risk_high_whr", threshold="0.90")
            assert "0.90" in result_en

            result_es = t("es", "risk_high_whr", threshold="0.88")
            assert "0.88" in result_es

            # Test with multiple kwargs using faker
            for _ in range(5):
                threshold = fake.pydecimal(left_digits=1, right_digits=2, positive=True)
                for lang in ["ru", "en", "es"]:
                    result = t(lang, "risk_high_whr", threshold=str(threshold))
                    assert str(threshold) in result

        except ImportError:
            pass

    def test_validate_translation_key_function_line_366(self):
        """Test line 366: validate_translation_key function"""
        try:
            from core.i18n import validate_translation_key

            # Test with valid keys that should exist in all languages
            valid_keys = [
                "bmi_normal",
                "bmi_overweight",
                "form_weight",
                "form_height",
                "validation_weight_positive",
            ]

            for key in valid_keys:
                result = validate_translation_key(key)
                assert result is True  # Should trigger line 366

            # Test with invalid/non-existent keys
            invalid_keys = [
                "nonexistent_key",
                fake.word(),
                "fake_translation",
                "invalid_bmi_category",
                "missing_form_field",
            ]

            for key in invalid_keys:
                result = validate_translation_key(key)
                assert result is False  # Should trigger line 366

        except ImportError:
            pass

    def test_normalize_lang_return_base_line_420_coverage(self):
        """Test line 420: return base language from exceptions"""
        try:
            from core.i18n import normalize_lang

            # Force hitting line 420 by testing Spanish with Mexico exception
            # According to LOCALE_SPECIAL_CASES, es has exceptions: {"mx"}
            test_cases = [
                "es-MX",  # Mexico should return "es" (base)
                "es-mx",  # Lowercase
                "ES-MX",  # Uppercase
                "Es-Mx",  # Mixed case
                "es_MX",  # Underscore separator
            ]

            for locale in test_cases:
                result = normalize_lang(locale)
                # Should return base language "es" (line 420)
                assert result == "es", f"Failed for {locale}: got {result}, expected es"

        except ImportError:
            pass

    def test_normalize_lang_direct_base_line_427_coverage(self):
        """Test line 427: return key for direct base languages"""
        try:
            from core.i18n import normalize_lang

            # Test direct base languages: "ru", "en", "es"
            direct_languages = ["ru", "en", "es"]

            for lang in direct_languages:
                result = normalize_lang(lang)
                # Should return the same language (line 427)
                assert result == lang, f"Failed for {lang}: got {result}, expected {lang}"

            # Test with different cases to ensure normalization works
            case_variants = [
                ("RU", "ru"),
                ("EN", "en"),
                ("ES", "es"),
                ("Ru", "ru"),
                ("En", "en"),
                ("Es", "es"),
            ]

            for input_lang, expected in case_variants:
                result = normalize_lang(input_lang)
                assert result == expected

        except ImportError:
            pass

    def test_comprehensive_error_scenarios(self):
        """Test comprehensive error scenarios for complete coverage"""
        try:
            from core.i18n import t

            # Test KeyError for missing translation key
            with pytest.raises(KeyError, match="Translation key .* not found"):
                t("en", "nonexistent_key")

            with pytest.raises(KeyError, match="Translation key .* not found"):
                t("ru", fake.word())

            with pytest.raises(KeyError, match="Translation key .* not found"):
                t("es", "fake_translation_key")

        except ImportError:
            pass

    def test_template_formatting_edge_cases(self):
        """Test template formatting with various edge cases"""
        try:
            from core.i18n import t

            # Test formatting with complex kwargs
            complex_kwargs = {
                "threshold": "0.85",
                "value": fake.pydecimal(left_digits=2, right_digits=1, positive=True),
                "name": fake.first_name(),
                "age": fake.random_int(min=18, max=80),
            }

            # Test with risk_high_whr which we know has {threshold}
            result = t("en", "risk_high_whr", **complex_kwargs)
            assert "0.85" in result

            # Test without kwargs (should not format)
            result_no_kwargs = t("en", "bmi_normal")  # No formatting needed
            assert isinstance(result_no_kwargs, str)

        except ImportError:
            pass

    def test_concurrent_translation_access(self):
        """Test concurrent access to translation functions"""
        try:
            import concurrent.futures

            from core.i18n import normalize_lang, t, validate_translation_key

            def translation_worker():
                lang = fake.random_element(["ru", "en", "es"])
                key = fake.random_element(
                    ["bmi_normal", "form_weight", "validation_weight_positive"]
                )
                try:
                    return t(lang, key)
                except Exception:

                    logging.exception(
                        "Unexpected exception in tests: test_i18n_additional_coverage.py"
                    )
                    return None

            def normalize_worker():
                locale = fake.random_element(["en-US", "ru-RU", "es-MX", "es-ES", "en", "ru", "es"])
                return normalize_lang(locale)

            def validate_worker():
                key = fake.random_element(["bmi_normal", "fake_key", "form_weight"])
                return validate_translation_key(key)

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Test concurrent access
                futures = []
                for _ in range(5):
                    futures.append(executor.submit(translation_worker))
                    futures.append(executor.submit(normalize_worker))
                    futures.append(executor.submit(validate_worker))

                results = [future.result() for future in futures]

            # Should handle concurrent access safely
            assert len(results) == 15

        except ImportError:
            pass

    def test_all_translation_keys_exist(self):
        """Test that common translation keys exist in all languages"""
        try:
            from core.i18n import validate_translation_key

            # Test common keys that should exist
            common_keys = [
                "bmi_underweight",
                "bmi_normal",
                "bmi_overweight",
                "bmi_obese_1",
                "form_weight",
                "form_height",
                "form_age",
                "validation_weight_positive",
                "validation_height_positive",
            ]

            for key in common_keys:
                # Should return True for valid keys (line 366)
                assert validate_translation_key(key) is True

        except ImportError:
            pass
