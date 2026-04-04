from __future__ import annotations

import json
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUBY_BIN = shutil.which("ruby")

if RUBY_BIN is None:
    pytestmark = pytest.mark.skip(reason="ruby is required for Fastlane validator tests")


SCREENSHOT_NAMES = [
    "01_core-value",
    "02_nutrition-analysis",
    "03_meal-planner",
    "04_grocery-list",
    "05_health-progress",
    "06_personalization",
    "07_ai-assistant",
]
LOCALES = ["en-US", "ru-RU", "es-ES"]
IPAD_SIZE = (2064, 2752)
IPHONE_SIZE = (1290, 2796)


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def _write_png(path: Path, *, width: int, height: int, profile: str = "srgb") -> None:
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    row = b"\x00" + (b"\x80" * width)
    pixel_data = zlib.compress(row * height, level=9)

    chunks = [_png_chunk(b"IHDR", header)]
    if profile == "srgb":
        chunks.append(_png_chunk(b"sRGB", b"\x00"))
    elif profile == "iccp":
        icc_payload = b"Display P3\x00\x00" + zlib.compress(b"stub-profile")
        chunks.append(_png_chunk(b"iCCP", icc_payload))
    elif profile != "none":
        raise ValueError(f"Unsupported profile {profile}")

    chunks.append(_png_chunk(b"IDAT", pixel_data))
    chunks.append(_png_chunk(b"IEND", b""))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))


def _write_png_with_iccp_name_bytes(
    path: Path, *, width: int, height: int, profile_name: bytes
) -> None:
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    row = b"\x00" + (b"\x80" * width)
    pixel_data = zlib.compress(row * height, level=9)
    icc_payload = profile_name + b"\x00\x00" + zlib.compress(b"stub-profile")
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"iCCP", icc_payload)
        + _png_chunk(b"IDAT", pixel_data)
        + _png_chunk(b"IEND", b"")
    )


def _run_ruby(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert RUBY_BIN is not None
    return subprocess.run(
        [RUBY_BIN, str(script), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _prepare_metadata(metadata_root: Path) -> tuple[Path, Path]:
    review_notes = metadata_root / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = metadata_root.parent / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps(
            [
                {
                    "data_protections": ["DATA_NOT_COLLECTED"],
                },
            ]
        ),
        encoding="utf-8",
    )

    for locale in LOCALES:
        locale_dir = metadata_root / locale
        locale_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "name.txt": "PulsePlate",
            "subtitle.txt": "Wellness planner",
            "description.txt": "PulsePlate keeps wellness planning calm.",
            "keywords.txt": "nutrition,wellness,progress",
            "promotional_text.txt": "Track progress with calmer wellness guidance.",
            "release_notes.txt": "Updated App Store assets.",
            "privacy_url.txt": "https://pulseplate.app/privacy",
            "support_url.txt": "https://pulseplate.app/support",
            "marketing_url.txt": "https://pulseplate.app",
        }
        for filename, content in payload.items():
            (locale_dir / filename).write_text(content, encoding="utf-8")

    return review_notes, privacy_json


def test_validate_dimensions_accepts_complete_locale_matrix(tmp_path: Path) -> None:
    screenshots_root = tmp_path / "screenshots"
    for locale in LOCALES:
        locale_dir = screenshots_root / locale
        locale_dir.mkdir(parents=True, exist_ok=True)
        for name in SCREENSHOT_NAMES:
            _write_png(
                locale_dir / f"iPhone 17 Pro Max-{name}.png",
                width=IPHONE_SIZE[0],
                height=IPHONE_SIZE[1],
            )
            _write_png(
                locale_dir / f"iPad Pro 13-inch (M5)-{name}.png",
                width=IPAD_SIZE[0],
                height=IPAD_SIZE[1],
            )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_dimensions.rb",
        str(screenshots_root),
    )

    assert result.returncode == 0, result.stderr
    assert "validate_dimensions: OK" in result.stdout


def test_validate_dimensions_fails_when_a_family_is_missing(tmp_path: Path) -> None:
    screenshots_root = tmp_path / "screenshots"
    for locale in LOCALES:
        locale_dir = screenshots_root / locale
        locale_dir.mkdir(parents=True, exist_ok=True)
        for name in SCREENSHOT_NAMES:
            _write_png(
                locale_dir / f"iPhone 17 Pro Max-{name}.png",
                width=IPHONE_SIZE[0],
                height=IPHONE_SIZE[1],
            )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_dimensions.rb",
        str(screenshots_root),
    )

    assert result.returncode == 1
    assert "missing families ipad_13" in result.stderr


