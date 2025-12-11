from __future__ import annotations

import os
import importlib.util
import pytest

# Load routers __init__ module directly to avoid conflicts
spec = importlib.util.spec_from_file_location(
    "routers",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "routers", "__init__.py"),
)
if spec is None or spec.loader is None:
    raise ImportError("Cannot load routers module")
routers_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routers_module)
routers = routers_module


def test_routers_getattr_returns_module() -> None:
    foods_module = routers.foods
    assert foods_module.__name__ == "app.routers.foods"


def test_routers_getattr_invalid() -> None:
    with pytest.raises(AttributeError) as exc:
        getattr(routers, "unknown")
    assert "unknown" in str(exc.value)
