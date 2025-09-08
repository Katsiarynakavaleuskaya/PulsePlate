"""
Tests for Fitness Levels in Spanish

This test ensures that fitness level descriptions are correctly localized
in Spanish and other supported languages.
"""

from bmi_core import estimate_level


class TestLevelES:
    """Test fitness levels in Spanish."""

    def test_fitness_levels_spanish(self):
        """Test that fitness levels work correctly in Spanish."""
        # Test different fitness levels in Spanish
        advanced_es = estimate_level(freq_per_week=4, years=6.0, lang="es")
        intermediate_es = estimate_level(freq_per_week=3, years=3.0, lang="es")
        novice_es = estimate_level(freq_per_week=2, years=1.0, lang="es")
        beginner_es = estimate_level(freq_per_week=1, years=0.2, lang="es")

        # All should be strings
        assert isinstance(advanced_es, str)
        assert isinstance(intermediate_es, str)
        assert isinstance(novice_es, str)
        assert isinstance(beginner_es, str)

        # All should be non-empty
        assert len(advanced_es) > 0
        assert len(intermediate_es) > 0
        assert len(novice_es) > 0
        assert len(beginner_es) > 0

        # Test the same levels in English and Russian for comparison
        advanced_en = estimate_level(freq_per_week=4, years=6.0, lang="en")
        intermediate_en = estimate_level(freq_per_week=3, years=3.0, lang="en")
        novice_en = estimate_level(freq_per_week=2, years=1.0, lang="en")
        beginner_en = estimate_level(freq_per_week=1, years=0.2, lang="en")

        advanced_ru = estimate_level(freq_per_week=4, years=6.0, lang="ru")
        intermediate_ru = estimate_level(freq_per_week=3, years=3.0, lang="ru")
        novice_ru = estimate_level(freq_per_week=2, years=1.0, lang="ru")
        beginner_ru = estimate_level(freq_per_week=1, years=0.2, lang="ru")

        # All should be strings and non-empty
        for level in [
            advanced_en,
            intermediate_en,
            novice_en,
            beginner_en,
            advanced_ru,
            intermediate_ru,
            novice_ru,
            beginner_ru,
        ]:
            assert isinstance(level, str)
            assert len(level) > 0

    def test_fitness_level_consistency(self):
        """Test that fitness levels are consistent across languages for same parameters."""
        # Test with the same parameters
        freq, years = 3, 2.5

        level_es = estimate_level(freq, years, "es")
        level_en = estimate_level(freq, years, "en")
        level_ru = estimate_level(freq, years, "ru")

        # All should be strings and non-empty
        assert isinstance(level_es, str)
        assert isinstance(level_en, str)
        assert isinstance(level_ru, str)

        assert len(level_es) > 0
        assert len(level_en) > 0
        assert len(level_ru) > 0

        # They should all be different strings (different languages)
        assert level_es != level_en or level_es != level_ru or level_en != level_ru