def test_validate_color_gamut_rejects_mixed_supported_profiles(tmp_path: Path) -> None:
    screenshots_root = tmp_path / "screenshots" / "en-US"
    screenshots_root.mkdir(parents=True, exist_ok=True)
    _write_png(
        screenshots_root / "iPhone 17 Pro Max-01_welcome.png",
        width=IPHONE_SIZE[0],
        height=IPHONE_SIZE[1],
        profile="srgb",
    )
    _write_png(
        screenshots_root / "iPad Pro 13-inch (M5)-01_welcome.png",
        width=IPAD_SIZE[0],
        height=IPAD_SIZE[1],
        profile="iccp",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_color_gamut.rb",
        str(tmp_path / "screenshots"),
    )

    assert result.returncode == 1
    assert "Mixed color profiles detected" in result.stderr


def test_validate_color_gamut_rejects_missing_embedded_profile(tmp_path: Path) -> None:
    screenshots_root = tmp_path / "screenshots" / "en-US"
    screenshots_root.mkdir(parents=True, exist_ok=True)
    _write_png(
        screenshots_root / "iPhone 17 Pro Max-01_welcome.png",
        width=IPHONE_SIZE[0],
        height=IPHONE_SIZE[1],
        profile="none",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_color_gamut.rb",
        str(tmp_path / "screenshots"),
    )

    assert result.returncode == 1
    assert "Missing color profile chunk" in result.stderr


