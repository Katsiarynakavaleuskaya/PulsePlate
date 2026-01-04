"""
Shared fixtures for app group tests.
Provides reusable setup for environment variables and test clients.
"""

from typing import Generator, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app as app_mod


def assert_vip_response(response, expected_status_codes=None, expected_data_fields=None):
    """
    Helper function to assert VIP API responses without conditionals in tests.

    Args:
        response: The HTTP response object
        expected_status_codes: List of acceptable status codes (default: [200, 403])
        expected_data_fields: Dict of expected fields in response data (only checked for 200 status)
    """
    if expected_status_codes is None:
        expected_status_codes = [200, 403]

    assert response.status_code in expected_status_codes, (
        f"Expected status code in {expected_status_codes}, got {response.status_code}"
    )

    if response.status_code == 200 and expected_data_fields:
        # Safely parse JSON response
        try:
            data = response.json()
        except Exception as e:
            assert False, (
                f"Failed to parse JSON response: {e}. Response text: {response.text[:200]}"
            )

        for field, expected_value in expected_data_fields.items():
            # Check that the field exists in the response data
            assert field in data, (
                f"Expected field '{field}' not found in response data. Available fields: {list(data.keys())}"
            )

            if expected_value == "exists":
                # Just check that the field exists (already verified above)
                continue
            elif isinstance(expected_value, str) and expected_value.startswith("contains:"):
                # Handle "contains:" prefix for partial string matching
                search_text = expected_value[9:]  # Remove "contains:" prefix
                field_value = data[field]

                # Ensure the field value is a string for contains check
                if not isinstance(field_value, str):
                    field_value = str(field_value)

                assert search_text in field_value, (
                    f"Expected '{search_text}' to be contained in field '{field}' (value: '{field_value}')"
                )
            else:
                assert data[field] == expected_value, (
                    f"Expected field '{field}' to equal {expected_value}, got {data[field]}"
                )


@pytest.fixture
def app_test_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """
    Provides a TestClient instance for app tests with proper environment setup.

    Sets up common environment variables and provides a configured TestClient.
    Environment variables are automatically restored after each test.
    """
    # Set up environment variables using monkeypatch for automatic cleanup
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    # Create test client with proper typing
    app_instance = cast(FastAPI, app_mod.app)
    client = TestClient(app_instance)

    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def app_with_api_key(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """
    Provides a TestClient with API key authentication enabled.

    Sets up strict API key mode for testing authentication flows.
    Environment variables are automatically restored after each test.
    """
    # Set up environment variables for API key testing using monkeypatch
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("API_KEY", "test_key")

    # Create test client with proper typing
    app_instance = cast(FastAPI, app_mod.app)
    client = TestClient(app_instance)

    try:
        yield client
    finally:
        client.close()


@pytest.fixture
def test_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """
    Alias for app_test_client for backward compatibility.

    Provides a TestClient instance for app tests with proper environment setup.
    This fixture is used by test_app_health_and_root.py and test_app_bodyfat_v1.py.
    """
    # Set up environment variables using monkeypatch for automatic cleanup
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("FEATURE_PREMIUM_NUTRITION", "true")

    # Create test client with proper typing
    app_instance = cast(FastAPI, app_mod.app)
    client = TestClient(app_instance)

    try:
        yield client
    finally:
        client.close()
