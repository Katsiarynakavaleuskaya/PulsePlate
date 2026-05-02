"""Guard: AppIcon ios-marketing asset must be a valid 1024x1024 PNG.

App Store requires exactly one ios-marketing icon at 1024x1024 (1x scale)
in the asset catalog. This guard prevents silent asset drift that would
block App Store submission.

Complementary to tests/test_fitchef_asset_taxonomy.py which validates
catalog completeness (filenames + no unreferenced PNGs). This guard
validates the ios-marketing entry specifically: idiom, size, PNG binary
validity, and pixel dimensions.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APPICON_DIR = REPO_ROOT / "ios" / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset"
CONTENTS_JSON = APPICON_DIR / "Contents.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _read_png_dimensions(path: Path) -> tuple[int, int]:
    """Parse width and height from a PNG IHDR chunk (no external deps)."""
    with path.open("rb") as fh:
        signature = fh.read(8)
        assert signature == PNG_SIGNATURE, f"{path.name} is not a valid PNG file"

        _length_bytes = fh.read(4)  # IHDR chunk length
        chunk_type = fh.read(4)
        assert (
            chunk_type == b"IHDR"
        ), f"{path.name}: first PNG chunk is {chunk_type!r}, expected IHDR"

        width, height = struct.unpack(">II", fh.read(8))
        return width, height


def test_appicon_marketing_entry_is_declared_once() -> None:
    """Contents.json must declare exactly one ios-marketing entry at 1024x1024."""
    assert CONTENTS_JSON.exists(), f"Missing {CONTENTS_JSON.relative_to(REPO_ROOT)}"

    data = json.loads(CONTENTS_JSON.read_text(encoding="utf-8"))
    marketing_entries = [
        img for img in data.get("images", []) if img.get("idiom") == "ios-marketing"
    ]

    assert (
        len(marketing_entries) == 1
    ), f"Expected exactly 1 ios-marketing entry, found {len(marketing_entries)}"

    entry = marketing_entries[0]
    assert (
        entry.get("size") == "1024x1024"
    ), f"ios-marketing size must be 1024x1024, got {entry.get('size')}"
    # Modern Xcode 15+ uses "platform" instead of "scale" for ios-marketing.
    # Accept either: scale == "1x" (legacy) or platform == "ios" (modern).
    has_scale = entry.get("scale") == "1x"
    has_platform = entry.get("platform") == "ios"
    assert (
        has_scale or has_platform
    ), f"ios-marketing must have scale '1x' or platform 'ios', got {entry}"
    filename = entry.get("filename", "")
    assert filename, "ios-marketing entry must have a non-empty filename"
    assert filename.endswith(".png"), f"ios-marketing filename must end with .png, got {filename}"


def test_appicon_marketing_png_exists_and_is_1024_square() -> None:
    """Referenced ios-marketing PNG must exist and be exactly 1024x1024."""
    data = json.loads(CONTENTS_JSON.read_text(encoding="utf-8"))
    entry = next(img for img in data.get("images", []) if img.get("idiom") == "ios-marketing")

    png_path = APPICON_DIR / entry["filename"]
    assert png_path.exists(), f"ios-marketing PNG missing: {png_path.relative_to(REPO_ROOT)}"
    assert png_path.stat().st_size > 0, f"ios-marketing PNG is empty: {png_path.name}"

    width, height = _read_png_dimensions(png_path)
    assert (width, height) == (
        1024,
        1024,
    ), f"ios-marketing PNG must be 1024x1024, got {width}x{height}"