def test_validate_healthkit_copy_reports_invalid_privacy_json_shape(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, _privacy_json = _prepare_metadata(metadata_root)
    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text('{"data_protections":["DATA_NOT_COLLECTED"]}', encoding="utf-8")

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert "App privacy JSON must be a non-empty array" in result.stderr


def test_validate_healthkit_copy_reports_invalid_privacy_json_without_crashing(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, _privacy_json = _prepare_metadata(metadata_root)
    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text("{invalid", encoding="utf-8")

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Invalid JSON in {privacy_json}" in result.stderr


def test_validate_healthkit_copy_reports_missing_review_notes_without_redundant_phrase_errors(
    tmp_path: Path,
) -> None:
    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )
    missing_review_notes = tmp_path / "review_information" / "notes.txt"

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(missing_review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Missing reviewer notes: {missing_review_notes}" in result.stderr
    assert "Reviewer notes must mention" not in result.stderr


def test_validate_metadata_rejects_non_comma_keyword_separators(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    (metadata_root / "en-US" / "keywords.txt").write_text("wellness;nutrition", encoding="utf-8")

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert "Keywords must be comma-separated" in result.stderr


@pytest.mark.parametrize(
    ("locale", "content"),
    [
        ("en-US", "Doctor-led nutrition treatment for every patient."),
        ("ru-RU", "Врач ставит диагноз и лечит пациента."),
        ("es-ES", "Tratamiento médico guiado por doctor para cada paciente."),
    ],
)
def test_validate_metadata_rejects_blocked_medical_wording_in_each_locale(
    tmp_path: Path, locale: str, content: str
) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    description_path = metadata_root / locale / "description.txt"
    description_path.write_text(content, encoding="utf-8")

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Blocked medical wording found in {description_path}" in result.stderr


def test_validate_metadata_rejects_guaranteed_promissory_claims(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    promotional_text_path = metadata_root / "en-US" / "promotional_text.txt"
    promotional_text_path.write_text(
        "Guaranteed results in 7 days with clinically proven progress.",
        encoding="utf-8",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert (
        f"Blocked guaranteed/promissory wording found in {promotional_text_path}" in result.stderr
    )


def test_validate_metadata_rejects_wellness_only_contradiction_wording(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    subtitle_path = metadata_root / "en-US" / "subtitle.txt"
    subtitle_path.write_text("Doctor-led clinical therapy planner", encoding="utf-8")

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Blocked medical wording found in {subtitle_path}" in result.stderr


@pytest.mark.parametrize(
    "content",
    [
        "Doctor-led wellness guidance for better habits.",
        "Doctor led wellness guidance for better habits.",
    ],
)
def test_validate_metadata_rejects_doctor_led_variants_without_other_medical_tokens(
    tmp_path: Path, content: str
) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    subtitle_path = metadata_root / "en-US" / "subtitle.txt"
    subtitle_path.write_text(content, encoding="utf-8")

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Blocked medical wording found in {subtitle_path}" in result.stderr


def test_validate_metadata_rejects_store_truth_claims(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    release_notes_path = metadata_root / "en-US" / "release_notes.txt"
    release_notes_path.write_text(
        "Start your free trial and subscribe for $9.99 per month.",
        encoding="utf-8",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Blocked StoreKit/App Store truth claim found in {release_notes_path}" in result.stderr


def test_validate_metadata_allows_wellness_disclaimer_variants(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    description_path = metadata_root / "en-US" / "description.txt"
    description_path.write_text(
        "PulsePlate supports wellness planning and does not diagnose or treat medical conditions.",
        encoding="utf-8",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr


def test_validate_metadata_allows_non_pricing_subscription_terms(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    release_notes_path = metadata_root / "en-US" / "release_notes.txt"
    release_notes_path.write_text(
        "Fixes a subscription settings sync bug and improves eligibility copy review.",
        encoding="utf-8",
    )
    keywords_path = metadata_root / "en-US" / "keywords.txt"
    keywords_path.write_text("wellness,subscription,planning,coach", encoding="utf-8")

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr


def test_validate_metadata_allows_non_pricing_cadence_wording(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    release_notes_path = metadata_root / "en-US" / "release_notes.txt"
    release_notes_path.write_text(
        "Get 10 wellness tips per month and seasonal planning refreshes each year.",
        encoding="utf-8",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr


def test_validate_metadata_allows_spanish_healthy_adjective(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    description_path = metadata_root / "es-ES" / "description.txt"
    description_path.write_text(
        "Comida sana y planificación wellness para hábitos más consistentes.",
        encoding="utf-8",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr


def test_validate_metadata_allows_neutral_quick_logging_copy(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    promotional_text_path = metadata_root / "en-US" / "promotional_text.txt"
    promotional_text_path.write_text(
        "Quickly log meals and review wellness history without extra steps.",
        encoding="utf-8",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr


def test_validate_metadata_rejects_medical_app_name(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    name_path = metadata_root / "en-US" / "name.txt"
    name_path.write_text("Doctor BMI Coach", encoding="utf-8")

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Blocked medical wording found in {name_path}" in result.stderr


def test_validate_metadata_rejects_invalid_argument_count(tmp_path: Path) -> None:
    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(tmp_path / "metadata"),
        str(tmp_path / "review_information" / "notes.txt"),
    )

    assert result.returncode == 1
    assert (
        "Usage: validate_metadata.rb <metadata_path> <review_notes> <privacy_json>" in result.stderr
    )


def test_validate_color_gamut_rejects_invalid_utf8_icc_profile_name_without_crashing(
    tmp_path: Path,
) -> None:
    screenshots_root = tmp_path / "screenshots" / "en-US"
    screenshots_root.mkdir(parents=True, exist_ok=True)
    _write_png_with_iccp_name_bytes(
        screenshots_root / "iPhone 17 Pro Max-01_welcome.png",
        width=IPHONE_SIZE[0],
        height=IPHONE_SIZE[1],
        profile_name=b"\xff\xfebad-profile",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_color_gamut.rb",
        str(tmp_path / "screenshots"),
    )

    assert result.returncode == 1
    assert "Unsupported color profile" in result.stderr


def test_metadata_and_healthkit_validators_accept_seeded_package(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)

    metadata_result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_metadata.rb",
        str(metadata_root),
        str(review_notes),
        str(privacy_json),
    )
    assert metadata_result.returncode == 0, metadata_result.stderr

    pulseplate_root = tmp_path / "PulsePlate"
    for locale, folder in {"en-US": "en.lproj", "ru-RU": "ru.lproj", "es-ES": "es.lproj"}.items():
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        description = {
            "en-US": "PulsePlate reads Health nutrition and body weight data to show wellness progress and planning with your consent.",
            "ru-RU": "PulsePlate читает данные о питании и весе из Health, чтобы с вашего согласия показывать wellness-прогресс и планирование.",
            "es-ES": "PulsePlate lee nutrición y peso corporal de Health para mostrar progreso y planificación wellness con tu consentimiento.",
        }[locale]
        (locale_dir / "InfoPlist.strings").write_text(
            "\n".join(
                [
                    f'"NSHealthShareUsageDescription" = "{description}";',
                ]
            ),
            encoding="utf-8",
        )

    healthkit_result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )
    assert healthkit_result.returncode == 0, healthkit_result.stderr


def test_validate_healthkit_copy_rejects_read_only_and_data_collection_contradictions(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "The app writes back to Health and collects Health data on our servers.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Reviewer notes contradict read-only HealthKit posture: {review_notes}" in result.stderr
    assert (
        f"Reviewer notes contradict DATA_NOT_COLLECTED Health posture: {review_notes}"
        in result.stderr
    )


def test_validate_healthkit_copy_uses_actual_privacy_posture_for_contradictions(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "The app writes back to Health and collects Health data on our servers.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_USED_TO_TRACK_YOU"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            "\n".join(
                [
                    '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
                    '"NSHealthUpdateUsageDescription" = "PulsePlate can write updates back to Health.";',
                ]
            ),
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert "NSHealthUpdateUsageDescription must be absent for read-only HealthKit" in result.stderr
    assert (
        "App privacy JSON must declare on-device HealthKit data as DATA_NOT_COLLECTED"
        in result.stderr
    )
    assert (
        f"Reviewer notes contradict read-only HealthKit posture: {review_notes}"
        not in result.stderr
    )
    assert (
        f"Reviewer notes contradict DATA_NOT_COLLECTED Health posture: {review_notes}"
        not in result.stderr
    )


def test_validate_healthkit_copy_emits_sorted_advisory_lines_without_failing(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "This review mentions analytics and personalization for a future audit.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr
    advisory_lines = [line for line in result.stdout.splitlines() if line.startswith("ADVISORY: ")]
    assert advisory_lines == [
        f"ADVISORY: {review_notes} :: review whether App Privacy answers need updating for analytics/advertising language",
        f"ADVISORY: {review_notes} :: review whether App Privacy answers need updating for personalization/data-sharing language",
    ]
    assert "validate_healthkit_copy: OK" in result.stdout


def test_validate_healthkit_copy_does_not_emit_advisory_for_meal_tracking_language(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "This review only references meal tracking and planning for wellness coaching.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr
    assert "ADVISORY:" not in result.stdout


def test_validate_healthkit_copy_emits_advisory_for_tracking_pixels_language(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "This review mentions tracking pixels for an ad attribution audit.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr
    assert (
        f"ADVISORY: {review_notes} :: review whether App Privacy answers need updating for analytics/advertising language"
        in result.stdout
    )


def test_validate_healthkit_copy_ignores_negated_privacy_contradictions(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "The app no longer writes back to Health and does not currently collect Health data on our servers.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr
    assert "Reviewer notes contradict" not in result.stderr


def test_validate_healthkit_copy_does_not_treat_bare_no_as_negation_with_following_words(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "No, we syncs to Health and collect Health data on our servers.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 1
    assert f"Reviewer notes contradict read-only HealthKit posture: {review_notes}" in result.stderr
    assert (
        f"Reviewer notes contradict DATA_NOT_COLLECTED Health posture: {review_notes}"
        in result.stderr
    )


def test_validate_healthkit_copy_ignores_spanish_no_se_negation(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "No se sincroniza de vuelta con Health y no almacenamos datos de Health en nuestros servidores.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr
    assert "Reviewer notes contradict" not in result.stderr


def test_validate_healthkit_copy_ignores_spanish_nunca_se_negation(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    _review_notes, _privacy_json = _prepare_metadata(metadata_root)
    review_notes = tmp_path / "review_information" / "notes.txt"
    review_notes.parent.mkdir(parents=True, exist_ok=True)
    review_notes.write_text(
        "\n".join(
            [
                "HealthKit review summary",
                "This flow is wellness-only.",
                "Users provide consent before enabling access.",
                "The HealthKit integration is read-only.",
                "Nunca se sincroniza de vuelta con Health y nunca almacena datos de Health en nuestros servidores.",
            ]
        ),
        encoding="utf-8",
    )

    privacy_json = tmp_path / "app_privacy_details.json"
    privacy_json.write_text(
        json.dumps([{"data_protections": ["DATA_NOT_COLLECTED"]}]),
        encoding="utf-8",
    )

    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            '"NSHealthShareUsageDescription" = "PulsePlate reads Health data with consent for wellness progress.";',
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr
    assert "Reviewer notes contradict" not in result.stderr


def test_validate_healthkit_copy_allows_wellness_disclaimer_variant(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    review_notes, privacy_json = _prepare_metadata(metadata_root)
    pulseplate_root = tmp_path / "PulsePlate"
    for folder in ("en.lproj", "ru.lproj", "es.lproj"):
        locale_dir = pulseplate_root / folder
        locale_dir.mkdir(parents=True, exist_ok=True)
        (locale_dir / "InfoPlist.strings").write_text(
            (
                '"NSHealthShareUsageDescription" = '
                '"PulsePlate reads Health data for wellness planning and does not diagnose or treat medical conditions.";'  # noqa: E501
            ),
            encoding="utf-8",
        )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_healthkit_copy.rb",
        str(pulseplate_root),
        str(review_notes),
        str(privacy_json),
    )

    assert result.returncode == 0, result.stderr
