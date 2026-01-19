"""
Tests for Spanish i18n support in the BMI App.
"""

from core.bmi.engine import _bmi_category
from core.i18n import t, normalize_lang


def _bmi_category_localized(bmi: float, lang: str) -> str:
    """Helper to get localized BMI category."""
    category_key = _bmi_category(bmi=bmi, age=30, group="general")
    if category_key is None:
        return "N/A"
    lang_norm = normalize_lang(lang)
    # Use legacy keys for full category names (bmi_normal = "Peso normal", not "Normal")
    legacy_map = {
        "underweight": "bmi_underweight",
        "normal": "bmi_normal",
        "overweight": "bmi_overweight",
        "obesity_1": "bmi_obese_1",
        "obesity_2": "bmi_obese_2",
        "obesity_3": "bmi_obese_3",
    }
    legacy_key = legacy_map.get(category_key, f"bmi_{category_key}")
    return t(lang_norm, legacy_key)


class TestSpanishI18n:
    """Test Spanish internationalization support."""

    def test_bmi_category_spanish(self):
        """Test BMI categories in Spanish."""
        # Test different BMI values
        assert _bmi_category_localized(17.0, "es") == "Bajo peso"
        assert _bmi_category_localized(22.0, "es") == "Peso normal"
        assert _bmi_category_localized(27.0, "es") == "Sobrepeso"
        assert _bmi_category_localized(32.0, "es") == "Obesidad Clase I"
        assert _bmi_category_localized(37.0, "es") == "Obesidad Clase II"
        assert _bmi_category_localized(45.0, "es") == "Obesidad Clase III"

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
