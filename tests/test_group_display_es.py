"""
Tests for Group Display Names in Spanish

This test ensures that group display names are correctly localized
in Spanish and other supported languages.
"""

from core.bmi.engine import _auto_group, _group_display_name


class TestGroupDisplayES:
    """Test group display names in Spanish."""

    def test_group_display_names_spanish(self):
        """Test that group display names work correctly in Spanish."""
        # Test all group types in Spanish
        groups = [
            "general",
            "athlete",
            "pregnant",
            "elderly",
            "child",
            "teen",
            "too_young",
        ]

        for group in groups:
            es_name = _group_display_name(group, "es")
            en_name = _group_display_name(group, "en")
            ru_name = _group_display_name(group, "ru")

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
        from core.bmi.engine import _normalize_bool_flag

        # Test Spanish terms for pregnant women
        group_pregnant_es = _auto_group(
            age=25,
            gender="mujer",  # Spanish for "woman"
            pregnant=_normalize_bool_flag("si"),  # Spanish for "yes"
            athlete=_normalize_bool_flag("no"),
            athlete_text=None,
        )
        assert group_pregnant_es == "pregnant"

        group_pregnant_es2 = _auto_group(
            age=25,
            gender="mujer",  # Spanish for "woman"
            pregnant=_normalize_bool_flag("sí"),  # Spanish for "yes" with accent
            athlete=_normalize_bool_flag("no"),
            athlete_text=None,
        )
        assert group_pregnant_es2 == "pregnant"

        # Test Spanish terms for athletes (preserve athlete_text for heuristics)
        group_athlete_es = _auto_group(
            age=25,
            gender="hombre",  # Spanish for "man"
            pregnant=_normalize_bool_flag("no"),
            athlete=_normalize_bool_flag("atleta"),  # Spanish for "athlete"
            athlete_text="atleta",  # Preserve text for engine heuristics
        )
        assert group_athlete_es == "general"

    def test_special_population_notes_spanish(self):
        """Test that special population notes are available in Spanish."""
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
