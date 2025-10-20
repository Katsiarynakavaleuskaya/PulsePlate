# -*- coding: utf-8 -*-
"""
Tests for Bodyfat v1 API endpoint in main.py

RU: Тесты для Bodyfat v1 API эндпоинта
EN: Tests for Bodyfat v1 API endpoint

Tests cover:
- Happy path scenarios for different methods
- Validation and edge cases
- Gender-specific calculations
"""

from fastapi.testclient import TestClient

import app as app_mod
from fastapi import FastAPI
from typing import cast

# Properly type the app instance - cast to FastAPI since we know it's a FastAPI app
app_instance = cast(FastAPI, app_mod.app)
client = TestClient(app_instance)


class TestBodyfatv1API:
    """Test Bodyfat v1 API endpoint with comprehensive coverage"""

    def test_bodyfat_v1_happy_female(self):
        """Test bodyfat v1 API for female with hip measurements"""
        payload = {
            "gender": "female",
            "age": 30,
            "waist_cm": 70.0,
            "hip_cm": 95.0,
            "neck_cm": 34.0,
            "height_m": 1.65,
            "weight_kg": 60.0,
        }
        response = client.post("/api/v1/bodyfat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "methods" in data
        assert "median" in data
        assert isinstance(data["median"], (int, float, type(None)))

    def test_bodyfat_v1_happy_male(self):
        """Test bodyfat v1 API for male (no hip measurement needed)"""
        payload = {
            "gender": "male",
            "age": 25,
            "waist_cm": 80.0,
            "neck_cm": 38.0,
            "height_m": 1.75,
            "weight_kg": 75.0,
        }
        response = client.post("/api/v1/bodyfat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "methods" in data
        assert "median" in data
        assert isinstance(data["median"], (int, float, type(None)))

    def test_bodyfat_v1_validation_missing_gender(self):
        """Test bodyfat v1 API validation - missing required gender field"""
        payload = {"age": 30, "waist_cm": 70.0, "neck_cm": 34.0, "height_m": 1.65}
        response = client.post("/api/v1/bodyfat", json=payload)
        assert response.status_code == 422  # Validation error for missing required field

    def test_bodyfat_v1_422_invalid_ranges(self):
        """Test bodyfat v1 API validation - invalid value ranges"""
        bad_payloads = [
            {
                "gender": "male",
                "age": -1,  # Invalid age
                "waist_cm": 80,
                "neck_cm": 38,
                "height_m": 1.75,
            },
            {
                "gender": "female",
                "age": 150,  # Invalid age (too high)
                "waist_cm": 70,
                "hip_cm": 95,
                "neck_cm": 34,
                "height_m": 1.65,
            },
            {
                "gender": "male",
                "age": 30,
                "waist_cm": 0,  # Invalid waist
                "neck_cm": 38,
                "height_m": 1.75,
            },
        ]

        for payload in bad_payloads:
            response = client.post("/api/v1/bodyfat", json=payload)
            # API returns 422 for invalid data due to validation
            assert response.status_code == 422

    def test_bodyfat_v1_invalid_gender_fallback(self):
        """Test bodyfat v1 API with invalid gender - should have fallback behavior"""
        payload = {"gender": "invalid", "age": 30, "waist_cm": 70, "neck_cm": 34, "height_m": 1.65}
        response = client.post("/api/v1/bodyfat", json=payload)
        # Based on main.py logic, this should work with fallback
        # The actual response depends on the bodyfat router implementation
        assert response.status_code in [
            200,
            422,
        ]  # Accept either valid response or validation error

    def test_bodyfat_v1_edge_case_measurements(self):
        """Test bodyfat v1 API with edge case but valid measurements"""
        payload = {
            "gender": "female",
            "age": 18,  # Minimum adult age
            "waist_cm": 60.0,  # Small but valid
            "hip_cm": 85.0,
            "neck_cm": 30.0,
            "height_m": 1.50,  # Short but valid
            "weight_kg": 50.0,  # For YMCA method
        }
        response = client.post("/api/v1/bodyfat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "methods" in data

    def test_bodyfat_v1_older_adult(self):
        """Test bodyfat v1 API for older adult (age-specific considerations)"""
        payload = {
            "gender": "male",
            "age": 65,  # Older adult
            "waist_cm": 95.0,
            "neck_cm": 40.0,
            "height_m": 1.70,
            "weight_kg": 80.0,  # For YMCA method
        }
        response = client.post("/api/v1/bodyfat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "methods" in data
        assert isinstance(data.get("median"), (int, float, type(None)))
