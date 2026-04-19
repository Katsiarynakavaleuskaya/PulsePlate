from __future__ import annotations

from types import SimpleNamespace

import pytest
from tests.helpers.module_resolve import resolve_module


def test_ws_duplicate_registration_guard_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Duplicate /ws path must fail fast to prevent silent route shadowing."""
    main_module = resolve_module("app.main")

    fake_app = SimpleNamespace(
        routes=[
            SimpleNamespace(path="/health"),
            SimpleNamespace(path="/ws"),
        ]
    )
    monkeypatch.setattr(main_module, "app", fake_app)
    guard = getattr(main_module, "_assert_no_duplicate_ws_route")

    with pytest.raises(RuntimeError, match="Duplicate /ws route detected"):
        guard()


def test_ws_duplicate_registration_guard_passes_without_ws_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main_module = resolve_module("app.main")

    fake_app = SimpleNamespace(
        routes=[
            SimpleNamespace(path="/health"),
            SimpleNamespace(path="/metrics"),
        ]
    )
    monkeypatch.setattr(main_module, "app", fake_app)
    guard = getattr(main_module, "_assert_no_duplicate_ws_route")

    guard()
