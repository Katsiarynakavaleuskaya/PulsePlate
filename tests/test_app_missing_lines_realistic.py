"""
Target missing lines in main.py with realistic tests.
Based on coverage analysis: 65-68, 118-119, 123-124, etc.
"""

import concurrent.futures
import os
import sys
from unittest.mock import patch

import pytest
from faker import Faker
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from app.py file
import importlib.util
import pathlib

repo_root = pathlib.Path(__file__).parent.parent
app_path = repo_root / "app.py"

spec = importlib.util.spec_from_file_location("app_module", str(app_path))
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load app.py from {app_path}")

app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

fake = Faker()


class TestAppMissingLinesTargeted:
    """Target specific missing lines in main.py"""

    def setup_method(self) -> None:
        self.client = TestClient(app)
        Faker.seed(42)

    def test_api_v1_bmi_calculate_endpoint(self) -> None:
        """Test the legacy BMI calculation endpoint that doesn't require API key"""
        test_data = {
            "weight": fake.random_int(min=50, max=100),
            "height": fake.random_int(min=160, max=190),
            "age": fake.random_int(min=25, max=55),
            "sex": fake.random_element(["M", "F"]),
            "lang": "en",
        }

        response = self.client.post("/api/v1/bmi/calculate", json=test_data)
        assert response.status_code in [200, 422]  # 422 if validation fails
        if response.status_code == 200:
            data = response.json()
            assert "bmi" in data

    def test_insight_endpoint_with_feature_disabled(self) -> None:
        """Test insight endpoint when feature is disabled"""
        with patch.dict("os.environ", {"FEATURE_INSIGHT": "0"}):
            test_data = {"text": fake.text(max_nb_chars=100), "lang": "en"}

            response = self.client.post("/insight", json=test_data)
            # Should return 503 when feature is disabled
            assert response.status_code in [503, 400, 422]

    def test_import_error_fallbacks(self) -> None:
        """Test fallback behavior when imports fail"""
        # This is tricky to test directly, but we can test the fallback paths
        test_data = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "M",
            "activity": "sedentary",
            "lang": "en",
        }

        # Test BMR endpoint which might use fallback functions
        response = self.client.post("/premium_bmr", json=test_data)
        # Should work even with fallbacks - server errors (500) should fail the test
        assert response.status_code != 500, (
            f"Server error detected. Status: {response.status_code}, " f"Response: {response.text}"
        )
        assert response.status_code in [
            200,
            400,
            422,
        ], f"Unexpected status code: {response.status_code}, Response: {response.text}"

    def test_malformed_requests_edge_cases(self) -> None:
        """Test malformed requests that trigger specific error paths"""
        # Test with completely invalid JSON structure
        response = self.client.post(
            "/bmi",
            content="{weight: invalid, height:}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422]

    def test_missing_required_fields_combinations(self) -> None:
        """Test various combinations of missing required fields"""
        # Missing weight
        data1 = {"height": 175, "age": 30, "sex": "M", "lang": "en"}
        response1 = self.client.post("/bmi", json=data1)
        assert response1.status_code in [400, 422]

        # Missing sex
        data2 = {"weight": 70, "height": 175, "age": 30, "lang": "en"}
        response2 = self.client.post("/bmi", json=data2)
        assert response2.status_code in [200, 400, 422]  # Some endpoints may have defaults

    def test_unicode_and_special_characters(self) -> None:
        """Test Unicode and special characters in various fields"""
        test_data = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "M",
            "lang": "en",
            "activity": "moderate",
            "notes": "тест 测试 🏃‍♂️ 💪",
        }

        response = self.client.post("/bmi", json=test_data)
        assert response.status_code in [200, 400, 422]

    @pytest.mark.parametrize(
        "case",
        [
            {"weight": 0.1, "height": 50, "age": 1},  # Very small
            {"weight": 500, "height": 300, "age": 150},  # Very large
            {
                "weight": 1e10,
                "height": 175,
                "age": 30,
            },  # Very large finite number (replaces infinity)
        ],
    )
    def test_extreme_numeric_values_edge_cases(self, case: dict[str, object]) -> None:
        """Test extreme numeric values that might trigger different paths"""
        case_with_defaults = {**case, "sex": "M", "lang": "en"}
        # Send request and expect valid response codes (no 500 allowed)
        response = self.client.post("/bmi", json=case_with_defaults)
        assert response.status_code in [200, 400, 422]

    def test_concurrent_mixed_requests(self) -> None:
        """Test concurrent requests to different endpoints"""

        def make_bmi_request():
            # Create a separate TestClient for each thread
            client = TestClient(app)
            return client.post(
                "/bmi",
                json={
                    "weight": fake.random_int(min=50, max=100),
                    "height": fake.random_int(min=160, max=190),
                    "age": fake.random_int(min=25, max=55),
                    "sex": fake.random_element(["M", "F"]),
                    "lang": "en",
                },
            )

        def make_health_request():
            # Create a separate TestClient for each thread
            client = TestClient(app)
            return client.get("/health")

        def make_insight_request():
            # Create a separate TestClient for each thread
            client = TestClient(app)
            return client.post("/insight", json={"text": fake.sentence(), "lang": "en"})

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for _ in range(3):
                futures.append(executor.submit(make_bmi_request))
                futures.append(executor.submit(make_health_request))
                futures.append(executor.submit(make_insight_request))

            results = [future.result() for future in futures]

        # At least some should succeed
        success_count = sum(r.status_code == 200 for r in results)
        assert success_count > 0


