from unittest.mock import patch


def test_bmi_visualization_no_matplotlib_returns_fallback(monkeypatch):
    import bmi_visualization as mod

    # Force re-import path where matplotlib is unavailable
    with patch.dict(mod.__dict__, {"MATPLOTLIB_AVAILABLE": False}):
        from bmi_visualization import generate_bmi_visualization

        data = generate_bmi_visualization(bmi=24.0, age=30, gender="male")
        assert data["available"] is False
        assert "Visualization not available" in data["error"]
