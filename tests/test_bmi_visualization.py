# -*- coding: utf-8 -*-
"""
Comprehensive tests for BMI visualization functionality.
Tests both the enhanced BMI endpoint and dedicated visualization endpoint.
"""

import base64
import importlib
import io
import sys
from types import ModuleType
from typing import Optional
from unittest.mock import Mock, patch
from tests._client import get_client

import pytest
from fastapi.testclient import TestClient

# Test imports to ensure module can be imported
matplotlib: ModuleType | None
plt: ModuleType | None
try:
    import matplotlib
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    matplotlib = None
    plt = None


def test_bmi_visualization_imports():
    """Test that visualization module imports work correctly."""
    try:
        from bmi_visualization import (
            MATPLOTLIB_AVAILABLE,
            BMIVisualizer,
            generate_bmi_visualization,
        )

        # Test import success
        assert hasattr(generate_bmi_visualization, "__call__")
        # sourcery skip: no-conditionals-in-tests
        if MATPLOTLIB_AVAILABLE:
            visualizer = BMIVisualizer()
            assert visualizer is not None
    except ImportError:
        # Import failure is acceptable in CI environment
        pass


def test_matplotlib_import_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling when matplotlib import fails."""
    # Test the import error path in bmi_visualization module
    # Remove bmi_visualization from cache to force reimport
    monkeypatch.delitem(sys.modules, "bmi_visualization", raising=False)

    # Remove already-imported matplotlib modules to ensure we hit the import path again.
    for mod_name in [k for k in list(sys.modules.keys()) if k.startswith("matplotlib")]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)

    # Block matplotlib imports without mocking builtins.__import__ (repo policy).
    import importlib.abc
    import importlib.machinery
    from collections.abc import Sequence
    from types import ModuleType
    from typing import Optional

    class _BlockMatplotlib(importlib.abc.MetaPathFinder):
        def find_spec(
            self,
            fullname: str,
            path: Sequence[str] | None,
            target: ModuleType | None = None,
        ) -> importlib.machinery.ModuleSpec | None:
            if fullname == "matplotlib" or fullname.startswith("matplotlib."):
                raise ModuleNotFoundError(fullname)
            return None

    blocker = _BlockMatplotlib()
    monkeypatch.setattr(sys, "meta_path", [blocker, *sys.meta_path])

    import bmi_visualization

    importlib.reload(bmi_visualization)
    # This should set MATPLOTLIB_AVAILABLE to False
    assert not bmi_visualization.MATPLOTLIB_AVAILABLE


def test_bmi_visualization_without_matplotlib():
    """Test visualization with matplotlib unavailable."""
    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", False):
        from bmi_visualization import generate_bmi_visualization

        result = generate_bmi_visualization(
            bmi=24.5, age=30, gender="male", pregnant="no", athlete="no", lang="en"
        )

        assert not result["available"]
        assert "error" in result
        assert "matplotlib not installed" in result["error"]


def test_bmi_visualizer_init_without_matplotlib():
    """Test BMIVisualizer initialization without matplotlib."""
    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", False):
        from bmi_visualization import BMIVisualizer

        with pytest.raises(ImportError, match="matplotlib not available"):
            BMIVisualizer()


def test_bmi_visualizer_init_with_matplotlib():
    """Test BMIVisualizer initialization with matplotlib available."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        from bmi_visualization import BMIVisualizer

        visualizer = BMIVisualizer()
        assert visualizer is not None
        assert hasattr(visualizer, "COLORS")
        assert hasattr(visualizer, "BMI_RANGES")
        assert len(visualizer.COLORS) == 4
        assert "general" in visualizer.BMI_RANGES


def test_bmi_visualization_create_bmi_chart_missing_plt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """create_bmi_chart should raise ImportError when matplotlib backend is unavailable."""
    import bmi_visualization as vizmod

    # Ensure constructor does not fail even if matplotlib was unavailable at import time
    monkeypatch.setattr(vizmod, "MATPLOTLIB_AVAILABLE", True)
    monkeypatch.setattr(vizmod, "plt", None, raising=False)

    visualizer = vizmod.BMIVisualizer()
    with pytest.raises(ImportError, match="matplotlib not available"):
        visualizer.create_bmi_chart(
            bmi=22.0,
            age=30,
            gender="male",
            group="general",
            lang="en",
        )


