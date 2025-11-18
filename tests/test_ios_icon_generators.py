import os
from pathlib import Path

import pytest
from PIL import Image

from ios import generate_app_icons
from ios import generate_app_icons_from_source as gen_from_source
from ios.Scripts import generate_app_icons_from_source_script as script_gen


def _make_icons_dir(tmp_path: Path) -> Path:
    icons_dir = tmp_path / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset"
    icons_dir.mkdir(parents=True, exist_ok=True)
    return icons_dir


def _make_source(tmp_path: Path, size: int = 256) -> Path:
    source = tmp_path / "source.png"
    Image.new("RGBA", (size, size), (255, 0, 0, 255)).save(source)
    return source


def test_create_pulseplate_icon_dimensions():
    icon = generate_app_icons.create_pulseplate_icon(64)
    assert icon.size == (64, 64)
    assert icon.mode == "RGBA"


def test_generate_all_icons_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _make_icons_dir(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert generate_app_icons.generate_all_icons()

    generated = list((tmp_path / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset").iterdir())
    assert generated  # ensure icons were written


def test_generate_all_icons_missing_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    assert not generate_app_icons.generate_all_icons()


def test_resize_icon_handles_missing_file(tmp_path: Path):
    result = gen_from_source.resize_icon("missing.png", str(tmp_path), "out.png", 20)
    assert result is False


def test_generate_all_icons_from_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    icons_dir = _make_icons_dir(tmp_path)
    monkeypatch.chdir(tmp_path)
    source = _make_source(tmp_path, 512)

    assert gen_from_source.generate_all_icons_from_source(str(source))

    expected_file = icons_dir / "AppIcon-20@2x.png"
    assert expected_file.exists()


def test_script_generator_uses_env_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    icons_dir = tmp_path / "custom_appicons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    source = _make_source(tmp_path, 300)
    monkeypatch.setenv("IOS_APPICONSET_DIR", str(icons_dir))

    assert script_gen.generate_all_icons_from_source(str(source))
    assert any(icons_dir.iterdir())

    monkeypatch.delenv("IOS_APPICONSET_DIR")


def test_script_generator_missing_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    icons_dir = tmp_path / "custom_appicons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("IOS_APPICONSET_DIR", str(icons_dir))

    assert script_gen.generate_all_icons_from_source(str(tmp_path / "missing.png")) is False
