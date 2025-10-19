"""
Tests for HTTP client configuration.

RU: Тесты для конфигурации HTTP клиентов.
EN: Tests for HTTP client configuration.
"""

import pytest
from core.food_apis.http_config import HTTPClientConfig


class TestHTTPClientConfig:
    """Test HTTPClientConfig class."""

    def test_get_timeout_returns_default_value(self):
        """Test that get_timeout returns the default timeout value."""
        timeout = HTTPClientConfig.get_timeout()
        assert timeout == 10.0
        assert isinstance(timeout, float)

    def test_create_client_with_default_timeout(self):
        """Test creating client with default timeout."""
        client = HTTPClientConfig.create_client()
        assert client.timeout.connect == 10.0
        assert client.timeout.read == 10.0
        assert client.timeout.write == 10.0
        assert client.timeout.pool == 10.0

    def test_create_client_with_custom_timeout(self):
        """Test creating client with custom timeout."""
        custom_timeout = 5.0
        client = HTTPClientConfig.create_client(timeout=custom_timeout)
        assert client.timeout.connect == custom_timeout
        assert client.timeout.read == custom_timeout
        assert client.timeout.write == custom_timeout
        assert client.timeout.pool == custom_timeout

    def test_create_client_with_none_timeout_uses_default(self):
        """Test creating client with None timeout uses default."""
        client = HTTPClientConfig.create_client(timeout=None)
        assert client.timeout.connect == 10.0
        assert client.timeout.read == 10.0
        assert client.timeout.write == 10.0
        assert client.timeout.pool == 10.0
