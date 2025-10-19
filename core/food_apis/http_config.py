"""
HTTP Client Configuration

RU: Общая конфигурация для HTTP клиентов API.
EN: Shared configuration for API HTTP clients.

This module provides centralized HTTP client configuration to avoid
duplication across different API clients (USDA, Open Food Facts, etc.).
"""

import httpx
from typing import Optional


class HTTPClientConfig:
    """Centralized HTTP client configuration."""

    # Default timeout for all API requests
    DEFAULT_TIMEOUT = 10.0

    @classmethod
    def create_client(cls, timeout: Optional[float] = None) -> httpx.AsyncClient:
        """
        Create a configured httpx.AsyncClient.

        Args:
            timeout: Request timeout in seconds (default: DEFAULT_TIMEOUT)

        Returns:
            Configured httpx.AsyncClient instance
        """
        return httpx.AsyncClient(
            timeout=timeout or cls.DEFAULT_TIMEOUT,
        )

    @classmethod
    def get_timeout(cls) -> float:
        """Get default timeout value."""
        return cls.DEFAULT_TIMEOUT
