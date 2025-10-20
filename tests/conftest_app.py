"""
Shared fixtures for app group tests.
Provides reusable setup for environment variables and test clients.
"""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

import app as app_mod


@pytest.fixture
def app_test_client() -> Generator[TestClient, None, None]:
    """
    Provides a TestClient instance for app tests with proper environment setup.

    Sets up common environment variables and provides a configured TestClient.
    """
    # Set up environment variables
    os.environ["API_KEY"] = "test_key"
    os.environ["FEATURE_PREMIUM_NUTRITION"] = "true"

    # Create test client
    client = TestClient(app_mod.app)

    yield client

    # Cleanup (if needed)
    # Environment variables will be cleaned up by pytest automatically


@pytest.fixture
def app_with_api_key() -> Generator[TestClient, None, None]:
    """
    Provides a TestClient with API key authentication enabled.

    Sets up strict API key mode for testing authentication flows.
    """
    # Set up environment variables for API key testing
    os.environ["API_KEY_REQUIRED"] = "true"
    os.environ["API_KEY"] = "test_key"

    # Create test client
    client = TestClient(app_mod.app)

    yield client

    # Cleanup
    if "API_KEY_REQUIRED" in os.environ:
        del os.environ["API_KEY_REQUIRED"]