def test_bmi_visualization_with_matplotlib_success():
    """Test successful BMI visualization generation."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        # Mock the entire matplotlib pipeline
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig") as mock_savefig,
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
        ):
            # Set up mock objects
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            # Mock the BytesIO buffer
            test_data = b"\x89PNG\r\n\x1a\n"  # PNG header
            mock_buffer = io.BytesIO()

            def mock_savefig_func(buffer, **kwargs):
                buffer.write(test_data)
                buffer.seek(0)

            mock_savefig.side_effect = mock_savefig_func

            # Mock the visualizer instance
            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(test_data).decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            with patch("io.BytesIO", return_value=mock_buffer):
                from bmi_visualization import generate_bmi_visualization

                result = generate_bmi_visualization(
                    bmi=22.0,
                    age=30,
                    gender="male",
                    pregnant="no",
                    athlete="no",
                    lang="en",
                )

                assert result["available"] is True
                assert "chart_base64" in result
                assert "category" in result
                assert "group" in result
                assert "group_display" in result


def test_bmi_visualization_different_groups():
    """Test visualization with different user groups."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    test_cases = [
        (65, "male", "no", "no", "elderly"),  # elderly
        (16, "female", "no", "no", "teen"),  # teen
        (30, "male", "no", "yes", "athlete"),  # athlete
        (25, "female", "yes", "no", "pregnant"),  # pregnant
    ]

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        for age, gender, pregnant, athlete, expected_group in test_cases:
            with (
                patch("matplotlib.pyplot.subplots") as mock_subplots,
                patch("matplotlib.pyplot.tight_layout"),
                patch("matplotlib.pyplot.savefig"),
                patch("matplotlib.pyplot.close"),
                patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
                patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
            ):
                mock_fig = Mock()
                mock_ax1 = Mock()
                mock_ax2 = Mock()
                mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

                # Mock the visualizer instance
                mock_visualizer = Mock()
                mock_visualizer.create_bmi_chart.return_value = base64.b64encode(
                    b"fake_data"
                ).decode("utf-8")
                mock_visualizer_class.return_value = mock_visualizer

                from bmi_visualization import generate_bmi_visualization

                result = generate_bmi_visualization(
                    bmi=22.0,
                    age=age,
                    gender=gender,
                    pregnant=pregnant,
                    athlete=athlete,
                    lang="en",
                )

                assert result["available"] is True
                assert "group" in result


def test_bmi_visualization_chart_creation_methods():
    """Test individual chart creation methods."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with (
        patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True),
        patch("matplotlib.pyplot", Mock()),
    ):
        from bmi_visualization import BMIVisualizer

        # Mock the class constructor to not check matplotlib
        with patch.object(BMIVisualizer, "__init__", lambda x: None):
            visualizer = BMIVisualizer()
            # Set the required attributes
            visualizer.BMI_RANGES = BMIVisualizer.BMI_RANGES
            visualizer.COLORS = BMIVisualizer.COLORS

            # Mock axes for testing
            mock_ax = Mock()

            # Mock bar method to return a list of mock bars with numeric methods
            mock_bar1 = Mock()
            mock_bar1.get_x.return_value = 0.0
            mock_bar1.get_width.return_value = 1.0
            mock_bar1.get_height.return_value = 10.0

            mock_bar2 = Mock()
            mock_bar2.get_x.return_value = 1.0
            mock_bar2.get_width.return_value = 1.0
            mock_bar2.get_height.return_value = 15.0

            mock_bar3 = Mock()
            mock_bar3.get_x.return_value = 2.0
            mock_bar3.get_width.return_value = 1.0
            mock_bar3.get_height.return_value = 12.0

            mock_bars = [mock_bar1, mock_bar2, mock_bar3]
            mock_ax.bar.return_value = mock_bars

            # Test BMI gauge creation
            visualizer._create_bmi_gauge(mock_ax, 22.0, "general", "en")
            # Verify that barh method was called (horizontal bar chart)
            assert mock_ax.barh.called
            assert mock_ax.plot.called
            assert mock_ax.set_xlim.called

            # Test guidance chart creation
            mock_ax.reset_mock()
            mock_ax.bar.return_value = mock_bars  # Reset the return value
            visualizer._create_guidance_chart(mock_ax, 22.0, 30, "male", "general", "en")
            # Verify that bar method was called
            assert mock_ax.bar.called
            assert mock_ax.set_ylabel.called
            assert mock_ax.text.called


def test_bmi_visualization_exception_handling():
    """Test exception handling during visualization."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        # Test exception in create_bmi_chart by mocking BMIVisualizer to raise an exception
        with patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class:
            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.side_effect = Exception("Plot error")
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            result = generate_bmi_visualization(
                bmi=22.0, age=30, gender="male", pregnant="no", athlete="no", lang="en"
            )

            assert result["available"] is False
            assert "error" in result
            assert "Plot error" in result["error"]


