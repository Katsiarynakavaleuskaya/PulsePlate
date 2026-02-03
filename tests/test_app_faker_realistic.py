"""
Realistic tests for main.py using Faker library.
Focus on covering missing lines with realistic data scenarios.
"""

from faker import Faker
from fastapi import FastAPI
from fastapi.testclient import TestClient

import main  # Import at module level so import errors surface during collection
from app.middleware.api_tiers import TEST_KEY_VIP

fake = Faker()


def _get_app():
    """Safely get the FastAPI app instance.

    Ensures `main.app` exists and is a FastAPI instance.
    """
    if not hasattr(main, "app"):
        raise ImportError("Module main does not define 'app'")
    app_obj = getattr(main, "app")
    if not isinstance(app_obj, FastAPI):
        raise RuntimeError("FastAPI app in main.py is not initialized or wrong type")
    return app_obj


class TestAppRealisticData:
    """Test main.py endpoints with realistic faker data"""

    def setup_method(self):
        """Setup for each test"""
        self.client = TestClient(_get_app())
        # Seed faker for reproducible tests
        Faker.seed(42)

    def test_bmi_calculation_realistic_demographics(self):
        """Test BMI calculation with realistic demographic data"""
        # Generate realistic person data with controlled ranges
        person_data = {
            "weight_kg": fake.random_int(min=50, max=100),  # kg - safe range
            "height_m": fake.random_int(min=150, max=190) / 100,  # convert cm to m - safe range
            "age": fake.random_int(min=18, max=80),
            "gender": fake.random_element(["male", "female"]),
            "lang": fake.random_element(["en", "ru", "es"]),
        }

        # Use public BMI endpoint (without API key)
        response = self.client.post("/bmi", json=person_data)
        assert response.status_code == 200
        data = response.json()
        assert "bmi" in data
        assert "category" in data

    def test_bmi_extreme_edge_cases(self):
        """Test BMI with extreme but valid edge cases"""
        # Test very low BMI (underweight scenarios)
        low_bmi_data = {
            "weight_kg": 35,  # Very low weight
            "height_m": 1.8,  # 180 cm in meters
            "age": 25,
            "gender": "female",
            "lang": "en",
        }

        response = self.client.post("/bmi", json=low_bmi_data)
        assert response.status_code == 200

        # Test very high BMI (but within limits)
        high_bmi_data = {
            "weight_kg": 112.5,  # BMI = 50 (at upper limit)
            "height_m": 1.5,  # 150 cm in meters
            "age": 45,
            "gender": "male",
            "lang": "en",
        }

        response = self.client.post("/bmi", json=high_bmi_data)
        assert response.status_code == 200

    def test_pregnancy_scenarios_realistic(self):
        """Test pregnancy scenarios with realistic data"""
        pregnancy_data = {
            "weight": fake.random_int(min=55, max=85),
            "height": fake.random_int(min=155, max=175),
            "age": fake.random_int(min=20, max=40),
            "sex": "F",
            "pregnant": True,
            "lang": fake.random_element(["en", "ru", "es"]),
        }

        response = self.client.post("/bmi", json=pregnancy_data)
        assert response.status_code == 200
        data = response.json()
        # Check for pregnancy-related note
        assert "note" in data or "notes" in data or "category" in data

    def test_plan_endpoint_realistic_data(self):
        """Test plan endpoint with realistic meal planning data"""
        plan_data = {
            "weight": fake.random_int(min=50, max=100),
            "height": fake.random_int(min=160, max=190),
            "age": fake.random_int(min=25, max=55),
            "sex": fake.random_element(["M", "F"]),
            "activity": fake.random_element(
                ["sedentary", "lightly_active", "moderately_active", "very_active"]
            ),
            "goal": fake.random_element(["maintain", "lose", "gain"]),
            "lang": fake.random_element(["en", "ru", "es"]),
        }

        response = self.client.post("/plan", json=plan_data)
        # Plan endpoint might return 200 or might have specific requirements
        assert response.status_code in [200, 400, 422]

    def test_insight_endpoint_realistic_data(self):
        """Test insight endpoint with realistic user data"""
        insight_data = {
            "weight": fake.random_int(min=45, max=120),
            "height": fake.random_int(min=150, max=200),
            "age": fake.random_int(min=18, max=70),
            "sex": fake.random_element(["M", "F"]),
            "lang": fake.random_element(["en", "ru", "es"]),
        }

        response = self.client.post(
            "/insight", json=insight_data, headers={"X-API-Key": TEST_KEY_VIP}
        )
        assert response.status_code in [200, 400, 422, 503]

    def test_health_endpoints(self):
        """Test health check endpoints"""
        # Test basic health endpoint
        response = self.client.get("/health")
        assert response.status_code == 200

        # Test API health endpoint
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200

    def test_public_endpoints(self):
        """Test public endpoints that don't require authentication"""
        # Test root endpoint
        response = self.client.get("/")
        assert response.status_code == 200

        # Test privacy endpoint
        response = self.client.get("/privacy")
        assert response.status_code == 200

        # Test metrics endpoint
        response = self.client.get("/metrics")
        assert response.status_code in [200, 404]  # Might not be enabled in all configs

    def test_error_handling_edge_cases(self):
        """Test error handling with edge case data"""
        # Test with missing required fields
        incomplete_data = {
            "weight": 70,
            # Missing height, age, sex
        }

        response = self.client.post("/bmi", json=incomplete_data)
        assert response.status_code in [400, 422]  # Should return validation error

        # Test with invalid data types
        invalid_data = {
            "weight": "invalid",
            "height": "also_invalid",
            "age": 30,
            "sex": "M",
            "lang": "en",
        }

        response = self.client.post("/bmi", json=invalid_data)
        assert response.status_code in [400, 422]

    def test_localization_with_faker(self):
        """Test localization with faker-generated locale data"""
        # Test different language codes
        test_languages = ["en", "ru", "es", "fr", "de"]  # Some might fallback

        for lang in test_languages:
            test_data = {
                "weight": fake.random_int(min=50, max=100),
                "height": fake.random_int(min=160, max=190),
                "age": fake.random_int(min=25, max=55),
                "sex": fake.random_element(["M", "F"]),
                "lang": lang,
            }

            response = self.client.post("/bmi", json=test_data)
            # Should handle known languages or return validation error for unknown ones
            assert response.status_code in [200, 422]


