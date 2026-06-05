from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_BASE = REPO_ROOT / "appstore" / "fitchef"
LOCALES = ("en-US", "ru-RU", "es-ES")
LOCALIZED_LOCALES = ("ru-RU", "es-ES")
ALLOWED_TEXT_PACK_SUFFIXES = {".json", ".md"}
MEDIA_SUFFIXES = {".heic", ".jpeg", ".jpg", ".mov", ".mp4", ".pdf", ".png", ".webp"}
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
        "лечить",
        "лечение",
        "терап",
        "врач",
        "пациент",
        "клиничес",
        "диетолог",
        "эксперт по питанию",
        "лекарств",
        "медицин",
        "нутрициолог",
        "препарат",
        "таблет",
        "гарантир",
        "мгновенн",
        "быстрые результаты",
        "доказанн",
        "пробный период",
        "подписк",
        "скидк",
    ),
    "es-ES": (
        "diagnos",
        "trata",
        "tratar",
        "tratamiento",
        "curar",
        "cura",
        "terapia",
        "terapeut",
        "medico",
        "medica",
        "doctor",
        "paciente",
        "clinic",
        "nutricionista",
        "dietista",
        "experto en nutricion",
        "receta medica",
        "prescripcion",
        "medicamento",
        "farmaco",
        "pastilla",
        "pildora",
        "dosis",
        "garantiz",
        "resultados rapidos",
        "resultados inmediatos",
        "adelgaza rapido",
        "pierde peso rapido",
        "quema grasa",
        "transforma tu cuerpo",
        "100% efectivo",
        "diabetes",
        "colesterol",
        "hipertension",
        "obesidad",
        "ansiedad",
        "depresion",
        "trastorno alimentario",
        "prueba gratis",
        "suscripcion",
        "descuento",
        "precio",
        "#1",
        "mejor app",
        "clinicamente probado",
        "recomendado por medicos",
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
LOCALIZED_REQUIRED_MARKERS = {
    "ru-RU": ("вне области",),
    "es-ES": ("fuera del alcance", "internal_review_only"),
}
LOCALE_SCRIPT_RANGES = {
    "ru-RU": ("А", "я", "ё"),
}
LOCALE_COPY_SIGNALS = {
    "es-ES": (
        "balance diario",
        "apoyo",
        "actualizacion",
        "activos",
        "analisis",
        "canonico",
        "comidas",
        "configuracion",
        "compra",
        "clara",
        "entiende",
        "fuera del alcance",
        "habitos",
        "ideas",
        "lista",
        "localizacion",
        "macros",
        "medida",
        "menu",
        "meta",
        "metas",
        "micronutrientes",
        "nutrientes",
        "nutricion",
        "orientacion",
        "paquete",
        "peso",
        "perfil",
        "planificacion",
        "practica",
        "preferencias",
        "progreso",
        "sigue",
        "sugerencia",
        "sugerencias",
        "tipos",
        "utiles",
    ),
}
LOCALE_KEYWORD_SIGNALS = {
    "es-ES": (
        "alimentos",
        "calorias",
        "habitos",
        "imc",
        "ia",
        "lista compra",
        "macros",
        "menu",
        "nutricion",
        "plan comidas",
        "recetas",
    ),
}
LOCALE_BOILERPLATE_FRAGMENTS = {
    "ru-RU": (
        "localization pack",
        "wellness-only",
        "professional-role",
        "guaranteed-outcome",
        "shipped or canon-governed",
    ),
    "es-ES": (
        "localization pack",
        "wellness-only",
        "professional-role",
        "guaranteed-outcome",
        "shipped or canon-governed",
        "pricing",
        "placeholder lorem ipsum",
        "lorem ipsum",
    ),
}
LOCALIZED_DECISION_LOG_BLOCKED_ENGLISH = {
    "ru-RU": (
        "reuses the same",
        "localization lane",
        "dirty local root assets",
        "new binary exports",
        "future binary refresh",
        "dedicated reviewed PR",
        "canonical asset keys",
    ),
    "es-ES": (
        "reuses the same",
        "localization lane",
        "dirty local root assets",
        "new binary exports",
        "future binary refresh",
        "dedicated reviewed PR",
        "canonical asset keys",
    ),
}
LOCALIZED_PREVIEW_BLOCKED_ENGLISH = {
    "ru-RU": (
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
    ),
    "es-ES": (
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
    ),
}
LOCALIZED_MANIFEST_BLOCKED_ENGLISH = {
    "ru-RU": (
        "canonical welcoming",
        "existing asset taxonomy",
        "dedicated explaining",
        "explanatory fallback",
        "cooking-specific",
        "mascot variant",
        "default neutral",
        "currently available",
        "guiding fallback",
    ),
    "es-ES": (
        "canonical welcoming",
        "existing asset taxonomy",
        "dedicated explaining",
        "explanatory fallback",
        "cooking-specific",
        "mascot variant",
        "default neutral",
        "currently available",
        "guiding fallback",
    ),
}
LOCALIZED_DOC_BLOCKED_ENGLISH = {
    "ru-RU": (
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
        "wellness-only",
        "placeholder lorem ipsum",
        "lorem ipsum",
        "remain out of scope",
    ),
    "es-ES": (
        "this folder",
        "this pr",
        "does not commit",
        "final video binary",
        "capture-ready",
        "governing order",
        "operating rules",
        "target device",
        "screenshot order",
        "headlines and subtext",
        "metadata matches",
        "wellness-only",
        "placeholder lorem ipsum",
        "lorem ipsum",
        "remain out of scope",
    ),
}
NO_UPLOAD_CLAIMS = (
    "submit_ready",
    "release-ready",
    "submission-ready",
    "ready for upload",
    "upload proof",
    "app store connect draft",
    "готов к загрузке",
    "готова к загрузке",
    "готов к отправке",
    "готова к отправке",
    "готов к релизу",
    "listo para subir",
    "lista para subir",
    "listo para enviar",
    "lista para enviar",
    "listo para lanzamiento",
    "lista para lanzamiento",
    "subida completada",
    "publicado en app store",
)
LOCAL_PATH_AND_SECRET_FRAGMENTS = (
    "/users/",
    "/tmp/",
    "file://",
    "worktrees/",
    "artifacts/",
    ".venv/",
    "node_modules/",
    "gh_token",
    "github_token",
    "api_key",
    "secret",
    "password",
)


def _pack_root(locale: str) -> Path:
    """Return the governed App Store pack root for a locale."""
    return PACK_BASE / locale


def _screenshots_dir(locale: str) -> Path:
    return _pack_root(locale) / "iphone-6.9" / "screenshots"


def _preview_dir(locale: str) -> Path:
    return _pack_root(locale) / "iphone-6.9" / "preview"


def _metadata_dir(locale: str) -> Path:
    return _pack_root(locale) / "metadata"


def _visual_qa_prep_path(locale: str = "ru-RU") -> Path:
    return _pack_root(locale) / "iphone-6.9" / "visual_qa_prep.md"


def _cross_locale_review_prep_path() -> Path:
    return PACK_BASE / "localization_qa" / "cross_locale_review_prep.md"


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


def _has_locale_script(text: str, locale: str) -> bool:
    if locale in LOCALE_COPY_SIGNALS:
        return _has_locale_signal(text, LOCALE_COPY_SIGNALS[locale])
    if locale not in LOCALE_SCRIPT_RANGES:
        return True
    start, end, extra = LOCALE_SCRIPT_RANGES[locale]
    return any(start <= char.lower() <= end or char.lower() == extra for char in text)


def _has_locale_keyword_signal(keyword: str, locale: str) -> bool:
    if locale in LOCALE_KEYWORD_SIGNALS:
        return _has_locale_signal(keyword, LOCALE_KEYWORD_SIGNALS[locale])
    return _has_locale_script(keyword, locale)


def _has_locale_signal(text: str, signals: Iterable[str]) -> bool:
    scan_text = _claim_scan_text(text)
    tokens = set(re.findall(r"[a-z0-9]+", scan_text))
    for signal in signals:
        normalized_signal = _claim_scan_text(signal)
        if " " in normalized_signal:
            if normalized_signal in scan_text:
                return True
            continue
        if len(normalized_signal) <= 3:
            if normalized_signal in tokens:
                return True
            continue
        if normalized_signal in scan_text:
            return True
    return False


def _claim_scan_text(text: str) -> str:
    """Normalize localized App Store copy before matching safety blocker stems."""
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _blocked_terms_in(locale: str, text: str) -> list[str]:
    scan_text = _claim_scan_text(text)
    return sorted(term for term in BLOCKED_COPY_TERMS[locale] if term in scan_text)


def _blocked_fragments_in_texts(
    blocked_fragments: Iterable[str],
    texts: Iterable[str],
) -> list[str]:
    """Match blocked fragments case-insensitively with accent folding."""
    scan_texts = [_claim_scan_text(text) for text in texts]
    return sorted(
        fragment
        for fragment in blocked_fragments
        if any(_claim_scan_text(fragment) in scan_text for scan_text in scan_texts)
    )


def _blocked_upload_claims_in(text: str) -> list[str]:
    """Return upload/submission claims after locale-safe normalization."""
    scan_text = _claim_scan_text(text)
    return sorted(claim for claim in NO_UPLOAD_CLAIMS if _claim_scan_text(claim) in scan_text)


def _safety_blockers_in(locale: str, text: str) -> list[str]:
    return [*_blocked_terms_in(locale, text), *_blocked_upload_claims_in(text)]


def test_es_locale_signal_rejects_copied_english_copy() -> None:
    """ES localization guards must not accept copied EN operational text."""
    copied_english_rationale = (
        "Uses live dashboard context and keeps the mascot as a supportive layer."
    )
    copied_english_decision_log = (
        "Reuses the same localization lane without dirty local root assets."
    )
    spanish_rationale = "Usa datos de nutricion y mantiene FitChef como apoyo visual."
    spanish_decision_log = "La localizacion queda fuera del alcance de la carga protegida."
    mixed_rationales = (spanish_rationale, copied_english_rationale)

    assert not _has_locale_script(copied_english_rationale, "es-ES")
    assert not _has_locale_script(copied_english_decision_log, "es-ES")
    assert _has_locale_script(spanish_rationale, "es-ES")
    assert _has_locale_script(spanish_decision_log, "es-ES")
    assert all(_has_locale_script(rationale, "es-ES") for rationale in mixed_rationales) is False


def _unsupported_text_pack_files(locale: str) -> list[Path]:
    return [
        path
        for path in _pack_root(locale).rglob("*")
        if path.is_file() and path.suffix.lower() not in ALLOWED_TEXT_PACK_SUFFIXES
    ]


def _media_files_under(path: Path) -> list[Path]:
    return [
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in MEDIA_SUFFIXES
    ]


def _localized_markdown_files(locale: str) -> list[Path]:
    return sorted(
        path for path in _pack_root(locale).rglob("*") if path.is_file() and path.suffix == ".md"
    )


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
    assert (metadata_dir / "app_store_metadata.json").exists()
    assert (metadata_dir / "icon_source_inventory.json").exists()
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
    )
    all_metadata = " ".join(_flatten_strings(payload)).lower()
    if locale in LOCALIZED_LOCALES:
        assert "wellness" not in all_metadata
        english_fragments = LOCALE_BOILERPLATE_FRAGMENTS[locale]
        assert not [
            fragment for fragment in english_fragments if fragment in all_metadata
        ], f"{locale} metadata contains English compliance-note copy"
        localized_visible_fields = (
            payload["subtitle"],
            payload["promo_text"],
            *payload["description_paragraphs"],
        )
        assert all(
            _has_locale_script(field, locale) for field in localized_visible_fields
        ), f"{locale} visible metadata field lacks locale-specific copy signal"
        assert all(
            _has_locale_keyword_signal(keyword, locale) for keyword in payload["keywords"]
        ), f"{locale} metadata keyword lacks locale-specific copy signal"
    offending_terms = _blocked_terms_in(locale, visible_metadata)
    assert not offending_terms, f"Blocked term(s) found in metadata: {offending_terms}"
    upload_claims = _blocked_upload_claims_in(visible_metadata)
    assert not upload_claims, f"{locale} metadata overclaims release scope: {upload_claims}"


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
        visible_copy = " ".join([*shot["headline"], *shot["supporting_copy"]])
        if locale in LOCALIZED_LOCALES:
            for line_kind in ("headline", "supporting_copy"):
                for index, copy_line in enumerate(shot[line_kind], start=1):
                    assert _has_locale_script(copy_line, locale), (
                        f"{locale} {line_kind} line {index} for {shot['id']} "
                        "lacks locale-specific copy signal"
                    )
        offending_terms = _blocked_terms_in(locale, visible_copy)
        assert not offending_terms, f"Blocked term(s) found in shot copy: {offending_terms}"
        upload_claims = _blocked_upload_claims_in(visible_copy)
        assert not upload_claims, f"{locale} shot copy overclaims release scope: {upload_claims}"
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

    if locale in LOCALIZED_LOCALES:
        blocked_english_fragments = LOCALIZED_DECISION_LOG_BLOCKED_ENGLISH[locale]
        assert all(
            _has_locale_script(entry, locale) for entry in payload["decision_log"]
        ), f"{locale} icon inventory decision entry lacks locale-specific copy signal"
        offending_fragments = _blocked_fragments_in_texts(
            blocked_english_fragments,
            payload["decision_log"],
        )
        assert not offending_fragments, (
            f"{locale} icon inventory decision log contains English boilerplate: "
            f"{offending_fragments}"
        )
        for entry in payload["decision_log"]:
            safety_blockers = _safety_blockers_in(locale, entry)
            assert not safety_blockers, (
                f"{locale} icon inventory decision log contains unsafe claim: " f"{safety_blockers}"
            )