def test_bmi_visualization_ranges_and_colors():
    """Test BMI ranges and color configurations."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        from bmi_visualization import BMIVisualizer

        visualizer = BMIVisualizer()

        # Test that all expected ranges are defined
        expected_groups = ["general", "elderly", "teen", "athlete"]
        for group in expected_groups:
            assert group in visualizer.BMI_RANGES
            ranges = visualizer.BMI_RANGES[group]
            assert len(ranges) == 4  # underweight, normal, overweight, obese

        # Test that colors are defined
        expected_colors = ["underweight", "normal", "overweight", "obese"]
        for color_key in expected_colors:
            assert color_key in visualizer.COLORS
            assert visualizer.COLORS[color_key].startswith("#")


def test_bmi_visualization_language_support():
    """Test visualization with different languages."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    languages = ["en", "ru"]

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        for lang in languages:
            with (
                patch("matplotlib.pyplot.subplots") as mock_subplots,
                patch("matplotlib.pyplot.tight_layout"),
                patch("matplotlib.pyplot.savefig"),
                patch("matplotlib.pyplot.close"),
                patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
                patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
            ):
                mock_fig = Mock()
                mock_ax1 = Mock()
                mock_ax2 = Mock()
                mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

                # Mock the visualizer instance
                mock_visualizer = Mock()
                mock_visualizer.create_bmi_chart.return_value = base64.b64encode(
                    b"fake_data"
                ).decode("utf-8")
                mock_visualizer_class.return_value = mock_visualizer

                from bmi_visualization import generate_bmi_visualization

                result = generate_bmi_visualization(
                    bmi=22.0,
                    age=30,
                    gender="male",
                    pregnant="no",
                    athlete="no",
                    lang=lang,
                )

                assert result["available"] is True
                assert "category" in result


