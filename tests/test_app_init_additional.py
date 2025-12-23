from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest

def _load_app_init(
    monkeypatch: pytest.MonkeyPatch, *, spec_none: bool = False, base_spec_none: bool = False
) -> ModuleType:
    original_spec_from_file = importlib.util.spec_from_file_location

    def patched_spec_from_file(name: str, location: str, *args, **kwargs):
        if spec_none and name == "app_module":
            return None
        return original_spec_from_file(name, location, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "spec_from_file_location", patched_spec_from_file)

    if base_spec_none:
        monkeypatch.setattr(importlib.util, "spec_from_loader", lambda *a, **k: None)

    module_name = "app_init_test_module"
    spec = original_spec_from_file(module_name, str(Path("app/__init__.py")))
    assert spec is not None and spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
        return module

def test_app_init_spec_none(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_app_init(monkeypatch, spec_none=True)
    assert module.app is None
    assert module._mod is None

def test_app_init_base_spec_none(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_app_init(monkeypatch, base_spec_none=True)
    assert module.__spec__ is None
