from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = REPO_ROOT / "ios" / "PulsePlate" / "Assets.xcassets"

FITCHEF_IMAGESETS = {
    "FitChef": [
        "fitchef_neutral@1x.png",
        "fitchef_neutral@2x.png",
        "fitchef_neutral@3x.png",
    ],
    "FitChefWink": [
        "fitchef_wink@1x.png",
        "fitchef_wink@2x.png",
        "fitchef_wink@3x.png",
    ],
    "FitChefWelcome": [
        "fitchef_welcome@1x.png",
        "fitchef_welcome@2x.png",
        "fitchef_welcome@3x.png",
    ],
    "FitChefThinking": [
        "fitchef_thinking@1x.png",
        "fitchef_thinking@2x.png",
        "fitchef_thinking@3x.png",
    ],
    "FitChefSurprised": [
        "fitchef_surprised@1x.png",
        "fitchef_surprised@2x.png",
        "fitchef_surprised@3x.png",
    ],
    "FitChefSleepy": [
        "fitchef_sleepy@1x.png",
        "fitchef_sleepy@2x.png",
        "fitchef_sleepy@3x.png",
    ],
}


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fitchef_imagesets_reference_existing_files() -> None:
    for asset_name, expected_files in FITCHEF_IMAGESETS.items():
        asset_dir = ASSETS_ROOT / f"{asset_name}.imageset"
        contents_path = asset_dir / "Contents.json"
        payload = _load_json(contents_path)
        image_entries = payload["images"]
        filenames = [entry["filename"] for entry in image_entries if "filename" in entry]

        assert filenames == expected_files
        for filename in expected_files:
            assert (asset_dir / filename).is_file(), f"Missing {asset_name}/{filename}"


def test_fitchef_generic_image_placeholder_is_not_tracked() -> None:
    assert not (ASSETS_ROOT / "Image.imageset").exists()


def test_fitchef_marketing_icon_contract_uses_canonical_filename() -> None:
    asset_dir = ASSETS_ROOT / "AppIcon.appiconset"
    contents_path = asset_dir / "Contents.json"
    payload = _load_json(contents_path)
    image_entries = payload["images"]

    assert image_entries == [
        {
            "filename": "AppIcon.png",
            "idiom": "ios-marketing",
            "platform": "ios",
            "size": "1024x1024",
        }
    ]
    assert (asset_dir / "AppIcon.png").is_file()
