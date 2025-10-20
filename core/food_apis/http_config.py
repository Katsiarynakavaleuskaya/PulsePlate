"""
HTTP Client Configuration

RU: Общая конфигурация для HTTP клиентов API.
EN: Shared configuration for API HTTP clients.

This module provides centralized HTTP client configuration to avoid
duplication across different API clients (USDA, Open Food Facts, etc.).
"""

import httpx
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager


class HTTPClientConfig:
    """Centralized HTTP client configuration."""

    # Default timeout for all API requests
    DEFAULT_TIMEOUT = 10.0

    @classmethod
    def create_client(
        cls,
        timeout: Optional[float] = None,
        *,
        limits: Optional[httpx.Limits] = None,
        headers: Optional[Dict[str, str]] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        event_hooks: Optional[Dict[str, Any]] = None,
        trust_env: Optional[bool] = None,
        **client_kwargs: Any,
    ) -> httpx.AsyncClient:
        """
        Create a configured httpx.AsyncClient.

        Lifecycle: the caller is responsible for closing the returned client
        (use `await client.aclose()`), or prefer the context-managed
        alternative `create_client_context()` below.

        Args:
            timeout: Request timeout in seconds (default: DEFAULT_TIMEOUT)
            limits: Optional connection limits
            headers: Optional default headers
            transport: Optional custom transport
            event_hooks: Optional httpx event hooks
            trust_env: Whether to read proxy config from environment
            **client_kwargs: Any other httpx.AsyncClient kwargs to forward

        Returns:
            Configured httpx.AsyncClient instance
        """
        init_kwargs: Dict[str, Any] = {
            "timeout": timeout or cls.DEFAULT_TIMEOUT,
            **client_kwargs,
        }
        if limits is not None:
            init_kwargs["limits"] = limits
        if headers is not None:
            init_kwargs["headers"] = headers
        if transport is not None:
            init_kwargs["transport"] = transport
        if event_hooks is not None:
            init_kwargs["event_hooks"] = event_hooks
        if trust_env is not None:
            init_kwargs["trust_env"] = trust_env

        return httpx.AsyncClient(**init_kwargs)

    @classmethod
    @asynccontextmanager
    async def create_client_context(
        cls,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ):
        """
        Async context manager that yields a configured AsyncClient and
        guarantees it is closed after use.

        Usage:
            async with HTTPClientConfig.create_client_context() as client:
                resp = await client.get("https://example.com")
        """
        client = cls.create_client(timeout=timeout, **kwargs)
        try:
            yield client
        finally:
            await client.aclose()

    @classmethod
    def get_timeout(cls) -> float:
        """Get default timeout value."""
        return cls.DEFAULT_TIMEOUT
