# -*- coding: utf-8 -*-
"""
tests/test_planner_engines_advanced_facades.py

Comprehensive tests for planner_engines_advanced facade functions.

RU: Testy dlia fasadnykh funktsii planner_engines_advanced.
EN: Tests for nutrition_analysis and config facade functions.
"""

from __future__ import annotations


class TestNutritionAnalysisFacades:
    """Tests for core/nutrition_analysis.py facade functions."""

    # --- analyze_nutrition ---

    def test_analyze_nutrition_empty_dict(self) -> None:
        """Test analyze_nutrition with empty dict returns status empty."""
        from core.nutrition_analysis import analyze_nutrition

        result = analyze_nutrition({})
        assert result is not None
        assert result["status"] == "empty"
        assert result["macros"] == {}
        assert result["totals"] == {}

    def test_analyze_nutrition_with_macros(self) -> None:
        """Test analyze_nutrition calculates macro breakdown."""
        from core.nutrition_analysis import analyze_nutrition

        data = {"protein": 100, "carbs": 200, "fat": 80}
        result = analyze_nutrition(data)

        assert result is not None
        assert result["status"] == "analyzed"
        assert "protein_pct" in result["macros"]
        assert "carbs_pct" in result["macros"]
        assert "fat_pct" in result["macros"]

    def test_analyze_nutrition_invalid_input(self) -> None:
        """Test analyze_nutrition with invalid input returns None."""
        from core.nutrition_analysis import analyze_nutrition

        assert analyze_nutrition(None) is None  # type: ignore[arg-type]
        assert analyze_nutrition("string") is None  # type: ignore[arg-type]
        assert analyze_nutrition([1, 2, 3]) is None  # type: ignore[arg-type]

    def test_analyze_nutrition_non_numeric_values(self) -> None:
        """Test analyze_nutrition with non-numeric values."""
        from core.nutrition_analysis import analyze_nutrition

        data = {"protein": "invalid", "carbs": 100, "fat": 50}
        result = analyze_nutrition(data)
        assert result is not None
        assert result["status"] == "invalid_values"

    def test_analyze_nutrition_zero_macros(self) -> None:
        """Test analyze_nutrition with zero macros hits zero-calories branch."""
        from core.nutrition_analysis import analyze_nutrition

        data = {"protein": 0, "carbs": 0, "fat": 0}
        result = analyze_nutrition(data)
        assert result is not None
        assert result["macros"]["protein_pct"] == 0.0
        assert result["macros"]["carbs_pct"] == 0.0
        assert result["macros"]["fat_pct"] == 0.0

    # --- calculate_nutrition_score ---

    def test_calculate_nutrition_score_empty_dict(self) -> None:
        """Test calculate_nutrition_score with empty dict returns 0."""
        from core.nutrition_analysis import calculate_nutrition_score

        result = calculate_nutrition_score({})
        assert result == 0.0

    def test_calculate_nutrition_score_balanced(self) -> None:
        """Test calculate_nutrition_score with balanced macros."""
        from core.nutrition_analysis import calculate_nutrition_score

        data = {"protein": 75, "carbs": 100, "fat": 33}
        result = calculate_nutrition_score(data)
        assert result is not None
        assert 50 <= result <= 100

    def test_calculate_nutrition_score_invalid_input(self) -> None:
        """Test calculate_nutrition_score with invalid input returns None."""
        from core.nutrition_analysis import calculate_nutrition_score

        assert calculate_nutrition_score(None) is None  # type: ignore[arg-type]
        assert calculate_nutrition_score("string") is None  # type: ignore[arg-type]

    def test_calculate_nutrition_score_non_numeric(self) -> None:
        """Test calculate_nutrition_score with non-numeric values returns None."""
        from core.nutrition_analysis import calculate_nutrition_score

        assert calculate_nutrition_score({"protein": "bad", "carbs": 10, "fat": 5}) is None

    def test_calculate_nutrition_score_unbalanced(self) -> None:
        """Test calculate_nutrition_score with unbalanced macros."""
        from core.nutrition_analysis import calculate_nutrition_score

        data = {"protein": 10, "carbs": 20, "fat": 100}
        result = calculate_nutrition_score(data)
        assert result is not None
        assert result < 50

    # --- get_nutrition_recommendations ---

    def test_get_nutrition_recommendations_empty_dict(self) -> None:
        """Test get_nutrition_recommendations with empty dict."""
        from core.nutrition_analysis import get_nutrition_recommendations

        result = get_nutrition_recommendations({})
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_nutrition_recommendations_balanced(self) -> None:
        """Test get_nutrition_recommendations with balanced macros."""
        from core.nutrition_analysis import get_nutrition_recommendations

        data = {"protein": 75, "carbs": 100, "fat": 33}
        result = get_nutrition_recommendations(data)
        assert result is not None
        assert isinstance(result, list)

    def test_get_nutrition_recommendations_invalid_input(self) -> None:
        """Test get_nutrition_recommendations with invalid input returns None."""
        from core.nutrition_analysis import get_nutrition_recommendations

        assert get_nutrition_recommendations(None) is None  # type: ignore[arg-type]

    def test_get_nutrition_recommendations_non_numeric(self) -> None:
        """Test get_nutrition_recommendations with non-numeric values returns None."""
        from core.nutrition_analysis import get_nutrition_recommendations

        assert get_nutrition_recommendations({"protein": "bad"}) is None

    def test_get_nutrition_recommendations_low_protein(self) -> None:
        """Test get_nutrition_recommendations suggests more protein."""
        from core.nutrition_analysis import get_nutrition_recommendations

        data = {"protein": 10, "carbs": 300, "fat": 50}
        result = get_nutrition_recommendations(data)
        assert result is not None
        assert any("protein" in r.lower() for r in result)

    def test_get_nutrition_recommendations_high_protein_low_carbs_low_fat(self) -> None:
        """Test recommendations for high protein, low carbs, low fat."""
        from core.nutrition_analysis import get_nutrition_recommendations

        # ~80% protein calories, ~13% carbs, ~7% fat (by calories)
        data = {"protein": 200, "carbs": 30, "fat": 8}
        result = get_nutrition_recommendations(data)
        assert result is not None
        assert any("protein" in r.lower() for r in result)  # high protein
        assert any("carb" in r.lower() for r in result)  # low carbs
        assert any("fat" in r.lower() for r in result)  # low fat

    def test_get_nutrition_recommendations_high_fat(self) -> None:
        """Test recommendations for high fat intake."""
        from core.nutrition_analysis import get_nutrition_recommendations

        # Very high fat: fat_pct > 40
        data = {"protein": 30, "carbs": 50, "fat": 150}
        result = get_nutrition_recommendations(data)
        assert result is not None
        assert any("fat" in r.lower() for r in result)

    # --- validate_nutrition_data ---

    def test_validate_nutrition_data_valid(self) -> None:
        """Test validate_nutrition_data with valid data."""
        from core.nutrition_analysis import validate_nutrition_data

        assert validate_nutrition_data({"protein": 50, "carbs": 100}) is True
        assert validate_nutrition_data({"calories": 2000}) is True

    def test_validate_nutrition_data_invalid_type(self) -> None:
        """Test validate_nutrition_data with invalid types."""
        from core.nutrition_analysis import validate_nutrition_data

        assert validate_nutrition_data(None) is False
        assert validate_nutrition_data("string") is False
        assert validate_nutrition_data([1, 2, 3]) is False

    def test_validate_nutrition_data_invalid_values(self) -> None:
        """Test validate_nutrition_data with invalid value types."""
        from core.nutrition_analysis import validate_nutrition_data

        assert validate_nutrition_data({"protein": "invalid"}) is False
        assert validate_nutrition_data({"calories": []}) is False

    def test_validate_nutrition_data_empty_dict(self) -> None:
        """Test validate_nutrition_data with empty dict."""
        from core.nutrition_analysis import validate_nutrition_data

        assert validate_nutrition_data({}) is True

    def test_validate_nutrition_data_unknown_keys(self) -> None:
        """Test validate_nutrition_data with only unknown keys."""
        from core.nutrition_analysis import validate_nutrition_data

        assert validate_nutrition_data({"unknown": 100}) is False


