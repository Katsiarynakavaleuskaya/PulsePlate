"""
Shared fixtures for app group tests.
Provides reusable setup for environment variables and test clients.
"""

from typing import Generator, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app as app_mod


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
