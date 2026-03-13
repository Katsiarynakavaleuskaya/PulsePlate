from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPO_ROOT / "appstore" / "fitchef" / "en-US"
SCREENSHOTS_DIR = PACK_ROOT / "iphone-6.9" / "screenshots"
PREVIEW_DIR = PACK_ROOT / "iphone-6.9" / "preview"
METADATA_DIR = PACK_ROOT / "metadata"
# Source of truth: docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md
# ALLOWED_MASCOT_KEYS mirrors the canonical FitChef taxonomy for this pack guard.
ALLOWED_MASCOT_KEYS = {
    "FitChef",
    "FitChefOnboardingWelcome",
    "FitChefThinking",
    "FitChefWink",
    "FitChefSurprised",
    "FitChefSleepy",
}


def _load_json(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON file from the governed App Store pack."""
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_path(relative_path: str) -> Path:
    """Resolve a governed repo-relative path and fail closed outside the repo."""
    source_path = Path(relative_path)
    assert not source_path.is_absolute(), f"Absolute path not allowed: {relative_path}"

    resolved_path = (REPO_ROOT / source_path).resolve()
    _ = resolved_path.relative_to(REPO_ROOT.resolve())
    return resolved_path


def test_repo_path_rejects_absolute_and_parent_escape_refs() -> None:
    """Keep App Store pack source references bounded to the current repository."""
    with pytest.raises(AssertionError, match="Absolute path not allowed"):
        _repo_path("/tmp/outside.json")

    with pytest.raises(ValueError):
        _repo_path("../outside.json")


def test_fitchef_app_store_pack_folder_contract_exists() -> None:
    """Keep the governed EN pack folder structure stable."""
    assert SCREENSHOTS_DIR.exists()
    assert PREVIEW_DIR.exists()
    assert METADATA_DIR.exists()
    assert (SCREENSHOTS_DIR / "README.md").exists()
    assert (PREVIEW_DIR / "README.md").exists()
    assert (PREVIEW_DIR / "preview_script.md").exists()
    assert (METADATA_DIR / "source_of_truth.md").exists()
    assert (METADATA_DIR / "upload_checklist.md").exists()


def test_app_store_metadata_stays_en_only_and_within_practical_limits() -> None:
    """Validate locale, keyword budget, and safe subtitle constraints."""
    payload = _load_json(METADATA_DIR / "app_store_metadata.json")

    assert payload["locale"] == "en-US"
    assert payload["product_name"] == "PulsePlate"
    assert payload["brand_mascot"] == "FitChef"
    assert len(payload["subtitle"]) <= 30
    assert len(",".join(payload["keywords"])) <= 100
    assert len(payload["promo_text"]) <= 170
    assert len(payload["description_paragraphs"]) == 3

    blocked_terms = ("diagnose", "diagnosis", "treat", "cure", "#1", "best app")
    flattened = " ".join(
        [payload["subtitle"], payload["promo_text"], *payload["description_paragraphs"]]
    ).lower()
    offending_terms = sorted(term for term in blocked_terms if term in flattened)
    assert not offending_terms, f"Blocked term(s) found in metadata: {offending_terms}"


def test_screenshot_manifest_defines_seven_governed_shots_with_real_refs() -> None:
    """Require exactly seven EN screenshot manifests tied to real repo surfaces."""
    payload = _load_json(SCREENSHOTS_DIR / "shot_manifest.json")
    shots = payload["shots"]

    assert payload["locale"] == "en-US"
    assert payload["device_class"] == "iPhone 6.9"
    assert payload["canvas_px"] == {"width": 1320, "height": 2868}
    assert len(shots) == 7
    assert [shot["id"] for shot in shots] == [
        "shot-01",
        "shot-02",
        "shot-03",
        "shot-04",
        "shot-05",
        "shot-06",
        "shot-07",
    ]

    filenames = [shot["expected_filename"] for shot in shots]
    assert len(filenames) == len(set(filenames))
    assert all(filename.endswith(".png") for filename in filenames)

    for shot in shots:
        assert shot["approved_mascot_asset_key"] in ALLOWED_MASCOT_KEYS
        assert shot["output_status"] == "source-approved"
        assert len(shot["headline"]) == 2
        assert 2 <= len(shot["supporting_copy"]) <= 3
        for source_ref in shot["repo_source_refs"]:
            assert _repo_path(source_ref).exists(), f"Missing source ref: {source_ref}"


def test_preview_storyboard_is_bounded_and_reuses_manifest_shot_ids() -> None:
    """Keep the preview script aligned with the screenshot sequence and time cap."""
    manifest = _load_json(SCREENSHOTS_DIR / "shot_manifest.json")
    storyboard = _load_json(PREVIEW_DIR / "storyboard.json")
    expected_shot_ids = [shot["id"] for shot in manifest["shots"]]

    assert storyboard["locale"] == "en-US"
    assert storyboard["device_class"] == "iPhone 6.9"
    assert storyboard["target_duration_seconds"] <= 30
    assert len(storyboard["scenes"]) == 7

    actual_shot_ids = [scene["shot_id"] for scene in storyboard["scenes"]]
    assert actual_shot_ids == expected_shot_ids

    last_end_second = 0
    for scene in storyboard["scenes"]:
        assert scene["start_second"] < scene["end_second"]
        assert scene["start_second"] == last_end_second
        last_end_second = scene["end_second"]

    assert last_end_second == storyboard["target_duration_seconds"]


def test_icon_source_inventory_references_only_canonical_local_assets() -> None:
    """App Store pack must point only to governed icon/mascot sources."""
    payload = _load_json(METADATA_DIR / "icon_source_inventory.json")

    assert payload["locale"] == "en-US"
    assert payload["promotion_policy"] == "canonical-main-assets-only"

    app_icon = payload["app_icon"]
    assert _repo_path(app_icon["primary_source_path"]).exists()
    assert _repo_path(app_icon["catalog_marketing_icon_path"]).exists()
    assert _repo_path(app_icon["catalog_contents_path"]).exists()

    referenced_catalog_paths = []
    for asset in payload["mascot_assets"]:
        assert asset["asset_key"] in ALLOWED_MASCOT_KEYS
        catalog_path = _repo_path(asset["catalog_path"])
        assert catalog_path.exists()
        referenced_catalog_paths.append(asset["catalog_path"])

    assert len(referenced_catalog_paths) == len(set(referenced_catalog_paths))