class TestConfigFacades:
    """Tests for core/config.py facade functions."""

    # --- load_config ---

    def test_load_config_no_path(self) -> None:
        """Test load_config with no path returns dict."""
        from core.config import load_config

        result = load_config()
        assert isinstance(result, dict)

    def test_load_config_with_path(self) -> None:
        """Test load_config with path returns empty dict (stub)."""
        from core.config import load_config

        result = load_config("/some/path")
        assert isinstance(result, dict)

    # --- get_config_value ---

    def test_get_config_value_missing_key(self) -> None:
        """Test get_config_value returns default for missing key."""
        from core.config import get_config_value

        result = get_config_value("nonexistent_key", "default")
        assert result == "default"

    def test_get_config_value_invalid_key_type(self) -> None:
        """Test get_config_value with non-string key returns default."""
        from core.config import get_config_value

        result = get_config_value(123, "default")  # type: ignore[arg-type]
        assert result == "default"

    def test_get_config_value_none_default(self) -> None:
        """Test get_config_value returns None as default."""
        from core.config import get_config_value

        result = get_config_value("missing")
        assert result is None

    # --- set_config_value ---

    def test_set_config_value_valid(self) -> None:
        """Test set_config_value with valid key/value."""
        from core.config import get_config_value, set_config_value

        result = set_config_value("test_key", "test_value")
        assert result is True
        assert get_config_value("test_key") == "test_value"

    def test_set_config_value_invalid_key_type(self) -> None:
        """Test set_config_value with non-string key returns False."""
        from core.config import set_config_value

        result = set_config_value(123, "value")  # type: ignore[arg-type]
        assert result is False

    def test_set_config_value_various_types(self) -> None:
        """Test set_config_value with various value types."""
        from core.config import get_config_value, set_config_value

        assert set_config_value("int_key", 42) is True
        assert get_config_value("int_key") == 42

        assert set_config_value("list_key", [1, 2, 3]) is True
        assert get_config_value("list_key") == [1, 2, 3]

        assert set_config_value("dict_key", {"nested": True}) is True
        assert get_config_value("dict_key") == {"nested": True}

    # --- validate_config ---

    def test_validate_config_valid(self) -> None:
        """Test validate_config with valid config dict."""
        from core.config import validate_config

        assert validate_config({"key1": "value1", "key2": 123}) is True
        assert validate_config({}) is True

    def test_validate_config_invalid_type(self) -> None:
        """Test validate_config with invalid types."""
        from core.config import validate_config

        assert validate_config(None) is False
        assert validate_config("string") is False
        assert validate_config([1, 2, 3]) is False

    def test_validate_config_non_string_keys(self) -> None:
        """Test validate_config with non-string keys."""
        from core.config import validate_config

        assert validate_config({123: "value"}) is False
        assert validate_config({None: "value"}) is False
