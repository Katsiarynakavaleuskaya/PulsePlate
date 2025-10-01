# -*- coding: utf-8 -*-
"""
Tests for BMI v1 API endpoint in app module.

RU: Тесты для BMI v1 API эндпоинта (модуль app), не main.py.
EN: Tests for BMI v1 API endpoint (app module).

Tests cover:
- Happy path scenarios
- Validation errors (422)
- Edge cases and boundary values
- Authentication scenarios
"""

import os
from typing import cast

from fastapi.testclient import TestClient
from starlette.types import ASGIApp

import app as app_mod

client = TestClient(cast(ASGIApp, app_mod.app))


class TestBMIv1API:
    """Test BMI v1 API endpoint with comprehensive coverage"""

    def setup_method(self):
        """Setup test environment"""
        os.environ["API_KEY"] = "test_key"

    def test_bmi_v1_happy_path_general(self):
        """Test BMI v1 API happy path for general population"""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "group": "general",
            "age": 30,
            "gender": "male",
            "lang": "en",
        }
        response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert data["bmi"] > 0
        assert "category" in data
        assert data["group"] == "general"

    def test_bmi_v1_happy_path_athlete(self):
        """Test BMI v1 API for athlete population"""
        payload = {
            "weight_kg": 80.0,
            "height_cm": 180.0,
            "group": "athlete",
            "age": 25,
            "gender": "male",
            "athlete": "yes",
            "lang": "en",
        }
        response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200
        data = response.json()
        assert data["athlete"] is True
        assert data["group"] == "athlete"

    def test_bmi_v1_pregnant_category(self):
        """Test BMI v1 API for pregnant women"""
        payload = {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "group": "general",
            "age": 28,
            "gender": "female",
            "pregnant": "yes",
            "lang": "en",
        }
        response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200
        data = response.json()
        assert data["category"] is None  # BMI not valid during pregnancy
        assert "pregnancy" in data["note"].lower()

    def test_bmi_v1_with_waist_risk(self):
        """Test BMI v1 API with waist circumference risk assessment"""
        payload = {
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "group": "general",
            "age": 35,
            "gender": "male",
            "waist_cm": 105.0,  # High risk for males (>102)
            "lang": "en",
        }
        response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200
        data = response.json()
        assert "risk" in data["note"].lower()

    def test_bmi_v1_422_missing_required_fields(self):
        """Test BMI v1 API validation - missing required fields"""
        bad_payloads = [
            {"weight_kg": 70},  # Missing height_cm
            {"height_cm": 170},  # Missing weight_kg
            {},  # Missing both
        ]

        for payload in bad_payloads:
            response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
            assert response.status_code == 422

    def test_bmi_v1_422_invalid_values(self):
        """Test BMI v1 API validation - invalid value ranges"""
        bad_payloads = [
            {"weight_kg": 0, "height_cm": 170, "group": "general"},  # Zero weight
            {"weight_kg": 70, "height_cm": 0, "group": "general"},  # Zero height
            {"weight_kg": -10, "height_cm": 150, "group": "general"},  # Negative weight
            {"weight_kg": 70, "height_cm": -10, "group": "general"},  # Negative height
        ]

        for payload in bad_payloads:
            response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
            assert response.status_code == 422

    def test_bmi_v1_realistic_validation(self):
        """Test BMI v1 API realistic value validation"""
        # Extremely low BMI should fail validation
        payload = {
            "weight_kg": 1.0,  # Unrealistically low for height
            "height_cm": 170.0,
            "group": "general",
        }
        response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == 422

    def test_bmi_v1_public_access_no_key(self):
        """Test BMI v1 API is publicly accessible (no API key required)"""
        payload = {"weight_kg": 70.0, "height_cm": 170.0, "group": "general"}

        # BMI endpoint is now public - should work without API key
        response = client.post("/api/v1/bmi", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert data["bmi"] > 0

    def test_bmi_v1_localization_russian(self):
        """Test BMI v1 API with Russian localization"""
        payload = {"weight_kg": 70.0, "height_cm": 170.0, "group": "general", "lang": "ru"}
        response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200

    def test_bmi_v1_localization_spanish(self):
        """Test BMI v1 API with Spanish localization"""
        payload = {"weight_kg": 70.0, "height_cm": 170.0, "group": "general", "lang": "es"}
        response = client.post("/api/v1/bmi", json=payload, headers={"X-API-Key": "test_key"})
        assert response.status_code == 200