@pytest.mark.parametrize("localized_locale", LOCALIZED_LOCALES)
def test_localized_packs_reuse_en_structural_contract_without_binaries(
    localized_locale: str,
) -> None:
    """Localized packs mirror EN structure but remain text/JSON only."""
    en_manifest = _load_json(_screenshots_dir("en-US") / "shot_manifest.json")
    localized_manifest = _load_json(_screenshots_dir(localized_locale) / "shot_manifest.json")
    en_storyboard = _load_json(_preview_dir("en-US") / "storyboard.json")
    localized_storyboard = _load_json(_preview_dir(localized_locale) / "storyboard.json")

    assert [shot["id"] for shot in localized_manifest["shots"]] == [
        shot["id"] for shot in en_manifest["shots"]
    ]
    assert [shot["repo_source_refs"] for shot in localized_manifest["shots"]] == [
        shot["repo_source_refs"] for shot in en_manifest["shots"]
    ]
    assert [shot["product_surface"] for shot in localized_manifest["shots"]] == [
        shot["product_surface"] for shot in en_manifest["shots"]
    ]
    assert [shot["contract_emotion"] for shot in localized_manifest["shots"]] == [
        shot["contract_emotion"] for shot in en_manifest["shots"]
    ]
    assert [shot["approved_mascot_asset_key"] for shot in localized_manifest["shots"]] == [
        shot["approved_mascot_asset_key"] for shot in en_manifest["shots"]
    ]
    assert localized_manifest["safe_area_px"] == en_manifest["safe_area_px"]
    assert [scene["shot_id"] for scene in localized_storyboard["scenes"]] == [
        scene["shot_id"] for scene in en_storyboard["scenes"]
    ]
    assert [scene["id"] for scene in localized_storyboard["scenes"]] == [
        scene["id"] for scene in en_storyboard["scenes"]
    ]
    assert [scene["start_second"] for scene in localized_storyboard["scenes"]] == [
        scene["start_second"] for scene in en_storyboard["scenes"]
    ]
    assert [scene["end_second"] for scene in localized_storyboard["scenes"]] == [
        scene["end_second"] for scene in en_storyboard["scenes"]
    ]

    unsupported_files = _unsupported_text_pack_files(localized_locale)
    assert (
        not unsupported_files
    ), f"{localized_locale} pack must stay text/JSON only: {unsupported_files}"


