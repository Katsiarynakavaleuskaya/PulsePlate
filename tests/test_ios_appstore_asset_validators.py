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
    "01_welcome",
    "02_home",
    "03_plate",
    "04_pro_vip_paywall",
    "05_privacy_profile",
    "06_health_permission",
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
    elif profile == "none":
        pass
    else:
        raise ValueError(f"Unsupported profile {profile}")

    chunks.append(_png_chunk(b"IDAT", pixel_data))
    chunks.append(_png_chunk(b"IEND", b""))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))


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
                    "category": "HEALTH",
                    "purposes": ["APP_FUNCTIONALITY"],
                    "data_protections": ["DATA_LINKED_TO_YOU"],
                },
                {
                    "category": "FITNESS",
                    "purposes": ["APP_FUNCTIONALITY"],
                    "data_protections": ["DATA_LINKED_TO_YOU"],
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


def test_validate_color_gamut_requires_consistent_embedded_profile(tmp_path: Path) -> None:
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
        profile="none",
    )

    result = _run_ruby(
        REPO_ROOT / "ios/fastlane/verify/validate_color_gamut.rb",
        str(tmp_path / "screenshots"),
    )

    assert result.returncode == 1
    assert "Missing color profile chunk" in result.stderr


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
                    f'"NSHealthUpdateUsageDescription" = "{description}";',
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
