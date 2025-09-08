"""
Simple debug test for premium week endpoint.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as app_mod


class TestPremiumWeekSimpleDebug:
    """Simple debug test for premium week endpoint."""

    def test_premium_week_endpoint_debug(self):
        """Test premium week endpoint with debug info."""
        client = TestClient(app_mod.app)

        with patch.dict(os.environ, {"API_KEY": "test_key"}):
            payload = {
                "sex": "male",
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "activity": "moderate",
                "goal": "maintain",
                "lang": "en",
                "diet_flags": [],
            }

            response = client.post(
                "/api/v1/premium/plan/week",
                json=payload,
                headers={"X-API-Key": "test_key"},
            )

            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")

            # Should succeed
            assert response.status_code == 200
            data = response.json()
            assert "daily_menus" in data
            assert "weekly_coverage" in data
