"""
Tests for Group Display Names in Spanish

This test ensures that group display names are correctly localized
in Spanish and other supported languages.
"""

import pytest

from bmi_core import auto_group, group_display_name


class TestGroupDisplayES:
    """Test group display names in Spanish."""

    def test_group_display_names_spanish(self):
        """Test that group display names work correctly in Spanish."""
        # Test all group types in Spanish
        groups = ["general", "athlete", "pregnant", "elderly", "child", "teen", "too_young"]

        for group in groups:
            es_name = group_display_name(group, "es")
            en_name = group_display_name(group, "en")
            ru_name = group_display_name(group, "ru")

            # All should be strings
            assert isinstance(es_name, str)
            assert isinstance(en_name, str)
            assert isinstance(ru_name, str)

            # All should be non-empty
            assert len(es_name) > 0
            assert len(en_name) > 0
            assert len(ru_name) > 0

    def test_auto_group_spanish_terms(self):
        """Test that auto_group recognizes Spanish terms."""
        # Test Spanish terms for pregnant women
        group_pregnant_es = auto_group(
            age=25,
            gender="mujer",  # Spanish for "woman"
            pregnant="si",  # Spanish for "yes"
            athlete="no",
            lang="es"
        )
        assert group_pregnant_es == "pregnant"

        group_pregnant_es2 = auto_group(
            age=25,
            gender="mujer",  # Spanish for "woman"
            pregnant="sí",  # Spanish for "yes" with accent
            athlete="no",
            lang="es"
        )
        assert group_pregnant_es2 == "pregnant"

        # Test Spanish terms for athletes
        group_athlete_es = auto_group(
            age=25,
            gender="hombre",  # Spanish for "man"
            pregnant="no",
            athlete="atleta",  # Spanish for "athlete"
            lang="es"
        )
        assert group_athlete_es == "athlete"

    def test_special_population_notes_spanish(self):
        """Test that special population notes are available in Spanish."""
        from bmi_core import interpret_group
        from core.i18n import t

        # Test elderly note in Spanish
        elderly_note = t("es", "risk_elderly_note")
        assert isinstance(elderly_note, str)
        assert len(elderly_note) > 0
        assert "sarcopenia" in elderly_note or "IMC" in elderly_note  # Check key term is present

        # Test child note in Spanish
        child_note = t("es", "risk_child_note")
        assert isinstance(child_note, str)
        assert len(child_note) > 0

        # Test teen note in Spanish
        teen_note = t("es", "risk_teen_note")
        assert isinstance(teen_note, str)
        assert len(teen_note) > 0