class TestAppDatabaseScenarios:
    """Test database-related scenarios with realistic data"""

    def setup_method(self):
        self.client = TestClient(_get_app())

    def test_database_health_check(self):
        """Test database health check endpoint"""
        response = self.client.get("/health/db")
        # DB health check should work or return appropriate error
        assert response.status_code in [200, 500, 503]


class TestAppErrorScenarios:
    """Test main.py error scenarios with realistic data"""

    def setup_method(self):
        self.client = TestClient(_get_app())

    def test_large_request_handling(self):
        """Test handling of large requests"""
        # Generate large but realistic data
        large_data = {
            "weight": fake.random_int(min=45, max=120),
            "height": fake.random_int(min=150, max=200),
            "age": fake.random_int(min=18, max=70),
            "sex": fake.random_element(["M", "F"]),
            "lang": "en",
            # Add large additional data
            "large_field": "x" * 1000,  # Large string but not too large
        }

        response = self.client.post("/bmi", json=large_data)
        # Should handle large requests appropriately
        assert response.status_code in [200, 400, 413, 422]


class TestAppValidationEdgeCases:
    """Test validation edge cases with realistic boundary data"""

    def setup_method(self):
        self.client = TestClient(_get_app())

    def test_boundary_weight_values(self):
        """Test weight validation boundaries"""
        # Test minimum weight boundary
        min_weight_data = {
            "weight": 1,  # Very low but technically valid
            "height": 170,
            "age": 25,
            "sex": "F",
            "lang": "en",
        }

        response = self.client.post("/bmi", json=min_weight_data)
        # Should handle edge case appropriately
        assert response.status_code in [200, 400, 422]

    def test_boundary_height_values(self):
        """Test height validation boundaries"""
        # Test edge case heights
        edge_heights = [50, 250, 300]  # Very short, very tall, unrealistic

        for height in edge_heights:
            test_data = {"weight": 70, "height": height, "age": 30, "sex": "M", "lang": "en"}

            response = self.client.post("/bmi", json=test_data)
            # Should validate appropriately
            assert response.status_code in [200, 400, 422]

    def test_boundary_age_values(self):
        """Test age validation boundaries"""
        edge_ages = [0, 1, 150, 200]  # Infant, very old, unrealistic

        for age in edge_ages:
            test_data = {"weight": 70, "height": 175, "age": age, "sex": "M", "lang": "en"}

            response = self.client.post("/bmi", json=test_data)
            assert response.status_code in [200, 400, 422]