def test_ru_visual_qa_prep_exists_and_pack_stays_text_only() -> None:
    """The RU visual-QA prep bundle must stay as governed text, not media output."""
    prep_path = _visual_qa_prep_path()

    assert prep_path.exists()
    assert prep_path.suffix == ".md"

    unsupported_files = _unsupported_text_pack_files("ru-RU")
    assert not unsupported_files, f"RU pack must stay text/JSON only: {unsupported_files}"


def test_ru_visual_qa_prep_covers_manifest_and_storyboard_in_order() -> None:
    """Prep notes should cover the governed seven-shot RU sequence once in order."""
    manifest = _load_json(_screenshots_dir("ru-RU") / "shot_manifest.json")
    storyboard = _load_json(_preview_dir("ru-RU") / "storyboard.json")
    scenes_by_shot_id = {scene["shot_id"]: scene for scene in storyboard["scenes"]}
    text = _visual_qa_prep_path().read_text(encoding="utf-8")

    previous_index = -1
    for shot in manifest["shots"]:
        shot_id = shot["id"]
        scene = scenes_by_shot_id[shot_id]
        shot_anchor = f"`{shot_id}`"
        shot_index = text.find(shot_anchor)

        assert shot_index > previous_index
        assert text.count(shot_anchor) == 1
        assert f"`{shot['expected_filename']}`" in text
        assert f"`{scene['id']}`" in text
        assert f"`{scene['start_second']}-{scene['end_second']}s`" in text
        assert shot["product_surface"] in text
        assert shot["approved_mascot_asset_key"] in text
        for source_ref in shot["repo_source_refs"]:
            assert f"`{source_ref}`" in text
            assert _repo_path(source_ref).exists()
        previous_index = shot_index


