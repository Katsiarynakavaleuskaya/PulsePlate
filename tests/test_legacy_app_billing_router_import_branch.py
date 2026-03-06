from __future__ import annotations

import legacy_app
import pytest


def test_legacy_app_logs_when_billing_router_import_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _raise_import_error(name: str):
        raise ImportError(f"missing module: {name}")

    monkeypatch.setattr(legacy_app.importlib, "import_module", _raise_import_error)

    caplog.set_level("WARNING")
    legacy_app._register_billing_routes_compat()

    assert "Billing router not loaded: missing module: app.routers.billing" in caplog.text