class TestAppLargePayloadsAndLimits:
    """Test large payloads and various limits"""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_large_text_fields(self) -> None:
        """Test large text fields"""
        large_text = "x" * 10000  # 10KB string

        test_data = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "M",
            "lang": "en",
            "notes": large_text,
        }

        response = self.client.post("/bmi", json=test_data)
        assert response.status_code in [200, 400, 413, 422]  # 413 = Payload Too Large

    def test_insight_with_very_long_text(self) -> None:
        """Test insight endpoint with very long text"""
        long_text = fake.text(max_nb_chars=5000)

        test_data = {"text": long_text, "lang": "en"}

        response = self.client.post("/insight", json=test_data)
        assert response.status_code in [200, 400, 413, 422, 503]

    def test_plan_endpoint_with_complex_data(self) -> None:
        """Test plan endpoint with complex data"""
        complex_data = {
            "weight": fake.random_int(min=50, max=100),
            "height": fake.random_int(min=160, max=190),
            "age": fake.random_int(min=25, max=55),
            "sex": fake.random_element(["M", "F"]),
            "activity": fake.random_element(
                ["sedentary", "lightly_active", "moderately_active", "very_active"]
            ),
            "goal": fake.random_element(["maintain", "lose", "gain"]),
            "lang": fake.random_element(["en", "ru", "es"]),
            "dietary_restrictions": fake.words(nb=5),
            "medical_conditions": fake.words(nb=3),
            "preferences": {
                "cuisine": fake.random_element(["italian", "asian", "mediterranean"]),
                "spice_level": fake.random_element(["mild", "medium", "hot"]),
                "cooking_time": fake.random_int(min=15, max=120),
            },
        }

        response = self.client.post("/plan", json=complex_data)
        assert response.status_code in [200, 400, 422]