def test_ru_visual_qa_prep_preserves_manual_no_upload_scope() -> None:
    """Visual QA prep must not imply protected release or upload authority."""
    text = _visual_qa_prep_path().read_text(encoding="utf-8").lower()
    assert "fastlane" in text
    assert "app store connect" in text
    assert "вне области" in text
    assert "internal_review_only" in text
    offending_claims = sorted(claim for claim in NO_UPLOAD_CLAIMS if claim in text)
    assert not offending_claims, f"RU visual QA prep overclaims release scope: {offending_claims}"


def test_ru_visual_qa_prep_avoids_local_paths_and_blocked_claim_terms() -> None:
    """Prep notes must stay repo-relative and wellness-safe."""
    text = _visual_qa_prep_path().read_text(encoding="utf-8")
    text_lower = text.lower()
    blocked_english_fragments = (
        "this folder",
        "this pr",
        "wellness-only",
        "remain out of scope",
        "placeholder lorem ipsum",
        "lorem ipsum",
    )

    assert any("А" <= char <= "я" or char == "ё" for char in text)
    offending_fragments = sorted(
        fragment
        for fragment in (*LOCAL_PATH_AND_SECRET_FRAGMENTS, *blocked_english_fragments)
        if fragment in text_lower
    )
    assert not offending_fragments, (
        "RU visual QA prep contains unsafe local or English boilerplate fragments: "
        f"{offending_fragments}"
    )

    offending_terms = _blocked_terms_in("ru-RU", text_lower)
    assert not offending_terms, "Blocked term(s) found in RU visual QA prep: " f"{offending_terms}"


