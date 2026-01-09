"""Middleware package for FastAPI application.

RU: Промежуточное ПО для обработки запросов.
EN: Middleware for request processing and validation.
"""

from types import ModuleType

__all__ = ["api_tiers", "metrics"]


def __getattr__(name: str) -> ModuleType:
    """Lazy import middleware modules.

    Args:
        name: Module name to import

    Returns:
        ModuleType: Imported module

    Raises:
        AttributeError: If module not found in __all__
    """
    if name in __all__:
        from importlib import import_module

        return import_module(f"app.middleware.{name}")
    raise AttributeError(name)