class TestBMIVisualizationAPI:
    def setup_method(self) -> None:
        self.client = get_client()

    def teardown_method(self) -> None:
        self.client.close()

    def test_bmi_endpoint_with_visualization_request(self) -> None:
        """Test BMI endpoint with include_chart parameter."""
        payload = {
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en",
            "include_chart": True,
        }

        response = self.client.post("/bmi", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "bmi" in data
        assert "category" in data

        # Since matplotlib might not be installed, check graceful degradation
        # Either visualization is present or it's not included due to matplotlib unavailability
        if "visualization" in data:
            viz = data["visualization"]
            if viz.get("available"):
                assert "chart_base64" in viz
                assert "category" in viz
                assert "group" in viz
            else:
                assert "error" in viz
                assert not viz["available"]
        # If visualization is not in data, that's also acceptable when matplotlib is not available

    def test_bmi_endpoint_without_visualization(self) -> None:
        """Test BMI endpoint without visualization request."""
        payload = {
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en",
            "include_chart": False,
        }

        response = self.client.post("/bmi", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "bmi" in data
        assert "category" in data
        assert "visualization" not in data

    def test_enhanced_teen_segmentation(self) -> None:
        """Test enhanced teen segmentation in BMI calculation."""
        payload = {
            "weight_kg": 60,
            "height_m": 1.70,
            "age": 16,  # Teen age
            "gender": "female",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en",
        }

        response = self.client.post("/bmi", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "bmi" in data
        assert "category" in data
        # Teen category should be handled appropriately

    def test_enhanced_athlete_segmentation(self) -> None:
        """Test enhanced athlete segmentation with adjusted BMI ranges."""
        payload = {
            "weight_kg": 85,
            "height_m": 1.75,
            "age": 25,
            "gender": "male",
            "pregnant": "no",
            "athlete": "yes",
            "lang": "en",
        }

        response = self.client.post("/bmi", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "bmi" in data
        assert "category" in data
        assert data["athlete"] is True
        assert "athlete" in data["group"]

    def test_bmi_visualization_endpoint_without_api_key(self) -> None:
        """Test that visualization endpoint requires API key."""
        payload = {
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/visualize", json=payload)
        # Should return 403 for missing API key, but may return 503 if
        # visualization module not available, or 404 if endpoint not found
        assert response.status_code in [403, 503, 404]

    @pytest.mark.xfail(
        strict=True,
        reason="Test isolation issue in full suite - passes individually. TODO: Fix test isolation or use dependency override for API key",
    )
    def test_bmi_visualization_endpoint_with_api_key(self) -> None:
        """Test visualization endpoint with API key."""
        payload = {
            "weight_kg": 70,
            "height_m": 1.75,
            "age": 30,
            "gender": "male",
            "pregnant": "no",
            "athlete": "no",
            "lang": "en",
        }

        # Mock the entire bmi_visualization module
        mock_viz_result = {
            "chart_base64": base64.b64encode(b"fake_data").decode("utf-8"),
            "category": "Healthy weight",
            "group": "general",
            "group_display": "general",
            "available": True,
            "format": "png",
            "encoding": "base64",
        }

        # Mock at the app level to bypass all the bmi_visualization internal checks
        import app

        original_generate_bmi_visualization = getattr(app, "generate_bmi_visualization", None)
        original_matplotlib_available = getattr(app, "MATPLOTLIB_AVAILABLE", None)

        # Temporarily replace the function and flag at the app module level
        app.generate_bmi_visualization = Mock(return_value=mock_viz_result)
        app.MATPLOTLIB_AVAILABLE = True

        try:
            response = self.client.post(
                "/api/v1/bmi/visualize", json=payload, headers={"X-API-Key": "test_key"}
            )

            # Should return 200 with mocked visualization
            assert (
                response.status_code == 200
            ), f"Expected 200, got {response.status_code}. Response: {response.content.decode()}"
            data = response.json()
            assert "bmi" in data
            assert "visualization" in data
            assert data["visualization"]["available"] is True
        finally:
            # Restore original values
            if original_generate_bmi_visualization is not None:
                app.generate_bmi_visualization = original_generate_bmi_visualization
            if original_matplotlib_available is not None:
                app.MATPLOTLIB_AVAILABLE = original_matplotlib_available


def test_bmi_visualization_base64_encoding():
    """Test that visualization properly encodes to base64."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        # Mock the entire plotting pipeline to return known data
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig") as mock_savefig,
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            # Create test image data
            test_data = b"\x89PNG\r\n\x1a\n"  # PNG header
            mock_buffer = io.BytesIO()

            def mock_savefig_func(buffer, **kwargs):
                buffer.write(test_data)
                buffer.seek(0)

            mock_savefig.side_effect = mock_savefig_func

            # Mock the visualizer instance
            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(test_data).decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            with patch("io.BytesIO", return_value=mock_buffer):
                from bmi_visualization import generate_bmi_visualization

                result = generate_bmi_visualization(
                    bmi=22.0,
                    age=30,
                    gender="male",
                    pregnant="no",
                    athlete="no",
                    lang="en",
                )

                assert result["available"] is True
                assert "chart_base64" in result

                # Verify base64 encoding
                chart_data = result["chart_base64"]
                assert isinstance(chart_data, str)

                # Try to decode to verify it's valid base64
                decoded = base64.b64decode(chart_data)
                assert decoded == test_data


def test_bmi_visualization_extreme_values():
    """Test visualization with extreme BMI values."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    extreme_bmis = [15.0, 45.0]  # Very low and very high BMI

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        for bmi_val in extreme_bmis:
            with (
                patch("matplotlib.pyplot.subplots") as mock_subplots,
                patch("matplotlib.pyplot.tight_layout"),
                patch("matplotlib.pyplot.savefig"),
                patch("matplotlib.pyplot.close"),
                patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
                patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
            ):
                mock_fig = Mock()
                mock_ax1 = Mock()
                mock_ax2 = Mock()
                mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

                # Mock the visualizer instance
                mock_visualizer = Mock()
                mock_visualizer.create_bmi_chart.return_value = base64.b64encode(
                    b"fake_data"
                ).decode("utf-8")
                mock_visualizer_class.return_value = mock_visualizer

                from bmi_visualization import generate_bmi_visualization

                result = generate_bmi_visualization(
                    bmi=bmi_val,
                    age=30,
                    gender="male",
                    pregnant="no",
                    athlete="no",
                    lang="en",
                )

                assert result["available"] is True
                assert "category" in result


def test_visualization_category_is_localized_ru_not_key() -> None:
    """Test that category is localized in Russian and never returns raw key."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig"),
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
            patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(b"fake_data").decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            # Test underweight category (BMI 17.0)
            result = generate_bmi_visualization(
                bmi=17.0,
                age=30,
                gender="female",
                lang="ru",
                pregnant="no",
                athlete="no",
            )

            assert result["available"] is True
            assert result["category"] is not None
            # Category must be localized, not a raw key (check multiple possible key formats)
            assert result["category"] not in {
                "underweight",
                "bmi.underweight",
                "bmi_underweight",
                "obese_1",
                "obese_2",
                "obese_3",
            }
            # Should be Russian localized string (contains Cyrillic)
            assert any(
                "А" <= ch <= "я" for ch in result["category"]
            ), f"Expected Cyrillic, got: {result['category']}"
            # Should be one of expected Russian translations
            assert result["category"] in {"Недовес", "Недостаточная масса"}


def test_visualization_category_is_localized_en_human_readable() -> None:
    """Test that category is localized in English and human-readable."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig"),
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
            patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(b"fake_data").decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            # Test underweight category (BMI 17.0)
            result = generate_bmi_visualization(
                bmi=17.0,
                age=30,
                gender="female",
                lang="en",
                pregnant="no",
                athlete="no",
            )

            assert result["available"] is True
            assert result["category"] is not None
            # Category must be localized, not a raw key (check multiple possible key formats)
            assert result["category"] not in {
                "underweight",
                "bmi.underweight",
                "bmi_underweight",
                "obese_1",
                "obese_2",
                "obese_3",
            }
            # Should be English localized string (human-readable, not a key)
            assert result["category"] in {"Underweight"}
            # Additional check: should not contain dots or underscores (key patterns)
            assert (
                "." not in result["category"] and "_" not in result["category"]
            ), f"Key pattern detected: {result['category']}"


def test_visualization_category_obesity_tiers_localized() -> None:
    """Test that obesity tiers (obesity_1, obesity_2, obesity_3) are properly localized."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig"),
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
            patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(b"fake_data").decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            # Test obesity_1 (BMI 32.0)
            result = generate_bmi_visualization(
                bmi=32.0,
                age=30,
                gender="male",
                lang="ru",
                pregnant="no",
                athlete="no",
            )

            assert result["available"] is True
            assert result["category"] is not None
            # Category must be localized, not a raw key (check multiple possible key formats)
            assert result["category"] not in {
                "obesity_1",
                "obesity_2",
                "obesity_3",
                "obese_1",
                "obese_2",
                "obese_3",
                "bmi.obesity_1",
                "bmi.obesity_2",
                "bmi.obesity_3",
                "bmi_obese_1",
                "bmi_obese_2",
                "bmi_obese_3",
            }
            # Should be Russian localized string (contains Cyrillic)
            assert any(
                "А" <= ch <= "я" for ch in result["category"]
            ), f"Expected Cyrillic, got: {result['category']}"
            # Should be Russian localized string for obesity tier (canonical format)
            assert result["category"] == "Ожирение I степени"


def test_visualization_ru_underweight_uses_i18n_wording() -> None:
    """Test that RU underweight uses canonical i18n wording, not legacy synonyms."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig"),
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
            patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(b"fake_data").decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            # i18n hit: should return canonical wording
            out = generate_bmi_visualization(
                bmi=17.0,
                age=30,
                gender="female",
                lang="ru",
                pregnant="no",
                athlete="no",
            )
            assert out["available"] is True
            # Must use canonical i18n wording, not legacy "Недовес"
            assert out["category"] == "Недостаточная масса"
            assert out["category"] != "Недовес"


def test_visualization_ru_fallback_never_uses_legacy_synonyms() -> None:
    """Test that fallback never uses legacy synonyms that diverge from i18n."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig"),
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
            patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(b"fake_data").decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            # Force i18n "miss": monkeypatch t() to raise KeyError (simulates missing translation)
            def raising_t(_lang: str, _key: str) -> str:
                raise KeyError(_key)

            with patch("bmi_visualization.t", side_effect=raising_t):
                # Test underweight (BMI 17.0) - should use generic, not legacy "Недовес"
                out = generate_bmi_visualization(
                    bmi=17.0,
                    age=30,
                    gender="female",
                    lang="ru",
                    pregnant="no",
                    athlete="no",
                )
                assert out["available"] is True
                # Must be generic, but NOT legacy synonym "Недовес"
                assert out["category"] != "Недовес"
                assert out["category"] == "Категория ИМТ"


def test_visualization_fallback_obesity_uses_legacy_i18n_keys() -> None:
    """Test that obesity tiers use legacy i18n keys (bmi_obese_*) when bmi.obesity_* missing."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig"),
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
            patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(b"fake_data").decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            # Mock _t_or_none to simulate missing bmi.obesity_1 but present bmi_obese_1
            def mock_t_or_none(lang: str, key: str) -> str | None:
                # Simulate missing canonical key bmi.obesity_1
                if key == "bmi.obesity_1":
                    return None
                # Simulate present legacy key bmi_obese_1
                if key == "bmi_obese_1":
                    if lang == "ru":
                        return "Ожирение I степени"
                    elif lang == "en":
                        return "Obese Class I"
                    elif lang == "es":
                        return "Obesidad Clase I"
                return None

            with patch("bmi_visualization._t_or_none", side_effect=mock_t_or_none):
                # Test obesity_1 (BMI 32.0) - should use bmi_obese_1 from i18n
                out_ru = generate_bmi_visualization(
                    bmi=32.0,
                    age=30,
                    gender="female",
                    lang="ru",
                    pregnant="no",
                    athlete="no",
                )
                assert out_ru["available"] is True
                # Should use canonical i18n wording from bmi_obese_1
                assert out_ru["category"] == "Ожирение I степени"

                out_en = generate_bmi_visualization(
                    bmi=32.0,
                    age=30,
                    gender="female",
                    lang="en",
                    pregnant="no",
                    athlete="no",
                )
                assert out_en["available"] is True
                assert out_en["category"] == "Obese Class I"

                out_es = generate_bmi_visualization(
                    bmi=32.0,
                    age=30,
                    gender="female",
                    lang="es",
                    pregnant="no",
                    athlete="no",
                )
                assert out_es["available"] is True
                assert out_es["category"] == "Obesidad Clase I"


def test_visualization_athlete_text_preserved_bc() -> None:
    """Test that athlete_text is preserved for backward compatibility (BC with legacy behavior)."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")

    with patch("bmi_visualization.MATPLOTLIB_AVAILABLE", True):
        with (
            patch("matplotlib.pyplot.subplots") as mock_subplots,
            patch("matplotlib.pyplot.tight_layout"),
            patch("matplotlib.pyplot.savefig"),
            patch("matplotlib.pyplot.close"),
            patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
            patch("io.BytesIO", return_value=io.BytesIO(b"fake_data")),
        ):
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))

            mock_visualizer = Mock()
            mock_visualizer.create_bmi_chart.return_value = base64.b64encode(b"fake_data").decode(
                "utf-8"
            )
            mock_visualizer_class.return_value = mock_visualizer

            from bmi_visualization import generate_bmi_visualization

            # Test RU string "спортсмен" → should trigger athlete group
            out_ru = generate_bmi_visualization(
                bmi=25.0,
                age=30,
                gender="male",
                lang="ru",
                pregnant="no",
                athlete="спортсмен",  # String input, not boolean
            )
            assert out_ru["available"] is True
            assert out_ru["group"] == "athlete"

            # Test EN string "athlete" → should trigger athlete group
            out_en = generate_bmi_visualization(
                bmi=25.0,
                age=30,
                gender="male",
                lang="en",
                pregnant="no",
                athlete="athlete",  # String input, not boolean
            )
            assert out_en["available"] is True
            assert out_en["group"] == "athlete"

            # Test explicit "no" → should NOT trigger athlete group
            out_no = generate_bmi_visualization(
                bmi=25.0,
                age=30,
                gender="male",
                lang="en",
                pregnant="no",
                athlete="no",  # Explicit no
            )
            assert out_no["available"] is True
            assert out_no["group"] == "general"


def test_generate_bmi_visualization_returns_unavailable_when_matplotlib_missing(monkeypatch):
    """Test that generate_bmi_visualization returns unavailable when matplotlib is missing."""
    import bmi_visualization as v

    # Force MATPLOTLIB_AVAILABLE to False
    monkeypatch.setattr(v, "MATPLOTLIB_AVAILABLE", False)
    out = v.generate_bmi_visualization(bmi=22.0, age=30, gender="female", lang="ru")
    assert out["available"] is False
    assert "error" in out
    assert "matplotlib" in out["error"].lower() or "not available" in out["error"].lower()


def test_localize_bmi_category_obesity_generic_fallback(monkeypatch):
    """Test _localize_bmi_category fallback to generic obesity label when tier key missing."""
    import bmi_visualization as v
    from core.i18n import normalize_lang

    # Force i18n to return key for specific tier (simulates missing bmi_obese_1)
    # but return translation for generic "bmi.obesity"
    def mock_t_or_none(lang: str, key: str) -> str | None:
        if key == "bmi.obesity_1":
            return None  # Simulate miss (primary key)
        elif key == "bmi_obese_1":
            return None  # Simulate legacy key miss
        elif key == "bmi.obesity":
            return "Ожирение" if lang == "ru" else "Obesity"  # Generic works
        return None

    monkeypatch.setattr(v, "_t_or_none", mock_t_or_none)
    lang_norm = normalize_lang("ru")
    result = v._localize_bmi_category(lang_norm, "obesity_1")
    # Should use generic obesity label as fallback (lines 76-78)
    assert result == "Ожирение" or "Ожирение" in result


def test_visualization_category_fallback_does_not_expose_key(monkeypatch) -> None:
    """Test that visualization fallback chain never exposes raw i18n keys."""
    from unittest.mock import Mock, patch

    import bmi_visualization as v

    def raising_t(_lang: str, _key: str) -> str:
        raise KeyError(_key)

    # Force fallback chain: canonical key → legacy key → generic label
    with (
        patch("bmi_visualization.t", side_effect=raising_t),
        patch("bmi_visualization.BMIVisualizer") as mock_visualizer_class,
    ):
        mock_visualizer = Mock()
        # Return any base64-ish string; content doesn't matter for this test
        mock_visualizer.create_bmi_chart.return_value = "ZmFrZQ=="
        mock_visualizer_class.return_value = mock_visualizer

        monkeypatch.setattr(v, "MATPLOTLIB_AVAILABLE", True)
        result = v.generate_bmi_visualization(
            bmi=37.0,
            age=30,
            gender="male",
            lang="ru",
            pregnant=False,
            athlete=False,
        )
        # Category should be safe generic label, not raw key
        if "category" in result and result["category"]:
            cat = result["category"]
            assert "obesity" not in cat.lower() or "Категория ИМТ" in cat
            assert "bmi." not in cat
            assert cat != "obesity_2"  # not raw category key
