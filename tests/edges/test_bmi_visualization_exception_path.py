from unittest.mock import patch


def test_bmi_visualization_exception_path_returns_error(monkeypatch):
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
