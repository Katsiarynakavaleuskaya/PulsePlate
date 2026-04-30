from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from scripts.release import reviewer_packet_hashes

REPO_ROOT = Path(__file__).resolve().parents[1]
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _write_metadata_pack(repo_root: Path) -> None:
    notes_path = repo_root / "ios/fastlane/metadata/review_information/notes.txt"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text("Reviewer note\r\n", encoding="utf-8")

    privacy_path = repo_root / "ios/fastlane/app_privacy_details.json"
    privacy_path.parent.mkdir(parents=True, exist_ok=True)
    privacy_path.write_text('[{"data_protections":["DATA_NOT_COLLECTED"]}]\n', encoding="utf-8")

    for locale in reviewer_packet_hashes.REQUIRED_LOCALES:
        locale_dir = repo_root / "ios/fastlane/metadata" / locale
        locale_dir.mkdir(parents=True, exist_ok=True)
        for filename in reviewer_packet_hashes.REQUIRED_METADATA_FILES:
            (locale_dir / filename).write_text(
                f"{locale}:{filename}\r\n",
                encoding="utf-8",
            )


def test_canonical_utf8_bytes_normalizes_line_endings_and_trailing_lf() -> None:
    assert reviewer_packet_hashes.canonical_utf8_bytes(b"a\r\nb\rc\n\n") == b"a\nb\nc\n"
    assert reviewer_packet_hashes.canonical_utf8_bytes("wellness".encode("utf-8")) == b"wellness\n"


def test_sha256_contract_is_lowercase_hex_without_prefix() -> None:
    digest = reviewer_packet_hashes.sha256_lower_hex(b"reviewer")

    assert digest == hashlib.sha256(b"reviewer").hexdigest()
    assert HASH_RE.fullmatch(digest)
    assert not digest.startswith("sha256:")


def test_build_contract_emits_schema_hash_fields_and_current_artifact_names(
    tmp_path: Path,
) -> None:
    _write_metadata_pack(tmp_path)

    payload = reviewer_packet_hashes.build_reviewer_packet_hash_contract(tmp_path)
    artifact_paths = {entry["path"] for entry in payload["source_artifacts"]}

    assert payload["schema_version"] == "release-reviewer-packet-hashes.v1"
    assert payload["hash_algorithm"] == "sha256"
    assert payload["canonicalization"] == "utf8-lf-single-trailing-newline"
    assert HASH_RE.fullmatch(payload["reviewer_notes_hash"])
    assert HASH_RE.fullmatch(payload["appstore_metadata_hash"])
    assert "ios/fastlane/metadata/review_information/notes.txt" in artifact_paths
    assert "ios/fastlane/app_privacy_details.json" in artifact_paths
    assert "ios/fastlane/metadata/en-US/name.txt" in artifact_paths
    assert "ios/fastlane/metadata/ru-RU/release_notes.txt" in artifact_paths
    assert "ios/fastlane/metadata/es-ES/support_url.txt" in artifact_paths


def test_reviewer_notes_hash_is_independent_from_metadata_hash(tmp_path: Path) -> None:
    _write_metadata_pack(tmp_path)
    first = reviewer_packet_hashes.build_reviewer_packet_hash_contract(tmp_path)

    notes_path = tmp_path / "ios/fastlane/metadata/review_information/notes.txt"
    notes_path.write_text("Changed reviewer note\n", encoding="utf-8")
    second = reviewer_packet_hashes.build_reviewer_packet_hash_contract(tmp_path)

    assert second["reviewer_notes_hash"] != first["reviewer_notes_hash"]
    assert second["appstore_metadata_hash"] == first["appstore_metadata_hash"]


def test_metadata_hash_is_stable_for_discovery_order_and_changes_on_content(
    tmp_path: Path,
) -> None:
    _write_metadata_pack(tmp_path)
    first = reviewer_packet_hashes.build_reviewer_packet_hash_contract(tmp_path)
    second = reviewer_packet_hashes.build_reviewer_packet_hash_contract(tmp_path)

    assert second["appstore_metadata_hash"] == first["appstore_metadata_hash"]

    metadata_path = tmp_path / "ios/fastlane/metadata/es-ES/keywords.txt"
    metadata_path.write_text("nutrition,wellness,release\n", encoding="utf-8")
    changed = reviewer_packet_hashes.build_reviewer_packet_hash_contract(tmp_path)

    assert changed["appstore_metadata_hash"] != first["appstore_metadata_hash"]
    assert changed["reviewer_notes_hash"] == first["reviewer_notes_hash"]


def test_schema_file_matches_emitted_payload_shape(tmp_path: Path) -> None:
    _write_metadata_pack(tmp_path)
    payload = reviewer_packet_hashes.build_reviewer_packet_hash_contract(tmp_path)
    schema = json.loads(
        (REPO_ROOT / "docs/release/REVIEWER_PACKET_HASH_CONTRACT.schema.json").read_text(
            encoding="utf-8"
        )
    )

    required = set(schema["required"])
    assert required <= set(payload)
    assert payload["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert payload["hash_algorithm"] == schema["properties"]["hash_algorithm"]["const"]
    assert payload["canonicalization"] == schema["properties"]["canonicalization"]["const"]
    assert HASH_RE.fullmatch(payload["reviewer_notes_hash"])
    assert HASH_RE.fullmatch(payload["appstore_metadata_hash"])


@pytest.mark.parametrize(
    "relative_path",
    [
        "ios/fastlane/metadata/review_information/notes.txt",
        "ios/fastlane/metadata/en-US/name.txt",
        "ios/fastlane/metadata/ru-RU/description.txt",
        "ios/fastlane/metadata/es-ES/release_notes.txt",
    ],
)
def test_landed_appstore_readiness_artifacts_exist(relative_path: str) -> None:
    assert (REPO_ROOT / relative_path).is_file()
