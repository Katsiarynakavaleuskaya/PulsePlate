from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_BASE = REPO_ROOT / "appstore" / "fitchef"
LOCALES = ("en-US", "ru-RU")
ALLOWED_RU_PACK_SUFFIXES = {".json", ".md"}
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
BLOCKED_COPY_TERMS = {
    "en-US": (
        "diagnose",
        "diagnosis",
        "treat",
        "treatment",
        "cure",
        "therapy",
        "doctor",
        "patient",
        "guaranteed",
        "instant results",
        "rapid results",
        "clinically proven",
        "#1",
        "best app",
        "free trial",
        "subscription",
    ),
    "ru-RU": (
        "диагноз",
        "лечит",
        "лечение",
        "терап",
        "врач",
        "пациент",
        "клиничес",
        "лекарств",
        "медицин",
        "препарат",
        "таблет",
        "гарантир",
        "мгновенн",
        "быстрые результаты",
        "доказанн",
        "пробный период",
        "подписка",
        "скидк",
    ),
}
EXPECTED_SHOT_IDS = [
    "shot-01",
    "shot-02",
    "shot-03",
    "shot-04",
    "shot-05",
    "shot-06",
    "shot-07",
]


def _pack_root(locale: str) -> Path:
    """Return the governed App Store pack root for a locale."""
    return PACK_BASE / locale


def _screenshots_dir(locale: str) -> Path:
    return _pack_root(locale) / "iphone-6.9" / "screenshots"


def _preview_dir(locale: str) -> Path:
    return _pack_root(locale) / "iphone-6.9" / "preview"


def _metadata_dir(locale: str) -> Path:
    return _pack_root(locale) / "metadata"


