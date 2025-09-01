# -*- coding: utf-8 -*-
"""
Test BMI visualization endpoint functionality.
Tests both the enhanced BMI endpoint and dedicated visualization endpoint.
"""

import importlib
from fastapi.testclient import TestClient

app_module = importlib.import_module("app")
client = TestClient(app_module.app)


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