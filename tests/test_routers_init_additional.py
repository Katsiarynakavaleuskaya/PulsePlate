from __future__ import annotations

import pytest

import app.routers as routers


def test_routers_getattr_returns_module() -> None:
    foods_module = routers.foods
    assert foods_module.__name__ == "app.routers.foods"


def test_routers_getattr_invalid() -> None:
    with pytest.raises(AttributeError) as exc:
        getattr(routers, "unknown")
    assert "unknown" in str(exc.value)