def _load_json(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON file from the governed App Store pack."""
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_strings(value: Any) -> list[str]:
    """Return every string nested in JSON-like metadata."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_flatten_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_flatten_strings(item))
        return strings
    return []


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


@pytest.mark.parametrize("locale", LOCALES)
def test_fitchef_app_store_pack_folder_contract_exists(locale: str) -> None:
    """Keep the governed locale pack folder structure stable."""
    screenshots_dir = _screenshots_dir(locale)
    preview_dir = _preview_dir(locale)
    metadata_dir = _metadata_dir(locale)

    assert screenshots_dir.exists()
    assert preview_dir.exists()
    assert metadata_dir.exists()
    assert (screenshots_dir / "README.md").exists()
    assert (preview_dir / "README.md").exists()
    assert (preview_dir / "preview_script.md").exists()
    assert (metadata_dir / "source_of_truth.md").exists()
    assert (metadata_dir / "upload_checklist.md").exists()


@pytest.mark.parametrize("locale", LOCALES)
def test_app_store_metadata_stays_locale_scoped_and_within_limits(locale: str) -> None:
    """Validate locale, UTF-8 keyword budget, and safe subtitle constraints."""
    payload = _load_json(_metadata_dir(locale) / "app_store_metadata.json")

    assert payload["locale"] == locale
    assert payload["product_name"] == "PulsePlate"
    assert payload["brand_mascot"] == "FitChef"
    assert len(payload["subtitle"]) <= 30
    assert len(",".join(payload["keywords"])) <= 100
    if locale == "en-US":
        assert all(keyword.isascii() for keyword in payload["keywords"])
    assert len(payload["promo_text"]) <= 170
    assert len(payload["description_paragraphs"]) == 3

    visible_metadata = " ".join(
        [
            payload["subtitle"],
            payload["promo_text"],
            ",".join(payload["keywords"]),
            *payload["description_paragraphs"],
        ]
    ).lower()
    all_metadata = " ".join(_flatten_strings(payload)).lower()
    if locale == "ru-RU":
        assert "wellness" not in all_metadata
        english_fragments = (
            "localization pack",
            "wellness-only",
            "professional-role",
            "guaranteed-outcome",
            "shipped or canon-governed",
        )
        assert not [
            fragment for fragment in english_fragments if fragment in all_metadata
        ], "RU metadata contains English compliance-note copy"
    offending_terms = sorted(
        term for term in BLOCKED_COPY_TERMS[locale] if term in visible_metadata
    )
    assert not offending_terms, f"Blocked term(s) found in metadata: {offending_terms}"


@pytest.mark.parametrize("locale", LOCALES)
def test_screenshot_manifest_defines_seven_governed_shots_with_real_refs(
    locale: str,
) -> None:
    """Require exactly seven screenshot manifests tied to real repo surfaces."""
    payload = _load_json(_screenshots_dir(locale) / "shot_manifest.json")
    shots = payload["shots"]

    assert payload["locale"] == locale
    assert payload["device_class"] == "iPhone 6.9"
    assert payload["canvas_px"] == {"width": 1320, "height": 2868}
    assert len(shots) == 7
    assert [shot["id"] for shot in shots] == EXPECTED_SHOT_IDS

    filenames = [shot["expected_filename"] for shot in shots]
    assert len(filenames) == len(set(filenames))
    assert all(filename.endswith(".png") for filename in filenames)

    for shot in shots:
        assert shot["approved_mascot_asset_key"] in ALLOWED_MASCOT_KEYS
        assert shot["output_status"] == "source-approved"
        assert len(shot["headline"]) == 2
        assert 2 <= len(shot["supporting_copy"]) <= 3
        visible_copy = " ".join([*shot["headline"], *shot["supporting_copy"]]).lower()
        offending_terms = sorted(
            term for term in BLOCKED_COPY_TERMS[locale] if term in visible_copy
        )
        assert not offending_terms, f"Blocked term(s) found in shot copy: {offending_terms}"
        for source_ref in shot["repo_source_refs"]:
            assert _repo_path(source_ref).exists(), f"Missing source ref: {source_ref}"


@pytest.mark.parametrize("locale", LOCALES)
def test_preview_storyboard_is_bounded_and_reuses_manifest_shot_ids(locale: str) -> None:
    """Keep the preview script aligned with the screenshot sequence and time cap."""
    manifest = _load_json(_screenshots_dir(locale) / "shot_manifest.json")
    storyboard = _load_json(_preview_dir(locale) / "storyboard.json")
    expected_shot_ids = [shot["id"] for shot in manifest["shots"]]

    assert storyboard["locale"] == locale
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


@pytest.mark.parametrize("locale", LOCALES)
def test_icon_source_inventory_references_only_canonical_local_assets(locale: str) -> None:
    """App Store pack must point only to governed icon/mascot sources."""
    payload = _load_json(_metadata_dir(locale) / "icon_source_inventory.json")

    assert payload["locale"] == locale
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

    if locale == "ru-RU":
        decision_log = " ".join(payload["decision_log"])
        blocked_english_fragments = (
            "reuses the same",
            "localization lane",
            "dirty local root assets",
            "new binary exports",
            "future binary refresh",
            "dedicated reviewed PR",
            "canonical asset keys",
        )
        assert any("А" <= char <= "я" or char == "ё" for char in decision_log)
        offending_fragments = sorted(
            fragment for fragment in blocked_english_fragments if fragment in decision_log
        )
        assert not offending_fragments, (
            "RU icon inventory decision log contains English boilerplate: " f"{offending_fragments}"
        )


def test_ru_pack_reuses_en_structural_contract_without_binaries() -> None:
    """RU localization mirrors EN structure but remains text/JSON only."""
    en_manifest = _load_json(_screenshots_dir("en-US") / "shot_manifest.json")
    ru_manifest = _load_json(_screenshots_dir("ru-RU") / "shot_manifest.json")
    en_storyboard = _load_json(_preview_dir("en-US") / "storyboard.json")
    ru_storyboard = _load_json(_preview_dir("ru-RU") / "storyboard.json")

    assert [shot["id"] for shot in ru_manifest["shots"]] == [
        shot["id"] for shot in en_manifest["shots"]
    ]
    assert [shot["repo_source_refs"] for shot in ru_manifest["shots"]] == [
        shot["repo_source_refs"] for shot in en_manifest["shots"]
    ]
    assert [shot["product_surface"] for shot in ru_manifest["shots"]] == [
        shot["product_surface"] for shot in en_manifest["shots"]
    ]
    assert [shot["contract_emotion"] for shot in ru_manifest["shots"]] == [
        shot["contract_emotion"] for shot in en_manifest["shots"]
    ]
    assert [shot["approved_mascot_asset_key"] for shot in ru_manifest["shots"]] == [
        shot["approved_mascot_asset_key"] for shot in en_manifest["shots"]
    ]
    assert ru_manifest["safe_area_px"] == en_manifest["safe_area_px"]
    assert [scene["shot_id"] for scene in ru_storyboard["scenes"]] == [
        scene["shot_id"] for scene in en_storyboard["scenes"]
    ]
    assert [scene["id"] for scene in ru_storyboard["scenes"]] == [
        scene["id"] for scene in en_storyboard["scenes"]
    ]
    assert [scene["start_second"] for scene in ru_storyboard["scenes"]] == [
        scene["start_second"] for scene in en_storyboard["scenes"]
    ]
    assert [scene["end_second"] for scene in ru_storyboard["scenes"]] == [
        scene["end_second"] for scene in en_storyboard["scenes"]
    ]

    unsupported_files = [
        path
        for path in _pack_root("ru-RU").rglob("*")
        if path.is_file() and path.suffix.lower() not in ALLOWED_RU_PACK_SUFFIXES
    ]
    assert not unsupported_files, f"RU pack must stay text/JSON only: {unsupported_files}"


def test_ru_preview_plan_uses_ru_operational_copy() -> None:
    """The ru-RU preview plan should not mix in English storyboard boilerplate."""
    storyboard = _load_json(_preview_dir("ru-RU") / "storyboard.json")
    text = " ".join(
        [
            (_preview_dir("ru-RU") / "preview_script.md").read_text(encoding="utf-8"),
            *(scene["focus"] for scene in storyboard["scenes"]),
        ]
    )
    blocked_english_fragments = (
        "## Duration",
        "## Script",
        "seconds target total",
        "Show ",
        "Caption:",
        "Finish on",
        " opens with ",
        "supporting cue",
        "logo lockup",
        "opening frame",
        "Macro and",
        "Weekly meal",
        "Shopping list",
        "Progress and",
        "Personalized goals",
        "assistant finish",
    )

    offending_fragments = sorted(
        fragment for fragment in blocked_english_fragments if fragment in text
    )
    assert not offending_fragments, (
        "RU preview plan contains English operational copy: " f"{offending_fragments}"
    )


def test_ru_screenshot_manifest_rationales_are_localized() -> None:
    """RU handoff rationale strings should not retain EN manifest boilerplate."""
    manifest = _load_json(_screenshots_dir("ru-RU") / "shot_manifest.json")
    rationales = " ".join(shot["asset_rationale"] for shot in manifest["shots"])
    blocked_english_fragments = (
        "canonical welcoming",
        "existing asset taxonomy",
        "dedicated explaining",
        "explanatory fallback",
        "cooking-specific",
        "mascot variant",
        "default neutral",
        "currently available",
        "guiding fallback",
    )

    assert any("А" <= char <= "я" or char == "ё" for char in rationales)
    offending_fragments = sorted(
        fragment for fragment in blocked_english_fragments if fragment in rationales
    )
    assert not offending_fragments, (
        "RU manifest rationale contains English boilerplate: " f"{offending_fragments}"
    )


def test_ru_wellness_blockers_do_not_reject_food_recipe_copy() -> None:
    """FitChef food-recipe copy must not be blocked as prescription language."""
    recipe_copies = (
        "Рецепты, меню и список покупок помогают спокойнее планировать питание.",
        "Подборка рецептов помогает собрать недельное меню.",
    )

    for recipe_copy in recipe_copies:
        offending_terms = sorted(
            term for term in BLOCKED_COPY_TERMS["ru-RU"] if term in recipe_copy.lower()
        )
        assert not offending_terms, f"Food recipe copy should stay allowed: {offending_terms}"


@pytest.mark.parametrize(
    ("prescription_copy", "expected_term"),
    [
        ("Рецепт на лекарства помогает контролировать курс.", "лекарств"),
        ("Рецепт препарата не относится к wellness-планированию.", "препарат"),
        ("План таблеток не должен попадать в App Store pack.", "таблет"),
    ],
)
def test_ru_wellness_blockers_reject_prescription_medicine_copy(
    prescription_copy: str,
    expected_term: str,
) -> None:
    """RU pack guards must block prescription-medicine context without blocking food recipes."""
    offending_terms = sorted(
        term for term in BLOCKED_COPY_TERMS["ru-RU"] if term in prescription_copy.lower()
    )

    assert expected_term in offending_terms


def test_ru_pack_docs_preserve_no_upload_scope_and_safe_claims() -> None:
    """RU markdown/script files must stay scoped to repo prep, not upload readiness."""
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in _pack_root("ru-RU").rglob("*")
        if path.is_file() and path.suffix == ".md"
    ).lower()
    blocked_english_fragments = (
        "this folder",
        "this pr",
        "does not commit",
        "final video binary",
        "capture-ready",
        "governing order",
        "operating rules",
        "locale:",
        "target device",
        "screenshot order",
        "headlines and subtext",
        "metadata matches",
        "remain out of scope",
    )

    assert "fastlane" in text
    assert "app store connect" in text
    assert "вне области" in text
    english_fragments = sorted(
        fragment for fragment in blocked_english_fragments if fragment in text
    )
    assert not english_fragments, f"RU docs contain English operational copy: {english_fragments}"
    safe_boundary_text = text.replace("неклиническим", "")
    offending_terms = sorted(
        term for term in BLOCKED_COPY_TERMS["ru-RU"] if term in safe_boundary_text
    )
    assert not offending_terms, f"Blocked term(s) found in RU docs: {offending_terms}"
