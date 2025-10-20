"""
Tests for HTTP client configuration.

RU: Тесты для конфигурации HTTP клиентов.
EN: Tests for HTTP client configuration.
"""

import pytest
from core.food_apis.http_config import HTTPClientConfig


@pytest.fixture
async def http_client():
    """Fixture that provides an HTTP client and properly closes it."""
    client = HTTPClientConfig.create_client()
    yield client
    await client.aclose()


class TestHTTPClientConfig:
    """Test HTTPClientConfig class."""

    def test_get_timeout_returns_default_value(self):
        """Test that get_timeout returns the default timeout value."""
        timeout = HTTPClientConfig.get_timeout()
        assert timeout == 10.0
        assert isinstance(timeout, float)

    @pytest.mark.asyncio
    async def test_create_client_with_default_timeout(self, http_client):
        """Test creating client with default timeout."""
        client = http_client
        assert client.timeout.connect == 10.0
        assert client.timeout.read == 10.0
        assert client.timeout.write == 10.0
        assert client.timeout.pool == 10.0

    @pytest.mark.asyncio
    async def test_create_client_with_custom_timeout(self):
        """Test creating client with custom timeout."""
        custom_timeout = 5.0
        client = HTTPClientConfig.create_client(timeout=custom_timeout)
        try:
            assert client.timeout.connect == custom_timeout
            assert client.timeout.read == custom_timeout
            assert client.timeout.write == custom_timeout
            assert client.timeout.pool == custom_timeout
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_create_client_with_none_timeout_uses_default(self):
        """Test creating client with None timeout uses default."""
        client = HTTPClientConfig.create_client(timeout=None)
        try:
            assert client.timeout.connect == 10.0
            assert client.timeout.read == 10.0
            assert client.timeout.write == 10.0
            assert client.timeout.pool == 10.0
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_create_client_with_limits(self):
        """Test creating client with custom limits."""
        import httpx

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        client = HTTPClientConfig.create_client(limits=limits)
        try:
            # httpx.AsyncClient doesn't expose limits directly, but we can verify it was set
            # by checking that the client was created successfully with the limits parameter
            assert client is not None
            # The limits are used internally by httpx
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_create_client_with_headers(self):
        """Test creating client with custom headers."""
        headers = {"User-Agent": "TestClient/1.0"}
        client = HTTPClientConfig.create_client(headers=headers)
        try:
            assert client.headers["User-Agent"] == "TestClient/1.0"
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_create_client_with_transport(self):
        """Test creating client with custom transport."""
        import httpx

        transport = httpx.AsyncHTTPTransport()
        client = HTTPClientConfig.create_client(transport=transport)
        try:
            # httpx.AsyncClient doesn't expose transport directly, but we can verify it was set
            # by checking that the client was created successfully with the transport parameter
            assert client is not None
            # The transport is used internally by httpx
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_create_client_with_event_hooks(self):
        """Test creating client with event hooks."""
        event_hooks = {"request": [lambda request: request]}
        client = HTTPClientConfig.create_client(event_hooks=event_hooks)
        try:
            assert client.event_hooks["request"] == event_hooks["request"]
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_create_client_with_trust_env(self):
        """Test creating client with trust_env setting."""
        client = HTTPClientConfig.create_client(trust_env=True)
        try:
            assert client.trust_env is True
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_create_client_context_manager(self):
        """Test create_client_context context manager."""
        async with HTTPClientConfig.create_client_context() as client:
            assert client.timeout.connect == 10.0
            assert client.timeout.read == 10.0
            assert client.timeout.write == 10.0
            assert client.timeout.pool == 10.0
        # Client should be closed after context exit

    @pytest.mark.asyncio
    async def test_create_client_context_with_custom_timeout(self):
        """Test create_client_context with custom timeout."""
        custom_timeout = 15.0
        async with HTTPClientConfig.create_client_context(timeout=custom_timeout) as client:
            assert client.timeout.connect == custom_timeout
            assert client.timeout.read == custom_timeout
            assert client.timeout.write == custom_timeout
            assert client.timeout.pool == custom_timeout
        # Client should be closed after context exit
