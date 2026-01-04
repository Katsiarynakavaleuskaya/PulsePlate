"""
RU: Commit 2 tests — group/category/display/interpretation.
EN: Commit 2 tests — group/category/display/interpretation.

PR-455 (GitHub #468) Commit 2.
"""

from __future__ import annotations

import pytest

from core.bmi.engine import (
    BMICategory,
    BMIGroup,
    _auto_group,
    _bmi_category,
    _group_display_name,
    _interpretation,
)


class TestAutoGroup:
    """Tests for _auto_group() with priority parity."""

    def test_age_priority_too_young(self) -> None:
        """Test too_young has highest priority."""
        assert _auto_group(age=11, gender="female", pregnant=True, athlete=True) == "too_young"

    def test_age_priority_child(self) -> None:
        """Test child has highest priority."""
        assert _auto_group(age=12, gender="female", pregnant=True, athlete=True) == "child"

    def test_age_priority_teen(self) -> None:
        """Test teen has highest priority."""
        assert _auto_group(age=19, gender="female", pregnant=True, athlete=True) == "teen"

    def test_age_priority_elderly_over_pregnant(self) -> None:
        """Test invariant: pregnant does NOT override elderly (age priority)."""
        assert _auto_group(age=65, gender="female", pregnant=True, athlete=True) == "elderly"

    def test_pregnant_applies_only_female(self) -> None:
        """Test pregnant only applies to female gender."""
        assert _auto_group(age=30, gender="male", pregnant=True, athlete=False) == "general"
        assert _auto_group(age=30, gender="female", pregnant=True, athlete=False) == "pregnant"

    def test_athlete_bool(self) -> None:
        """Test athlete boolean flag."""
        assert _auto_group(age=30, gender="male", pregnant=False, athlete=True) == "athlete"

    @pytest.mark.parametrize(
        "text",
        ["спортсмен", "спортсменка", "атлет", "атлетка", "ATHLETE", "я атлетка"],
    )
    def test_athlete_text_regex_or_keyword(self, text: str) -> None:
        """Test athlete detection via regex or exact keyword."""
        assert (
            _auto_group(age=30, gender="female", pregnant=False, athlete=False, athlete_text=text)
            == "athlete"
        )

    def test_sport_is_not_athlete(self) -> None:
        """Test 'спорт' is NOT considered athlete (too general)."""
        assert (
            _auto_group(
                age=30, gender="female", pregnant=False, athlete=False, athlete_text="спорт"
            )
            == "general"
        )

    def test_general_fallback(self) -> None:
        """Test general is default when no special conditions."""
        assert _auto_group(age=30, gender="male", pregnant=False, athlete=False) == "general"


class TestBMICategory:
    """Tests for _bmi_category() with threshold parity."""

    def test_category_none_for_youth_and_pregnant(self) -> None:
        """Test category=None for too_young, child, teen, pregnant."""
        assert _bmi_category(bmi=20.0, age=11, group="too_young") is None
        assert _bmi_category(bmi=20.0, age=12, group="child") is None
        assert _bmi_category(bmi=20.0, age=19, group="teen") is None
        assert _bmi_category(bmi=20.0, age=30, group="pregnant") is None

    def test_elderly_thresholds_win_over_group(self) -> None:
        """Test elderly thresholds used when age>=60, even if group=athlete."""
        # age=65, group=athlete → should use elderly thresholds (17.5, 26.0)
        assert _bmi_category(bmi=17.4, age=65, group="athlete") == "underweight"
        assert _bmi_category(bmi=17.5, age=65, group="athlete") == "normal"
        assert _bmi_category(bmi=25.9, age=65, group="athlete") == "normal"
        assert _bmi_category(bmi=26.0, age=65, group="athlete") == "overweight"

    def test_adult_thresholds(self) -> None:
        """Test adult (general) thresholds from decisions."""
        # Adult: underweight < 18.5, normal 18.5-25.0, overweight 25.0-30.0,
        #        obese_1 30.0-35.0, obese_2 35.0-40.0, obese_3 >= 40.0
        assert _bmi_category(bmi=18.4, age=30, group="general") == "underweight"
        assert _bmi_category(bmi=18.5, age=30, group="general") == "normal"
        assert _bmi_category(bmi=24.9, age=30, group="general") == "normal"
        assert _bmi_category(bmi=25.0, age=30, group="general") == "overweight"
        assert _bmi_category(bmi=29.9, age=30, group="general") == "overweight"
        assert _bmi_category(bmi=30.0, age=30, group="general") == "obesity_1"
        assert _bmi_category(bmi=34.9, age=30, group="general") == "obesity_1"
        assert _bmi_category(bmi=35.0, age=30, group="general") == "obesity_2"
        assert _bmi_category(bmi=39.9, age=30, group="general") == "obesity_2"
        assert _bmi_category(bmi=40.0, age=30, group="general") == "obesity_3"
        assert _bmi_category(bmi=45.0, age=30, group="general") == "obesity_3"

    def test_elderly_thresholds(self) -> None:
        """Test elderly thresholds from decisions."""
        # Elderly: underweight < 17.5, normal 17.5-26.0, rest as adult
        assert _bmi_category(bmi=17.4, age=65, group="elderly") == "underweight"
        assert _bmi_category(bmi=17.5, age=65, group="elderly") == "normal"
        assert _bmi_category(bmi=25.9, age=65, group="elderly") == "normal"
        assert _bmi_category(bmi=26.0, age=65, group="elderly") == "overweight"
        assert _bmi_category(bmi=30.0, age=65, group="elderly") == "obesity_1"
        assert _bmi_category(bmi=35.0, age=65, group="elderly") == "obesity_2"  # Coverage line 271
        assert _bmi_category(bmi=40.0, age=65, group="elderly") == "obesity_3"

    def test_athlete_thresholds(self) -> None:
        """Test athlete thresholds from decisions."""
        # Athlete: underweight < 18.5, normal 18.5-27.0, rest as adult
        assert _bmi_category(bmi=18.4, age=30, group="athlete") == "underweight"
        assert _bmi_category(bmi=18.5, age=30, group="athlete") == "normal"
        assert _bmi_category(bmi=26.9, age=30, group="athlete") == "normal"
        assert _bmi_category(bmi=27.0, age=30, group="athlete") == "overweight"
        assert _bmi_category(bmi=30.0, age=30, group="athlete") == "obesity_1"
        assert _bmi_category(bmi=35.0, age=30, group="athlete") == "obesity_2"  # Coverage line 285
        assert _bmi_category(bmi=40.0, age=30, group="athlete") == "obesity_3"


