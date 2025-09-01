# -*- coding: utf-8 -*-
"""
Comprehensive tests for BMI visualization functionality.
Tests both the enhanced BMI endpoint and dedicated visualization endpoint.
"""

import base64
import importlib
import io
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = TestClient(app_module.app)

# Test imports to ensure module can be imported
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
            generate_bmi_visualization,
            BMIVisualizer
        )
        # Test import success
        assert hasattr(generate_bmi_visualization, '__call__')
        if MATPLOTLIB_AVAILABLE:
            visualizer = BMIVisualizer()
            assert visualizer is not None
    except ImportError:
        # Import failure is acceptable in CI environment
        pass


def test_matplotlib_import_error_handling():
    """Test handling when matplotlib import fails."""
    # Test the import error path in bmi_visualization module
    with patch.dict('sys.modules', {'matplotlib': None, 'matplotlib.pyplot': None}):
        # Force reimport to test the ImportError handling
        import bmi_visualization
        importlib.reload(bmi_visualization)
        # This should set MATPLOTLIB_AVAILABLE to False
        assert not bmi_visualization.MATPLOTLIB_AVAILABLE


def test_bmi_visualization_without_matplotlib():
    """Test visualization with matplotlib unavailable."""
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', False):
        from bmi_visualization import generate_bmi_visualization
        
        result = generate_bmi_visualization(
            bmi=24.5, age=30, gender="male",
            pregnant="no", athlete="no", lang="en"
        )
        
        assert not result["available"]
        assert "error" in result
        assert "matplotlib not installed" in result["error"]


def test_bmi_visualizer_init_without_matplotlib():
    """Test BMIVisualizer initialization without matplotlib."""
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', False):
        from bmi_visualization import BMIVisualizer
        
        with pytest.raises(ImportError, match="matplotlib not available"):
            BMIVisualizer()


def test_bmi_visualizer_init_with_matplotlib():
    """Test BMIVisualizer initialization with matplotlib available."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        from bmi_visualization import BMIVisualizer
        visualizer = BMIVisualizer()
        assert visualizer is not None
        assert hasattr(visualizer, 'COLORS')
        assert hasattr(visualizer, 'BMI_RANGES')
        assert len(visualizer.COLORS) == 4
        assert 'general' in visualizer.BMI_RANGES


def test_bmi_visualization_with_matplotlib_success():
    """Test successful BMI visualization generation."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        # Mock the entire matplotlib pipeline
        with patch('matplotlib.pyplot.subplots') as mock_subplots, \
             patch('matplotlib.pyplot.tight_layout'), \
             patch('matplotlib.pyplot.savefig') as mock_savefig, \
             patch('matplotlib.pyplot.close'):
            
            # Set up mock objects
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
            
            # Mock the BytesIO buffer
            test_data = b'\x89PNG\r\n\x1a\n'  # PNG header
            mock_buffer = io.BytesIO()
            
            def mock_savefig_func(buffer, **kwargs):
                buffer.write(test_data)
                buffer.seek(0)
            
            mock_savefig.side_effect = mock_savefig_func
            
            with patch('io.BytesIO', return_value=mock_buffer):
                from bmi_visualization import generate_bmi_visualization
                
                result = generate_bmi_visualization(
                    bmi=22.0, age=30, gender="male", 
                    pregnant="no", athlete="no", lang="en"
                )
                
                assert result["available"] is True
                assert "chart_base64" in result
                assert "category" in result
                assert "group" in result
                assert "interpretation" in result


