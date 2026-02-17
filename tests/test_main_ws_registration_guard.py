from __future__ import annotations

from types import SimpleNamespace

import pytest


def test_ws_duplicate_registration_guard_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Duplicate /ws path must fail fast to prevent silent route shadowing."""
    import app.main as main_module

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
    import app.main as main_module

    fake_app = SimpleNamespace(
        routes=[
            SimpleNamespace(path="/health"),
            SimpleNamespace(path="/metrics"),
        ]
    )
    monkeypatch.setattr(main_module, "app", fake_app)
    guard = getattr(main_module, "_assert_no_duplicate_ws_route")

    guard()
