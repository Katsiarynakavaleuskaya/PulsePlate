"""Tests for quick_icon_generator_script.py icon generation functions."""

import sys
from pathlib import Path

import pytest
from PIL import Image

# Add ios/Scripts to path for import
ios_scripts_dir = Path(__file__).parent.parent / "ios" / "Scripts"
sys.path.insert(0, str(ios_scripts_dir))

from icon_constants import IOS_ICON_SIZES  # noqa: E402
from quick_icon_generator_script import create_icons_from_source  # noqa: E402


@pytest.fixture
def iconset_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a temporary AppIcon directory via environment override."""
    path = tmp_path / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset"
    monkeypatch.setenv("IOS_APPICONSET_DIR", str(path))
    return path


class TestCreateIconsFromSource:
    """Test create_icons_from_source function."""

    def test_create_icons_from_source_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iconset_dir: Path
    ) -> None:
        """Test successful icon generation."""
        # Create temporary source image file
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        # Create temporary AppIcon.appiconset directory
        iconset_dir.mkdir(parents=True, exist_ok=True)

        # Mock IOS_ICON_SIZES to use a small set
        test_sizes = {"test_icon_20.png": 20, "test_icon_40.png": 40}
        monkeypatch.setattr("quick_icon_generator_script.IOS_ICON_SIZES", test_sizes)

        result = create_icons_from_source(str(source_file))

        assert result is True
        assert (iconset_dir / "test_icon_20.png").exists()
        assert (iconset_dir / "test_icon_40.png").exists()

    def test_create_icons_from_source_missing_source(self, iconset_dir: Path) -> None:
        """Test create_icons_from_source with missing source file."""
        result = create_icons_from_source("nonexistent.png")

        assert result is False
        assert not iconset_dir.exists()

    def test_create_icons_from_source_missing_output_dir(
        self, tmp_path: Path, iconset_dir: Path
    ) -> None:
        """Test create_icons_from_source with missing output directory."""
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        # Don't create icons_dir - should fail
        assert not iconset_dir.exists()

        result = create_icons_from_source(str(source_file))

        assert result is False

    def test_create_icons_from_source_unsupported_format(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        iconset_dir: Path,
    ) -> None:
        """Test create_icons_from_source with unsupported image formats."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("not an image")

        iconset_dir.mkdir(parents=True, exist_ok=True)

        # Mock Image.open to raise OSError
        original_open = Image.open

        def mock_open(fp: str) -> object:
            if "source.txt" in str(fp):
                raise OSError("cannot identify image file")
            return original_open(fp)

        monkeypatch.setattr("quick_icon_generator_script.Image.open", mock_open)

        result = create_icons_from_source(str(source_file))

        assert result is False

    def test_create_icons_from_source_io_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        iconset_dir: Path,
    ) -> None:
        """Test create_icons_from_source handles file I/O errors."""
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        iconset_dir.mkdir(parents=True, exist_ok=True)

        # Mock IOS_ICON_SIZES
        test_sizes = {"test_icon_20.png": 20}
        monkeypatch.setattr("quick_icon_generator_script.IOS_ICON_SIZES", test_sizes)

        # Mock Image.save to raise OSError
        original_save = Image.Image.save

        def mock_save(
            self: Image.Image, fp: str, format: str | None = None, **kwargs: object
        ) -> None:
            raise OSError("Simulated I/O error")

        monkeypatch.setattr("quick_icon_generator_script.Image.Image.save", mock_save)

        result = create_icons_from_source(str(source_file))

        assert result is False

    def test_create_icons_from_source_rgba_conversion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iconset_dir: Path
    ) -> None:
        """Test RGBA conversion (create source in RGB mode, assert created files are PNG and RGBA)."""
        # Create source image in RGB mode
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGB", (1024, 1024), color=(255, 0, 0))
        source_img.save(source_file, "PNG")

        iconset_dir.mkdir(parents=True, exist_ok=True)

        # Mock IOS_ICON_SIZES
        test_sizes = {"test_icon_20.png": 20}
        monkeypatch.setattr("quick_icon_generator_script.IOS_ICON_SIZES", test_sizes)

        result = create_icons_from_source(str(source_file))

        assert result is True
        created_file = iconset_dir / "test_icon_20.png"
        assert created_file.exists()

        # Verify created file is PNG and RGBA
        created_img = Image.open(created_file)
        assert created_img.mode == "RGBA"
        assert created_file.suffix == ".png"

    def test_create_icons_from_source_size_validation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iconset_dir: Path
    ) -> None:
        """Test size validation (assert number of created files equals len(IOS_ICON_SIZES))."""
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        iconset_dir.mkdir(parents=True, exist_ok=True)

        # Mock IOS_ICON_SIZES to a known set
        test_sizes = {"icon1.png": 20, "icon2.png": 40, "icon3.png": 60}
        monkeypatch.setattr("quick_icon_generator_script.IOS_ICON_SIZES", test_sizes)

        result = create_icons_from_source(str(source_file))

        assert result is True
        # Count created files
        created_files = list(iconset_dir.glob("*.png"))
        assert len(created_files) == len(test_sizes)
        assert result is True  # Return value matches
