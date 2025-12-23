"""
App package entrypoint.

Intentionally boring: no dynamic imports, no sys.path hacks.
Uses lazy import to avoid triggering full app load during model imports.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

_app = None


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies during test setup."""
    global _app
    if name == "app":
        if _app is None:
            from app.main import app as _imported_app

            _app = _imported_app
        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app"]