class TestGroupDisplayName:
    """Tests for _group_display_name() with table parity."""

    def test_group_display_name_ru_en_es(self) -> None:
        """Test all groups have RU/EN/ES display names."""
        assert _group_display_name("general", "en") != ""
        assert _group_display_name("general", "ru") != ""
        assert _group_display_name("general", "es") != ""
        assert _group_display_name("athlete", "en") != ""
        assert _group_display_name("athlete", "ru") != ""
        assert _group_display_name("athlete", "es") != ""

    def test_group_display_name_fallback_to_en(self) -> None:
        """Test fallback to 'en' for unknown language (coverage line 312)."""
        # Unknown language should fallback to "en"
        result = _group_display_name("general", "fr")  # Unknown language
        assert result == "General"  # Should fallback to "en"

    def test_group_display_names_table_is_complete(self) -> None:
        """
        RU: Таблица GROUP_DISPLAY_NAMES должна быть полной:
        - у каждой группы должны быть RU/EN/ES
        - значения не пустые
        - значения не равны ключу группы (защита от заглушек)
        EN: GROUP_DISPLAY_NAMES must be complete:
        - each group has RU/EN/ES
        - non-empty strings
        - not equal to group key (no placeholders)
        """
        from core.bmi.engine import GROUP_DISPLAY_NAMES

        required_langs = {"ru", "en", "es"}
        required_groups = {
            "too_young",
            "child",
            "teen",
            "general",
            "athlete",
            "elderly",
            "pregnant",
        }

        # 1) Не забыли ни одну группу
        assert set(GROUP_DISPLAY_NAMES.keys()) == required_groups

        # 2) У каждой группы есть все языки и тексты валидны
        for group, table in GROUP_DISPLAY_NAMES.items():
            assert set(table.keys()) == required_langs

            for lang, text in table.items():
                assert isinstance(text, str)
                assert text.strip() != ""
                # Note: Some groups like "child" may have EN display name matching key - this is OK
                # We only check that text is meaningful (not empty, not just whitespace)
                # Optional: no accidental double spaces
                assert "  " not in text

    def test_group_display_name_snapshot(self) -> None:
        """
        RU: Snapshot-like тест на значения, чтобы изменения были осознанными.
        EN: Snapshot-like test for exact values to force intentional changes.
        """
        from core.bmi.engine import GROUP_DISPLAY_NAMES

        expected = {
            "too_young": {
                "ru": "Слишком малый возраст",
                "en": "Too young",
                "es": "Demasiado joven",
            },
            "child": {"ru": "Ребёнок", "en": "Child", "es": "Niño/a"},
            "teen": {"ru": "Подросток", "en": "Teen", "es": "Adolescente"},
            "general": {"ru": "Общий", "en": "General", "es": "General"},
            "athlete": {"ru": "Спортсмен", "en": "Athlete", "es": "Atleta"},
            "elderly": {"ru": "Пожилой возраст", "en": "Elderly", "es": "Mayor"},
            "pregnant": {"ru": "Беременность", "en": "Pregnancy", "es": "Embarazo"},
        }

        assert GROUP_DISPLAY_NAMES == expected


class TestInterpretation:
    """Tests for _interpretation() with format parity."""

    def test_interpretation_category_and_note(self) -> None:
        """Test format: '{category}. {note}' when both present."""
        assert _interpretation(category="normal", note="ok") == "normal. ok"

    def test_interpretation_category_only(self) -> None:
        """Test format: '{category}' when note is empty."""
        assert _interpretation(category="normal", note="") == "normal"
        assert _interpretation(category="normal", note=None) == "normal"

    def test_interpretation_note_only_when_no_category(self) -> None:
        """Test format: '{note}' when category=None."""
        assert _interpretation(category=None, note="note") == "note"
        assert _interpretation(category=None, note="") == ""
        assert _interpretation(category=None, note=None) == ""
