"""Guard the CAB-03 AppIcon projection and canonical validator result.

The current-Xcode/actool-qualified marketing entry has four exact keys:
filename, idiom, scale, and size. The unified release validator owns PNG
signature, IHDR, CRC, dimensions, and approved-byte identity checks.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.release import check_ios_appstore_verify as validator_module

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENTS_JSON = (
    REPO_ROOT / "ios" / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset" / "Contents.json"
)
EXPECTED_MARKETING_ENTRY = {
    "filename": "AppIcon-1024.png",
    "idiom": "ios-marketing",
    "scale": "1x",
    "size": "1024x1024",
}


def test_appicon_marketing_entry_is_declared_once() -> None:
    """Contents.json must declare exactly one ios-marketing entry at 1024x1024."""
    assert not CONTENTS_JSON.is_symlink(), "AppIcon Contents.json must be a regular repo file"
    assert CONTENTS_JSON.is_file(), f"Missing {CONTENTS_JSON.relative_to(REPO_ROOT)}"

    data = json.loads(CONTENTS_JSON.read_text(encoding="utf-8"))
    marketing_entries = [
        img for img in data.get("images", []) if img.get("idiom") == "ios-marketing"
    ]

    assert (
        len(marketing_entries) == 1
    ), f"Expected exactly 1 ios-marketing entry, found {len(marketing_entries)}"

    entry = marketing_entries[0]
    assert entry == EXPECTED_MARKETING_ENTRY, (
        "ios-marketing entry must contain exactly the canonical four-field tuple; " f"got {entry}"
    )


def test_appicon_marketing_validator_reports_exact_canonical_success() -> None:
    """The sole canonical PNG validator must report the exact admitted success."""

    assert validator_module.check_appicon_marketing() == [
        (
            True,
            "appicon_marketing",
            "AppIcon exact ios-marketing slot and approved PNG OK (AppIcon-1024.png)",
        )
    ]
