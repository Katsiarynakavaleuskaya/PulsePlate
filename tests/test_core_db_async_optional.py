"""Coverage tests for optional async support in core.db."""

from __future__ import annotations

import importlib

import pytest

import core.db as db_module


def test_core_db_handles_missing_async_support(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reload core.db with sqlalchemy.ext.asyncio unavailable and ensure fallbacks are set."""

    original_import = importlib.import_module

    def fake_import(name: str, package: str | None = None):
        if name == "sqlalchemy.ext.asyncio":
            raise ImportError("async extras not installed")
        return original_import(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    reloaded = importlib.reload(db_module)
    assert reloaded.create_async_engine is None
    assert reloaded.async_sessionmaker is None

    monkeypatch.undo()
    importlib.reload(db_module)
