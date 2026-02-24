"""
Tests for Fitness Levels in Spanish

This test ensures that fitness level descriptions are correctly localized
in Spanish and other supported languages.

Uses canonical core.bmi.engine.estimate_level and get_fitness_level_display.
"""

import pytest

from core.bmi.engine import (
    estimate_level,
    get_fitness_level_display,
    FITNESS_LEVEL_DISPLAY_NAMES,
)


class TestFitnessLevelLocalization:
    """Test fitness level localization across supported languages."""

    @pytest.mark.parametrize(
        "level,lang,expected",
        [
            ("beginner", "es", "Principiante"),
            ("novice", "es", "Novato"),
            ("intermediate", "es", "Intermedio"),
            ("advanced", "es", "Avanzado"),
            ("beginner", "ru", "Начинающий"),
            ("novice", "ru", "Новичок"),
            ("intermediate", "ru", "Средний"),
            ("advanced", "ru", "Продвинутый"),
            ("beginner", "en", "Beginner"),
            ("novice", "en", "Novice"),
            ("intermediate", "en", "Intermediate"),
            ("advanced", "en", "Advanced"),
        ],
    )
    def test_fitness_level_display_names(self, level: str, lang: str, expected: str) -> None:
        """Test localized display names for fitness levels."""
        result = get_fitness_level_display(level, lang)  # type: ignore[arg-type]
        assert result == expected

    def test_fitness_level_display_names_dict_structure(self) -> None:
        """Test that FITNESS_LEVEL_DISPLAY_NAMES has all required keys."""
        required_levels = {"beginner", "novice", "intermediate", "advanced"}
        required_langs = {"ru", "en", "es"}

        assert set(FITNESS_LEVEL_DISPLAY_NAMES.keys()) == required_levels

        for level in required_levels:
            assert set(FITNESS_LEVEL_DISPLAY_NAMES[level].keys()) == required_langs

    def test_estimate_level_returns_valid_keys(self) -> None:
        """Test that estimate_level returns keys present in display names."""
        test_cases = [
            (0, 0.0),
            (1, 0.5),
            (2, 2.0),
            (3, 5.0),
        ]

        for freq, years in test_cases:
            level = estimate_level(freq_per_week=freq, years=years)
            assert level in FITNESS_LEVEL_DISPLAY_NAMES
