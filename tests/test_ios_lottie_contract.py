from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOTTIE_URL = "https://github.com/airbnb/lottie-ios"
LOTTIE_VERSION = "4.6.1"
LOTTIE_REVISION = "f4db77d7fe" + "acba0c2360" + "b84a40c38a" + "6ce8ff399d"

PACKAGE_MANIFESTS = (
    REPO_ROOT / "ios/Package.swift",
    REPO_ROOT / "ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/Package.swift",
)
LOCKFILES = (
    REPO_ROOT / "ios/Package.resolved",
    REPO_ROOT
    / "ios/PulsePlate.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
)
PROJECT_FILE = REPO_ROOT / "ios/PulsePlate.xcodeproj/project.pbxproj"


def _normalized_url(value: str) -> str:
    return value.removesuffix(".git").rstrip("/")


def _lottie_pin(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    matches = [pin for pin in payload["pins"] if pin["identity"] == "lottie-ios"]
    assert len(matches) == 1, f"{path}: expected exactly one lottie-ios pin"
    pin = matches[0]
    return {
        "identity": pin["identity"],
        "kind": pin["kind"],
        "location": _normalized_url(pin["location"]),
        "revision": pin["state"]["revision"],
        "version": pin["state"]["version"],
    }


def test_lottie_swiftpm_declarations_are_exact_and_canonical() -> None:
    expected = f'.package(url: "{LOTTIE_URL}", exact: "{LOTTIE_VERSION}")'

    for manifest in PACKAGE_MANIFESTS:
        source = manifest.read_text(encoding="utf-8")
        compact_source = " ".join(source.split())
        assert source.count(expected) == 1, manifest
        assert source.count(LOTTIE_URL) == 1, manifest
        assert "4.5.2" not in source, manifest
        assert "lottie-ios.git" not in source, manifest
        assert not re.search(r"\.package\s*\(.*?\bfrom\s*:", compact_source), manifest
        assert not re.search(r"\.package\s*\(.*?\bbranch\s*:", compact_source), manifest
        assert not re.search(r"\.package\s*\(.*?\.upToNext", compact_source), manifest


def test_xcode_lottie_requirement_is_exact_and_animation_tests_are_included() -> None:
    source = PROJECT_FILE.read_text(encoding="utf-8")
    package_block = re.search(
        r'XCRemoteSwiftPackageReference "lottie-ios" \*/ = \{(?P<body>.*?)\n\s*\};',
        source,
        flags=re.DOTALL,
    )
    assert package_block is not None
    body = package_block.group("body")

    assert f'repositoryURL = "{LOTTIE_URL}";' in body
    assert "kind = exactVersion;" in body
    assert f"version = {LOTTIE_VERSION};" in body
    assert "minimumVersion" not in body
    assert "branch =" not in body
    assert "4.5.2" not in body

    exception_blocks = re.findall(
        r"PBXFileSystemSynchronizedBuildFileExceptionSet \*/ = \{(?P<body>.*?)\n\s*\};",
        source,
        flags=re.DOTALL,
    )
    test_exceptions = [body for body in exception_blocks if "/* PulsePlateTests */" in body]
    assert len(test_exceptions) == 1
    assert "AnimationTests.swift," not in test_exceptions[0]


def test_generated_lottie_locks_have_semantic_parity() -> None:
    pins = [_lottie_pin(path) for path in LOCKFILES]
    assert pins[0] == pins[1]
    assert pins[0] == {
        "identity": "lottie-ios",
        "kind": "remoteSourceControl",
        "location": LOTTIE_URL,
        "revision": LOTTIE_REVISION,
        "version": LOTTIE_VERSION,
    }


def test_lottie_dependency_surfaces_ban_legacy_or_broad_requirements() -> None:
    surfaces = (*PACKAGE_MANIFESTS, PROJECT_FILE, *LOCKFILES)
    for path in surfaces:
        source = path.read_text(encoding="utf-8")
        assert "4.5.2" not in source, path

    project_source = PROJECT_FILE.read_text(encoding="utf-8")
    assert "kind = upToNextMajorVersion;" not in project_source
    assert "kind = branch;" not in project_source
