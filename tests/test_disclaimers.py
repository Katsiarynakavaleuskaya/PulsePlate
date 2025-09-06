"""
Tests for Medical Disclaimers module

Tests comprehensive medical and legal disclaimers for nutrition application.
"""

import pytest

from core.disclaimers import (
    LEGAL_DISCLAIMER,
    MEDICAL_DISCLAIMER,
    PRIVACY_DISCLAIMER,
    SPECIAL_POPULATION_DISCLAIMERS,
    get_comprehensive_disclaimer,
    get_disclaimer_text,
    get_professional_referral,
)


class TestMedicalDisclaimers:
    """Test medical disclaimer system."""

    def test_medical_disclaimer_english(self):
        """Test medical disclaimer in English."""
        disclaimer = get_disclaimer_text("medical", language="en")

        # Should contain key medical disclaimer elements
        assert "NOT intended for medical diagnosis" in disclaimer
        assert "treatment" in disclaimer
        assert "qualified healthcare professionals" in disclaimer

        # Should include warning symbols
        assert "⚠️" in disclaimer
        assert "IMPORTANT MEDICAL DISCLAIMER" in disclaimer

    def test_medical_disclaimer_russian(self):
        """Test medical disclaimer in Russian."""
        disclaimer = get_disclaimer_text("medical", language="ru")

        # Should contain Russian text
        assert "НЕ предназначено для медицинской диагностики" in disclaimer
        assert "лечения" in disclaimer
        assert "КВАЛИФИЦИРОВАННЫМИ" in disclaimer  # All caps in actual text

        # Should include warning symbols
        assert "⚠️" in disclaimer

    def test_special_population_disclaimers(self):
        """Test special population disclaimers."""
        # Test pregnancy disclaimer
        pregnancy_disclaimer = get_disclaimer_text("medical", "pregnancy", "en")
        assert "pregnancy" in pregnancy_disclaimer.lower()
        assert (
            "obstetrician" in pregnancy_disclaimer.lower()
            or "prenatal" in pregnancy_disclaimer.lower()
        )

        # Test children disclaimer
        children_disclaimer = get_disclaimer_text("medical", "children", "en")
        assert "children" in children_disclaimer.lower()

        # Test elderly disclaimer
        elderly_disclaimer = get_disclaimer_text("medical", "elderly", "en")
        assert (
            "elderly" in elderly_disclaimer.lower()
            or "older adults" in elderly_disclaimer.lower()
        )

    def test_legal_disclaimer(self):
        """Test legal disclaimer."""
        legal_disclaimer = get_disclaimer_text("legal", language="en")

        assert "provided 'as is'" in legal_disclaimer.lower()
        assert "not liable" in legal_disclaimer.lower()
        assert "health consequences" in legal_disclaimer.lower()

    def test_privacy_disclaimer(self):
        """Test privacy disclaimer."""
        privacy_disclaimer = get_disclaimer_text("privacy", language="en")

        assert "privacy" in privacy_disclaimer.lower()
        assert "does not store" in privacy_disclaimer.lower()
        assert "locally" in privacy_disclaimer.lower()

    def test_comprehensive_disclaimer(self):
        """Test comprehensive disclaimer combining all elements."""
        comprehensive = get_comprehensive_disclaimer()

        # Should include key safety elements
        assert "NOT intended for medical diagnosis" in comprehensive
        assert "provided 'as is'" in comprehensive
        assert "privacy" in comprehensive.lower()

    def test_comprehensive_disclaimer_with_populations(self):
        """Test comprehensive disclaimer with special populations."""
        comprehensive = get_comprehensive_disclaimer(["pregnancy", "children"])

        # Should include special population warnings
        assert "pregnancy" in comprehensive.lower()
        assert "children" in comprehensive.lower()

    def test_professional_referral_system(self):
        """Test professional referral recommendations."""
        # Test general referral
        general_referral = get_professional_referral("general")
        assert (
            "dietitian" in general_referral.lower()
            or "physician" in general_referral.lower()
        )

        # Test pregnancy referral
        pregnancy_referral = get_professional_referral("pregnancy")
        assert (
            "obstetrician" in pregnancy_referral.lower()
            or "midwife" in pregnancy_referral.lower()
        )

        # Test pediatric referral
        pediatric_referral = get_professional_referral("pediatric")
        assert "pediatrician" in pediatric_referral.lower()


