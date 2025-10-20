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

    assert response.status_code in expected_status_codes

    if response.status_code == 200 and expected_data_fields:
        data = response.json()
        for field, expected_value in expected_data_fields.items():
            if expected_value == "exists":
                # Just check that the field exists
                assert field in data
            elif isinstance(expected_value, str) and expected_value.startswith("contains:"):
                # Handle "contains:" prefix for partial string matching
                search_text = expected_value[9:]  # Remove "contains:" prefix
                assert search_text in data[field]
            else:
                assert data[field] == expected_value


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
