"""
Coverage tests for app._resolve_build_targets_callable fallback path.

RU: Проверяем, что fallback возвращает глобальную функцию, даже если модуль
временно отсутствует в sys.modules.
EN: Ensure fallback returns the module-level build_nutrition_targets when
sys.modules entries are missing (rare reload scenarios).
"""

from __future__ import annotations

import sys
import types

from typing import Any, cast

import pytest


def test_resolve_build_targets_callable_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Verify fallback path uses module-level function."""

    import app  # Local import to avoid circular issues

    original_module = sys.modules["app"]
    build_targets_fn = getattr(app, "build_nutrition_targets")
    assert callable(build_targets_fn)

    # Remove module references so candidates tuple yields None
    monkeypatch.delitem(sys.modules, "app", raising=False)
    monkeypatch.setitem(sys.modules, "app_module", None)
    monkeypatch.setitem(sys.modules, "_app_top_module", None)
    try:
        resolved = app._resolve_build_targets_callable()
    finally:
        sys.modules["app"] = original_module

    assert resolved is build_targets_fn


def test_resolve_build_targets_callable_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU/EN: Ensure fallback returns None when no callable is registered."""

    import app

    for module_name in ("app", "app_module", "_app_top_module"):
        module_obj = sys.modules.get(module_name)
        if module_obj is not None:
            monkeypatch.setattr(
                cast(Any, module_obj), "build_nutrition_targets", None, raising=False
            )

    assert getattr(app, "build_nutrition_targets") is None

    resolved = app._resolve_build_targets_callable()

    assert resolved is None
