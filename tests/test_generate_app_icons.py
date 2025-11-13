"""Tests for generate_app_icons_script.py icon generation functions."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Add ios/Scripts to path for import
ios_scripts_dir = Path(__file__).parent.parent / "ios" / "Scripts"
sys.path.insert(0, str(ios_scripts_dir))

from generate_app_icons_script import create_pulseplate_icon, generate_all_icons  # noqa: E402
from icon_constants import IOS_ICON_SIZES  # noqa: E402


class TestCreatePulseplateIcon:
    """Test create_pulseplate_icon function."""

    @pytest.mark.parametrize("size", [16, 40, 120, 1024])
    def test_create_pulseplate_icon_valid_sizes(self, size: int) -> None:
        """Test create_pulseplate_icon with valid sizes [16,40,120,1024]."""
        icon = create_pulseplate_icon(size)

        assert isinstance(icon, Image.Image)
        assert icon.size == (size, size)
        assert icon.mode == "RGBA"

        # Check a few pixel colors (center and background)
        # Center should have heart color (red)
        center_x, center_y = size // 2, size // 2
        center_pixel = icon.getpixel((center_x, center_y))
        # Heart color is (255, 93, 93, 255) - check if red component is high
        assert center_pixel[0] > 200, "Center should have red heart color"

        # Background should be transparent or navy
        bg_pixel = icon.getpixel((0, 0))
        # Navy is (15, 23, 42, 255) or transparent (0, 0, 0, 0)
        assert bg_pixel[3] in (0, 255), "Background should be transparent or opaque"

    @pytest.mark.parametrize("invalid_size", [15.5, "16", 15, -1, 0])
    def test_create_pulseplate_icon_invalid_sizes(self, invalid_size: int | float | str) -> None:
        """Test create_pulseplate_icon raises TypeError/ValueError for invalid sizes."""
        if isinstance(invalid_size, (float, str)):
            with pytest.raises(TypeError, match="size must be an integer"):
                create_pulseplate_icon(invalid_size)  # type: ignore[arg-type]
        else:
            with pytest.raises(ValueError, match="size must be >= 16"):
                create_pulseplate_icon(invalid_size)


class TestGenerateAllIcons:
    """Test generate_all_icons function."""

    def test_generate_all_icons_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test generate_all_icons success path."""
        icons_dir = tmp_path / "AppIcon.appiconset"
        icons_dir.mkdir(parents=True)

        # Mock IOS_ICON_SIZES to use a small set for testing
        test_sizes = {"test_icon_20.png": 20, "test_icon_40.png": 40}
        monkeypatch.setattr("generate_app_icons_script.IOS_ICON_SIZES", test_sizes)

        # Mock the script directory resolution
        def mock_dirname(path: str) -> str:
            return str(tmp_path)

        monkeypatch.setattr("generate_app_icons_script.os.path.dirname", mock_dirname)

        # Mock os.path.join to return our test directory
        original_join = os.path.join

        def mock_join(*args: str) -> str:
            if "AppIcon.appiconset" in args:
                return str(icons_dir)
            return original_join(*args)

        monkeypatch.setattr("generate_app_icons_script.os.path.join", mock_join)

        result = generate_all_icons()

        assert result is True
        # Verify files were written
        assert (icons_dir / "test_icon_20.png").exists()
        assert (icons_dir / "test_icon_40.png").exists()

    def test_generate_all_icons_missing_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test generate_all_icons missing directory returns False."""
        # Ensure directory doesn't exist
        icons_dir = tmp_path / "AppIcon.appiconset"
        assert not icons_dir.exists()

        # Mock the script directory resolution
        def mock_dirname(path: str) -> str:
            return str(tmp_path)

        monkeypatch.setattr("generate_app_icons_script.os.path.dirname", mock_dirname)

        # Mock os.path.join to return our test directory
        original_join = os.path.join

        def mock_join(*args: str) -> str:
            if "AppIcon.appiconset" in args:
                return str(icons_dir)
            return original_join(*args)

        monkeypatch.setattr("generate_app_icons_script.os.path.join", mock_join)

        result = generate_all_icons()

        assert result is False

    def test_generate_all_icons_io_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test generate_all_icons handles I/O errors."""
        icons_dir = tmp_path / "AppIcon.appiconset"
        icons_dir.mkdir(parents=True)

        # Mock IOS_ICON_SIZES to use a small set
        test_sizes = {"test_icon_20.png": 20, "test_icon_40.png": 40}
        monkeypatch.setattr("generate_app_icons_script.IOS_ICON_SIZES", test_sizes)

        # Mock the script directory resolution
        def mock_dirname(path: str) -> str:
            return str(tmp_path)

        monkeypatch.setattr("generate_app_icons_script.os.path.dirname", mock_dirname)

        # Mock os.path.join
        original_join = os.path.join

        def mock_join(*args: str) -> str:
            if "AppIcon.appiconset" in args:
                return str(icons_dir)
            return original_join(*args)

        monkeypatch.setattr("generate_app_icons_script.os.path.join", mock_join)

        # Mock Image.save to raise OSError for one filename
        original_save = Image.Image.save
        call_count = 0

        def mock_save(
            self: Image.Image, fp: str, format: str | None = None, **kwargs: object
        ) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1 and "test_icon_20.png" in str(fp):
                raise OSError("Simulated I/O error")
            return original_save(self, fp, format, **kwargs)

        monkeypatch.setattr("generate_app_icons_script.Image.Image.save", mock_save)

        result = generate_all_icons()

        # Should return False due to partial failure
        assert result is False
        captured = capsys.readouterr()
        assert "Ошибка" in captured.out or "error" in captured.out.lower()