@pytest.mark.parametrize("locale", LOCALIZED_LOCALES)
def test_localized_preview_plan_uses_localized_operational_copy(locale: str) -> None:
    """Localized preview plans should not mix in English storyboard boilerplate."""
    storyboard = _load_json(_preview_dir(locale) / "storyboard.json")
    preview_script = (_preview_dir(locale) / "preview_script.md").read_text(encoding="utf-8")
    text = " ".join(
        [
            preview_script,
            *(scene["focus"] for scene in storyboard["scenes"]),
        ]
    )
    text_lower = text.lower()
    blocked_english_fragments = LOCALIZED_PREVIEW_BLOCKED_ENGLISH[locale]

    offending_fragments = sorted(
        fragment for fragment in blocked_english_fragments if fragment.lower() in text_lower
    )
    assert (
        not offending_fragments
    ), f"{locale} preview plan contains English operational copy: {offending_fragments}"
    assert _has_locale_script(
        preview_script, locale
    ), f"{locale} preview script lacks locale-specific copy signal"
    assert all(
        _has_locale_script(scene["focus"], locale) for scene in storyboard["scenes"]
    ), f"{locale} preview scene focus lacks locale-specific copy signal"
    for scene in storyboard["scenes"]:
        safety_blockers = _safety_blockers_in(locale, scene["focus"])
        assert (
            not safety_blockers
        ), f"{locale} preview scene focus contains unsafe claim: {safety_blockers}"


@pytest.mark.parametrize("locale", LOCALIZED_LOCALES)
def test_localized_screenshot_manifest_rationales_are_localized(locale: str) -> None:
    """Localized handoff rationale strings should not retain EN manifest boilerplate."""
    manifest = _load_json(_screenshots_dir(locale) / "shot_manifest.json")
    rationales = [shot["asset_rationale"] for shot in manifest["shots"]]
    blocked_english_fragments = LOCALIZED_MANIFEST_BLOCKED_ENGLISH[locale]

    assert all(_has_locale_script(rationale, locale) for rationale in rationales)
    offending_fragments = _blocked_fragments_in_texts(
        blocked_english_fragments,
        rationales,
    )
    assert (
        not offending_fragments
    ), f"{locale} manifest rationale contains English boilerplate: {offending_fragments}"
    for rationale in rationales:
        safety_blockers = _safety_blockers_in(locale, rationale)
        assert (
            not safety_blockers
        ), f"{locale} manifest rationale contains unsafe claim: {safety_blockers}"


def test_ru_wellness_blockers_do_not_reject_food_recipe_copy() -> None:
    """FitChef food-recipe copy must not be blocked as prescription language."""
    recipe_copies = (
        "Рецепты, меню и список покупок помогают спокойнее планировать питание.",
        "Подборка рецептов помогает собрать недельное меню.",
    )

    for recipe_copy in recipe_copies:
        offending_terms = _blocked_terms_in("ru-RU", recipe_copy)
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
    offending_terms = _blocked_terms_in("ru-RU", prescription_copy)

    assert expected_term in offending_terms


