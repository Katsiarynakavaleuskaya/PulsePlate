"""Deterministic App Store repo-local release validator.

Checks repo-local evidence for iOS App Store release truth without
network calls, App Store Connect credentials, or protected secrets.

Exit 0 = all checks pass.
Exit 1 = at least one check failed.

Usage:
    python3 scripts/release/check_ios_appstore_verify.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import plistlib
import re
import struct
import sys
import unicodedata
import zlib
from typing import Any, List, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# --- Paths ---

INFO_RELEASE_PLIST = REPO_ROOT / "ios" / "PulsePlate" / "Info-Release.plist"
APPCONFIG_SWIFT = REPO_ROOT / "ios" / "PulsePlate" / "Services" / "AppConfig.swift"
APPICON_CONTENTS = (
    REPO_ROOT / "ios" / "PulsePlate" / "Assets.xcassets" / "AppIcon.appiconset" / "Contents.json"
)
EXPECTED_APPICON_MARKETING_ENTRY = {
    "filename": "AppIcon-1024.png",
    "idiom": "ios-marketing",
    "scale": "1x",
    "size": "1024x1024",
}
# CAB-03 admitted baseline; a future asset PR rotates this validator-owned pin with the PNG.
EXPECTED_APPICON_MARKETING_SHA256 = (
    "f238b1eae8dd17dd8a30e4eaf15a16a9827462eec129e98770feb878a0e83c4b"  # pragma: allowlist secret
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PRIVACY_MANIFEST = REPO_ROOT / "ios" / "PulsePlate" / "PrivacyInfo.xcprivacy"
APP_PRIVACY_JSON = REPO_ROOT / "ios" / "fastlane" / "app_privacy_details.json"
HEALTHKIT_MANAGER = REPO_ROOT / "ios" / "PulsePlate" / "Models" / "HealthKitManager.swift"
CONSENT_STORE = REPO_ROOT / "ios" / "PulsePlate" / "Services" / "AIWellnessConsentStore.swift"
DISCLOSURE_SHEET = REPO_ROOT / "ios" / "PulsePlate" / "Views" / "AIWellnessDisclosureSheet.swift"
REVIEWER_NOTES = REPO_ROOT / "ios" / "fastlane" / "metadata" / "review_information" / "notes.txt"
SCREENSHOT_GATE = REPO_ROOT / "docs" / "release" / "APPSTORE_SCREENSHOT_ASSET_GATE.md"
REVIEWER_SUBMISSION_MATRIX = (
    REPO_ROOT / "docs" / "release" / "APPSTORE_REVIEWER_SUBMISSION_MATRIX.md"
)
FITCHEF_PACK_BASE = REPO_ROOT / "appstore" / "fitchef"
FITCHEF_RELEASE_READINESS_DIR = FITCHEF_PACK_BASE / "release_readiness"
FITCHEF_SHOT_SCENARIO_MATRIX = FITCHEF_RELEASE_READINESS_DIR / "shot_scenario_matrix.json"
FITCHEF_RENDERED_REVIEW_CHECKLIST = (
    FITCHEF_RELEASE_READINESS_DIR / "rendered_review_testflight_readiness.md"
)
FASTLANE_SCREENSHOTS_DIR = REPO_ROOT / "ios" / "fastlane" / "screenshots"
APPSTORE_SCREENSHOT_CONTEXT = (
    REPO_ROOT / "ios" / "PulsePlate" / "AppStore" / "AppStoreScreenshotContext.swift"
)
APPSTORE_SCREENSHOT_TESTS = (
    REPO_ROOT / "ios" / "PulsePlateUITests" / "AppStoreScreenshotTests.swift"
)

LOCALES = ("en-US", "es-ES", "ru-RU")
METADATA_DIR = REPO_ROOT / "ios" / "fastlane" / "metadata"
LPROJ_DIR = REPO_ROOT / "ios" / "PulsePlate"

CANONICAL_BASE_URL = "https://pulseplate.app"
FORBIDDEN_HOSTS = ("api.pulseplate.com", "api.pulseplate.app")
EXPECTED_PRIVACY_CATEGORIES = {"HEALTH", "PURCHASE_HISTORY", "OTHER_USER_CONTENT"}
FITCHEF_LOCALES = ("en-US", "ru-RU", "es-ES")
FITCHEF_ALLOWED_PACK_SUFFIXES = {".json", ".md"}
FITCHEF_MEDIA_SUFFIXES = {".heic", ".jpeg", ".jpg", ".mov", ".mp4", ".pdf", ".png", ".webp"}
EXPECTED_FITCHEF_SCENARIOS = {
    "core_value": {
        "shot_id": "shot-01",
        "filename": "01_core-value.png",
        "screenshot_name": "01_core-value",
        "accessibility_identifier": "appstore.core_value.screen",
        "classification": "SUBMIT_READY",
        "scene_id": "scene-01",
    },
    "nutrition_analysis": {
        "shot_id": "shot-02",
        "filename": "02_nutrition-analysis.png",
        "screenshot_name": "02_nutrition-analysis",
        "accessibility_identifier": "appstore.nutrition_analysis.screen",
        "classification": "IMPLEMENTATION_REQUIRED",
        "scene_id": "scene-02",
    },
    "meal_planner": {
        "shot_id": "shot-03",
        "filename": "03_meal-planner.png",
        "screenshot_name": "03_meal-planner",
        "accessibility_identifier": "appstore.meal_planner.screen",
        "classification": "IMPLEMENTATION_REQUIRED",
        "scene_id": "scene-03",
    },
    "grocery_list": {
        "shot_id": "shot-04",
        "filename": "04_grocery-list.png",
        "screenshot_name": "04_grocery-list",
        "accessibility_identifier": "appstore.grocery_list.screen",
        "classification": "IMPLEMENTATION_REQUIRED",
        "scene_id": "scene-04",
    },
    "health_progress": {
        "shot_id": "shot-05",
        "filename": "05_health-progress.png",
        "screenshot_name": "05_health-progress",
        "accessibility_identifier": "appstore.health_progress.screen",
        "classification": "IMPLEMENTATION_REQUIRED",
        "scene_id": "scene-05",
    },
    "personalization": {
        "shot_id": "shot-06",
        "filename": "06_personalization.png",
        "screenshot_name": "06_personalization",
        "accessibility_identifier": "appstore.personalization.screen",
        "classification": "IMPLEMENTATION_REQUIRED",
        "scene_id": "scene-06",
    },
    "ai_assistant": {
        "shot_id": "shot-07",
        "filename": "07_ai-assistant.png",
        "screenshot_name": "07_ai-assistant",
        "accessibility_identifier": "appstore.ai_assistant.screen",
        "classification": "IMPLEMENTATION_REQUIRED",
        "scene_id": "scene-07",
    },
}
EXPECTED_FITCHEF_SHOTS = {
    meta["shot_id"]: {**meta, "scenario_id": scenario_id}
    for scenario_id, meta in EXPECTED_FITCHEF_SCENARIOS.items()
}
LOCAL_TMP_PATH_FRAGMENT = "/" + "tmp/"
FORBIDDEN_FITCHEF_RELEASE_FRAGMENTS = (
    "/users/",
    "/home/",
    LOCAL_TMP_PATH_FRAGMENT,
    "file://",
    "worktrees/",
    "artifacts/",
    ".venv/",
    "node_modules/",
    "gh_token",
    "github_token",
    "api_key",
    "password",
    "ready for upload",
    "upload proof",
    "release-ready",
    "release ready",
    "submission-ready",
    "submission ready",
    "submission complete",
    "submit complete",
    "ready to submit",
    "app store connect draft",
    "free trial",
    "subscription",
    "improve health",
    "google play",
    "play store",
    "android",
)
FITCHEF_RELEASE_LOCAL_PATH_PATTERNS = (
    re.compile(r"[a-z]:[\\/]+users[\\/]+", re.IGNORECASE),
    re.compile(r"[\\/]+appdata[\\/]+local[\\/]+temp[\\/]+", re.IGNORECASE),
    re.compile(r"/home/(?:runner/work|[^/\s]+)", re.IGNORECASE),
    re.compile(r"%temp%", re.IGNORECASE),
)
FITCHEF_RELEASE_CREDENTIAL_PATTERNS = (
    re.compile(r"secret\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"secret\s+key\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"api[\s_-]?key\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"(?:gh|github)[\s_-]?token\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b(?:ghp|ghs)_[A-Za-z0-9_.-]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-proj-[A-Za-z0-9_-]{20,}\b"),
)
FITCHEF_PROTECTED_ACTION_CLAIM_PATTERNS = (
    re.compile(
        r"\bsubmit\s+ready\s*(?::|=)?\s*(?:true|yes|completed|succeeded|done|passed|1)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpublic\s+submission\s+allowed\s*(?::|=)?\s*"
        r"(?:true|yes|completed|succeeded|done|passed|1)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"fastlane\s+upload\s*(?::|=)?\s*(?:true|yes|completed|succeeded|done|passed)",
        re.IGNORECASE,
    ),
    re.compile(
        r"app\s+store\s+connect\s+mutation\s*(?::|=)?\s*"
        r"(?:true|yes|completed|succeeded|done|passed)",
        re.IGNORECASE,
    ),
    re.compile(
        r"screenshot\s+binary\s+export\s*(?::|=)?\s*"
        r"(?:true|yes|completed|succeeded|done|passed)",
        re.IGNORECASE,
    ),
    re.compile(
        r"screenshot\s+binary\s+commit\s*(?::|=)?\s*"
        r"(?:true|yes|completed|succeeded|done|passed)",
        re.IGNORECASE,
    ),
    re.compile(
        r"preview\s+video\s+export\s*(?::|=)?\s*" r"(?:true|yes|completed|succeeded|done|passed)",
        re.IGNORECASE,
    ),
    re.compile(
        r"preview\s+video\s+binary\s+commit\s*(?::|=)?\s*"
        r"(?:true|yes|completed|succeeded|done|passed)",
        re.IGNORECASE,
    ),
    re.compile(
        r"environment\s+activation\s*(?::|=)?\s*" r"(?:true|yes|completed|succeeded|done|passed)",
        re.IGNORECASE,
    ),
)
FITCHEF_RELEASE_TOP_LEVEL_KEYS = {
    "schema_version",
    "classification",
    "validation_gate",
    "source_pr",
    "locales",
    "source_paths",
    "blocked_release_actions",
    "scenarios",
    "locale_review_matrix",
}
FITCHEF_RELEASE_SOURCE_PR_KEYS = {"number", "merge_commit"}
EXPECTED_FITCHEF_SOURCE_PR = {
    "number": 1886,
    "merge_commit": "26b7cf4f",
}
EXPECTED_FITCHEF_RELEASE_SCHEMA_VERSION = "fitchef-appstore-release-readiness.v1"
FITCHEF_RELEASE_SOURCE_PATH_KEYS = {
    "screenshot_gate",
    "reviewer_matrix",
    "ios_context",
    "ios_ui_tests",
}
EXPECTED_FITCHEF_SOURCE_PATHS = {
    "screenshot_gate": "docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md",
    "reviewer_matrix": "docs/release/APPSTORE_REVIEWER_SUBMISSION_MATRIX.md",
    "ios_context": "ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift",
    "ios_ui_tests": "ios/PulsePlateUITests/AppStoreScreenshotTests.swift",
}
EXPECTED_FITCHEF_BLOCKED_RELEASE_ACTIONS = (
    "fastlane_upload",
    "app_store_connect_mutation",
    "screenshot_binary_export",
    "screenshot_binary_commit",
    "preview_video_export",
    "preview_video_binary_commit",
    "environment_activation",
)
FITCHEF_FORBIDDEN_PACK_PATH_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "artifacts",
    "node_modules",
    "worktrees",
}
FITCHEF_RELEASE_SCENARIO_KEYS = {
    "shot_id",
    "scenario_id",
    "expected_filename",
    "ui_test_screenshot_name",
    "accessibility_identifier",
    "reviewer_matrix_classification",
    "screenshot_gate_classification",
    "public_submission_allowed",
    "rendered_review_required",
    "testflight_smoke_status",
    "privacy_ai_wellness_note",
    "reviewer_action",
}
FITCHEF_RELEASE_LOCALE_ROW_KEYS = {
    "locale",
    "shot_id",
    "manifest_path",
    "storyboard_path",
    "scene_id",
    "time_range",
    "line_fit_status",
    "safe_area_status",
    "fitchef_overlap_status",
    "wellness_claim_status",
    "reviewer_action",
}
FITCHEF_RELEASE_WELLNESS_STATUS_VALUES = {
    "ai_wellness_disclosure_required",
    "convenience_only",
    "educational_support_only",
    "habit_support_only",
    "habit_tracking_only",
    "support_framing_only",
    "user_control_only",
}
EXPECTED_FITCHEF_WELLNESS_STATUS_BY_SHOT = {
    "shot-01": "support_framing_only",
    "shot-02": "educational_support_only",
    "shot-03": "habit_support_only",
    "shot-04": "convenience_only",
    "shot-05": "habit_tracking_only",
    "shot-06": "user_control_only",
    "shot-07": "ai_wellness_disclosure_required",
}
FITCHEF_RELEASE_WELLNESS_CLAIM_PATTERNS = (
    re.compile(r"\bdiagnos(?:e|es|ed|ing|is|tic)\b", re.IGNORECASE),
    re.compile(r"\btreat(?:s|ed|ing|ments?)?\b", re.IGNORECASE),
    re.compile(r"\bcur(?:e|es|ed|ing)\b", re.IGNORECASE),
    re.compile(r"\btherap(?:y|eutic)\b", re.IGNORECASE),
    re.compile(
        r"\bmedical[-\s]+(?:advice|claim|care|grade|monitoring|professional|provider|treatment|therapy)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bhealthcare\s+(?:professional|provider)\b", re.IGNORECASE),
    re.compile(r"\b(?:dietitians?|nutritionists?)\b", re.IGNORECASE),
    re.compile(r"\b(?:doctors?|physicians?|clinicians?)\b", re.IGNORECASE),
    re.compile(r"\b(?:medication|prescription)s?\b", re.IGNORECASE),
    re.compile(r"\bclinical\s+nutrition\b", re.IGNORECASE),
    re.compile(r"\bcrisis\s+support\b", re.IGNORECASE),
    re.compile(r"\bemergency\s+care\b", re.IGNORECASE),
    re.compile(r"\b(?:cholesterol|hypertension|blood\s+pressure)\b", re.IGNORECASE),
    re.compile(r"\bdiabetes\b", re.IGNORECASE),
    re.compile(r"\bpatients?\b", re.IGNORECASE),
)
FITCHEF_RELEASE_OUTCOME_CLAIM_PATTERNS = (
    re.compile(
        r"\bguaranteed[-\s]+(?:health[-\s]+)?(?:weight[-\s]+loss|adherence|outcomes?|results?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bclinically[-\s]+proven\b", re.IGNORECASE),
    re.compile(r"\b(?:instant|rapid|immediate)[-\s]+(?:outcomes?|results?)\b", re.IGNORECASE),
    re.compile(r"\bresultados?\s+rapidos?\b", re.IGNORECASE),
    re.compile(r"\bmost[-\s]+accurate\b", re.IGNORECASE),
    re.compile(r"(?<!\w)#\s*1(?!\w)", re.IGNORECASE),
    re.compile(r"\bnumber[-\s]+one\b", re.IGNORECASE),
    re.compile(
        r"\b(?:best|top[-\s]+ranked|top[-\s]+rated)\s+(?:nutrition|wellness|diet)\b", re.IGNORECASE
    ),
)
FITCHEF_RELEASE_LOCALIZED_WELLNESS_FRAGMENTS = (
    "ansiedad",
    "colesterol",
    "controla tu colesterol",
    "depresion",
    "diagnostico",
    "diagnosticos",
    "hipertension",
    "soporte para hipertension",
    "tratar",
    "trata",
    "medico",
    "medicos",
    "medicacion",
    "medicamento",
    "medicamentos",
    "prescripcion medica",
    "prescripciones medicas",
    "tratamiento medico",
    "tratamientos medicos",
    "terapia",
    "terapeut",
    "nutricionista",
    "dietista",
    "experto en nutricion",
    "paciente",
    "pacientes",
    "nutricion clinica",
    "диагноз",
    "диагност",
    "лекарств",
    "лечение",
    "диетолог",
    "нутрициолог",
    "эксперт по питанию",
    "врач",
    "врачеб",
    "медикамент",
    "терап",
    "медицинск",
    "клиническая нутри",
    "клиническое питание",
    "пациент",
)
FITCHEF_RELEASE_NEVER_BOUNDARY_NEGATED_MEDICAL_TERMS = {
    "blood pressure",
    "cholesterol",
    "diabetes",
    "hypertension",
}
FITCHEF_RELEASE_NEVER_BOUNDARY_NEGATED_LOCALIZED_FRAGMENTS = {
    "ansiedad",
    "colesterol",
    "controla tu colesterol",
    "depresion",
    "hipertension",
    "soporte para hipertension",
}
FITCHEF_RELEASE_LOCALIZED_UPLOAD_FRAGMENTS = (
    "listo para subir",
    "lista para subir",
    "subida completada",
    "carga completada",
    "listo para lanzamiento",
    "listo para release",
    "listo para enviar",
    "lista para enviar",
    "publicado en app store",
    "publicada en app store",
    "готов к загрузке",
    "готова к загрузке",
    "готов к отправке",
    "готова к отправке",
    "готов к релизу",
    "готова к релизу",
    "загрузка завершена",
)
FITCHEF_RELEASE_LOCALIZED_WELLNESS_BOUNDARY_MARKERS = (
    "sin ",
    "no ",
    "no ofrece",
    "no proporciona",
    "без ",
    "не ",
    "не является",
    "не предоставляет",
    "исключает",
)
FITCHEF_RELEASE_LOCALIZED_WELLNESS_BOUNDARY_CONTEXT_WORDS = {
    "consejo",
    "diagnostico",
    "diagnosticos",
    "el",
    "la",
    "las",
    "los",
    "medico",
    "medicos",
    "ni",
    "nutricion",
    "o",
    "paciente",
    "pacientes",
    "para",
    "terapia",
    "tratamiento",
    "tratamientos",
    "y",
    "без",
    "врачебный",
    "врачебных",
    "диагноз",
    "диагностика",
    "для",
    "и",
    "или",
    "как",
    "клиническая",
    "клиническое",
    "лечение",
    "медицинский",
    "медицинских",
    "медицинскую",
    "не",
    "нутриция",
    "пациент",
    "пациентов",
    "питание",
    "поддержка",
    "совет",
    "терапия",
}
FITCHEF_RELEASE_LOCALIZED_WELLNESS_BOUNDARY_CONTEXT_STEMS = (
    "diagnostic",
    "medic",
    "nutricion",
    "pacient",
    "terap",
    "tratamient",
    "диагноз",
    "диагност",
    "клиническ",
    "лечени",
    "медицинск",
    "нутри",
    "пациент",
    "терап",
)
FITCHEF_RELEASE_WELLNESS_BOUNDARY_MARKERS = (
    "no ",
    "not ",
    "does not",
    "do not",
    "without ",
)
FITCHEF_RELEASE_WELLNESS_BOUNDARY_CONTEXT_WORDS = {
    "a",
    "advice",
    "an",
    "and",
    "any",
    "autonomy",
    "care",
    "claim",
    "claims",
    "clinical",
    "crisis",
    "diagnosis",
    "diagnose",
    "diagnostic",
    "diet",
    "efficiency",
    "guidance",
    "guaranteed",
    "hidden",
    "imply",
    "implies",
    "make",
    "medical",
    "nutrition",
    "offer",
    "or",
    "outcome",
    "patient",
    "patients",
    "pricing",
    "provide",
    "support",
    "tailoring",
    "the",
    "therapy",
    "treatment",
    "trial",
}
FITCHEF_METADATA_PROTECTED_STATUS_FRAGMENTS = (
    "app store submission complete",
    "ready to submit",
    "release ready",
    "release-ready",
    "submission complete",
    "submission ready",
    "submission-ready",
    "submit complete",
)

# Pricing patterns that should NOT appear in metadata (hardcoded prices/trials).
PRICING_PATTERNS = [
    re.compile(r"\$\d"),
    re.compile(r"€\s*\d", re.IGNORECASE),
    re.compile(r"₽\s*\d", re.IGNORECASE),
    re.compile(r"\d+(?:[.,]\d+)?\s*€"),
    re.compile(r"\d+(?:[.,]\d+)?\s*(?:₽|руб(?:\.|ля|лей)?)", re.IGNORECASE),
    re.compile(r"\d+\s*USD", re.IGNORECASE),
    re.compile(r"\d+\s*EUR", re.IGNORECASE),
    re.compile(r"\d+\s*RUB", re.IGNORECASE),
    re.compile(r"\bUSD\s*\d", re.IGNORECASE),
    re.compile(r"\bEUR\s*\d", re.IGNORECASE),
    re.compile(r"\bRUB\s*\d", re.IGNORECASE),
    re.compile(r"\bprice\s+(?:eur|rub|usd)\s+\d", re.IGNORECASE),
    re.compile(r"\bprice\s+\d+(?:[.,]\d+)?\b", re.IGNORECASE),
    re.compile(r"\bprice\s*[:=]\s*\d+(?:[.,]\d+)?\b", re.IGNORECASE),
    re.compile(r"\btrial\s+(?:days?|months?)\s+\d", re.IGNORECASE),
    re.compile(r"\btrial\s+\d+\b", re.IGNORECASE),
    re.compile(r"\btrial\s*[:=]\s*\d+\b", re.IGNORECASE),
    re.compile(r"\d+[\s-]*day\s+(?:free\s+)?trial", re.IGNORECASE),
    re.compile(r"\d+[\s-]*month\s+(?:free\s+)?trial", re.IGNORECASE),
    re.compile(r"\d+\s+(?:days?|months?)\s+free\b", re.IGNORECASE),
    re.compile(r"(?:free|бесплатн)\s+(?:for|на)\s+\d+", re.IGNORECASE),
    re.compile(r"(?:7|14|30)[\s-]*day\s+trial", re.IGNORECASE),
]
FITCHEF_RELEASE_LOCALIZED_PRICING_FRAGMENTS = (
    "prueba gratis",
    "periodo de prueba",
    "precio",
    "suscripcion",
    "descuento",
    "пробный период",
    "пробныи период",
    "подписк",
)

# --- Helpers ---

Results = List[Tuple[bool, str, str]]


def _scan_text_variants(value: str) -> list[str]:
    collapsed = re.sub(r"[_-]+", " ", value)
    if collapsed == value:
        return [value]
    return [value, collapsed]


def _read_png_dimensions(path: pathlib.Path) -> Tuple[int, int]:
    """Read width/height from PNG IHDR chunk (no external deps)."""
    with open(path, "rb") as fh:
        signature = fh.read(8)
        if signature != PNG_SIGNATURE:
            raise ValueError(f"Not a PNG file: {path}")

        length_bytes = fh.read(4)
        if len(length_bytes) != 4:
            raise ValueError(f"Incomplete IHDR length: {path}")
        chunk_length = struct.unpack(">I", length_bytes)[0]
        if chunk_length != 13:
            raise ValueError(f"Invalid IHDR length {chunk_length}: {path}")

        chunk_type = fh.read(4)
        if chunk_type != b"IHDR":
            raise ValueError(f"Missing IHDR chunk: {path}")

        ihdr_data = fh.read(chunk_length)
        if len(ihdr_data) != chunk_length:
            raise ValueError(f"Incomplete IHDR data: {path}")
        crc_bytes = fh.read(4)
        if len(crc_bytes) != 4:
            raise ValueError(f"Incomplete IHDR CRC: {path}")
        expected_crc = zlib.crc32(chunk_type)
        expected_crc = zlib.crc32(ihdr_data, expected_crc) & 0xFFFFFFFF
        actual_crc = struct.unpack(">I", crc_bytes)[0]
        if actual_crc != expected_crc:
            raise ValueError(f"Invalid IHDR CRC: {path}")

        width, height = struct.unpack(">II", ihdr_data[:8])
    return width, height


def _load_json_file(path: pathlib.Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def _flatten_strings(value: Any) -> list[str]:
    return _flatten_strings_with_path(value, ())


def _flatten_strings_with_path(value: Any, key_path: tuple[str, ...]) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.extend(_scan_text_variants(value))
    elif isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            nested_path = (*key_path, key_text)
            path_labels = {
                key_text,
                " ".join(nested_path),
                ".".join(nested_path),
                "_".join(nested_path),
            }
            strings.extend(
                variant for label in sorted(path_labels) for variant in _scan_text_variants(label)
            )
            if isinstance(item, (str, int, float, bool)) or item is None:
                parent_labels = set(path_labels)
                if key_path:
                    parent_labels.update(
                        {
                            " ".join(key_path),
                            ".".join(key_path),
                            "_".join(key_path),
                        }
                    )
                for label in sorted(parent_labels):
                    strings.extend(_scan_text_variants(f"{label} {item}"))
                    strings.extend(_scan_text_variants(f"{label}: {item}"))
                    strings.extend(_scan_text_variants(f"{label}={item}"))
            strings.extend(_flatten_strings_with_path(item, nested_path))
    elif isinstance(value, list):
        for item in value:
            strings.extend(_flatten_strings_with_path(item, key_path))
    elif isinstance(value, (int, float, bool)) or value is None:
        strings.append(str(value))
    return strings


def _claim_scan_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _is_safe_repo_relative_path(value: str) -> bool:
    path = pathlib.PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _repo_relative_path(path: pathlib.Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _display_repo_local_path(path: pathlib.Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _expected_fitchef_manifest_path(locale: str) -> str:
    return f"appstore/fitchef/{locale}/iphone-6.9/screenshots/shot_manifest.json"


def _expected_fitchef_storyboard_path(locale: str) -> str:
    return f"appstore/fitchef/{locale}/iphone-6.9/preview/storyboard.json"


def _expected_fitchef_line_fit_status(locale: str, shot_id: str) -> str:
    if shot_id == "shot-05" and locale in {"ru-RU", "es-ES"}:
        return "render-risk"
    if shot_id == "shot-06" and locale == "en-US":
        return "pass-length"
    if shot_id == "shot-07" and locale == "ru-RU":
        return "pass-length"
    return "review"


def _read_text_file(path: pathlib.Path) -> tuple[str, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return "", str(exc)


def _fitchef_pack_file_scan_text(path: pathlib.Path) -> tuple[str, str | None]:
    try:
        scan_path = path.relative_to(FITCHEF_PACK_BASE).as_posix()
    except ValueError:
        scan_path = path.name
    if path.suffix.lower() == ".json":
        payload, error = _load_json_file(path)
        if error:
            return "", f"Invalid JSON file under FitChef App Store pack: {path}: {error}"
        return "\n".join([scan_path, *_flatten_strings(payload)]), None
    text, error = _read_text_file(path)
    if error:
        return "", error
    return "\n".join([scan_path, text]), None


def _validate_fitchef_pack_file_boundaries() -> str | None:
    if not FITCHEF_PACK_BASE.exists():
        return f"FitChef App Store pack directory missing: {FITCHEF_PACK_BASE}"
    for path in FITCHEF_PACK_BASE.rglob("*"):
        relative_parts = {part.lower() for part in path.relative_to(FITCHEF_PACK_BASE).parts}
        forbidden_parts = sorted(relative_parts & FITCHEF_FORBIDDEN_PACK_PATH_PARTS)
        if forbidden_parts:
            return f"Forbidden FitChef App Store pack path segment found: {forbidden_parts[0]}"
        if path.is_symlink():
            return f"Symlink is not allowed in FitChef App Store pack: {path}"
        if not path.is_file():
            continue
        if path.suffix.lower() in FITCHEF_MEDIA_SUFFIXES:
            return f"Media file is not allowed in FitChef App Store pack: {path}"
        if path.suffix.lower() not in FITCHEF_ALLOWED_PACK_SUFFIXES:
            return f"Only JSON/Markdown files are allowed in FitChef App Store pack: {path}"
    return None


def _validate_fitchef_protected_media_boundaries() -> str | None:
    protected_dirs = (("Fastlane screenshots", FASTLANE_SCREENSHOTS_DIR),)
    for label, directory in protected_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() in FITCHEF_MEDIA_SUFFIXES:
                return f"Media file is not allowed in {label}: {_display_repo_local_path(path)}"
    return None


def _release_readiness_scan_text() -> tuple[str, str | None]:
    scan_parts: list[str] = []
    for path in sorted(FITCHEF_PACK_BASE.rglob("*")):
        if not path.is_file():
            continue
        text, error = _fitchef_pack_file_scan_text(path)
        if error:
            return "", error
        scan_parts.append(text)
    return "\n".join(scan_parts), None


def _validate_release_readiness_scan_text(text: str) -> str | None:
    text_variants = _scan_text_variants(text)
    lowered_variants = [variant.lower() for variant in text_variants]
    normalized_variants = [_claim_scan_text(variant) for variant in text_variants]
    for fragment in FORBIDDEN_FITCHEF_RELEASE_FRAGMENTS:
        if any(fragment in lowered for lowered in lowered_variants):
            return f"Forbidden release-readiness fragment found: {fragment}"
    for pattern in FITCHEF_RELEASE_LOCAL_PATH_PATTERNS:
        match = pattern.search(text)
        if match:
            return "Forbidden release-readiness local path found: <redacted>"
    for pattern in PRICING_PATTERNS:
        for variant in text_variants:
            match = pattern.search(variant)
            if match:
                return f"Pricing/trial claim found: {match.group()}"
    for fragment in FITCHEF_RELEASE_LOCALIZED_PRICING_FRAGMENTS:
        if any(fragment in normalized for normalized in normalized_variants):
            return f"Localized pricing/trial claim found: {fragment}"
    for pattern in FITCHEF_RELEASE_CREDENTIAL_PATTERNS:
        for variant in text_variants:
            match = pattern.search(variant)
            if match:
                return "Credential-like release bundle value found: <redacted>"
    for pattern in FITCHEF_PROTECTED_ACTION_CLAIM_PATTERNS:
        for variant in text_variants:
            match = pattern.search(variant)
            if match:
                return f"Protected release action claim found: {match.group()}"
    for fragment in FITCHEF_RELEASE_LOCALIZED_UPLOAD_FRAGMENTS:
        if any(fragment in normalized for normalized in normalized_variants):
            return f"Localized protected release action claim found: {fragment}"
    for variant in text_variants:
        for line in variant.splitlines():
            for pattern in FITCHEF_RELEASE_WELLNESS_CLAIM_PATTERNS:
                for match in pattern.finditer(line):
                    if _medical_term_is_boundary_negated(line, match.start(), match.group()):
                        continue
                    return f"Medical/wellness overclaim found: {match.group()}"
            for pattern in FITCHEF_RELEASE_OUTCOME_CLAIM_PATTERNS:
                for match in pattern.finditer(line):
                    if _outcome_claim_is_directly_boundary_negated(line, match.start()):
                        continue
                    return f"Guaranteed/clinical outcome claim found: {match.group()}"
    for normalized in normalized_variants:
        for line in normalized.splitlines():
            for fragment in FITCHEF_RELEASE_LOCALIZED_WELLNESS_FRAGMENTS:
                for match in re.finditer(re.escape(fragment), line):
                    if _localized_wellness_fragment_is_boundary_negated(
                        line, match.start(), fragment
                    ):
                        continue
                    return f"Localized medical/wellness overclaim found: {fragment}"
    return None


def _medical_term_is_boundary_negated(line: str, match_start: int, match_text: str) -> bool:
    """Return whether a medical term is only named as a nearby forbidden boundary."""

    if _claim_scan_text(match_text) in FITCHEF_RELEASE_NEVER_BOUNDARY_NEGATED_MEDICAL_TERMS:
        return False

    prefix = line[:match_start].lower()
    same_clause_prefix = re.split(r"[.:;!?]", prefix)[-1]
    marker_matches: list[re.Match[str]] = []
    for marker in FITCHEF_RELEASE_WELLNESS_BOUNDARY_MARKERS:
        marker_text = marker.strip()
        marker_matches.extend(
            re.finditer(rf"(?<![a-z]){re.escape(marker_text)}(?![a-z])", same_clause_prefix)
        )
    if not marker_matches:
        return False

    marker_match = max(marker_matches, key=lambda match: (match.start(), match.end()))
    text_between_marker_and_term = same_clause_prefix[marker_match.end() :]
    if not text_between_marker_and_term.strip():
        return True

    if re.search(
        rf"(?<![a-z]){re.escape(match_text.lower())}(?![a-z])", text_between_marker_and_term
    ):
        return False

    context_words = re.findall(r"[a-z]+", text_between_marker_and_term)
    return bool(context_words) and all(
        word in FITCHEF_RELEASE_WELLNESS_BOUNDARY_CONTEXT_WORDS for word in context_words
    )


def _outcome_claim_is_directly_boundary_negated(line: str, match_start: int) -> bool:
    """Allow explicit outcome-claim boundary lists without hiding later claims."""

    prefix = line[:match_start].lower()
    if re.search(r"(?:^|\b)(?:no|not|without)\s+$", prefix):
        return True
    same_clause_prefix = re.split(r"[.:;!?]", prefix)[-1]
    marker_matches: list[re.Match[str]] = []
    for marker in FITCHEF_RELEASE_WELLNESS_BOUNDARY_MARKERS:
        marker_text = marker.strip()
        marker_matches.extend(
            re.finditer(rf"(?<![a-z]){re.escape(marker_text)}(?![a-z])", same_clause_prefix)
        )
    if not marker_matches:
        return False
    marker_match = max(marker_matches, key=lambda match: (match.start(), match.end()))
    text_between_marker_and_claim = same_clause_prefix[marker_match.end() :]
    context_words = re.findall(r"[a-z]+", text_between_marker_and_claim)
    return (
        bool(context_words)
        and "and" not in context_words
        and all(word in FITCHEF_RELEASE_WELLNESS_BOUNDARY_CONTEXT_WORDS for word in context_words)
    )


def _localized_wellness_fragment_is_boundary_negated(
    normalized_line: str, match_start: int, fragment: str
) -> bool:
    """Return whether a localized medical fragment is listed as a forbidden boundary."""

    if fragment in FITCHEF_RELEASE_NEVER_BOUNDARY_NEGATED_LOCALIZED_FRAGMENTS:
        return False

    prefix = normalized_line[:match_start]
    same_clause_prefix = re.split(r"[.:;!?]", prefix)[-1]
    marker_matches: list[re.Match[str]] = []
    for marker in FITCHEF_RELEASE_LOCALIZED_WELLNESS_BOUNDARY_MARKERS:
        marker_text = marker.strip()
        marker_pattern = re.escape(marker_text).replace(r"\ ", r"\s+")
        marker_matches.extend(
            re.finditer(
                rf"(?<![a-zа-яё]){marker_pattern}(?![a-zа-яё])",
                same_clause_prefix,
            )
        )
    if not marker_matches:
        return False

    marker_match = max(marker_matches, key=lambda match: (match.start(), match.end()))
    text_between_marker_and_term = same_clause_prefix[marker_match.end() :]
    if not text_between_marker_and_term.strip():
        return True

    if re.search(re.escape(fragment), text_between_marker_and_term):
        return False

    context_words = re.findall(r"[a-zа-яё]+", text_between_marker_and_term)
    return bool(context_words) and all(
        word in FITCHEF_RELEASE_LOCALIZED_WELLNESS_BOUNDARY_CONTEXT_WORDS
        or any(
            word.startswith(stem)
            for stem in FITCHEF_RELEASE_LOCALIZED_WELLNESS_BOUNDARY_CONTEXT_STEMS
        )
        for word in context_words
    )


def _swift_enum_case_name(scenario_id: str) -> str:
    head, *tail = scenario_id.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _swift_scenario_case_declarations(source: str) -> dict[str, str]:
    return {
        match.group(2): match.group(1)
        for match in re.finditer(
            r"\bcase\s+([A-Za-z][A-Za-z0-9]*)\s*=\s*\"([a-z][a-z0-9_]*)\"",
            source,
        )
    }


def _swift_xctest_screenshot_methods(source: str) -> set[str]:
    return set(re.findall(r"\bfunc\s+(test[A-Za-z0-9_]*Screenshot)\s*\(", source))


def _swift_balanced_block_after(source: str, needle: str) -> str | None:
    start = source.find(needle)
    if start < 0:
        return None
    open_index = source.find("{", start)
    if open_index < 0:
        return None
    depth = 0
    for index in range(open_index, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_index + 1 : index]
    return None


def _swift_case_return_literal(source: str, property_name: str, enum_case: str) -> str | None:
    block = _swift_balanced_block_after(source, f"var {property_name}: String")
    if block is None:
        return None
    match = re.search(
        rf"case\s+\.{re.escape(enum_case)}\s*:\s*return\s+\"([^\"]+)\"",
        block,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _strip_swift_comments(source: str) -> str:
    """Remove Swift comments while preserving string literals for source contract checks."""

    output: list[str] = []
    index = 0
    in_string = False
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if in_string:
            output.append(char)
            if char == "\\" and next_char:
                output.append(next_char)
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            while index < len(source) and source[index] != "\n":
                index += 1
            if index < len(source):
                output.append("\n")
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(source) and not (
                source[index] == "*" and source[index + 1] == "/"
            ):
                if source[index] == "\n":
                    output.append("\n")
                index += 1
            index += 2 if index + 1 < len(source) else 0
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _swift_switch_case_block(block: str, enum_case: str) -> str | None:
    match = re.search(
        rf"case\s+\.{re.escape(enum_case)}\s*:",
        block,
        re.MULTILINE,
    )
    if not match:
        return None
    next_match = re.search(r"\n\s*case\s+\.", block[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(block)
    return block[match.end() : end]


def _swift_test_method_name(enum_case: str) -> str:
    return "test" + enum_case[0].upper() + enum_case[1:] + "Screenshot"


def _validate_non_empty_string(value: Any, *, label: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return f"{label} must be non-empty text"
    return None


def _validate_source_paths(source_paths: dict[str, Any]) -> str | None:
    if source_paths != EXPECTED_FITCHEF_SOURCE_PATHS:
        return (
            "Scenario matrix source_paths value drift: "
            f"{source_paths!r} != {EXPECTED_FITCHEF_SOURCE_PATHS!r}"
        )
    for label, raw_path in source_paths.items():
        if not isinstance(raw_path, str) or not _is_safe_repo_relative_path(raw_path):
            return f"Unsafe source_paths.{label}: {raw_path!r}"
        if not (REPO_ROOT / raw_path).exists():
            return f"Referenced source_paths.{label} does not exist: {raw_path}"
    return None


def _validate_source_pr(source_pr: dict[str, Any]) -> str | None:
    if source_pr != EXPECTED_FITCHEF_SOURCE_PR:
        return (
            "Scenario matrix source_pr provenance drift: "
            f"{source_pr!r} != {EXPECTED_FITCHEF_SOURCE_PR!r}"
        )
    return None


def _validate_ios_screenshot_sources() -> str | None:
    context_text, context_error = _read_text_file(APPSTORE_SCREENSHOT_CONTEXT)
    if context_error:
        return f"Cannot read iOS screenshot context: {context_error}"
    test_text, test_error = _read_text_file(APPSTORE_SCREENSHOT_TESTS)
    if test_error:
        return f"Cannot read iOS screenshot tests: {test_error}"
    context_text = _strip_swift_comments(context_text)
    test_text = _strip_swift_comments(test_text)
    capture_helper_body = _swift_balanced_block_after(
        test_text,
        "private func captureScreenshot(for scenario: Scenario)",
    )
    if capture_helper_body is None:
        return "iOS screenshot capture helper missing"
    required_capture_bindings = {
        "scenario launch argument": '"-appstore-screenshot-scenario", scenario.rawValue',
        "scenario accessibility id": "matching(identifier: scenario.accessibilityIdentifier)",
    }
    for label, expected_fragment in required_capture_bindings.items():
        if expected_fragment not in capture_helper_body:
            return f"iOS screenshot capture helper drift: missing {label}"
    if not re.search(r"\bsnapshot\(\s*scenario\.screenshotName\s*,", capture_helper_body):
        return "iOS screenshot capture helper drift: missing exact scenario snapshot name"

    expected_cases = {
        scenario_id: _swift_enum_case_name(scenario_id)
        for scenario_id in EXPECTED_FITCHEF_SCENARIOS
    }
    context_cases = _swift_scenario_case_declarations(context_text)
    if context_cases != expected_cases:
        return (
            "iOS screenshot context scenario set drift: " f"{context_cases!r} != {expected_cases!r}"
        )
    test_cases = _swift_scenario_case_declarations(test_text)
    if test_cases != expected_cases:
        return f"iOS screenshot test scenario set drift: {test_cases!r} != {expected_cases!r}"
    expected_test_methods = {
        _swift_test_method_name(enum_case) for enum_case in expected_cases.values()
    }
    actual_test_methods = _swift_xctest_screenshot_methods(test_text)
    if actual_test_methods != expected_test_methods:
        return (
            "iOS screenshot XCTest method set drift: "
            f"{sorted(actual_test_methods)!r} != {sorted(expected_test_methods)!r}"
        )

    scenario_view_block = _swift_balanced_block_after(context_text, "static func scenarioView()")
    if scenario_view_block is None:
        return "iOS screenshot context rendered scenarioView missing"
    for scenario_id, expected in EXPECTED_FITCHEF_SCENARIOS.items():
        enum_case = _swift_enum_case_name(scenario_id)
        case_declaration = f'case {enum_case} = "{scenario_id}"'
        if case_declaration not in context_text:
            return f"iOS screenshot context scenario id drift for {scenario_id}"
        if case_declaration not in test_text:
            return f"iOS screenshot test scenario id drift for {scenario_id}"

        context_accessibility_id = _swift_case_return_literal(
            context_text,
            "accessibilityIdentifier",
            enum_case,
        )
        if context_accessibility_id != expected["accessibility_identifier"]:
            return (
                f"iOS screenshot context accessibility id drift for {scenario_id}: "
                f"{context_accessibility_id!r} != {expected['accessibility_identifier']!r}"
            )

        test_accessibility_id = _swift_case_return_literal(
            test_text,
            "accessibilityIdentifier",
            enum_case,
        )
        if test_accessibility_id != expected["accessibility_identifier"]:
            return (
                f"iOS screenshot test accessibility id drift for {scenario_id}: "
                f"{test_accessibility_id!r} != {expected['accessibility_identifier']!r}"
            )

        test_screenshot_name = _swift_case_return_literal(test_text, "screenshotName", enum_case)
        if test_screenshot_name != expected["screenshot_name"]:
            return (
                f"iOS screenshot test screenshot name drift for {scenario_id}: "
                f"{test_screenshot_name!r} != {expected['screenshot_name']!r}"
            )

        rendered_case_block = _swift_switch_case_block(scenario_view_block, enum_case)
        if rendered_case_block is None:
            return f"iOS screenshot rendered scenarioView case missing for {scenario_id}"
        if ".appStoreScreenshotRoot(scenario.accessibilityIdentifier)" not in rendered_case_block:
            return (
                f"iOS screenshot rendered scenarioView case drift for {scenario_id}: "
                "missing screenshot root accessibility binding"
            )

        test_method_name = _swift_test_method_name(enum_case)
        method_body = _swift_balanced_block_after(test_text, f"func {test_method_name}()")
        if method_body is None:
            return f"iOS screenshot XCTest method missing for {scenario_id}: {test_method_name}"
        expected_capture_call = f"captureScreenshot(for: .{enum_case})"
        if expected_capture_call not in method_body:
            return (
                f"iOS screenshot XCTest method drift for {scenario_id}: "
                f"missing {expected_capture_call!r}"
            )
    return None


def _collect_markdown_scenario_classifications(
    path: pathlib.Path,
) -> tuple[dict[str, set[str]], str | None]:
    if not path.exists():
        return {}, f"File missing: {path}"

    content = path.read_text(encoding="utf-8")
    scenario_classifications: dict[str, set[str]] = {}
    row_re = re.compile(r"^\|(.+)\|$", re.MULTILINE)
    for row_match in row_re.finditer(content):
        cells = [c.strip().strip("`") for c in row_match.group(1).split("|")]
        scenario = None
        for cell in cells:
            if re.fullmatch(r"[a-z][a-z0-9_]*", cell):
                scenario = cell
                break
        if not scenario:
            continue
        for cell in cells:
            upper = cell.upper()
            if upper in ("SUBMIT_READY", "IMPLEMENTATION_REQUIRED", "INTERNAL_REVIEW_ONLY"):
                scenario_classifications.setdefault(scenario, set()).add(upper)
    return scenario_classifications, None


def _expected_scenario_classifications() -> dict[str, str]:
    return {
        scenario: meta["classification"] for scenario, meta in EXPECTED_FITCHEF_SCENARIOS.items()
    }


def _validate_expected_classifications(
    observed: dict[str, set[str]],
    *,
    source_label: str,
) -> str | None:
    expected = _expected_scenario_classifications()
    missing = set(expected) - set(observed)
    unknown = set(observed) - set(expected)
    wrong = {
        scenario: sorted(classes)
        for scenario, classes in observed.items()
        if scenario in expected and classes != {expected[scenario]}
    }

    if missing:
        return f"{source_label} missing scenarios: {sorted(missing)}"
    if unknown:
        return f"{source_label} has unknown scenarios: {sorted(unknown)}"
    if wrong:
        return f"{source_label} classification drift: {wrong}"
    return None


def _exact_keys_error(
    value: dict[str, Any],
    expected: set[str],
    *,
    label: str,
) -> str | None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        return f"{label} schema key drift; missing={missing}, extra={extra}"
    return None


# --- Check functions ---


def check_release_base_url() -> Results:
    """Verify Info-Release.plist contains canonical HTTPS BASE_URL."""
    results: Results = []
    tag = "release_base_url"

    if not INFO_RELEASE_PLIST.exists():
        results.append((False, tag, f"File missing: {INFO_RELEASE_PLIST}"))
        return results

    try:
        with open(INFO_RELEASE_PLIST, "rb") as fh:
            plist = plistlib.load(fh)
    except Exception as exc:
        results.append((False, tag, f"Cannot parse Info-Release.plist: {exc}"))
        return results

    base_url = plist.get("BASE_URL", "")
    if not base_url:
        results.append((False, tag, "BASE_URL key missing or empty in Info-Release.plist"))
        return results

    if not base_url.startswith("https://"):
        results.append((False, tag, f"BASE_URL is not HTTPS: {base_url}"))
        return results

    if base_url.rstrip("/") != CANONICAL_BASE_URL:
        results.append(
            (False, tag, f"BASE_URL is not canonical: {base_url} (expected {CANONICAL_BASE_URL})")
        )
        return results

    for host in FORBIDDEN_HOSTS:
        if host in base_url:
            results.append((False, tag, f"BASE_URL contains forbidden host {host}: {base_url}"))
            return results

    # Check AppConfig.swift for silent production fallback.
    if APPCONFIG_SWIFT.exists():
        content = APPCONFIG_SWIFT.read_text(encoding="utf-8")
        for host in FORBIDDEN_HOSTS:
            if host in content:
                results.append(
                    (False, tag, f"AppConfig.swift contains forbidden fallback host: {host}")
                )
                return results

    results.append((True, tag, f"BASE_URL = {base_url}"))
    return results


def check_appicon_marketing() -> Results:
    """Verify the exact AppIcon marketing slot and approved PNG bytes."""
    results: Results = []
    tag = "appicon_marketing"

    if APPICON_CONTENTS.is_symlink():
        results.append((False, tag, f"Symlink is not allowed: {APPICON_CONTENTS}"))
        return results
    if not APPICON_CONTENTS.is_file():
        results.append((False, tag, f"File missing: {APPICON_CONTENTS}"))
        return results

    try:
        data = json.loads(APPICON_CONTENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        results.append((False, tag, f"Invalid AppIcon Contents.json: {exc}"))
        return results

    if not isinstance(data, dict):
        results.append((False, tag, "AppIcon Contents.json root must be an object"))
        return results

    images = data.get("images")
    if not isinstance(images, list):
        results.append((False, tag, "AppIcon images must be a list"))
        return results
    if any(not isinstance(img, dict) for img in images):
        results.append((False, tag, "Every AppIcon images entry must be an object"))
        return results

    marketing = [img for img in images if img.get("idiom") == "ios-marketing"]

    if len(marketing) != 1:
        results.append(
            (False, tag, f"Expected exactly 1 ios-marketing entry, found {len(marketing)}")
        )
        return results

    entry = marketing[0]
    expected_keys = set(EXPECTED_APPICON_MARKETING_ENTRY)
    actual_keys = set(entry)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        results.append((False, tag, f"ios-marketing key drift; missing={missing}, extra={extra}"))
        return results

    for field, expected_value in EXPECTED_APPICON_MARKETING_ENTRY.items():
        actual_value = entry.get(field)
        if actual_value != expected_value:
            results.append(
                (
                    False,
                    tag,
                    f"ios-marketing {field} is {actual_value!r}, expected {expected_value!r}",
                )
            )
            return results

    filename = EXPECTED_APPICON_MARKETING_ENTRY["filename"]
    png_path = APPICON_CONTENTS.parent / filename
    if png_path.is_symlink():
        results.append((False, tag, f"Symlink is not allowed: {png_path}"))
        return results
    if not png_path.is_file():
        results.append((False, tag, f"ios-marketing PNG missing: {png_path}"))
        return results
    try:
        if png_path.stat().st_size == 0:
            results.append((False, tag, f"ios-marketing PNG is empty: {png_path}"))
            return results
    except OSError as exc:
        results.append((False, tag, f"Cannot inspect ios-marketing PNG: {exc}"))
        return results

    try:
        w, h = _read_png_dimensions(png_path)
    except (OSError, ValueError, struct.error) as exc:
        results.append((False, tag, f"Cannot read PNG dimensions: {exc}"))
        return results

    if (w, h) != (1024, 1024):
        results.append((False, tag, f"PNG dimensions {w}x{h}, expected 1024x1024"))
        return results

    try:
        digest = hashlib.sha256(png_path.read_bytes()).hexdigest()
    except OSError as exc:
        results.append((False, tag, f"Cannot read ios-marketing PNG bytes: {exc}"))
        return results
    if digest != EXPECTED_APPICON_MARKETING_SHA256:
        results.append(
            (
                False,
                tag,
                "ios-marketing PNG SHA-256 differs from the approved AppIcon baseline",
            )
        )
        return results

    results.append(
        (True, tag, f"AppIcon exact ios-marketing slot and approved PNG OK ({filename})")
    )
    return results


def check_privacy_manifest() -> Results:
    """Verify PrivacyInfo.xcprivacy exists and has valid structure."""
    results: Results = []
    tag = "privacy_manifest"

    if not PRIVACY_MANIFEST.exists():
        results.append((False, tag, f"File missing: {PRIVACY_MANIFEST}"))
        return results

    with open(PRIVACY_MANIFEST, "rb") as fh:
        try:
            plist = plistlib.load(fh)
        except Exception as exc:
            results.append((False, tag, f"Cannot parse PrivacyInfo.xcprivacy: {exc}"))
            return results

    tracking = plist.get("NSPrivacyTracking")
    if tracking is not False:
        results.append((False, tag, f"NSPrivacyTracking is {tracking!r}, expected False"))
        return results

    api_types = plist.get("NSPrivacyAccessedAPITypes")
    if not api_types:
        results.append((False, tag, "NSPrivacyAccessedAPITypes missing or empty"))
        return results

    results.append((True, tag, "PrivacyInfo.xcprivacy valid (tracking=False, API types declared)"))
    return results


def check_app_privacy_details() -> Results:
    """Verify app_privacy_details.json is valid and covers expected categories."""
    results: Results = []
    tag = "app_privacy_details"

    if not APP_PRIVACY_JSON.exists():
        results.append((False, tag, f"File missing: {APP_PRIVACY_JSON}"))
        return results

    try:
        data = json.loads(APP_PRIVACY_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        results.append((False, tag, f"Invalid JSON: {exc}"))
        return results

    if not isinstance(data, list) or len(data) == 0:
        results.append((False, tag, "app_privacy_details.json is empty or not an array"))
        return results

    categories = {entry.get("category") for entry in data if isinstance(entry, dict)}

    # Must not claim DATA_NOT_COLLECTED.
    for entry in data:
        if isinstance(entry, dict):
            protections = entry.get("data_protections", [])
            if "DATA_NOT_COLLECTED" in protections:
                results.append(
                    (
                        False,
                        tag,
                        f"DATA_NOT_COLLECTED found for category {entry.get('category')}",
                    )
                )
                return results

    missing = EXPECTED_PRIVACY_CATEGORIES - categories
    if missing:
        results.append((False, tag, f"Missing expected privacy categories: {sorted(missing)}"))
        return results

    results.append((True, tag, f"App Privacy details valid ({len(data)} categories declared)"))
    return results


def check_permission_strings() -> Results:
    """Verify only allowed sensitive permission strings are present."""
    results: Results = []
    tag = "permission_strings"

    forbidden_key = "NSHealthUpdateUsageDescription"
    allowed_key = "NSHealthShareUsageDescription"

    for locale in ("en", "ru", "es"):
        strings_file = LPROJ_DIR / f"{locale}.lproj" / "InfoPlist.strings"
        if not strings_file.exists():
            continue
        content = strings_file.read_text(encoding="utf-8", errors="replace")
        if forbidden_key in content:
            results.append(
                (
                    False,
                    tag,
                    f"Forbidden {forbidden_key} found in {locale}.lproj/InfoPlist.strings",
                )
            )
            return results

    # Verify allowed key exists in at least en locale.
    en_strings = LPROJ_DIR / "en.lproj" / "InfoPlist.strings"
    if not en_strings.exists():
        results.append(
            (False, tag, "en.lproj/InfoPlist.strings missing (required for permission review)")
        )
        return results

    content = en_strings.read_text(encoding="utf-8", errors="replace")
    if allowed_key not in content:
        results.append(
            (
                False,
                tag,
                f"{allowed_key} missing from en.lproj/InfoPlist.strings",
            )
        )
        return results

    results.append((True, tag, "Permission strings OK (read-only HealthKit, no write)"))
    return results


def check_healthkit_readonly() -> Results:
    """Verify HealthKit is read-only (no write operations)."""
    results: Results = []
    tag = "healthkit_readonly"

    if not HEALTHKIT_MANAGER.exists():
        results.append((False, tag, f"File missing: {HEALTHKIT_MANAGER}"))
        return results

    content = HEALTHKIT_MANAGER.read_text(encoding="utf-8")

    if "toShare: nil" not in content and "toShare:nil" not in content:
        results.append((False, tag, "HealthKitManager does not declare toShare: nil"))
        return results

    write_patterns = [".save(", "deleteObjects", "deleteObject", ".delete("]
    for pat in write_patterns:
        if pat in content:
            results.append((False, tag, f"HealthKit write operation found: {pat}"))
            return results

    results.append((True, tag, "HealthKit is read-only (toShare: nil, no write ops)"))
    return results


def check_ai_wellness_consent() -> Results:
    """Verify AI wellness consent gate exists and reviewer notes mention it."""
    results: Results = []
    tag = "ai_wellness_consent"

    if not CONSENT_STORE.exists():
        results.append((False, tag, f"File missing: {CONSENT_STORE}"))
        return results

    if not DISCLOSURE_SHEET.exists():
        results.append((False, tag, f"File missing: {DISCLOSURE_SHEET}"))
        return results

    # Reviewer notes should mention AI consent.
    if REVIEWER_NOTES.exists():
        notes = REVIEWER_NOTES.read_text(encoding="utf-8").lower()
        # Check for mentions of the AI consent or wellness disclosure topic.
        consent_keywords = ["ai", "consent", "wellness", "diagnos", "treat", "medical"]
        found = sum(1 for kw in consent_keywords if kw in notes)
        if found < 2:
            results.append(
                (
                    False,
                    tag,
                    "Reviewer notes do not sufficiently mention AI consent / wellness posture",
                )
            )
            return results

    results.append(
        (True, tag, "AI consent store + disclosure sheet exist, reviewer notes cover topic")
    )
    return results


def check_reviewer_pack() -> Results:
    """Verify reviewer notes exist and contain required posture markers."""
    results: Results = []
    tag = "reviewer_pack"

    if not REVIEWER_NOTES.exists():
        results.append((False, tag, f"File missing: {REVIEWER_NOTES}"))
        return results

    content = REVIEWER_NOTES.read_text(encoding="utf-8")
    lower = content.lower()

    # Required posture markers.
    required_markers = {
        "read-only": ["read-only", "read only"],
        "wellness_posture": ["does not diagnose", "does not treat", "not medical"],
        "healthkit_mention": ["healthkit", "health kit", "health access"],
    }

    for label, patterns in required_markers.items():
        if not any(p in lower for p in patterns):
            results.append((False, tag, f"Reviewer notes missing required marker: {label}"))
            return results

    # No real credentials pattern.
    credential_patterns = [
        re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"secret\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"api[_-]?key\s*[:=]\s*[A-Za-z0-9]{16,}", re.IGNORECASE),
    ]
    for pat in credential_patterns:
        if pat.search(content):
            results.append((False, tag, f"Reviewer notes may contain credentials: {pat.pattern}"))
            return results

    results.append((True, tag, "Reviewer notes present with required posture markers"))
    return results


def check_screenshot_policy() -> Results:
    """Verify screenshot asset gate exists and has no submission overclaims."""
    results: Results = []
    tag = "screenshot_policy"

    if not SCREENSHOT_GATE.exists():
        results.append((False, tag, f"File missing: {SCREENSHOT_GATE}"))
        return results

    scenario_classifications, parse_error = _collect_markdown_scenario_classifications(
        SCREENSHOT_GATE
    )
    if parse_error:
        results.append((False, tag, parse_error))
        return results

    submit_ready = {s for s, cl in scenario_classifications.items() if "SUBMIT_READY" in cl}
    impl_required = {
        s for s, cl in scenario_classifications.items() if "IMPLEMENTATION_REQUIRED" in cl
    }

    overclaimed = submit_ready & impl_required
    if overclaimed:
        results.append(
            (
                False,
                tag,
                f"Scenarios claimed as both SUBMIT_READY and IMPLEMENTATION_REQUIRED: {overclaimed}",
            )
        )
        return results

    classification_error = _validate_expected_classifications(
        scenario_classifications,
        source_label="Screenshot policy",
    )
    if classification_error:
        results.append((False, tag, classification_error))
        return results

    results.append(
        (True, tag, f"Screenshot policy OK ({len(submit_ready)} SUBMIT_READY, no overclaims)")
    )
    return results


def check_fitchef_release_readiness_bundle() -> Results:
    """Verify the FitChef rendered-review/TestFlight prep bundle is deterministic."""
    results: Results = []
    tag = "fitchef_release_readiness_bundle"

    pack_boundary_error = _validate_fitchef_pack_file_boundaries()
    if pack_boundary_error:
        results.append((False, tag, pack_boundary_error))
        return results
    protected_media_error = _validate_fitchef_protected_media_boundaries()
    if protected_media_error:
        results.append((False, tag, protected_media_error))
        return results

    if not FITCHEF_RELEASE_READINESS_DIR.exists():
        results.append((False, tag, f"Directory missing: {FITCHEF_RELEASE_READINESS_DIR}"))
        return results

    for path in FITCHEF_RELEASE_READINESS_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in FITCHEF_MEDIA_SUFFIXES:
            results.append((False, tag, f"Media file is not allowed in release bundle: {path}"))
            return results
        if path.suffix.lower() not in {".json", ".md"}:
            results.append((False, tag, f"Only JSON/Markdown files are allowed: {path}"))
            return results

    if not FITCHEF_SHOT_SCENARIO_MATRIX.exists():
        results.append((False, tag, f"File missing: {FITCHEF_SHOT_SCENARIO_MATRIX}"))
        return results
    if not FITCHEF_RENDERED_REVIEW_CHECKLIST.exists():
        results.append((False, tag, f"File missing: {FITCHEF_RENDERED_REVIEW_CHECKLIST}"))
        return results

    payload, load_error = _load_json_file(FITCHEF_SHOT_SCENARIO_MATRIX)
    if load_error or not isinstance(payload, dict):
        results.append((False, tag, f"Invalid scenario matrix JSON: {load_error or 'not object'}"))
        return results

    top_level_schema_error = _exact_keys_error(
        payload,
        FITCHEF_RELEASE_TOP_LEVEL_KEYS,
        label="Scenario matrix top-level",
    )
    if top_level_schema_error:
        results.append((False, tag, top_level_schema_error))
        return results
    if payload.get("schema_version") != EXPECTED_FITCHEF_RELEASE_SCHEMA_VERSION:
        results.append(
            (
                False,
                tag,
                "Scenario matrix schema_version drift: "
                f"{payload.get('schema_version')!r} != {EXPECTED_FITCHEF_RELEASE_SCHEMA_VERSION!r}",
            )
        )
        return results

    source_pr = payload.get("source_pr")
    if not isinstance(source_pr, dict):
        results.append((False, tag, "Scenario matrix source_pr must be an object"))
        return results
    source_pr_schema_error = _exact_keys_error(
        source_pr,
        FITCHEF_RELEASE_SOURCE_PR_KEYS,
        label="Scenario matrix source_pr",
    )
    if source_pr_schema_error:
        results.append((False, tag, source_pr_schema_error))
        return results
    source_pr_value_error = _validate_source_pr(source_pr)
    if source_pr_value_error:
        results.append((False, tag, source_pr_value_error))
        return results

    source_paths = payload.get("source_paths")
    if not isinstance(source_paths, dict):
        results.append((False, tag, "Scenario matrix source_paths must be an object"))
        return results
    source_paths_schema_error = _exact_keys_error(
        source_paths,
        FITCHEF_RELEASE_SOURCE_PATH_KEYS,
        label="Scenario matrix source_paths",
    )
    if source_paths_schema_error:
        results.append((False, tag, source_paths_schema_error))
        return results
    source_paths_value_error = _validate_source_paths(source_paths)
    if source_paths_value_error:
        results.append((False, tag, source_paths_value_error))
        return results

    blocked_actions = payload.get("blocked_release_actions")
    if not isinstance(blocked_actions, list) or tuple(blocked_actions) != (
        EXPECTED_FITCHEF_BLOCKED_RELEASE_ACTIONS
    ):
        results.append(
            (
                False,
                tag,
                "Scenario matrix blocked_release_actions drift: "
                f"{blocked_actions!r} != {EXPECTED_FITCHEF_BLOCKED_RELEASE_ACTIONS!r}",
            )
        )
        return results

    ios_source_error = _validate_ios_screenshot_sources()
    if ios_source_error:
        results.append((False, tag, ios_source_error))
        return results

    checklist = FITCHEF_RENDERED_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    combined_text, scan_error = _release_readiness_scan_text()
    if scan_error:
        results.append((False, tag, scan_error))
        return results
    scan_policy_error = _validate_release_readiness_scan_text(combined_text)
    if scan_policy_error:
        results.append((False, tag, scan_policy_error))
        return results

    if payload.get("classification") != "INTERNAL_REVIEW_ONLY":
        results.append((False, tag, "Scenario matrix must be INTERNAL_REVIEW_ONLY"))
        return results
    if payload.get("validation_gate") != "make ios-appstore-verify":
        results.append((False, tag, "Scenario matrix missing make ios-appstore-verify gate"))
        return results
    if tuple(payload.get("locales", ())) != FITCHEF_LOCALES:
        results.append((False, tag, f"Locale drift in scenario matrix: {payload.get('locales')}"))
        return results

    reviewer_classifications, reviewer_parse_error = _collect_markdown_scenario_classifications(
        REVIEWER_SUBMISSION_MATRIX
    )
    if reviewer_parse_error:
        results.append((False, tag, reviewer_parse_error))
        return results
    reviewer_classification_error = _validate_expected_classifications(
        reviewer_classifications,
        source_label="Reviewer submission matrix",
    )
    if reviewer_classification_error:
        results.append((False, tag, reviewer_classification_error))
        return results

    screenshot_classifications, screenshot_parse_error = _collect_markdown_scenario_classifications(
        SCREENSHOT_GATE
    )
    if screenshot_parse_error:
        results.append((False, tag, screenshot_parse_error))
        return results
    screenshot_classification_error = _validate_expected_classifications(
        screenshot_classifications,
        source_label="Screenshot gate",
    )
    if screenshot_classification_error:
        results.append((False, tag, screenshot_classification_error))
        return results

    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        results.append((False, tag, "Scenario matrix missing scenarios list"))
        return results
    observed_scenarios: dict[str, dict[str, Any]] = {}
    for item in scenarios:
        if not isinstance(item, dict):
            results.append((False, tag, "Scenario matrix row is not an object"))
            return results
        scenario_id = item.get("scenario_id")
        if not isinstance(scenario_id, str):
            results.append((False, tag, f"Scenario matrix row missing scenario_id: {item!r}"))
            return results
        if scenario_id in observed_scenarios:
            results.append((False, tag, f"Duplicate scenario id: {scenario_id}"))
            return results
        observed_scenarios[scenario_id] = item
    if set(observed_scenarios) != set(EXPECTED_FITCHEF_SCENARIOS):
        results.append(
            (
                False,
                tag,
                "Scenario ids drift: "
                f"expected {sorted(EXPECTED_FITCHEF_SCENARIOS)}, "
                f"found {sorted(observed_scenarios)}",
            )
        )
        return results

    for scenario_id, expected in EXPECTED_FITCHEF_SCENARIOS.items():
        item = observed_scenarios[scenario_id]
        scenario_schema_error = _exact_keys_error(
            item,
            FITCHEF_RELEASE_SCENARIO_KEYS,
            label=f"Scenario {scenario_id}",
        )
        if scenario_schema_error:
            results.append((False, tag, scenario_schema_error))
            return results
        expected_fields = {
            "shot_id": expected["shot_id"],
            "expected_filename": expected["filename"],
            "ui_test_screenshot_name": expected["screenshot_name"],
            "accessibility_identifier": expected["accessibility_identifier"],
            "reviewer_matrix_classification": expected["classification"],
            "screenshot_gate_classification": expected["classification"],
        }
        for field, expected_value in expected_fields.items():
            if item.get(field) != expected_value:
                results.append(
                    (
                        False,
                        tag,
                        f"{scenario_id} {field} drift: {item.get(field)!r} != {expected_value!r}",
                    )
                )
                return results
        if item.get("public_submission_allowed") is not False:
            results.append((False, tag, f"{scenario_id} must not claim public submission allowed"))
            return results
        if item.get("rendered_review_required") is not True:
            results.append((False, tag, f"{scenario_id} must require rendered review"))
            return results
        if item.get("testflight_smoke_status") != "not_started":
            results.append(
                (
                    False,
                    tag,
                    f"{scenario_id} TestFlight smoke status must stay not_started: "
                    f"{item.get('testflight_smoke_status')!r}",
                )
            )
            return results
        for field in ("privacy_ai_wellness_note", "reviewer_action"):
            text_error = _validate_non_empty_string(
                item.get(field),
                label=f"{scenario_id} {field}",
            )
            if text_error:
                results.append((False, tag, text_error))
                return results
        scenario_reviewer_action = str(item.get("reviewer_action", "")).lower()
        if (
            "render all locales" not in scenario_reviewer_action
            or "protected upload follow-up" not in scenario_reviewer_action
        ):
            results.append(
                (
                    False,
                    tag,
                    f"{scenario_id} reviewer_action missing rendered-review/upload boundary",
                )
            )
            return results

    locale_rows = payload.get("locale_review_matrix")
    if not isinstance(locale_rows, list):
        results.append((False, tag, "Scenario matrix missing locale_review_matrix list"))
        return results
    expected_pairs = {
        (locale, shot_id) for locale in FITCHEF_LOCALES for shot_id in EXPECTED_FITCHEF_SHOTS
    }
    if len(locale_rows) != len(expected_pairs):
        results.append(
            (
                False,
                tag,
                f"Locale review matrix row count drift: {len(locale_rows)} != {len(expected_pairs)}",
            )
        )
        return results
    observed_pairs: set[tuple[str, str]] = set()
    for row in locale_rows:
        if not isinstance(row, dict):
            results.append((False, tag, "Locale review matrix row is not an object"))
            return results
        row_schema_error = _exact_keys_error(
            row,
            FITCHEF_RELEASE_LOCALE_ROW_KEYS,
            label="Locale review matrix row",
        )
        if row_schema_error:
            results.append((False, tag, row_schema_error))
            return results
        locale = row.get("locale")
        shot_id = row.get("shot_id")
        if not isinstance(locale, str) or not isinstance(shot_id, str):
            results.append((False, tag, f"Locale review row missing locale/shot: {row!r}"))
            return results
        observed_pairs.add((locale, shot_id))
        if locale not in FITCHEF_LOCALES or shot_id not in EXPECTED_FITCHEF_SHOTS:
            results.append((False, tag, f"Unexpected locale/shot pair: {(locale, shot_id)}"))
            return results
        expected = EXPECTED_FITCHEF_SHOTS[shot_id]
        expected_manifest_path = _expected_fitchef_manifest_path(locale)
        expected_storyboard_path = _expected_fitchef_storyboard_path(locale)
        if row.get("manifest_path") != expected_manifest_path:
            results.append(
                (
                    False,
                    tag,
                    f"Manifest path must point to governed FitChef pack for {(locale, shot_id)}: "
                    f"{row.get('manifest_path')!r}",
                )
            )
            return results
        if row.get("storyboard_path") != expected_storyboard_path:
            results.append(
                (
                    False,
                    tag,
                    f"Storyboard path must point to governed FitChef pack for {(locale, shot_id)}: "
                    f"{row.get('storyboard_path')!r}",
                )
            )
            return results
        for field in ("manifest_path", "storyboard_path"):
            value = row.get(field)
            if not isinstance(value, str) or not _is_safe_repo_relative_path(value):
                results.append((False, tag, f"Unsafe {field} for {(locale, shot_id)}: {value!r}"))
                return results
            if not (REPO_ROOT / value).exists():
                results.append((False, tag, f"Referenced {field} does not exist: {value}"))
                return results
        manifest_payload, manifest_error = _load_json_file(REPO_ROOT / str(row["manifest_path"]))
        if manifest_error or not isinstance(manifest_payload, dict):
            results.append(
                (
                    False,
                    tag,
                    f"Cannot load manifest for {(locale, shot_id)}: "
                    f"{manifest_error or 'not object'}",
                )
            )
            return results
        storyboard_payload, storyboard_error = _load_json_file(
            REPO_ROOT / str(row["storyboard_path"])
        )
        if storyboard_error or not isinstance(storyboard_payload, dict):
            results.append(
                (
                    False,
                    tag,
                    f"Cannot load storyboard for {(locale, shot_id)}: "
                    f"{storyboard_error or 'not object'}",
                )
            )
            return results
        if manifest_payload.get("locale") != locale:
            results.append(
                (
                    False,
                    tag,
                    f"Manifest locale drift for {(locale, shot_id)}: "
                    f"{manifest_payload.get('locale')}",
                )
            )
            return results
        if storyboard_payload.get("locale") != locale:
            results.append(
                (
                    False,
                    tag,
                    f"Storyboard locale drift for {(locale, shot_id)}: "
                    f"{storyboard_payload.get('locale')}",
                )
            )
            return results
        shots = manifest_payload.get("shots")
        scenes = storyboard_payload.get("scenes")
        if not isinstance(shots, list) or not isinstance(scenes, list):
            results.append(
                (False, tag, f"Manifest/storyboard missing rows for {(locale, shot_id)}")
            )
            return results
        matching_shots = [
            shot for shot in shots if isinstance(shot, dict) and shot.get("id") == shot_id
        ]
        matching_scenes = [
            scene for scene in scenes if isinstance(scene, dict) and scene.get("shot_id") == shot_id
        ]
        if len(matching_shots) != 1 or len(matching_scenes) != 1:
            results.append(
                (
                    False,
                    tag,
                    f"Manifest/storyboard shot coverage drift for {(locale, shot_id)}",
                )
            )
            return results
        if matching_shots[0].get("expected_filename") != expected["filename"]:
            results.append(
                (
                    False,
                    tag,
                    f"Manifest filename drift for {(locale, shot_id)}: "
                    f"{matching_shots[0].get('expected_filename')}",
                )
            )
            return results
        if matching_scenes[0].get("id") != expected["scene_id"]:
            results.append(
                (
                    False,
                    tag,
                    f"Storyboard scene drift for {(locale, shot_id)}: "
                    f"{matching_scenes[0].get('id')}",
                )
            )
            return results
        expected_time_range = (
            f"{matching_scenes[0].get('start_second')}-" f"{matching_scenes[0].get('end_second')}s"
        )
        if row.get("time_range") != expected_time_range:
            results.append(
                (
                    False,
                    tag,
                    f"Time range drift for {(locale, shot_id)}: "
                    f"{row.get('time_range')} != {expected_time_range}",
                )
            )
            return results
        if row.get("scene_id") != expected["scene_id"]:
            results.append(
                (False, tag, f"Scene drift for {(locale, shot_id)}: {row.get('scene_id')}")
            )
            return results
        if row.get("safe_area_status") != "pending_render":
            results.append(
                (False, tag, f"Safe-area status must be pending_render: {(locale, shot_id)}")
            )
            return results
        if row.get("line_fit_status") not in {"review", "pass-length", "render-risk"}:
            results.append((False, tag, f"Unknown line-fit status: {row.get('line_fit_status')}"))
            return results
        expected_line_fit_status = _expected_fitchef_line_fit_status(locale, shot_id)
        if row.get("line_fit_status") != expected_line_fit_status:
            results.append(
                (
                    False,
                    tag,
                    f"Line-fit status drift for {(locale, shot_id)}: "
                    f"{row.get('line_fit_status')!r} != {expected_line_fit_status!r}",
                )
            )
            return results
        wellness_status = row.get("wellness_claim_status")
        if wellness_status not in FITCHEF_RELEASE_WELLNESS_STATUS_VALUES:
            results.append((False, tag, f"Unknown wellness-claim status: {wellness_status!r}"))
            return results
        expected_wellness_status = EXPECTED_FITCHEF_WELLNESS_STATUS_BY_SHOT[shot_id]
        if wellness_status != expected_wellness_status:
            results.append(
                (
                    False,
                    tag,
                    f"Wellness-claim status drift for {(locale, shot_id)}: "
                    f"{wellness_status!r} != {expected_wellness_status!r}",
                )
            )
            return results
        if "fitchef" not in str(row.get("fitchef_overlap_status", "")).lower():
            results.append((False, tag, f"Missing FitChef overlap cue for {(locale, shot_id)}"))
            return results
        reviewer_action_error = _validate_non_empty_string(
            row.get("reviewer_action"),
            label=f"Locale reviewer_action for {(locale, shot_id)}",
        )
        if reviewer_action_error:
            results.append((False, tag, reviewer_action_error))
            return results
        if "rendered review" not in str(row.get("reviewer_action", "")).lower():
            results.append((False, tag, f"Missing rendered-review action for {(locale, shot_id)}"))
            return results

    if observed_pairs != expected_pairs:
        missing = sorted(expected_pairs - observed_pairs)
        extra = sorted(observed_pairs - expected_pairs)
        results.append(
            (False, tag, f"Locale review matrix drift; missing={missing}, extra={extra}")
        )
        return results

    required_checklist_markers = [
        "Classification: INTERNAL_REVIEW_ONLY",
        "make ios-appstore-verify",
        "TestFlight",
        "Fastlane upload",
        "App Store Connect mutation",
    ]
    required_checklist_markers.extend(FITCHEF_LOCALES)
    required_checklist_markers.extend(EXPECTED_FITCHEF_SHOTS)
    for marker in required_checklist_markers:
        if marker not in checklist:
            results.append((False, tag, f"Rendered-review checklist missing marker: {marker}"))
            return results

    results.append(
        (
            True,
            tag,
            f"FitChef release-readiness bundle OK ({len(scenarios)} scenarios, {len(locale_rows)} locale rows)",
        )
    )
    return results


def check_storekit_pricing_truth() -> Results:
    """Verify metadata does not hardcode prices or trial claims."""
    results: Results = []
    tag = "storekit_pricing_truth"

    files_to_scan = []
    for locale in LOCALES:
        locale_dir = METADATA_DIR / locale
        if not locale_dir.is_dir():
            continue
        for name in (
            "description.txt",
            "release_notes.txt",
            "promotional_text.txt",
            "subtitle.txt",
        ):
            p = locale_dir / name
            if p.exists():
                files_to_scan.append(p)

    if not files_to_scan:
        results.append((False, tag, "No metadata files found to scan"))
        return results

    for path in files_to_scan:
        content = path.read_text(encoding="utf-8")
        content_variants = _scan_text_variants(content)
        for pat in PRICING_PATTERNS:
            for variant in content_variants:
                match = pat.search(variant)
                if match:
                    rel = _display_repo_local_path(path)
                    results.append(
                        (
                            False,
                            tag,
                            f"Hardcoded pricing found in {rel}: '{match.group()}'",
                        )
                    )
                    return results
        normalized_content_variants = [_claim_scan_text(variant) for variant in content_variants]
        for fragment in FITCHEF_RELEASE_LOCALIZED_PRICING_FRAGMENTS:
            if any(fragment in normalized for normalized in normalized_content_variants):
                rel = _display_repo_local_path(path)
                results.append(
                    (
                        False,
                        tag,
                        f"Localized hardcoded pricing found in {rel}: {fragment}",
                    )
                )
                return results
        lowered_content_variants = [variant.lower() for variant in content_variants]
        for fragment in FITCHEF_METADATA_PROTECTED_STATUS_FRAGMENTS:
            if any(fragment in lowered for lowered in lowered_content_variants):
                rel = _display_repo_local_path(path)
                results.append(
                    (
                        False,
                        tag,
                        f"Protected release status claim found in {rel}: {fragment}",
                    )
                )
                return results
        for pattern in FITCHEF_PROTECTED_ACTION_CLAIM_PATTERNS:
            for variant in content_variants:
                match = pattern.search(variant)
                if match:
                    rel = _display_repo_local_path(path)
                    results.append(
                        (
                            False,
                            tag,
                            f"Protected release action claim found in {rel}: {match.group()}",
                        )
                    )
                    return results

    results.append((True, tag, f"No hardcoded pricing in {len(files_to_scan)} metadata files"))
    return results


# --- Runner ---

ALL_CHECKS = [
    check_release_base_url,
    check_appicon_marketing,
    check_privacy_manifest,
    check_app_privacy_details,
    check_permission_strings,
    check_healthkit_readonly,
    check_ai_wellness_consent,
    check_reviewer_pack,
    check_screenshot_policy,
    check_fitchef_release_readiness_bundle,
    check_storekit_pricing_truth,
]


def main() -> int:
    """Run all checks and print results."""
    all_results: Results = []
    for check_fn in ALL_CHECKS:
        results = check_fn()
        all_results.extend(results)

    passes = 0
    failures = 0
    for ok, tag, msg in all_results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {tag}: {msg}")
        if ok:
            passes += 1
        else:
            failures += 1

    print()
    print(f"Results: {passes} passed, {failures} failed")

    if failures > 0:
        print("FAILED: App Store repo-local release validation did not pass.")
        return 1

    print("OK: All App Store repo-local release validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
