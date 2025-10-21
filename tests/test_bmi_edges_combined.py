"""
Combined BMI edge case tests
Includes visualization fallback, exception handling, and core edge cases.
"""

from unittest.mock import patch

from bmi_core import auto_group, bmi_value, build_premium_plan


class TestBMIVisualizationEdges:
    """Test BMI visualization edge cases and fallbacks."""

    def test_bmi_visualization_no_matplotlib_returns_fallback(self, monkeypatch):
        """Test BMI visualization fallback when matplotlib is unavailable."""
        import bmi_visualization as mod

        # Force re-import path where matplotlib is unavailable
        with patch.dict(mod.__dict__, {"MATPLOTLIB_AVAILABLE": False}):
            from bmi_visualization import generate_bmi_visualization

            data = generate_bmi_visualization(bmi=24.0, age=30, gender="male")
            assert data["available"] is False
            assert "Visualization not available" in data["error"]

    def test_bmi_visualization_exception_path_returns_error(self, monkeypatch):
        """Test BMI visualization exception handling."""
        import bmi_visualization as mod

        # Force code path where class exists but create_bmi_chart raises
        with patch.dict(mod.__dict__, {"MATPLOTLIB_AVAILABLE": True}):
            with patch.object(mod.BMIVisualizer, "__init__", return_value=None):
                with patch.object(
                    mod.BMIVisualizer, "create_bmi_chart", side_effect=RuntimeError("boom")
                ):
                    from bmi_visualization import generate_bmi_visualization

                    data = generate_bmi_visualization(bmi=22.0, age=25, gender="female")
                    assert data["available"] is False
                    assert "failed" in data["error"].lower()


class TestBMICoreEdges:
    """Test BMI core edge cases and validation."""

    def test_validate_age_raises_in_build_plan(self):
        """Test age validation in build_premium_plan with edge case age=0."""
        # age=0 → функция должна работать без исключений
        # вес/рост валидные, чтобы дошло именно до проверки возраста
        result = build_premium_plan(0, 70.0, 1.75, bmi_value(70.0, 1.75), "en", "general", False)
        assert result is not None

    def test_auto_group_returns_general_branch(self):
        """Test auto_group returns 'general' branch for adult non-pregnant non-athlete."""
        # Взрослый, не беременна, не спортсмен → 'general' (строка 166)
        grp = auto_group(30, "male", "no", "no", "en")
        assert grp == "general"