@pytest.mark.parametrize("locale", LOCALIZED_LOCALES)
def test_localized_pack_docs_preserve_no_upload_scope_and_safe_claims(locale: str) -> None:
    """Localized markdown/script files must stay scoped to repo prep, not upload readiness."""
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in _localized_markdown_files(locale)
    ).lower()
    blocked_english_fragments = LOCALIZED_DOC_BLOCKED_ENGLISH[locale]

    assert "fastlane" in text
    assert "app store connect" in text
    assert all(marker in text for marker in LOCALIZED_REQUIRED_MARKERS[locale])
    english_fragments = sorted(
        fragment for fragment in blocked_english_fragments if fragment in text
    )
    assert (
        not english_fragments
    ), f"{locale} docs contain English operational copy: {english_fragments}"
    upload_claims = _blocked_upload_claims_in(text)
    assert not upload_claims, f"{locale} docs overclaim release scope: {upload_claims}"
    safe_boundary_text = text.replace("неклиническим", "")
    offending_terms = _blocked_terms_in(locale, safe_boundary_text)
    assert not offending_terms, f"Blocked term(s) found in {locale} docs: {offending_terms}"


@pytest.mark.parametrize("locale", LOCALIZED_LOCALES)
def test_localized_pack_docs_are_localized_per_file(locale: str) -> None:
    """One localized markdown file must not mask a copied-English sibling file."""
    blocked_english_fragments = LOCALIZED_DOC_BLOCKED_ENGLISH[locale]
    scope_markers = LOCALIZED_REQUIRED_MARKERS[locale]

    for path in _localized_markdown_files(locale):
        text = path.read_text(encoding="utf-8")
        text_lower = text.lower()

        assert _has_locale_script(
            text, locale
        ), f"{locale} markdown file lacks locale-specific copy signal: {path}"
        if path.name != "preview_script.md":
            assert any(
                marker in text_lower for marker in scope_markers
            ), f"{locale} markdown file lacks scoped review marker: {path}"
        english_fragments = sorted(
            fragment for fragment in blocked_english_fragments if fragment in text_lower
        )
        assert (
            not english_fragments
        ), f"{locale} markdown file contains English operational copy: {english_fragments}"
        upload_claims = _blocked_upload_claims_in(text_lower)
        assert not upload_claims, f"{locale} markdown file overclaims release scope: {path}"
        safe_boundary_text = text_lower.replace("неклиническим", "")
        offending_terms = _blocked_terms_in(locale, safe_boundary_text)
        assert not offending_terms, f"Blocked term(s) found in {locale} docs: {offending_terms}"


def test_es_metadata_locale_guard_rejects_single_signal_false_green() -> None:
    """One Spanish keyword must not make copied-English visible metadata acceptable."""
    payload = {
        "subtitle": "Nutrition planning",
        "promo_text": "Plan meals with calmer daily support.",
        "keywords": ["nutrición", "IA"],
        "description_paragraphs": [
            "Track nutrients and plan meals.",
            "Build a weekly menu.",
            "Use friendly FitChef suggestions.",
        ],
    }
    localized_visible_fields = (
        payload["subtitle"],
        payload["promo_text"],
        *payload["description_paragraphs"],
    )

    assert _has_locale_keyword_signal("nutrición", "es-ES")
    assert not all(_has_locale_script(field, "es-ES") for field in localized_visible_fields)


def test_es_metadata_keyword_guard_rejects_masked_english_keyword() -> None:
    """One Spanish keyword must not mask an untranslated keyword sibling."""
    assert _has_locale_keyword_signal("nutrición", "es-ES")
    assert _has_locale_keyword_signal("IA", "es-ES")
    assert not _has_locale_keyword_signal("weekly planner", "es-ES")


def test_es_screenshot_copy_guard_rejects_masked_english_headline() -> None:
    """Spanish support copy must not mask a copied-English screenshot headline."""
    english_headline = "Smart Nutrition Powered by AI"
    spanish_support = "Nutrientes plan comidas hábitos"

    assert not _has_locale_script(english_headline, "es-ES")
    assert _has_locale_script(spanish_support, "es-ES")


def test_es_preview_guard_rejects_masked_english_scene_focus() -> None:
    """Spanish script text must not mask an untranslated storyboard scene focus."""
    english_focus = "Understand daily balance"
    spanish_script = "Mostrar el análisis de macros y micronutrientes."

    assert not _has_locale_script(english_focus, "es-ES")
    assert _has_locale_script(spanish_script, "es-ES")


def test_es_icon_decision_guard_rejects_masked_english_entry() -> None:
    """One Spanish decision entry must not mask an untranslated sibling entry."""
    english_decision = "The approved EN production pack references canonical source assets."
    spanish_decision = "Esta línea de localización no promociona nuevos binarios."

    assert not _has_locale_script(english_decision, "es-ES")
    assert _has_locale_script(spanish_decision, "es-ES")


