"""Middleware package for FastAPI application.

RU: Промежуточное ПО для обработки запросов.
EN: Middleware for request processing and validation.
"""

__all__ = ["api_tiers"]


def __getattr__(name: str):
    """Lazy import middleware modules."""
    if name in __all__:
        from importlib import import_module

        return import_module(f"app.middleware.{name}")
    raise AttributeError(name)
