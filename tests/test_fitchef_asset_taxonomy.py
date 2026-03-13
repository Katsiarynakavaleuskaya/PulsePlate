from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = REPO_ROOT / "ios" / "PulsePlate" / "Assets.xcassets"
APP_ICON_DIR = ASSETS_ROOT / "AppIcon.appiconset"
FITCHEF_DIR = ASSETS_ROOT / "FitChef.imageset"
VARIANT_BUCKETS = {
    "FitChefWink.imageset": "fitchef-wink",
    "FitChefThinking.imageset": "fitchef-thinking",
    "FitChefSurprised.imageset": "fitchef-surprised",
    "FitChefSleepy.imageset": "fitchef-sleepy",
    "FitChefOnboardingWelcome.imageset": "fitchef-onboarding-welcome",
}


def _load_contents(imageset_dir: Path) -> dict:
    """Load an xcassets Contents.json payload from a single image set."""
    return json.loads((imageset_dir / "Contents.json").read_text(encoding="utf-8"))


def _referenced_filenames(imageset_dir: Path) -> list[str]:
    """Return the ordered list of filenames referenced by an image set."""
    payload = _load_contents(imageset_dir)
    filenames: list[str] = []
    for image in payload.get("images", []):
        filename = image.get("filename")
        if filename:
            filenames.append(filename)
    return filenames


def _png_filenames(imageset_dir: Path) -> list[str]:
    """Return all PNG filenames physically present inside an image set."""
    return sorted(path.name for path in imageset_dir.glob("*.png"))


def test_fitchef_default_bucket_exists_and_uses_neutral_only_assets() -> None:
    """Keep the public FitChef bucket neutral and filename-stable."""
    referenced = _referenced_filenames(FITCHEF_DIR)
    assert referenced == [
        "fitchef-neutral@1x.png",
        "fitchef-neutral@2x.png",
        "fitchef-neutral@3x.png",
    ]
    assert all(" " not in filename for filename in referenced)
    assert all("Wink" not in filename for filename in referenced)
    assert all("Thinking" not in filename for filename in referenced)
    assert all("Surprised" not in filename for filename in referenced)
    assert all("Sleepy" not in filename for filename in referenced)
    assert all("Welcome" not in filename for filename in referenced)


def test_fitchef_variant_buckets_are_canonical_and_exist() -> None:
    """Require one semantic variant per dedicated FitChef image bucket."""
    assert not (ASSETS_ROOT / "Image.imageset").exists()
    assert not (ASSETS_ROOT / "FitChefPortraitWink.imageset").exists()
    assert not (ASSETS_ROOT / "FitChefPortraitThinking.imageset").exists()
    assert not (ASSETS_ROOT / "FitChefPortraitSurprised.imageset").exists()
    assert not (ASSETS_ROOT / "FitChefPortraitSleepy.imageset").exists()

    for bucket_name, variant_name in VARIANT_BUCKETS.items():
        bucket_dir = ASSETS_ROOT / bucket_name
        assert bucket_dir.exists(), f"Missing FitChef variant bucket: {bucket_name}"

        referenced = _referenced_filenames(bucket_dir)
        expected = [
            f"{variant_name}@1x.png",
            f"{variant_name}@2x.png",
            f"{variant_name}@3x.png",
        ]
        assert referenced == expected
        assert all(" " not in filename for filename in referenced)
        assert all(filename.startswith(variant_name) for filename in referenced)


def test_fitchef_catalogs_reference_existing_local_files() -> None:
    """Fail if FitChef image buckets contain stale or missing PNG files."""
    bucket_dirs = [FITCHEF_DIR] + [ASSETS_ROOT / bucket for bucket in VARIANT_BUCKETS]

    for bucket_dir in bucket_dirs:
        referenced = _referenced_filenames(bucket_dir)
        for filename in referenced:
            assert (
                bucket_dir / filename
            ).exists(), f"Missing asset file {filename} in {bucket_dir.name}"
        assert _png_filenames(bucket_dir) == sorted(
            referenced
        ), f"Stale or unreferenced PNG files remain in {bucket_dir.name}"


def test_app_icon_catalog_is_canonical_and_has_no_unreferenced_pngs() -> None:
    """Require AppIcon to reference only canonical PNG outputs."""
    referenced = _referenced_filenames(APP_ICON_DIR)
    expected = [
        "AppIcon-20@2x.png",
        "AppIcon-20@3x.png",
        "AppIcon-29@2x.png",
        "AppIcon-29@3x.png",
        "AppIcon-40@2x.png",
        "AppIcon-40@3x.png",
        "AppIcon-60@2x.png",
        "AppIcon-60@3x.png",
        "AppIcon-20@1x.png",
        "AppIcon-20@2x.png",
        "AppIcon-29@1x.png",
        "AppIcon-29@2x.png",
        "AppIcon-40@1x.png",
        "AppIcon-40@2x.png",
        "AppIcon-76@1x.png",
        "AppIcon-76@2x.png",
        "AppIcon-83.5@2x.png",
        "AppIcon-1024.png",
    ]
    assert referenced == expected
    assert all(" " not in filename for filename in referenced)

    png_files = _png_filenames(APP_ICON_DIR)
    assert png_files == sorted(set(expected))