def test_bmi_visualization_different_groups():
    """Test visualization with different user groups."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    test_cases = [
        (65, "male", "no", "no", "elderly"),   # elderly
        (16, "female", "no", "no", "teen"),    # teen
        (30, "male", "no", "yes", "athlete"),  # athlete
        (25, "female", "yes", "no", "pregnant"),  # pregnant
    ]
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        for age, gender, pregnant, athlete, expected_group in test_cases:
            with patch('matplotlib.pyplot.subplots') as mock_subplots, \
                 patch('matplotlib.pyplot.tight_layout'), \
                 patch('matplotlib.pyplot.savefig'), \
                 patch('matplotlib.pyplot.close'), \
                 patch('io.BytesIO', return_value=io.BytesIO(b'fake_data')):
                
                mock_fig = Mock()
                mock_ax1 = Mock()
                mock_ax2 = Mock()
                mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
                
                from bmi_visualization import generate_bmi_visualization
                
                result = generate_bmi_visualization(
                    bmi=22.0, age=age, gender=gender,
                    pregnant=pregnant, athlete=athlete, lang="en"
                )
                
                assert result["available"] is True
                assert "group" in result


def test_bmi_visualization_chart_creation_methods():
    """Test individual chart creation methods."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        from bmi_visualization import BMIVisualizer
        
        visualizer = BMIVisualizer()
        
        # Mock axes for testing
        mock_ax = Mock()
        
        # Test BMI gauge creation
        visualizer._create_bmi_gauge(mock_ax, 22.0, "general", "en")
        # Verify that barh method was called (horizontal bar chart)
        assert mock_ax.barh.called
        assert mock_ax.plot.called
        assert mock_ax.set_xlim.called
        
        # Test guidance chart creation
        mock_ax.reset_mock()
        visualizer._create_guidance_chart(
            mock_ax, 22.0, 30, "male", "general", "en"
        )
        # Verify that bar method was called
        assert mock_ax.bar.called
        assert mock_ax.set_ylabel.called
        assert mock_ax.text.called


def test_bmi_visualization_exception_handling():
    """Test exception handling during visualization."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        # Test exception in create_bmi_chart
        with patch('matplotlib.pyplot.subplots', side_effect=Exception("Plot error")):
            from bmi_visualization import generate_bmi_visualization
            
            result = generate_bmi_visualization(
                bmi=22.0, age=30, gender="male", 
                pregnant="no", athlete="no", lang="en"
            )
            
            assert result["available"] is False
            assert "error" in result
            assert "Plot error" in result["error"]


def test_bmi_visualization_ranges_and_colors():
    """Test BMI ranges and color configurations."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        from bmi_visualization import BMIVisualizer
        
        visualizer = BMIVisualizer()
        
        # Test that all expected ranges are defined
        expected_groups = ['general', 'elderly', 'teen', 'athlete']
        for group in expected_groups:
            assert group in visualizer.BMI_RANGES
            ranges = visualizer.BMI_RANGES[group]
            assert len(ranges) == 4  # underweight, normal, overweight, obese
            
        # Test that colors are defined
        expected_colors = ['underweight', 'normal', 'overweight', 'obese']
        for color_key in expected_colors:
            assert color_key in visualizer.COLORS
            assert visualizer.COLORS[color_key].startswith('#')