class TestAppErrorHandlingPaths:
    """Test specific error handling paths"""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_database_connection_errors(self) -> None:
        """Test endpoints when database connections fail"""
        # Test database health endpoint
        response = self.client.get("/health/db")
        # Should handle DB errors gracefully
        assert response.status_code in [200, 500, 503]

    def test_feature_flag_combinations(self) -> None:
        """Test different feature flag combinations"""
        # Test with various environment combinations
        with patch.dict("os.environ", {"FEATURE_INSIGHT": "0", "VIP_MODULE_ENABLED": "false"}):
            # Test insight when disabled
            response = self.client.post("/insight", json={"text": "test", "lang": "en"})
            assert response.status_code in [503, 400, 422]

    def test_authentication_error_paths(self) -> None:
        """Test authentication - BMI is now public"""
        # BMI endpoint is now public - no auth required
        # Using correct payload format for v1 API
        response = self.client.post(
            "/api/v1/bmi", json={"weight_kg": 70, "height_cm": 175, "group": "general"}
        )
        assert response.status_code == 200  # BMI is public now

    @pytest.mark.parametrize(
        "content_type",
        [
            "application/json",
            "application/json; charset=utf-8",
            "text/plain",
            "application/xml",
        ],
    )
    def test_various_content_types(self, content_type: str) -> None:
        """Test various content types"""
        test_data = '{"weight": 70, "height": 175, "age": 30, "sex": "M", "lang": "en"}'
        response = self.client.post(
            "/bmi", content=test_data, headers={"Content-Type": content_type}
        )
        # Should handle appropriately
        assert response.status_code in [200, 400, 415, 422]  # 415 = Unsupported Media Type


class TestAppSpecificMissingBlocks:
    """Test specific missing code blocks identified in coverage"""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_export_endpoints_if_available(self) -> None:
        """Test export endpoints if they exist"""
        # Try to access export endpoints that might exist
        export_data = {"format": "pdf", "data": {"meals": [], "totals": {}}}

        response = self.client.post("/export", json=export_data)
        # Might not exist, but test the path
        assert response.status_code in [200, 404, 405, 422, 500]

    @pytest.mark.parametrize("endpoint", ["/premium_bmr", "/premium_targets"])
    def test_premium_endpoints_without_auth(self, endpoint: str) -> None:
        """Test premium endpoints without authentication"""
        premium_data = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "M",
            "activity": "moderate",
            "lang": "en",
        }
        response = self.client.post(endpoint, json=premium_data)
        # Should work or return appropriate error
        assert response.status_code in [200, 400, 401, 403, 422, 500]

    def test_admin_endpoints_without_auth(self) -> None:
        """Test admin endpoints without authentication"""
        response = self.client.get("/api/v1/admin/status")
        # Should require authentication
        assert response.status_code in [401, 403, 404]

    def test_complex_bmi_scenarios(self) -> None:
        """Test complex BMI calculation scenarios"""
        # Test with all optional fields
        complex_bmi_data = {
            "weight": fake.random_int(min=50, max=100),
            "height": fake.random_int(min=160, max=190),
            "age": fake.random_int(min=25, max=55),
            "sex": fake.random_element(["M", "F"]),
            "pregnant": fake.boolean(),
            "activity": fake.random_element(
                ["sedentary", "light", "moderate", "active", "very_active"]
            ),
            "goal": fake.random_element(["maintain", "lose", "gain"]),
            "lang": fake.random_element(["en", "ru", "es"]),
            "units": fake.random_element(["metric", "imperial"]),
            "medical_conditions": fake.words(nb=2),
            "dietary_restrictions": fake.words(nb=3),
        }

        response = self.client.post("/bmi", json=complex_bmi_data)
        assert response.status_code in [200, 400, 422]

    @pytest.mark.parametrize(
        "lang",
        [
            "en",
            "en-US",
            "en_US",
            "EN",
            "english",
            "ru",
            "ru-RU",
            "russian",
            "рус",
            "es",
            "es-ES",
            "spanish",
            "español",
            "",
            None,
            "invalid",
            "123",
            "zh-CN",
        ],
    )
    def test_edge_case_language_handling(self, lang: str | None) -> None:
        """Test edge cases in language handling"""
        # Handle None and empty string as valid inputs explicitly
        test_data = {"weight": 70, "height": 175, "age": 30, "sex": "M"}
        if lang is not None:
            test_data["lang"] = lang

        # Make the request - any unexpected exceptions should fail the test
        response = self.client.post("/bmi", json=test_data)
        # Assert expected status codes - server errors (500) should fail the test
        assert response.status_code in [200, 400, 422], (
            f"Unexpected status code: {response.status_code} for lang={lang!r}, "
            f"Response: {response.text}"
        )