class TestDisclaimerConstants:
    """Test disclaimer constant data structures."""

    def test_medical_disclaimer_structure(self):
        """Test medical disclaimer data structure."""
        assert "en" in MEDICAL_DISCLAIMER
        assert "ru" in MEDICAL_DISCLAIMER

        for lang_disclaimer in MEDICAL_DISCLAIMER.values():
            assert len(lang_disclaimer) > 100  # Should be substantial
            assert (
                "medical" in lang_disclaimer.lower()
                or "медицинский" in lang_disclaimer.lower()
            )

    def test_special_population_structure(self):
        """Test special population disclaimers structure."""
        required_populations = ["pregnancy", "children", "elderly", "athletes"]

        for population in required_populations:
            if population in SPECIAL_POPULATION_DISCLAIMERS:
                pop_disclaimer = SPECIAL_POPULATION_DISCLAIMERS[population]
                assert "en" in pop_disclaimer
                assert "ru" in pop_disclaimer

                for lang_disclaimer in pop_disclaimer.values():
                    assert len(lang_disclaimer) > 50

    def test_legal_disclaimer_structure(self):
        """Test legal disclaimer structure."""
        assert "en" in LEGAL_DISCLAIMER
        assert "ru" in LEGAL_DISCLAIMER

        for lang_disclaimer in LEGAL_DISCLAIMER.values():
            assert len(lang_disclaimer) > 50
            assert (
                "liable" in lang_disclaimer.lower()
                or "ответственности" in lang_disclaimer.lower()
            )

    def test_privacy_disclaimer_structure(self):
        """Test privacy disclaimer structure."""
        assert "en" in PRIVACY_DISCLAIMER
        assert "ru" in PRIVACY_DISCLAIMER

        for lang_disclaimer in PRIVACY_DISCLAIMER.values():
            assert len(lang_disclaimer) > 50
            assert (
                "privacy" in lang_disclaimer.lower()
                or "конфиденциальности" in lang_disclaimer.lower()
            )


class TestDisclaimerIntegration:
    """Test integration of disclaimers with nutrition recommendations."""

    def test_disclaimer_language_consistency(self):
        """Test language consistency across disclaimer types."""
        # English
        medical_en = get_disclaimer_text("medical", language="en")
        legal_en = get_disclaimer_text("legal", language="en")
        privacy_en = get_disclaimer_text("privacy", language="en")

        # All should be in English (no Cyrillic characters)
        assert not any(
            russian_char in medical_en
            for russian_char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        )
        assert not any(
            russian_char in legal_en
            for russian_char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        )
        assert not any(
            russian_char in privacy_en
            for russian_char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        )

        # Russian
        medical_ru = get_disclaimer_text("medical", language="ru")
        legal_ru = get_disclaimer_text("legal", language="ru")
        privacy_ru = get_disclaimer_text("privacy", language="ru")

        # Should contain Cyrillic characters
        assert any(
            russian_char in medical_ru
            for russian_char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        )
        assert any(
            russian_char in legal_ru
            for russian_char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        )
        assert any(
            russian_char in privacy_ru
            for russian_char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        )

    def test_disclaimer_length_appropriate(self):
        """Test that disclaimers are appropriately detailed."""
        medical = get_disclaimer_text("medical", language="en")
        legal = get_disclaimer_text("legal", language="en")
        comprehensive = get_comprehensive_disclaimer()

        # Should be substantial but not excessive
        assert 100 < len(medical) < 2000
        assert 50 < len(legal) < 1500
        assert 500 < len(comprehensive) < 5000

    def test_fallback_behavior(self):
        """Test fallback behavior for invalid inputs."""
        # Test invalid disclaimer type
        try:
            result = get_disclaimer_text("invalid_type")
            # Should either raise exception or return empty string
            assert result == "" or len(result) == 0
        except (KeyError, ValueError):
            # Exception is acceptable for invalid input
            pass

    def test_special_population_pregnancy(self):
        """Test pregnancy-specific disclaimers."""
        pregnancy_disclaimer = get_disclaimer_text("medical", "pregnancy", "en")

        # Should emphasize medical supervision during pregnancy
        assert "pregnancy" in pregnancy_disclaimer.lower()
        assert (
            "medical supervision" in pregnancy_disclaimer.lower()
            or "healthcare provider" in pregnancy_disclaimer.lower()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
