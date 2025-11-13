"""Tests for generate_app_icons_from_source_script.py icon generation functions."""

import sys
from pathlib import Path

import pytest
from PIL import Image

# Add ios/Scripts to path for import
ios_scripts_dir = Path(__file__).parent.parent / "ios" / "Scripts"
sys.path.insert(0, str(ios_scripts_dir))

from generate_app_icons_from_source_script import (  # noqa: E402
    _process_image_for_icon,
    generate_all_icons_from_source,
    resize_icon,
)
from icon_constants import IOS_ICON_SIZES  # noqa: E402


@pytest.fixture
def iconset_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a temporary AppIcon.appiconset directory and set env override."""
    path = tmp_path / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset"
    monkeypatch.setenv("IOS_APPICONSET_DIR", str(path))
    return path


class TestProcessImageForIcon:
    """Test _process_image_for_icon function."""

    def test_process_image_rgba_conversion(self) -> None:
        """Test conversion from non-RGBA modes to RGBA."""
        # Create test images in different modes
        rgb_img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        grayscale_img = Image.new("L", (100, 100), color=128)

        # Process and verify output
        result_rgb = _process_image_for_icon(rgb_img, 50)
        result_grayscale = _process_image_for_icon(grayscale_img, 50)

        assert result_rgb.mode == "RGBA"
        assert result_grayscale.mode == "RGBA"
        assert result_rgb.size == (50, 50)
        assert result_grayscale.size == (50, 50)

    def test_process_image_size_validation(self) -> None:
        """Validate the output size and resampling quality."""
        rgba_img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 255))

        result = _process_image_for_icon(rgba_img, 100)

        assert result.size == (100, 100)
        assert result.mode == "RGBA"
        # Verify pixel samples - center should still be red
        center_pixel = result.getpixel((50, 50))
        assert center_pixel[0] > 200, "Center pixel should retain red color"

    def test_process_image_invalid_size(self) -> None:
        """Test with invalid size (should still process but may be small)."""
        rgba_img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))

        # Very small size
        result = _process_image_for_icon(rgba_img, 1)

        assert result.size == (1, 1)
        assert result.mode == "RGBA"


class TestResizeIcon:
    """Test resize_icon function."""

    def test_resize_icon_success(self, tmp_path: Path) -> None:
        """Test resize_icon success path using temp files."""
        # Create a temporary source image
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = resize_icon(str(source_file), str(output_dir), "test_icon.png", 120)

        assert result is True
        assert (output_dir / "test_icon.png").exists()

        # Verify the created file
        created_img = Image.open(output_dir / "test_icon.png")
        assert created_img.size == (120, 120)
        assert created_img.mode == "RGBA"

    def test_resize_icon_missing_source(self, tmp_path: Path) -> None:
        """Test resize_icon with missing source path."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = resize_icon("nonexistent.png", str(output_dir), "test_icon.png", 120)

        assert result is False

    def test_resize_icon_io_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test resize_icon handles I/O errors."""
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock Image.save to raise OSError
        original_save = Image.Image.save

        def mock_save(
            self: Image.Image, fp: str, format: str | None = None, **kwargs: object
        ) -> None:
            raise OSError("Simulated I/O error")

        monkeypatch.setattr("generate_app_icons_from_source_script.Image.Image.save", mock_save)

        result = resize_icon(str(source_file), str(output_dir), "test_icon.png", 120)

        assert result is False
        captured = capsys.readouterr()
        assert "Ошибка" in captured.out or "error" in captured.out.lower()

    def test_resize_icon_invalid_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test resize_icon with invalid image format."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("not an image")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock Image.open to raise OSError for corrupt file
        original_open = Image.open

        def mock_open(fp: str) -> object:
            if "source.txt" in str(fp):
                raise OSError("cannot identify image file")
            return original_open(fp)

        monkeypatch.setattr("generate_app_icons_from_source_script.Image.open", mock_open)

        result = resize_icon(str(source_file), str(output_dir), "test_icon.png", 120)

        assert result is False


class TestGenerateAllIconsFromSource:
    """Test generate_all_icons_from_source function."""

    def test_generate_all_icons_from_source_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iconset_dir: Path
    ) -> None:
        """Test successful full generation."""
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        iconset_dir.mkdir(parents=True)

        test_sizes = {"test_icon_20.png": 20, "test_icon_40.png": 40}
        monkeypatch.setattr("generate_app_icons_from_source_script.IOS_ICON_SIZES", test_sizes)

        result = generate_all_icons_from_source(str(source_file))

        assert result is True
        assert (iconset_dir / "test_icon_20.png").exists()
        assert (iconset_dir / "test_icon_40.png").exists()

    def test_generate_all_icons_from_source_missing_source(self, iconset_dir: Path) -> None:
        """Test generate_all_icons_from_source with missing source file."""
        result = generate_all_icons_from_source("nonexistent.png")

        assert result is False

    def test_generate_all_icons_from_source_directory_creation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iconset_dir: Path
    ) -> None:
        """Test that assets dir is created if it doesn't exist."""
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        test_sizes = {"test_icon_20.png": 20}
        monkeypatch.setattr("generate_app_icons_from_source_script.IOS_ICON_SIZES", test_sizes)

        result = generate_all_icons_from_source(str(source_file))

        assert result is True
        assert iconset_dir.exists()
        assert iconset_dir.is_dir()

    def test_generate_all_icons_from_source_partial_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        iconset_dir: Path,
    ) -> None:
        """Test partial failures (mock resize_icon to fail for one entry)."""
        source_file = tmp_path / "source.png"
        source_img = Image.new("RGBA", (1024, 1024), color=(255, 0, 0, 255))
        source_img.save(source_file, "PNG")

        iconset_dir.mkdir(parents=True)

        test_sizes = {"test_icon_20.png": 20, "test_icon_40.png": 40}
        monkeypatch.setattr("generate_app_icons_from_source_script.IOS_ICON_SIZES", test_sizes)

        original_resize = resize_icon
        call_count = 0

        def mock_resize_icon(source: str, output: str, filename: str, size: int) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return False  # First call fails
            return original_resize(source, output, filename, size)

        monkeypatch.setattr("generate_app_icons_from_source_script.resize_icon", mock_resize_icon)

        result = generate_all_icons_from_source(str(source_file))

        # Should return False due to partial failure
        assert result is False
        captured = capsys.readouterr()
        assert "Создано" in captured.out or "created" in captured.out.lower()