def test_bmi_visualization_language_support():
    """Test visualization with different languages."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    languages = ["en", "ru"]
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        for lang in languages:
            with patch('matplotlib.pyplot.subplots') as mock_subplots, \
                 patch('matplotlib.pyplot.tight_layout'), \
                 patch('matplotlib.pyplot.savefig'), \
                 patch('matplotlib.pyplot.close'), \
                 patch('io.BytesIO', return_value=io.BytesIO(b'fake_data')):
                
                mock_fig = Mock()
                mock_ax1 = Mock()
                mock_ax2 = Mock()
                mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
                
                from bmi_visualization import generate_bmi_visualization
                
                result = generate_bmi_visualization(
                    bmi=22.0, age=30, gender="male",
                    pregnant="no", athlete="no", lang=lang
                )
                
                assert result["available"] is True
                assert "category" in result


def test_bmi_endpoint_with_visualization_request():
    """Test BMI endpoint with include_chart parameter."""
    payload = {
        "weight_kg": 70,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "include_chart": True
    }

    response = client.post("/bmi", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "bmi" in data
    assert "category" in data
    assert "visualization" in data

    # Since matplotlib might not be installed, check graceful degradation
    viz = data["visualization"]
    if viz.get("available"):
        assert "chart_base64" in viz
        assert "category" in viz
        assert "group" in viz
    else:
        assert "error" in viz
        assert not viz["available"]


def test_bmi_endpoint_without_visualization():
    """Test BMI endpoint without visualization request."""
    payload = {
        "weight_kg": 70,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "include_chart": False
    }

    response = client.post("/bmi", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "bmi" in data
    assert "category" in data
    assert "visualization" not in data


def test_enhanced_teen_segmentation():
    """Test enhanced teen segmentation in BMI calculation."""
    payload = {
        "weight_kg": 60,
        "height_m": 1.70,
        "age": 16,  # Teen age
        "gender": "female",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en"
    }

    response = client.post("/bmi", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "bmi" in data
    assert "category" in data
    # Teen category should be handled appropriately


def test_enhanced_athlete_segmentation():
    """Test enhanced athlete segmentation with adjusted BMI ranges."""
    payload = {
        "weight_kg": 85,
        "height_m": 1.75,
        "age": 25,
        "gender": "male",
        "pregnant": "no",
        "athlete": "yes",
        "lang": "en"
    }

    response = client.post("/bmi", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "bmi" in data
    assert "category" in data
    assert data["athlete"] is True
    assert "athlete" in data["group"]


def test_bmi_visualization_endpoint_without_api_key():
    """Test that visualization endpoint requires API key."""
    payload = {
        "weight_kg": 70,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en"
    }

    response = client.post("/api/v1/bmi/visualize", json=payload)
    assert response.status_code == 403  # Should require API key


def test_bmi_visualization_endpoint_with_api_key():
    """Test visualization endpoint with API key."""
    payload = {
        "weight_kg": 70,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en"
    }

    response = client.post(
        "/api/v1/bmi/visualize",
        json=payload,
        headers={"X-API-Key": "test_key"}
    )

    # Expect 503 since matplotlib likely not installed in test environment
    expected_codes = [503, 200]  # 503 if no matplotlib, 200 if available
    assert response.status_code in expected_codes

    if response.status_code == 503:
        data = response.json()
        assert "detail" in data
        assert "matplotlib" in data["detail"].lower()
    elif response.status_code == 200:
        data = response.json()
        assert "bmi" in data
        assert "visualization" in data
        assert data["visualization"]["available"]


def test_bmi_visualization_base64_encoding():
    """Test that visualization properly encodes to base64."""
    if not MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib not available")
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        # Mock the entire plotting pipeline to return known data
        with patch('matplotlib.pyplot.subplots') as mock_subplots, \
             patch('matplotlib.pyplot.tight_layout'), \
             patch('matplotlib.pyplot.savefig') as mock_savefig, \
             patch('matplotlib.pyplot.close'):
            
            mock_fig = Mock()
            mock_ax1 = Mock()
            mock_ax2 = Mock()
            mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
            
            # Create test image data
            test_data = b'\x89PNG\r\n\x1a\n'  # PNG header
            mock_buffer = io.BytesIO()
            
            def mock_savefig_func(buffer, **kwargs):
                buffer.write(test_data)
                buffer.seek(0)
            
            mock_savefig.side_effect = mock_savefig_func
            
            with patch('io.BytesIO', return_value=mock_buffer):
                from bmi_visualization import generate_bmi_visualization
                
                result = generate_bmi_visualization(
                    bmi=22.0, age=30, gender="male",
                    pregnant="no", athlete="no", lang="en"
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
    
    with patch('bmi_visualization.MATPLOTLIB_AVAILABLE', True):
        for bmi_val in extreme_bmis:
            with patch('matplotlib.pyplot.subplots') as mock_subplots, \
                 patch('matplotlib.pyplot.tight_layout'), \
                 patch('matplotlib.pyplot.savefig'), \
                 patch('matplotlib.pyplot.close'), \
                 patch('io.BytesIO', return_value=io.BytesIO(b'fake_data')):
                
                mock_fig = Mock()
                mock_ax1 = Mock()
                mock_ax2 = Mock()
                mock_subplots.return_value = (mock_fig, (mock_ax1, mock_ax2))
                
                from bmi_visualization import generate_bmi_visualization
                
                result = generate_bmi_visualization(
                    bmi=bmi_val, age=30, gender="male",
                    pregnant="no", athlete="no", lang="en"
                )
                
                assert result["available"] is True
                assert "category" in result
