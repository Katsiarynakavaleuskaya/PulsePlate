from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import app.dependencies as deps


def test_validate_template_dir_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """validate_template_dir should raise when directory does not exist."""
    missing_dir = tmp_path / "does_not_exist"
    monkeypatch.setattr(deps, "TEMPLATE_DIR", str(missing_dir), raising=False)
    with pytest.raises(RuntimeError):
        deps.validate_template_dir()


def test_validate_template_dir_not_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """validate_template_dir should raise when path exists but not a directory."""
    file_path = tmp_path / "template.txt"
    file_path.write_text("content")
    monkeypatch.setattr(deps, "TEMPLATE_DIR", str(file_path), raising=False)
    with pytest.raises(RuntimeError):
        deps.validate_template_dir()


def test_validate_template_dir_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """validate_template_dir passes when directory exists."""
    monkeypatch.setattr(deps, "TEMPLATE_DIR", str(tmp_path), raising=False)
    deps.validate_template_dir()  # should not raise


def test_get_recipe_synthesizer_delegates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_recipe_synthesizer delegates to core.recipe_synth.get_recipe_synthesizer."""
    monkeypatch.setattr(deps, "TEMPLATE_DIR", str(tmp_path), raising=False)

    sentinel = SimpleNamespace()
    captured: dict[str, tuple[str, ...]] = {}

    def fake_get_synth(*, templates_dir: str) -> SimpleNamespace:
        captured["templates_dir"] = (templates_dir,)
        return sentinel

    monkeypatch.setattr(deps, "get_synth", fake_get_synth)
    result = deps.get_recipe_synthesizer()
    assert result is sentinel
    assert captured["templates_dir"][0] == str(tmp_path)
