"""
Shared test utilities for reusable test components.

RU: Общие утилиты для тестов: переиспользуемые компоненты
EN: Shared test utilities: reusable test components

This module provides reusable test utilities that can be imported across multiple test files.
"""

import httpx


class FailingProvider:
    """
    Test provider that raises httpx.ConnectError to simulate connection failures.

    RU: Тестовый провайдер, который вызывает httpx.ConnectError для симуляции ошибок подключения
    EN: Test provider that raises httpx.ConnectError to simulate connection failures

    Used for testing error handling paths when external services are unavailable.
    """

    name = "test"

    async def generate(self, _: str) -> str:  # pragma: no cover - invoked in tests
        """
        Generate method that always raises httpx.ConnectError.

        RU: Метод генерации, который всегда вызывает httpx.ConnectError
        EN: Generate method that always raises httpx.ConnectError

        Args:
            _: Input text (ignored)

        Raises:
            httpx.ConnectError: Always raised to simulate connection failure
        """
        raise httpx.ConnectError("Connection failed")


class SlowProvider:
    """
    Test provider that raises httpx.ReadTimeout to simulate timeout errors.

    RU: Тестовый провайдер, который вызывает httpx.ReadTimeout для симуляции ошибок таймаута
    EN: Test provider that raises httpx.ReadTimeout to simulate timeout errors

    Used for testing error handling paths when external services timeout.
    """

    name = "test"

    async def generate(self, _: str) -> str:  # pragma: no cover - invoked in tests
        """
        Generate method that always raises httpx.ReadTimeout.

        RU: Метод генерации, который всегда вызывает httpx.ReadTimeout
        EN: Generate method that always raises httpx.ReadTimeout

        Args:
            _: Input text (ignored)

        Raises:
            httpx.ReadTimeout: Always raised to simulate request timeout
        """
        raise httpx.ReadTimeout("Request timeout")
