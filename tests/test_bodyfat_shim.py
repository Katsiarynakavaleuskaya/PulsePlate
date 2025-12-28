from __future__ import annotations

import pytest


def test_bodyfat_shim_raises_helpful_error_when_router_symbol_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.routers.bodyfat as app_bodyfat_router
    import bodyfat

    monkeypatch.delattr(app_bodyfat_router, "get_router", raising=False)

    with pytest.raises(ImportError) as excinfo:
        bodyfat.get_router()

    assert "Bodyfat router moved to `app.routers.bodyfat.get_router`" in str(excinfo.value)