def test_localized_pack_docs_reject_no_upload_claims() -> None:
    """Localized docs must not become protected upload or submission-readiness proof."""
    assert "listo para subir" in NO_UPLOAD_CLAIMS
    assert "готов к загрузке" in NO_UPLOAD_CLAIMS
    assert "listo para subir" in _blocked_upload_claims_in("Paquete Listo Para Subir")
    assert "ready for upload" in _blocked_upload_claims_in("Metadata Ready For Upload")


def test_localized_json_copy_guards_reject_upload_and_safety_claims() -> None:
    """Localized JSON handoff fields must reject upload and wellness overclaims."""
    upload_claim = "Planificación lista para enviar"
    guaranteed_claim = "Vista con resultados garantizados"

    assert "lista para enviar" in _blocked_upload_claims_in(upload_claim)
    assert "garantiz" in _blocked_terms_in("es-ES", guaranteed_claim)
    assert _safety_blockers_in("es-ES", upload_claim)
    assert _safety_blockers_in("es-ES", guaranteed_claim)


def test_localized_manifest_boilerplate_guard_is_case_insensitive() -> None:
    """Capitalized copied EN rationale fragments must stay blocked."""
    blocked = _blocked_fragments_in_texts(
        LOCALIZED_MANIFEST_BLOCKED_ENGLISH["es-ES"],
        ["Mantiene apoyo visual. Canonical Welcoming mascot variant."],
    )

    assert "canonical welcoming" in blocked
    assert "mascot variant" in blocked


def test_localized_icon_decision_guard_is_case_insensitive() -> None:
    """Capitalized copied EN decision-log fragments must stay blocked."""
    blocked = _blocked_fragments_in_texts(
        LOCALIZED_DECISION_LOG_BLOCKED_ENGLISH["es-ES"],
        ["Reuses The Same localization lane without Dirty Local Root Assets."],
    )

    assert "reuses the same" in blocked
    assert "dirty local root assets" in blocked


def test_es_doc_file_guard_rejects_masked_english_doc() -> None:
    """One scoped Spanish markdown file must not mask a copied-English sibling file."""
    english_doc = "This folder prepares screenshots for future review."
    spanish_doc = "La localización queda fuera del alcance de la carga protegida."

    assert not _has_locale_script(english_doc, "es-ES")
    assert _has_locale_script(spanish_doc, "es-ES")


@pytest.mark.parametrize(
    ("blocked_copy", "expected_term"),
    [
        ("Оформите подписку для доступа к плану.", "подписк"),
        ("Условия подписки остаются за StoreKit.", "подписк"),
        ("Помогает лечить привычки.", "лечить"),
        ("Советы диетолога для вашего рациона.", "диетолог"),
        ("Эксперт по питанию рядом каждый день.", "эксперт по питанию"),
    ],
)
def test_ru_wellness_blockers_reject_storekit_and_treatment_copy(
    blocked_copy: str,
    expected_term: str,
) -> None:
    """RU pack guards should catch subscription and treatment declensions."""
    offending_terms = _blocked_terms_in("ru-RU", blocked_copy)

    assert expected_term in offending_terms


def test_es_pack_stays_text_only_and_has_no_media_binaries() -> None:
    """ES localization pack must not commit screenshots, preview videos, or PDFs."""
    unsupported_files = _unsupported_text_pack_files("es-ES")
    media_files = _media_files_under(_pack_root("es-ES"))

    assert not unsupported_files, f"ES pack must stay text/JSON only: {unsupported_files}"
    assert not media_files, f"ES pack must not contain media binaries: {media_files}"


def test_cross_locale_review_prep_exists_and_stays_text_only() -> None:
    """The cross-locale QA bundle must stay as governed text, not media output."""
    prep_path = _cross_locale_review_prep_path()
    qa_dir = prep_path.parent

    assert prep_path.exists()
    assert prep_path.suffix == ".md"
    assert qa_dir != _pack_root("en-US")
    assert qa_dir != _pack_root("ru-RU")
    assert qa_dir != _pack_root("es-ES")

    unsupported_files = [
        path for path in qa_dir.rglob("*") if path.is_file() and path.suffix.lower() != ".md"
    ]
    media_files = _media_files_under(qa_dir)
    assert not unsupported_files, f"Cross-locale QA must stay markdown-only: {unsupported_files}"
    assert not media_files, f"Cross-locale QA must not contain media binaries: {media_files}"


