"""Tests for ios.quick_icon_generator module import helpers."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def test_quick_icon_generator_import_inserts_scripts_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    module_name = "ios.quick_icon_generator"
    sys.modules.pop(module_name, None)
    scripts_dir = Path(__file__).resolve().parent.parent / "ios" / "Scripts"
    sys.path = [p for p in sys.path if p != str(scripts_dir)]

    fake_script = ModuleType("quick_icon_generator_script")
    fake_script.create_icons_from_source = lambda *_: True
    monkeypatch.setitem(sys.modules, "quick_icon_generator_script", fake_script)

    fake_pil = ModuleType("PIL")
    fake_pil.Image = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)

    module = importlib.import_module(module_name)
    assert str(scripts_dir) in sys.path
    assert hasattr(module, "create_icons_from_source")
