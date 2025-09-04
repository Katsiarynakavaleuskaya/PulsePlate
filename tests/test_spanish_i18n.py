"""
Tests for Spanish i18n support in the BMI App.
"""

import pytest

from bmi_core import bmi_category, interpret_group
from core.i18n import t


class TestSpanishI18n:
    """Test Spanish internationalization support."""

    def test_bmi_category_spanish(self):
        """Test BMI categories in Spanish."""
        # Test different BMI values
        assert bmi_category(17.0, "es") == "Bajo peso"
        assert bmi_category(22.0, "es") == "Peso normal"
        assert bmi_category(27.0, "es") == "Sobrepeso"
        assert bmi_category(32.0, "es") == "Obesidad Clase I"
        assert bmi_category(37.0, "es") == "Obesidad Clase II"
        assert bmi_category(45.0, "es") == "Obesidad Clase III"

    def test_interpret_group_spanish(self):
        """Test group interpretation in Spanish."""
        # Test athlete group
        result = interpret_group(26.0, "athlete", "es")
        assert "atleta" in result.lower() or "grasa corporal" in result.lower()

    def test_i18n_translation_function_spanish(self):
        """Test the i18n translation function directly."""
        # Test some basic translations
        assert t("es", "bmi_underweight") == "Bajo peso"
        assert t("es", "bmi_normal") == "Peso normal"
        assert t("es", "bmi_overweight") == "Sobrepeso"
        assert t("es", "form_weight") == "Peso (kg)"
        assert t("es", "form_height") == "Altura (cm)"
        assert t("es", "form_calculate") == "Calcular"

    def test_all_languages_consistency(self):
        """Test that all languages have consistent keys."""
        from core.i18n import TRANSLATIONS

        # Get all translation keys from Russian (our base)
        ru_keys = set(TRANSLATIONS["ru"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())
        es_keys = set(TRANSLATIONS["es"].keys())

        # All languages should have the same keys
        assert ru_keys == en_keys, "RU and EN translation keys don't match"
        assert ru_keys == es_keys, "RU and ES translation keys don't match"
        assert en_keys == es_keys, "EN and ES translation keys don't match"