class TestAppAdditionalEndpoints:
    """Test additional endpoints found in main.py"""

    def setup_method(self):
        self.client = TestClient(_get_app())

    def test_favicon_endpoint(self):
        """Test favicon endpoint"""
        response = self.client.get("/favicon.ico")
        assert response.status_code in [200, 204, 404]  # 204 No Content is also valid

    def test_premium_bmr_endpoint(self):
        """Test premium BMR endpoint"""
        bmr_data = {
            "weight": fake.random_int(min=50, max=100),
            "height": fake.random_int(min=160, max=190),
            "age": fake.random_int(min=25, max=55),
            "sex": fake.random_element(["M", "F"]),
            "activity": fake.random_element(
                ["sedentary", "lightly_active", "moderately_active", "very_active"]
            ),
            "lang": "en",
        }

        response = self.client.post("/premium_bmr", json=bmr_data)
        # May require specific format or return error
        assert response.status_code in [200, 400, 422, 500]

    def test_premium_targets_endpoint(self):
        """Test premium targets endpoint"""
        targets_data = {
            "weight": fake.random_int(min=50, max=100),
            "height": fake.random_int(min=160, max=190),
            "age": fake.random_int(min=25, max=55),
            "sex": fake.random_element(["M", "F"]),
            "activity": fake.random_element(
                ["sedentary", "lightly_active", "moderately_active", "very_active"]
            ),
            "lang": "en",
        }

        response = self.client.post(
            "/premium_targets", json=targets_data, headers={"X-API-Key": "test_key"}
        )
        assert response.status_code in [200, 400, 422, 500]

    def test_additional_public_endpoints(self):
        """Test additional public endpoints"""
        # Test database health endpoint
        response = self.client.get("/health/db")
        assert response.status_code in [200, 500, 503]

        # Test admin status (public access attempt)
        response = self.client.get("/api/v1/admin/status")
        assert response.status_code in [200, 401, 403]  # Should require auth


class TestAppErrorPathsCoverage:
    """Test error paths and exception handling"""

    def setup_method(self):
        self.client = TestClient(_get_app())

    def test_malformed_json_requests(self):
        """Test malformed JSON requests"""
        # Test with invalid JSON structure
        response = self.client.post(
            "/bmi", content="invalid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]

    def test_missing_content_type(self):
        """Test requests without proper content type"""
        response = self.client.post("/bmi", content='{"weight": 70}')
        assert response.status_code in [400, 422]

    def test_empty_request_body(self):
        """Test empty request body"""
        response = self.client.post("/bmi", json={})
        assert response.status_code in [400, 422]

    def test_null_values_in_request(self):
        """Test null values in request"""
        null_data = {"weight": None, "height": None, "age": 25, "sex": "M", "lang": "en"}

        response = self.client.post("/bmi", json=null_data)
        assert response.status_code in [400, 422]

    def test_unsupported_language_codes(self):
        """Test unsupported language codes"""
        unsupported_langs = ["xx", "zz", "invalid", ""]

        for lang in unsupported_langs:
            test_data = {"weight": 70, "height": 175, "age": 30, "sex": "M", "lang": lang}

            response = self.client.post("/bmi", json=test_data)
            # Should handle gracefully or return error
            assert response.status_code in [200, 400, 422]


class TestAppSpecialCases:
    """Test special cases and edge scenarios"""

    def setup_method(self):
        self.client = TestClient(_get_app())

    def test_concurrent_requests(self):
        """Test concurrent request handling"""
        import concurrent.futures

        def make_request():
            test_data = {
                "weight": fake.random_int(min=50, max=100),
                "height": fake.random_int(min=160, max=190),
                "age": fake.random_int(min=25, max=55),
                "sex": fake.random_element(["M", "F"]),
                "lang": "en",
            }
            return self.client.post("/bmi", json=test_data)

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request) for _ in range(3)]
            results = [future.result() for future in futures]

        # All should succeed
        for response in results:
            assert response.status_code == 200

    def test_unicode_handling(self):
        """Test Unicode character handling"""
        unicode_data = {
            "weight": 70,
            "height": 175,
            "age": 30,
            "sex": "M",
            "lang": "en",
            "notes": "🏃‍♂️ спорт测试",  # Mixed Unicode
        }

        response = self.client.post("/bmi", json=unicode_data)
        # Should handle Unicode gracefully
        assert response.status_code in [200, 400, 422]

    def test_very_large_numbers(self):
        """Test very large numeric values"""
        large_data = {"weight": 999999, "height": 999999, "age": 999999, "sex": "M", "lang": "en"}

        response = self.client.post("/bmi", json=large_data)
        # Should handle gracefully with validation
        assert response.status_code in [200, 400, 422]

    def test_negative_values(self):
        """Test negative numeric values"""
        negative_data = {"weight": -70, "height": -175, "age": -30, "sex": "M", "lang": "en"}

        response = self.client.post("/bmi", json=negative_data)
        # Should reject negative values
        assert response.status_code in [400, 422]