def test_cross_locale_review_prep_covers_sources_and_seven_shots() -> None:
    """Cross-locale QA notes must cover all locale packs and seven-shot parity."""
    text = _cross_locale_review_prep_path().read_text(encoding="utf-8")
    lower_text = text.lower()

    assert "internal_review_only" in lower_text
    assert "fastlane" in lower_text
    assert "app store connect" in lower_text
    assert "does not change" in lower_text
    assert "Safe area: `top=260px`, `bottom=260px`, `left_right=120px`" in text

    for locale in LOCALES:
        assert f"`{locale}`" in text
        assert f"appstore/fitchef/{locale}/iphone-6.9/screenshots/shot_manifest.json" in text
        assert f"appstore/fitchef/{locale}/iphone-6.9/preview/storyboard.json" in text
        manifest = _load_json(_screenshots_dir(locale) / "shot_manifest.json")
        storyboard = _load_json(_preview_dir(locale) / "storyboard.json")
        for shot, scene in zip(manifest["shots"], storyboard["scenes"], strict=True):
            row_anchor = f"| `{locale}` | `{shot['id']}` |"
            matching_rows = [line for line in text.splitlines() if line.startswith(row_anchor)]
            assert len(matching_rows) == 1
            row = matching_rows[0]
            headline_text = " / ".join(shot["headline"])
            supporting_text = " / ".join(shot["supporting_copy"])
            copy_lines = [*shot["headline"], *shot["supporting_copy"]]
            max_line_chars = max(len(line) for line in copy_lines)
            longest_token_chars = max(
                len(token) for line in copy_lines for token in line.replace("/", " ").split()
            )

            assert f"`{shot['expected_filename']}`" in row
            assert f"`{scene['id']}`" in row
            assert f"`{scene['start_second']}-{scene['end_second']}s`" in row
            assert shot["product_surface"] in row
            assert shot["approved_mascot_asset_key"] in row
            assert headline_text in row
            assert supporting_text in row
            assert f"| {max_line_chars} | {longest_token_chars} |" in row
            for source_ref in shot["repo_source_refs"]:
                assert f"`{source_ref}`" in row
                assert _repo_path(source_ref).exists()

    unsafe_fragments = sorted(
        fragment for fragment in LOCAL_PATH_AND_SECRET_FRAGMENTS if fragment in lower_text
    )
    upload_claims = _blocked_upload_claims_in(lower_text)
    assert not unsafe_fragments and not upload_claims, (
        "Cross-locale QA prep contains unsafe local/upload fragments: "
        f"{[*unsafe_fragments, *upload_claims]}"
    )


def test_es_wellness_blockers_do_not_reject_food_recipe_copy() -> None:
    """FitChef ES food-recipe copy must not be blocked as prescription language."""
    recipe_copies = (
        "Recetas para comidas y menus ayudan a planificar la semana.",
        "Recetas sencillas para organizar el menu.",
    )

    for recipe_copy in recipe_copies:
        offending_terms = _blocked_terms_in("es-ES", recipe_copy)
        assert not offending_terms, f"Food recipe copy should stay allowed: {offending_terms}"


@pytest.mark.parametrize(
    ("prescription_copy", "expected_term"),
    [
        ("La receta medica ayuda a ajustar el plan.", "receta medica"),
        ("La prescripción no pertenece al pack App Store.", "prescripcion"),
        ("El medicamento queda fuera de la planificacion diaria.", "medicamento"),
        ("El fármaco no debe entrar en el copy.", "farmaco"),
        ("La pastilla no pertenece a FitChef.", "pastilla"),
        ("La píldora no debe aparecer en el pack.", "pildora"),
    ],
)
def test_es_wellness_blockers_reject_prescription_medicine_copy(
    prescription_copy: str,
    expected_term: str,
) -> None:
    """ES pack guards must block prescription-medicine context without blocking food recipes."""
    offending_terms = _blocked_terms_in("es-ES", prescription_copy)

    assert expected_term in offending_terms


@pytest.mark.parametrize(
    ("blocked_copy", "expected_term"),
    [
        ("Ofrece diagnóstico de nutrición.", "diagnos"),
        ("Ayuda a tratar tus habitos.", "tratar"),
        ("Trata tus habitos con apoyo diario.", "trata"),
        ("Consejos de nutricionista para tu menú.", "nutricionista"),
        ("Resultados rápidos para tu cuerpo.", "resultados rapidos"),
        ("Clínicamente probado y recomendado por médicos.", "clinicamente probado"),
        ("Prueba gratis con descuento.", "prueba gratis"),
        ("Suscripcion con precio especial.", "suscripcion"),
    ],
)
def test_es_wellness_blockers_reject_storekit_treatment_and_professional_copy(
    blocked_copy: str,
    expected_term: str,
) -> None:
    """ES pack guards should catch pricing, treatment, and professional-role claims."""
    offending_terms = _blocked_terms_in("es-ES", blocked_copy)

    assert expected_term in offending_terms
