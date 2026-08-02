"""Deterministic frontend dependency security guards.

RU: Проверяем frontend security overrides.
EN: Ensure frontend security overrides are pinned to safe npm releases.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_LOCK_JSON = REPO_ROOT / "frontend" / "package-lock.json"
BRACE_EXPANSION_EVIDENCE_PATH = (
    REPO_ROOT / "docs" / "security" / "FRONTEND_BRACE_EXPANSION_REMEDIATION_CLASS.md"
)
NPM_REGISTRY_HOST = "registry.npmjs.org"
MIN_DOMPURIFY_VERSION = Version("3.4.11")
MIN_JS_YAML_VERSION = Version("4.2.0")
MIN_UNDICI_VERSION = Version("7.28.0")
MIN_WS_VERSION = Version("8.21.0")
BRACE_EXPANSION_BASE_OUTPUTS = {2: "2.0.3", 5: "5.0.6"}
BRACE_EXPANSION_APPROVED_OUTPUTS = {2: "2.1.3", 5: "5.0.8"}
BRACE_EXPANSION_VARIANT_FLOORS = {
    major: Version(output) for major, output in BRACE_EXPANSION_APPROVED_OUTPUTS.items()
}
BRACE_EXPANSION_OVERRIDE_CARRIERS = {
    2: "minimatch@3",
    5: "minimatch@10",
}
BRACE_EXPANSION_LOCK_SNAPSHOTS = {
    "base": {
        "node_modules/brace-expansion": {
            "version": "2.0.3",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.0.3.tgz"),
            "integrity_sha256": "".join(
                (
                    "2e68800c",
                    "2b65f95b",
                    "f8986a21",
                    "f6105f93",
                    "3e13f44f",
                    "e6f53f4a",
                    "1793d034",
                    "1f800c4e",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^1.0.0"},
        },
        "node_modules/glob/node_modules/brace-expansion": {
            "version": "5.0.6",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-5.0.6.tgz"),
            "integrity_sha256": "".join(
                (
                    "277cbc9a",
                    "033d49c7",
                    "879edfc7",
                    "860ca172",
                    "aafbb8ae",
                    "e5aadedb",
                    "fb536939",
                    "16da3fc1",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^4.0.2"},
            "engines": {"node": "18 || 20 || >=22"},
        },
    },
    "head": {
        "node_modules/brace-expansion": {
            "version": "2.1.3",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.1.3.tgz"),
            "integrity_sha256": "".join(
                (
                    "19c80f96",
                    "f0698328",
                    "96b90980",
                    "368ddb6a",
                    "145a49a2",
                    "7bf589df",
                    "4d5dc451",
                    "1263acf2",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^1.0.0"},
        },
        "node_modules/glob/node_modules/brace-expansion": {
            "version": "5.0.8",
            "resolved": ("https://registry.npmjs.org/brace-expansion/-/brace-expansion-5.0.8.tgz"),
            "integrity_sha256": "".join(
                (
                    "a8307831",
                    "bb57dfe2",
                    "e8c5f8b5",
                    "b5759460",
                    "6c648d7c",
                    "f84ec64c",
                    "3613e70f",
                    "d8a8584d",
                )
            ),
            "dev": True,
            "license": "MIT",
            "dependencies": {"balanced-match": "^4.0.2"},
            "engines": {"node": "20 || >=22"},
        },
    },
}
BRACE_EXPANSION_ADVISORY_RANGE_TEXT = {
    "GHSA-3jxr-9vmj-r5cp": ("<1.1.16", ">=2.0.0,<2.1.2", ">=3.0.0,<5.0.7"),
    "GHSA-832h-xg76-4gv6": ("<1.1.7",),
    "GHSA-f886-m6hf-6m8v": (
        "<1.1.13",
        ">=2.0.0,<2.0.3",
        ">=3.0.0,<3.0.2",
        ">=4.0.0,<5.0.5",
    ),
    "GHSA-jxxr-4gwj-5jf2": (">=5.0.0,<5.0.6",),
    "GHSA-mh99-v99m-4gvg": (
        "<1.1.17",
        ">=2.0.0,<2.1.3",
        ">=3.0.0,<3.0.3",
        ">=4.0.0,<5.0.8",
    ),
    "GHSA-v6h2-p8h4-qcjw": (
        ">=1.0.0,<=1.1.11",
        ">=2.0.0,<=2.0.1",
        "==3.0.0",
        "==4.0.0",
    ),
}
BRACE_EXPANSION_ADVISORY_RANGES = {
    advisory: tuple(SpecifierSet(value) for value in ranges)
    for advisory, ranges in BRACE_EXPANSION_ADVISORY_RANGE_TEXT.items()
}
BRACE_EXPANSION_CUTOFF_ADVISORIES = frozenset(
    {
        "GHSA-3jxr-9vmj-r5cp",
        "GHSA-832h-xg76-4gv6",
        "GHSA-f886-m6hf-6m8v",
        "GHSA-jxxr-4gwj-5jf2",
        "GHSA-mh99-v99m-4gvg",
        "GHSA-v6h2-p8h4-qcjw",
    }
)
BRACE_EXPANSION_APPLICABLE_ADVISORIES = frozenset({"GHSA-3jxr-9vmj-r5cp", "GHSA-mh99-v99m-4gvg"})
BRACE_EXPANSION_RENDERED_PROJECTIONS = {
    "GHSA-3jxr-9vmj-r5cp": (
        "**Applicable**: both `2.0.3` and `5.0.6` are affected",
        "`2.1.3` and `5.0.8` are outside every affected range",
    ),
    "GHSA-mh99-v99m-4gvg": (
        "**Applicable**: both `2.0.3` and `5.0.6` are affected",
        "`2.1.3` and `5.0.8` equal their relevant first-patched versions",
    ),
    "GHSA-jxxr-4gwj-5jf2": (
        "Non-applicable: `5.0.6` equals the first-patched version; " "2.x has no affected range",
        "`5.0.8` remains above the fixed boundary; " "2.x remains outside the advisory domain",
    ),
    "GHSA-f886-m6hf-6m8v": (
        "Non-applicable: `2.0.3` equals its first-patched version and " "`5.0.6` is above `5.0.5`",
        "both head outputs remain outside every affected range",
    ),
    "GHSA-v6h2-p8h4-qcjw": (
        "Non-applicable: `2.0.3` is above the affected 2.x interval and " "there is no 5.x range",
        "both head outputs remain outside every affected range",
    ),
    "GHSA-832h-xg76-4gv6": (
        "Non-applicable: neither base major is in the advisory domain",
        "neither head major is in the advisory domain",
    ),
}
BRACE_EXPANSION_GAD_CUTOFF = "2026-08-01T05:41:33Z"
BRACE_EXPANSION_EVIDENCE_RECEIPT_SCHEMA = "pulseplate.frontend-brace-expansion-evidence-receipt/v1"
BRACE_EXPANSION_EVIDENCE_RECEIPT_BEGIN = "<!-- BEGIN BRACE_EXPANSION_EVIDENCE_RECEIPT -->"
BRACE_EXPANSION_EVIDENCE_RECEIPT_END = "<!-- END BRACE_EXPANSION_EVIDENCE_RECEIPT -->"
BRACE_EXPANSION_EVIDENCE_RECEIPT_SHA256 = (
    "46ebe242f8db59ef4b3806269378b08df6a1daa4c474430d2487c614c5e0fc21"  # pragma: allowlist secret
)
BRACE_EXPANSION_AUDIT_EXPECTATIONS = {
    "base": {
        "brace_expansion_advisory_ids": (
            "GHSA-3jxr-9vmj-r5cp",
            "GHSA-mh99-v99m-4gvg",
        ),
        "brace_expansion_present": True,
        "exit_code": 1,
        "total": 12,
        "vulnerability_keys": (
            "@eslint/config-array",
            "@eslint/eslintrc",
            "@redocly/openapi-core",
            "brace-expansion",
            "dompurify",
            "js-yaml",
            "jspdf",
            "minimatch",
            "postcss",
            "react-router",
            "react-router-dom",
            "style-dictionary",
        ),
    },
    "head": {
        "brace_expansion_advisory_ids": (),
        "brace_expansion_present": False,
        "exit_code": 1,
        "total": 9,
        "vulnerability_keys": (
            "@eslint/eslintrc",
            "@redocly/openapi-core",
            "dompurify",
            "js-yaml",
            "jspdf",
            "postcss",
            "react-router",
            "react-router-dom",
            "style-dictionary",
        ),
    },
}
BRACE_EXPANSION_EXACT_BASE = "9949d01654f365b1ef9df0b9d35b5ddaa69348c0"  # pragma: allowlist secret
BRACE_EXPANSION_EXACT_BASE_DIGESTS = {
    "frontend/package.json": (
        "17235b55570d8137d35b54a6d6a7a605cb7eea23f1acf684f842baf06f85c05b"  # pragma: allowlist secret
    ),
    "frontend/package-lock.json": (
        "059def600151a44cc1feacc40cb2638df23140c6e0de62f8d26291a47f697300"  # pragma: allowlist secret
    ),
}
BRACE_EXPANSION_EXACT_HEAD_DIGESTS = {
    "frontend/package.json": (
        "97bd09c0eec4fd15a582dd6a3fc96f02b29610e7955166796421f3cea703f309"  # pragma: allowlist secret
    ),
    "frontend/package-lock.json": (
        "41d793fe5905be75656cffc03fd03f9c8371ecf1f8f60aa8ee979e789efe5885"  # pragma: allowlist secret
    ),
}
BRACE_EXPANSION_MANIFEST_INTENT_PATHS = frozenset(
    {
        ("overrides", "minimatch@3", "brace-expansion"),
        ("overrides", "minimatch@10", "brace-expansion"),
    }
)
BRACE_EXPANSION_LOCK_CLOSURE_PATHS = frozenset(
    {
        ("packages", "node_modules/brace-expansion", "version"),
        ("packages", "node_modules/brace-expansion", "resolved"),
        ("packages", "node_modules/brace-expansion", "integrity"),
        ("packages", "node_modules/glob/node_modules/brace-expansion", "version"),
        ("packages", "node_modules/glob/node_modules/brace-expansion", "resolved"),
        ("packages", "node_modules/glob/node_modules/brace-expansion", "integrity"),
        ("packages", "node_modules/glob/node_modules/brace-expansion", "engines", "node"),
    }
)
NPM_SURFACE_BASENAMES = frozenset({"package.json", "package-lock.json", "npm-shrinkwrap.json"})
NPM_LOCK_SURFACE_BASENAMES = frozenset({"package-lock.json", "npm-shrinkwrap.json"})
EXPECTED_REPO_NPM_SURFACES = frozenset(
    {
        "frontend/package-lock.json",
        "frontend/package.json",
        "package-lock.json",
        "package.json",
        "scripts/business_collateral/package.json",
    }
)
IGNORED_NPM_SURFACE_PARTS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "artifacts",
        "build",
        "dist",
        "node_modules",
        "worktrees",
    }
)


def _load_json(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), f"{path}: npm surface must be a JSON object"
    return document


def _git_stdout(*args: str) -> bytes:
    git_binary = shutil.which("git")
    assert git_binary is not None, "git is required for exact-base dependency guards"
    assert Path(git_binary).is_absolute(), "git binary must resolve to an absolute path"
    result = subprocess.run(
        [git_binary, "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return result.stdout


def _load_json_at_git_ref(*, ref: str, relative: str) -> tuple[dict, bytes]:
    blob = _git_stdout("show", f"{ref}:{relative}")
    document = json.loads(blob)
    assert isinstance(document, dict), f"{ref}:{relative}: npm surface must be a JSON object"
    return document, blob


def _load_exact_base_frontend_documents() -> tuple[dict, dict]:
    documents: dict[str, dict] = {}
    for relative, expected_digest in BRACE_EXPANSION_EXACT_BASE_DIGESTS.items():
        document, blob = _load_json_at_git_ref(
            ref=BRACE_EXPANSION_EXACT_BASE,
            relative=relative,
        )
        assert (
            hashlib.sha256(blob).hexdigest() == expected_digest
        ), f"{BRACE_EXPANSION_EXACT_BASE}:{relative}: exact-base blob digest drift"
        documents[relative] = document
    return documents["frontend/package.json"], documents["frontend/package-lock.json"]


def _assert_npm_registry_resolution(*, package_name: str, resolved: str) -> None:
    """Assert npm registry provenance for the unscoped package names guarded here."""
    assert isinstance(resolved, str) and resolved, f"{package_name} resolved URL missing"
    parsed = urlparse(resolved.removeprefix("git+"))
    assert parsed.scheme == "https", f"{package_name} lock resolution must use https"
    assert parsed.netloc == NPM_REGISTRY_HOST, f"{package_name} must resolve from npm registry"
    assert parsed.path.startswith(
        f"/{package_name}/"
    ), f"{package_name} lock resolution path mismatch"
    assert not resolved.startswith(
        "git+"
    ), f"{package_name} lock resolution must not use git override"


def _parse_version(*, value: object, source: str) -> Version:
    assert isinstance(value, str) and value, f"{source}: version missing"
    try:
        return Version(value)
    except InvalidVersion as exc:
        raise AssertionError(f"{source}: malformed version {value!r}") from exc


def _is_brace_expansion_lock_path(path: object) -> bool:
    if not isinstance(path, str):
        return False
    normalized = path.replace("\\", "/")
    return PurePosixPath(normalized).parts[-2:] == (
        "node_modules",
        "brace-expansion",
    )


def _fully_decode_url_path(path: str) -> str:
    """Decode a URL path to a finite fixed point and normalize path separators."""

    decoded = path.replace("\\", "/")
    for _ in range(len(decoded) + 1):
        next_value = unquote(decoded).replace("\\", "/")
        if next_value == decoded:
            return decoded
        decoded = next_value
    raise AssertionError("URL path percent-decoding did not converge")


def _has_brace_expansion_tarball_path_signal(value: object) -> bool:
    """Discover a candidate by package pathname before validating its origin."""

    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    raw_paths = {parsed.path}
    if not parsed.scheme and not parsed.netloc:
        raw_pathname = value.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0]
        raw_paths.add(raw_pathname)

    candidate_paths: set[str] = set()
    for raw_path in raw_paths:
        decoded_path = _fully_decode_url_path(raw_path)
        candidate_paths.add(f"/{decoded_path.lstrip('/')}")
        if not parsed.scheme and not parsed.netloc:
            _, separator, pathname = decoded_path.lstrip("/").partition("/")
            if separator and pathname:
                candidate_paths.add(f"/{pathname.lstrip('/')}")

    candidate_paths.update(posixpath.normpath(path) for path in tuple(candidate_paths))
    tarball_path_signal = "/brace-expansion/-/brace-expansion-"
    return any(tarball_path_signal in path and path.endswith(".tgz") for path in candidate_paths)


def _is_npm_alias_for_target(value: object, *, target: str) -> bool:
    """Recognize only npm's bounded package-alias spelling for the target."""

    return isinstance(value, str) and (
        value == f"npm:{target}" or value.startswith(f"npm:{target}@")
    )


def _find_override_key_paths(
    node: object,
    *,
    target: str,
    path: tuple[str, ...] = (),
) -> dict[tuple[str, ...], object]:
    found: dict[tuple[str, ...], object] = {}
    if _is_npm_alias_for_target(node, target=target):
        found[path] = node
        return found
    if isinstance(node, dict):
        for key, value in node.items():
            child_path = (*path, str(key))
            is_target_key = key == target or (isinstance(key, str) and key.startswith(f"{target}@"))
            if is_target_key:
                found[child_path] = value
            found.update(_find_override_key_paths(value, target=target, path=child_path))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.update(_find_override_key_paths(value, target=target, path=(*path, f"[{index}]")))
    return found


def _discover_brace_expansion_lock_entries(packages: object) -> dict[str, dict]:
    """Enumerate the finite lockfile candidate universe independently of validity."""

    assert isinstance(packages, dict), "frontend/package-lock.json: packages must be an object"
    entries: dict[str, dict] = {}
    for raw_path, package in packages.items():
        canonical_path_signal = _is_brace_expansion_lock_path(raw_path)
        name_signal = isinstance(package, dict) and package.get("name") == "brace-expansion"
        url_signal = isinstance(package, dict) and _has_brace_expansion_tarball_path_signal(
            package.get("resolved")
        )
        if not (canonical_path_signal or name_signal or url_signal):
            continue
        assert isinstance(raw_path, str)
        assert (
            canonical_path_signal
        ), f"{raw_path}: brace-expansion alias/noncanonical installed path"
        path = PurePosixPath(raw_path)
        assert "\\" not in raw_path, f"{raw_path}: lock path must use POSIX separators"
        assert not path.is_absolute(), f"{raw_path}: lock path must be relative"
        assert ".." not in path.parts, f"{raw_path}: lock path must not contain traversal segments"
        assert path.as_posix() == raw_path, f"{raw_path}: lock path must be canonical"
        assert path.parts[-2:] == (
            "node_modules",
            "brace-expansion",
        ), f"{raw_path}: malformed brace-expansion lock path"
        assert isinstance(package, dict), f"{raw_path}: package entry must be an object"
        if "name" in package:
            assert (
                package["name"] == "brace-expansion"
            ), f"{raw_path}: package name conflicts with brace-expansion path"
        entries[raw_path] = package
    return entries


def _normalize_brace_expansion_lock_entries(entries: dict[str, dict]) -> dict[str, dict]:
    """Replace raw npm integrity material with its stable evidence digest."""

    normalized: dict[str, dict] = {}
    for path, package in entries.items():
        integrity = package.get("integrity")
        assert isinstance(integrity, str) and integrity.strip(), f"{path}: integrity missing"
        record = {key: value for key, value in package.items() if key != "integrity"}
        record["integrity_sha256"] = hashlib.sha256(integrity.encode("utf-8")).hexdigest()
        normalized[path] = record
    return normalized


def _version_is_affected(*, version: Version, advisory: str) -> bool:
    ranges = BRACE_EXPANSION_ADVISORY_RANGES[advisory]
    return any(version in affected_range for affected_range in ranges)


def _derive_applicable_advisories(versions: set[Version]) -> frozenset[str]:
    return frozenset(
        advisory
        for advisory in BRACE_EXPANSION_ADVISORY_RANGES
        if any(_version_is_affected(version=version, advisory=advisory) for version in versions)
    )


def _assert_brace_expansion_head_postcondition(versions: set[Version]) -> None:
    assert set(BRACE_EXPANSION_ADVISORY_RANGES) == BRACE_EXPANSION_CUTOFF_ADVISORIES
    for advisory in BRACE_EXPANSION_CUTOFF_ADVISORIES:
        assert all(
            not _version_is_affected(version=version, advisory=advisory) for version in versions
        ), f"{advisory}: governed head occurrence remains affected"


def _require_exact_object(
    value: object,
    *,
    keys: frozenset[str],
    label: str,
) -> dict[str, object]:
    assert isinstance(value, dict), f"{label}: must be an object"
    assert set(value) == keys, f"{label}: unexpected or missing keys"
    return value


def _canonicalize_brace_expansion_receipt(receipt: dict[str, object]) -> bytes:
    return json.dumps(
        receipt,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _normalize_advisory_range_text(value: object) -> str:
    assert isinstance(value, str) and value.strip(), "receipt advisory range must be text"
    normalized = re.sub(r"\s+", "", value)
    if normalized.startswith("=") and not normalized.startswith(("==", ">=", "<=", "!=", "~=")):
        normalized = f"={normalized}"
    SpecifierSet(normalized)
    return normalized


def _reject_duplicate_brace_expansion_receipt_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    """Reject ambiguous JSON objects before canonical receipt hashing."""

    result: dict[str, object] = {}
    for key, value in pairs:
        assert key not in result, f"owner evidence receipt duplicate JSON key: {key}"
        result[key] = value
    return result


def _extract_brace_expansion_evidence_receipt(document: str) -> dict[str, object]:
    assert (
        document.count(BRACE_EXPANSION_EVIDENCE_RECEIPT_BEGIN) == 1
    ), "owner evidence receipt begin marker drift"
    assert (
        document.count(BRACE_EXPANSION_EVIDENCE_RECEIPT_END) == 1
    ), "owner evidence receipt end marker drift"
    section = document.split(BRACE_EXPANSION_EVIDENCE_RECEIPT_BEGIN, maxsplit=1)[1].split(
        BRACE_EXPANSION_EVIDENCE_RECEIPT_END,
        maxsplit=1,
    )[0]
    match = re.fullmatch(
        r"\s*```json\n(?P<payload>.*?)\n```\s*",
        section,
        flags=re.DOTALL,
    )
    assert match is not None, "owner evidence receipt fence missing or malformed"
    receipt = json.loads(
        match.group("payload"),
        object_pairs_hook=_reject_duplicate_brace_expansion_receipt_keys,
    )
    assert isinstance(receipt, dict), "owner evidence receipt must be a JSON object"

    digest_matches = re.findall(
        r"Canonical normalized receipt SHA-256: `([0-9a-f]{64})`",
        document,
    )
    assert len(digest_matches) == 1, "owner evidence receipt digest marker drift"
    computed_digest = hashlib.sha256(_canonicalize_brace_expansion_receipt(receipt)).hexdigest()
    assert (
        digest_matches[0] == BRACE_EXPANSION_EVIDENCE_RECEIPT_SHA256
    ), "owner evidence receipt declared digest drift"
    assert (
        computed_digest == BRACE_EXPANSION_EVIDENCE_RECEIPT_SHA256
    ), "owner evidence receipt content digest drift"
    return receipt


def _replace_brace_expansion_evidence_receipt(
    document: str,
    receipt: dict[str, object],
) -> tuple[str, str]:
    """Render a mutated receipt for fail-closed regression tests."""

    assert document.count(BRACE_EXPANSION_EVIDENCE_RECEIPT_BEGIN) == 1
    assert document.count(BRACE_EXPANSION_EVIDENCE_RECEIPT_END) == 1
    prefix, remainder = document.split(BRACE_EXPANSION_EVIDENCE_RECEIPT_BEGIN, maxsplit=1)
    _, suffix = remainder.split(BRACE_EXPANSION_EVIDENCE_RECEIPT_END, maxsplit=1)
    payload = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
    updated = (
        prefix
        + BRACE_EXPANSION_EVIDENCE_RECEIPT_BEGIN
        + f"\n```json\n{payload}\n```\n"
        + BRACE_EXPANSION_EVIDENCE_RECEIPT_END
        + suffix
    )
    digest_matches = re.findall(
        r"Canonical normalized receipt SHA-256: `([0-9a-f]{64})`",
        updated,
    )
    assert len(digest_matches) == 1
    new_digest = hashlib.sha256(_canonicalize_brace_expansion_receipt(receipt)).hexdigest()
    return updated.replace(digest_matches[0], new_digest, 1), new_digest


def _parse_brace_expansion_evidence_receipt(
    document: str,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    receipt = _extract_brace_expansion_evidence_receipt(document)
    _require_exact_object(
        receipt,
        keys=frozenset({"schema", "advisory_database", "npm_audit"}),
        label="owner evidence receipt",
    )
    assert receipt["schema"] == BRACE_EXPANSION_EVIDENCE_RECEIPT_SCHEMA

    database = _require_exact_object(
        receipt["advisory_database"],
        keys=frozenset(
            {
                "accept",
                "cutoff",
                "next_page",
                "query",
                "record_count",
                "records",
            }
        ),
        label="owner evidence advisory_database",
    )
    assert database["accept"] == "application/vnd.github+json"
    assert database["cutoff"] == BRACE_EXPANSION_GAD_CUTOFF
    assert database["next_page"] is None
    assert database["query"] == (
        "GET /advisories?ecosystem=npm&affects=brace-expansion&per_page=100"
    )
    assert type(database["record_count"]) is int
    assert database["record_count"] == 6
    records = database["records"]
    assert isinstance(records, list)
    assert len(records) == database["record_count"]

    record_map: dict[str, dict[str, object]] = {}
    record_ids: list[str] = []
    timestamp_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
    for index, raw_record in enumerate(records):
        record = _require_exact_object(
            raw_record,
            keys=frozenset(
                {
                    "cve_id",
                    "ghsa_id",
                    "html_url",
                    "published_at",
                    "ranges",
                    "severity",
                    "summary",
                    "updated_at",
                }
            ),
            label=f"owner evidence advisory_database.records[{index}]",
        )
        ghsa_id = record["ghsa_id"]
        cve_id = record["cve_id"]
        published_at = record["published_at"]
        updated_at = record["updated_at"]
        assert isinstance(ghsa_id, str) and re.fullmatch(r"GHSA-[a-z0-9-]+", ghsa_id)
        assert isinstance(cve_id, str) and re.fullmatch(r"CVE-\d{4}-\d+", cve_id)
        assert record["html_url"] == f"https://github.com/advisories/{ghsa_id}"
        assert isinstance(published_at, str) and re.fullmatch(timestamp_pattern, published_at)
        assert isinstance(updated_at, str) and re.fullmatch(timestamp_pattern, updated_at)
        assert published_at <= updated_at <= BRACE_EXPANSION_GAD_CUTOFF
        assert record["severity"] in {"low", "medium", "high", "critical"}
        assert isinstance(record["summary"], str) and record["summary"].strip()
        ranges = record["ranges"]
        assert isinstance(ranges, list) and ranges
        assert all(isinstance(value, str) for value in ranges)
        assert ranges == sorted(set(ranges)), f"{ghsa_id}: receipt ranges must be unique and sorted"
        normalized_ranges = tuple(sorted(_normalize_advisory_range_text(value) for value in ranges))
        assert len(normalized_ranges) == len(set(normalized_ranges))
        assert ghsa_id not in record_map, f"{ghsa_id}: duplicate receipt advisory"
        record_ids.append(ghsa_id)
        record_map[ghsa_id] = {**record, "normalized_ranges": normalized_ranges}

    assert record_ids == sorted(BRACE_EXPANSION_CUTOFF_ADVISORIES)
    receipt_ranges = {
        advisory: record["normalized_ranges"] for advisory, record in record_map.items()
    }
    expected_ranges = {
        advisory: tuple(sorted(ranges))
        for advisory, ranges in BRACE_EXPANSION_ADVISORY_RANGE_TEXT.items()
    }
    assert receipt_ranges == expected_ranges, "receipt advisory range inventory drift"

    audit = _require_exact_object(
        receipt["npm_audit"],
        keys=frozenset(
            {
                "base",
                "command",
                "head",
                "node",
                "npm",
                "overall_audit_clean",
                "registry",
            }
        ),
        label="owner evidence npm_audit",
    )
    assert audit["command"] == "npm audit --package-lock-only --json"
    assert audit["node"] == "v24.16.0"
    assert audit["npm"] == "11.13.0"
    assert audit["registry"] == "https://registry.npmjs.org/"
    assert audit["overall_audit_clean"] is False
    for snapshot_name, expected in BRACE_EXPANSION_AUDIT_EXPECTATIONS.items():
        snapshot = _require_exact_object(
            audit[snapshot_name],
            keys=frozenset(
                {
                    "brace_expansion_advisory_ids",
                    "brace_expansion_present",
                    "exit_code",
                    "total",
                    "vulnerability_keys",
                }
            ),
            label=f"owner evidence npm_audit.{snapshot_name}",
        )
        advisory_ids = snapshot["brace_expansion_advisory_ids"]
        vulnerability_keys = snapshot["vulnerability_keys"]
        assert isinstance(advisory_ids, list)
        assert advisory_ids == sorted(set(advisory_ids))
        assert tuple(advisory_ids) == expected["brace_expansion_advisory_ids"]
        assert type(snapshot["brace_expansion_present"]) is bool
        assert snapshot["brace_expansion_present"] is expected["brace_expansion_present"]
        assert type(snapshot["exit_code"]) is int
        assert snapshot["exit_code"] == expected["exit_code"]
        assert type(snapshot["total"]) is int
        assert snapshot["total"] == expected["total"]
        assert isinstance(vulnerability_keys, list)
        assert vulnerability_keys == sorted(set(vulnerability_keys))
        assert tuple(vulnerability_keys) == expected["vulnerability_keys"]
        assert snapshot["total"] == len(vulnerability_keys)
        assert snapshot["brace_expansion_present"] is ("brace-expansion" in vulnerability_keys)
    return record_map, audit


def _assert_brace_expansion_owner_evidence(
    document: str,
    *,
    head_artifact_blobs: dict[str, bytes],
) -> None:
    """Bind the executable cutoff inventory to its sole current evidence owner."""

    receipt_records, audit = _parse_brace_expansion_evidence_receipt(document)
    inventory_marker = "That finite reconciled response is `F_cutoff`:"
    applicable_marker = "The exact non-empty applicable subset"
    assert document.count(inventory_marker) == 1, "owner evidence F_cutoff marker drift"
    assert document.count(applicable_marker) == 1, "owner evidence A marker drift"
    inventory = document.split(inventory_marker, maxsplit=1)[1].split(
        applicable_marker,
        maxsplit=1,
    )[0]
    inventory_lines = inventory.strip().splitlines()
    expected_header = (
        "| Advisory | Affected ranges relevant to the database record | "
        "Base disposition | Universal head evidence |"
    )
    expected_separator = "| --- | --- | --- | --- |"
    assert (
        len(inventory_lines) == len(BRACE_EXPANSION_CUTOFF_ADVISORIES) + 2
    ), "owner evidence F_cutoff table cardinality drift"
    assert inventory_lines[0] == expected_header, "owner evidence F_cutoff header drift"
    assert inventory_lines[1] == expected_separator, "owner evidence F_cutoff separator drift"
    row_pattern = re.compile(
        r"^\| \[`(?P<advisory>GHSA-[a-z0-9-]+)`\]\((?P<href>[^)\n]+)\)"
        r" / `(?P<cve>CVE-\d{4}-\d+)` \| (?P<ranges>[^|]+) \|"
        r" (?P<disposition>[^|]+) \| (?P<head_evidence>[^|]+) \|$"
    )
    table_rows: list[tuple[str, str, str, str, str, str]] = []
    for index, rendered_row in enumerate(inventory_lines[2:], start=1):
        row_match = row_pattern.fullmatch(rendered_row)
        assert row_match is not None, f"owner evidence F_cutoff row {index} parse drift"
        table_rows.append(
            (
                row_match.group("advisory"),
                row_match.group("href"),
                row_match.group("cve"),
                row_match.group("ranges"),
                row_match.group("disposition").strip(),
                row_match.group("head_evidence").strip(),
            )
        )
    advisory_rows = [advisory for advisory, *_ in table_rows]
    assert len(advisory_rows) == len(set(advisory_rows)), "duplicate F_cutoff advisory row"
    assert (
        frozenset(advisory_rows) == BRACE_EXPANSION_CUTOFF_ADVISORIES
    ), "owner evidence F_cutoff inventory does not match the executable inventory"
    assert (
        frozenset(BRACE_EXPANSION_RENDERED_PROJECTIONS) == BRACE_EXPANSION_CUTOFF_ADVISORIES
    ), "owner evidence rendered projection inventory drift"
    parsed_ranges: dict[str, tuple[str, ...]] = {}
    parsed_applicable: set[str] = set()
    for advisory, href, cve, range_cell, disposition, head_evidence in table_rows:
        receipt_record = receipt_records[advisory]
        assert href == receipt_record["html_url"], f"{advisory}: owner evidence href drift"
        assert cve == receipt_record["cve_id"], f"{advisory}: owner evidence CVE drift"
        parsed_ranges[advisory] = tuple(
            sorted(
                _normalize_advisory_range_text(item.strip().strip("`"))
                for item in range_cell.split(";")
            )
        )
        assert (
            disposition,
            head_evidence,
        ) == BRACE_EXPANSION_RENDERED_PROJECTIONS[
            advisory
        ], f"{advisory}: owner evidence rendered projection drift"
        if advisory in BRACE_EXPANSION_APPLICABLE_ADVISORIES:
            parsed_applicable.add(advisory)
    assert parsed_ranges == {
        advisory: tuple(sorted(ranges))
        for advisory, ranges in BRACE_EXPANSION_ADVISORY_RANGE_TEXT.items()
    }, "owner evidence affected ranges do not match the executable inventory"
    assert parsed_ranges == {
        advisory: record["normalized_ranges"] for advisory, record in receipt_records.items()
    }, "owner evidence table ranges do not match the retained receipt"
    assert (
        frozenset(parsed_applicable) == BRACE_EXPANSION_APPLICABLE_ADVISORIES
    ), "owner evidence table applicability does not match the executable subset"

    applicable_section = document.split(applicable_marker, maxsplit=1)[1]
    assert applicable_section.count("A = {") == 1, "owner evidence A block count drift"
    applicable_blocks = re.findall(
        r"```text\nA = \{\n(?P<body>.*?)\n\}\n```",
        applicable_section,
        flags=re.DOTALL,
    )
    assert len(applicable_blocks) == 1, "owner evidence A block missing or malformed"
    applicable_lines = applicable_blocks[0].splitlines()
    assert applicable_lines, "owner evidence A block must not be empty"
    applicable_rows: list[str] = []
    for index, line in enumerate(applicable_lines):
        suffix = "," if index < len(applicable_lines) - 1 else ""
        row_match = re.fullmatch(rf"  (GHSA-[a-z0-9-]+){re.escape(suffix)}", line)
        assert row_match is not None, f"owner evidence A row {index + 1} parse drift"
        applicable_rows.append(row_match.group(1))
    assert len(applicable_rows) == len(set(applicable_rows)), "duplicate owner evidence A row"
    assert (
        frozenset(applicable_rows) == BRACE_EXPANSION_APPLICABLE_ADVISORIES
    ), "owner evidence A block does not match the executable subset"

    normalized = re.sub(r"\s+", " ", document).strip()
    canonical_negative_audit_claim = (
        "That bounded absence is not an overall audit PASS and does not claim zero "
        "vulnerabilities."
    )
    contradictory_positive_audit_claim = "Overall audit PASS: zero vulnerabilities."
    assert (
        normalized.count(canonical_negative_audit_claim) == 1
    ), "owner evidence canonical negative audit claim drift"
    assert (
        contradictory_positive_audit_claim not in normalized
    ), "owner evidence contradictory positive audit claim"
    assert "GET /advisories?ecosystem=npm&affects=brace-expansion&per_page=100" in document
    assert f"Cutoff: `{BRACE_EXPANSION_GAD_CUTOFF}`" in document
    assert "response contained exactly six records and no next page" in normalized
    assert "Node: v24.16.0" in document
    assert "npm: 11.13.0" in document
    assert "command: npm install --package-lock-only --ignore-scripts" in document

    base_audit = audit["base"]
    head_audit = audit["head"]
    assert isinstance(base_audit, dict) and isinstance(head_audit, dict)
    base_advisories = base_audit["brace_expansion_advisory_ids"]
    assert isinstance(base_advisories, list) and len(base_advisories) == 2
    audit_marker = "As secondary reconciliation evidence, exact-base"
    audit_end_marker = "## Operator intent `I_R` and deterministic closure `C_R`"
    assert document.count(audit_marker) == 1
    assert document.count(audit_end_marker) == 1
    audit_section = (
        audit_marker
        + document.split(audit_marker, maxsplit=1)[1].split(
            audit_end_marker,
            maxsplit=1,
        )[0]
    )
    expected_audit_section = (
        "As secondary reconciliation evidence, exact-base "
        f"`{audit['command']}` exited `{base_audit['exit_code']}`, reported "
        f"`{base_audit['total']}` total findings, and reported `brace-expansion` through "
        f"`{base_advisories[0]}` and `{base_advisories[1]}`. The proposed-head command also "
        f"exited `{head_audit['exit_code']}`, reported `{head_audit['total']}` unrelated "
        "findings, and returned no `brace-expansion` vulnerability key. "
        f"{canonical_negative_audit_claim}"
    )
    assert (
        re.sub(r"\s+", " ", audit_section).strip() == expected_audit_section
    ), "owner evidence audit projection does not match the retained receipt"
    assert set(head_artifact_blobs) == set(BRACE_EXPANSION_EXACT_HEAD_DIGESTS)
    for relative, expected_digest in BRACE_EXPANSION_EXACT_HEAD_DIGESTS.items():
        assert expected_digest in document, f"{relative}: head artifact digest missing from owner"
        assert (
            hashlib.sha256(head_artifact_blobs[relative]).hexdigest() == expected_digest
        ), f"{relative}: head artifact raw-byte digest drift"


def _changed_json_paths(
    base: object,
    head: object,
    *,
    path: tuple[str, ...] = (),
) -> set[tuple[str, ...]]:
    """Return every changed JSON path without limiting comparison to the target package."""

    if type(base) is not type(head):
        return {path}
    if isinstance(base, dict) and isinstance(head, dict):
        changed: set[tuple[str, ...]] = set()
        for key in set(base) | set(head):
            child_path = (*path, str(key))
            if key not in base or key not in head:
                changed.add(child_path)
                continue
            changed.update(_changed_json_paths(base[key], head[key], path=child_path))
        return changed
    if isinstance(base, list) and isinstance(head, list):
        changed = set()
        for index in range(max(len(base), len(head))):
            child_path = (*path, f"[{index}]")
            if index >= len(base) or index >= len(head):
                changed.add(child_path)
                continue
            changed.update(_changed_json_paths(base[index], head[index], path=child_path))
        return changed
    return {path} if base != head else set()


def _assert_exact_brace_expansion_json_delta(
    *,
    base_package: dict,
    head_package: dict,
    base_lock: dict,
    head_lock: dict,
) -> None:
    manifest_paths = _changed_json_paths(base_package, head_package)
    lock_paths = _changed_json_paths(base_lock, head_lock)
    assert manifest_paths == BRACE_EXPANSION_MANIFEST_INTENT_PATHS, (
        "frontend/package.json: complete JSON delta must be exactly the two I_R paths; "
        f"found {sorted(manifest_paths)!r}"
    )
    assert lock_paths == BRACE_EXPANSION_LOCK_CLOSURE_PATHS, (
        "frontend/package-lock.json: complete JSON delta must be exactly the seven C_R paths; "
        f"found {sorted(lock_paths)!r}"
    )


def _is_governed_npm_surface(relative: PurePosixPath) -> bool:
    return (
        relative.name in NPM_SURFACE_BASENAMES
        and not set(relative.parts) & IGNORED_NPM_SURFACE_PARTS
    )


def _enumerate_repo_npm_surfaces(*, root: Path = REPO_ROOT) -> frozenset[str]:
    surfaces: set[str] = set()
    for basename in NPM_SURFACE_BASENAMES:
        for path in root.rglob(basename):
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if _is_governed_npm_surface(relative):
                surfaces.add(relative.as_posix())
    return frozenset(surfaces)


def _enumerate_repo_npm_surfaces_at_git_ref(ref: str) -> frozenset[str]:
    tracked_paths = _git_stdout("ls-tree", "-r", "--name-only", ref).decode("utf-8")
    return frozenset(
        relative.as_posix()
        for raw_path in tracked_paths.splitlines()
        if _is_governed_npm_surface(relative := PurePosixPath(raw_path))
    )


def _discover_brace_expansion_surface_occurrences(
    *,
    relative: str,
    document: dict,
) -> tuple[dict[tuple[str, ...], object], dict[str, dict]]:
    basename = PurePosixPath(relative).name
    if basename == "package.json":
        return _find_override_key_paths(document, target="brace-expansion"), {}
    assert (
        basename in NPM_LOCK_SURFACE_BASENAMES
    ), f"{relative}: unsupported npm surface basename reached occurrence discovery"
    return {}, _discover_brace_expansion_lock_entries(document.get("packages"))


def _assert_brace_expansion_security_class(
    *,
    package_json: dict,
    package_lock: dict,
) -> None:
    """Validate every 2.x/5.x output variant of one brace-expansion class."""

    overrides = package_json.get("overrides")
    assert isinstance(overrides, dict), "frontend/package.json: overrides must be an object"
    assert (
        "brace-expansion" not in overrides
    ), "frontend/package.json: blanket brace-expansion override is forbidden"

    expected_override_outputs = {
        (carrier, "brace-expansion"): BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items()
    }
    discovered_override_outputs = _find_override_key_paths(
        overrides,
        target="brace-expansion",
    )
    assert (
        discovered_override_outputs == expected_override_outputs
    ), "frontend/package.json: brace-expansion override target/output set is not approved"

    for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items():
        exact_output = discovered_override_outputs[(carrier, "brace-expansion")]
        parsed_output = _parse_version(
            value=exact_output,
            source=f"frontend/package.json: overrides.{carrier}.brace-expansion",
        )
        assert parsed_output.major == major, f"{carrier}: brace-expansion major mismatch"
        assert (
            parsed_output >= BRACE_EXPANSION_VARIANT_FLOORS[major]
        ), f"{carrier}: brace-expansion below secure floor"
        assert (
            exact_output == BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        ), f"{carrier}: brace-expansion manifest output is not approved"

    packages = package_lock.get("packages")
    discovered_entries = _discover_brace_expansion_lock_entries(packages)
    entries: list[tuple[str, dict, Version]] = []
    for raw_path, package in discovered_entries.items():
        parsed_version = _parse_version(value=package.get("version"), source=raw_path)
        resolved = package.get("resolved")
        expected_resolved = (
            "https://registry.npmjs.org/brace-expansion/-/" f"brace-expansion-{parsed_version}.tgz"
        )
        assert resolved == expected_resolved, f"{raw_path}: brace-expansion provenance mismatch"
        integrity = package.get("integrity")
        assert isinstance(integrity, str) and integrity.strip(), f"{raw_path}: integrity missing"
        entries.append((raw_path, package, parsed_version))

    assert entries, "frontend/package-lock.json: brace-expansion package entries missing"
    found_majors = {version.major for _, _, version in entries}
    assert found_majors == set(
        BRACE_EXPANSION_VARIANT_FLOORS
    ), "frontend/package-lock.json: brace-expansion major set must be exactly {2, 5}"

    for path, package, parsed_version in entries:
        major = parsed_version.major
        assert (
            parsed_version >= BRACE_EXPANSION_VARIANT_FLOORS[major]
        ), f"{path}: brace-expansion below secure floor"
        raw_version = package["version"]
        assert (
            raw_version == BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        ), f"{path}: brace-expansion lock output is not approved"


def _brace_entry(version: str) -> dict[str, str]:
    return {
        "version": version,
        "resolved": (
            "https://registry.npmjs.org/brace-expansion/-/" f"brace-expansion-{version}.tgz"
        ),
        "integrity": "sha512-fixture",
    }


def _brace_expansion_guard_fixture() -> tuple[dict, dict]:
    return (
        {
            "overrides": {
                "minimatch@3": {"brace-expansion": "2.1.3"},
                "minimatch@10": {"brace-expansion": "5.0.8"},
            }
        },
        {
            "packages": {
                "node_modules/brace-expansion": _brace_entry("2.1.3"),
                "node_modules/glob/node_modules/brace-expansion": _brace_entry("5.0.8"),
            }
        },
    )


def test_frontend_brace_expansion_class_covers_all_lock_variants() -> None:
    """All current 2.x/5.x carrier outputs share one invariant."""

    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    _assert_brace_expansion_security_class(
        package_json=package_json,
        package_lock=package_lock,
    )


def test_frontend_brace_expansion_class_reconciles_surfaces_and_transitions() -> None:
    """Derive A, partition I_R/C_R, and enforce P over all cutoff candidates."""

    base_package, base_lock = _load_exact_base_frontend_documents()
    head_package = _load_json(FRONTEND_PACKAGE_JSON)
    head_lock = _load_json(FRONTEND_LOCK_JSON)
    _assert_exact_brace_expansion_json_delta(
        base_package=base_package,
        head_package=head_package,
        base_lock=base_lock,
        head_lock=head_lock,
    )

    base_overrides = _find_override_key_paths(base_package["overrides"], target="brace-expansion")
    head_overrides = _find_override_key_paths(head_package["overrides"], target="brace-expansion")
    raw_base_entries = _discover_brace_expansion_lock_entries(base_lock["packages"])
    raw_head_entries = _discover_brace_expansion_lock_entries(head_lock["packages"])
    base_entries = _normalize_brace_expansion_lock_entries(raw_base_entries)
    head_entries = _normalize_brace_expansion_lock_entries(raw_head_entries)

    base_surfaces = {
        "frontend/package.json": base_overrides,
        "frontend/package-lock.json": base_entries,
    }
    head_surfaces = {
        "frontend/package.json": head_overrides,
        "frontend/package-lock.json": head_entries,
    }
    assert all(base_surfaces.values()) and all(head_surfaces.values())
    assert set(base_surfaces) == set(head_surfaces), "brace-expansion surface delta"

    expected_base_overrides = {
        (carrier, "brace-expansion"): BRACE_EXPANSION_BASE_OUTPUTS[major]
        for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items()
    }
    expected_head_overrides = {
        (carrier, "brace-expansion"): BRACE_EXPANSION_APPROVED_OUTPUTS[major]
        for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items()
    }
    assert base_overrides == expected_base_overrides
    assert head_overrides == expected_head_overrides
    assert base_entries == BRACE_EXPANSION_LOCK_SNAPSHOTS["base"]
    assert head_entries == BRACE_EXPANSION_LOCK_SNAPSHOTS["head"]

    base_versions = {
        _parse_version(value=entry["version"], source=path) for path, entry in base_entries.items()
    }
    head_versions = {
        _parse_version(value=entry["version"], source=path) for path, entry in head_entries.items()
    }
    applicable = _derive_applicable_advisories(base_versions)
    assert applicable == BRACE_EXPANSION_APPLICABLE_ADVISORIES
    non_applicable = set(BRACE_EXPANSION_ADVISORY_RANGES) - set(applicable)
    assert non_applicable
    for advisory in non_applicable:
        assert all(
            not _version_is_affected(version=version, advisory=advisory)
            for version in base_versions
        ), f"{advisory}: non-applicable-at-base disposition is false"
    _assert_brace_expansion_head_postcondition(head_versions)

    intent_transitions = {
        (path, base_overrides[path], head_overrides[path]) for path in base_overrides
    }
    expected_intent_transitions = {
        (
            (BRACE_EXPANSION_OVERRIDE_CARRIERS[major], "brace-expansion"),
            BRACE_EXPANSION_BASE_OUTPUTS[major],
            BRACE_EXPANSION_APPROVED_OUTPUTS[major],
        )
        for major in BRACE_EXPANSION_OVERRIDE_CARRIERS
    }
    assert intent_transitions == expected_intent_transitions
    assert all(base != head for _, base, head in intent_transitions)


def test_brace_expansion_is_absent_from_other_repo_npm_surfaces() -> None:
    """The frontend class must not silently absorb another repository npm graph."""

    base_surfaces = _enumerate_repo_npm_surfaces_at_git_ref(BRACE_EXPANSION_EXACT_BASE)
    head_surfaces = _enumerate_repo_npm_surfaces()
    assert base_surfaces == EXPECTED_REPO_NPM_SURFACES
    assert head_surfaces == EXPECTED_REPO_NPM_SURFACES

    frontend_surfaces = {"frontend/package.json", "frontend/package-lock.json"}
    for snapshot, surfaces in (("base", base_surfaces), ("head", head_surfaces)):
        discovered_surfaces: set[str] = set()
        for relative in surfaces:
            if snapshot == "base":
                document, _ = _load_json_at_git_ref(
                    ref=BRACE_EXPANSION_EXACT_BASE,
                    relative=relative,
                )
            else:
                document = _load_json(REPO_ROOT / relative)
            manifest_occurrences, lock_entries = _discover_brace_expansion_surface_occurrences(
                relative=relative,
                document=document,
            )
            if manifest_occurrences or lock_entries:
                discovered_surfaces.add(relative)
            if relative not in frontend_surfaces:
                assert not manifest_occurrences, (
                    f"{snapshot}:{relative}: brace-expansion manifest/override occurrence "
                    "belongs to a separate surface/class"
                )
                assert not lock_entries, (
                    f"{snapshot}:{relative}: brace-expansion lock occurrence belongs to a "
                    "separate surface/class"
                )
        assert discovered_surfaces == frontend_surfaces


def test_npm_surface_discovery_catches_lockfile_v3_and_shrinkwrap(tmp_path: Path) -> None:
    """Both npm lock basenames must expose lockfile-v3 package occurrences."""

    relative_surfaces = {
        "graph/package-lock.json",
        "graph/npm-shrinkwrap.json",
    }
    document = {
        "lockfileVersion": 3,
        "packages": {"node_modules/brace-expansion": _brace_entry("2.1.3")},
    }
    for relative in relative_surfaces:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")

    assert _enumerate_repo_npm_surfaces(root=tmp_path) == relative_surfaces
    for relative in relative_surfaces:
        manifest_occurrences, lock_entries = _discover_brace_expansion_surface_occurrences(
            relative=relative,
            document=_load_json(tmp_path / relative),
        )
        assert manifest_occurrences == {}
        assert set(lock_entries) == {"node_modules/brace-expansion"}


@pytest.mark.parametrize("basename", sorted(NPM_LOCK_SURFACE_BASENAMES))
def test_lock_surface_dependency_edges_are_not_installed_occurrences(basename: str) -> None:
    """Resolver edges in lock documents are not manifest or installed occurrences."""

    manifest_occurrences, lock_entries = _discover_brace_expansion_surface_occurrences(
        relative=f"graph/{basename}",
        document={
            "lockfileVersion": 3,
            "packages": {"": {"dependencies": {"brace-expansion": "^2.0.1"}}},
        },
    )

    assert manifest_occurrences == {}
    assert lock_entries == {}


@pytest.mark.parametrize(
    "alias",
    (
        "npm:brace-expansion",
        "npm:brace-expansion@",
        "npm:brace-expansion@2.1.3",
    ),
)
def test_override_discovery_catches_bounded_npm_alias_values(alias: str) -> None:
    """Lockless manifests cannot hide the target behind an npm alias value."""

    document = {"overrides": {"future-carrier": {"renamed-package": alias}}}
    assert _find_override_key_paths(document, target="brace-expansion") == {
        ("overrides", "future-carrier", "renamed-package"): alias
    }


@pytest.mark.parametrize(
    "non_alias",
    (
        "brace-expansion@2.1.3",
        "npm:brace-expansions@2.1.3",
        "https://registry.npmjs.org/brace-expansion",
        2,
    ),
)
def test_override_discovery_does_not_generalize_beyond_npm_alias_values(non_alias: object) -> None:
    """The class models npm alias syntax, not arbitrary value heuristics."""

    assert not _find_override_key_paths(
        {"overrides": {"future-carrier": {"renamed-package": non_alias}}},
        target="brace-expansion",
    )


@pytest.mark.parametrize(
    "case",
    (
        "manifest-add",
        "manifest-remove",
        "manifest-change",
        "lock-add",
        "lock-remove",
        "lock-change",
        "lock-type-change",
    ),
)
def test_brace_expansion_exact_partition_rejects_unrelated_json_delta(case: str) -> None:
    """Any unrelated add, removal, or change must remain outside I_R/C_R."""

    base_package, base_lock = _load_exact_base_frontend_documents()
    head_package = deepcopy(_load_json(FRONTEND_PACKAGE_JSON))
    head_lock = deepcopy(_load_json(FRONTEND_LOCK_JSON))

    if case == "manifest-add":
        head_package["scripts"]["unrelated-guard-delta"] = "true"
    elif case == "manifest-remove":
        del head_package["scripts"]["test"]
    elif case == "manifest-change":
        head_package["name"] = "unrelated-guard-delta"
    elif case == "lock-add":
        head_lock["packages"][""]["unrelated-guard-delta"] = True
    elif case == "lock-remove":
        del head_lock["packages"][""]["name"]
    elif case == "lock-change":
        head_lock["lockfileVersion"] = 2
    elif case == "lock-type-change":
        head_lock["packages"]["node_modules/@adobe/css-tools"]["dev"] = 1
    else:
        raise AssertionError(f"unhandled unrelated delta case: {case}")

    expected_message = "two I_R paths" if case.startswith("manifest-") else "seven C_R paths"
    with pytest.raises(AssertionError, match=expected_message):
        _assert_exact_brace_expansion_json_delta(
            base_package=base_package,
            head_package=head_package,
            base_lock=base_lock,
            head_lock=head_lock,
        )


@pytest.mark.parametrize(
    ("base", "head"),
    (
        (True, 1),
        (False, 0),
        (1, 1.0),
    ),
)
def test_changed_json_paths_is_json_type_sensitive(base: object, head: object) -> None:
    """Python scalar equality must not hide a changed JSON representation class."""

    assert _changed_json_paths(base, head) == {()}


def test_brace_expansion_owner_evidence_binds_cutoff_and_replay() -> None:
    """The sole owner must carry the exact finite inventory and replay evidence."""

    _assert_brace_expansion_owner_evidence(
        BRACE_EXPANSION_EVIDENCE_PATH.read_text(encoding="utf-8"),
        head_artifact_blobs={
            relative: (REPO_ROOT / relative).read_bytes()
            for relative in BRACE_EXPANSION_EXACT_HEAD_DIGESTS
        },
    )


@pytest.mark.parametrize(
    "case",
    (
        "nested-duplicate-receipt-key",
        "malformed-extra-fcutoff-row",
        "second-applicable-block",
        "global-positive-audit-claim",
        "contradictory-head-evidence",
        "contradictory-disposition-suffix",
    ),
)
def test_brace_expansion_owner_evidence_rejects_ambiguous_carriers(case: str) -> None:
    """Every rendered security carrier must be unique and exhaustively parsed."""

    document = BRACE_EXPANSION_EVIDENCE_PATH.read_text(encoding="utf-8")
    if case == "nested-duplicate-receipt-key":
        document = document.replace(
            '    "node": "v24.16.0",',
            '    "node": "v0.0.0",\n    "node": "v24.16.0",',
            1,
        )
    elif case == "malformed-extra-fcutoff-row":
        marker = "\n\nThe exact non-empty applicable subset"
        extra = (
            "\n| Supplemental advisory note | no affected range | "
            "Non-applicable | not canonical evidence |"
        )
        document = document.replace(marker, f"{extra}{marker}", 1)
    elif case == "second-applicable-block":
        marker = "```\n\nOnly these two candidates"
        duplicate = (
            "```\n\n```text\nA = {\n  GHSA-f886-m6hf-6m8v\n}\n```" "\n\nOnly these two candidates"
        )
        document = document.replace(marker, duplicate, 1)
    elif case == "global-positive-audit-claim":
        document += "\nOverall audit PASS: zero vulnerabilities.\n"
    elif case == "contradictory-head-evidence":
        canonical = BRACE_EXPANSION_RENDERED_PROJECTIONS["GHSA-3jxr-9vmj-r5cp"][1]
        document = document.replace(
            canonical,
            "`2.1.3` and `5.0.8` remain affected and unsafe",
            1,
        )
    elif case == "contradictory-disposition-suffix":
        canonical = BRACE_EXPANSION_RENDERED_PROJECTIONS["GHSA-3jxr-9vmj-r5cp"][0]
        document = document.replace(
            canonical,
            "**Applicable**: neither `2.0.3` nor `5.0.6` is affected",
            1,
        )
    else:
        raise AssertionError(f"unhandled ambiguous carrier case: {case}")

    with pytest.raises(AssertionError):
        _assert_brace_expansion_owner_evidence(
            document,
            head_artifact_blobs={
                relative: (REPO_ROOT / relative).read_bytes()
                for relative in BRACE_EXPANSION_EXACT_HEAD_DIGESTS
            },
        )


@pytest.mark.parametrize(
    "case",
    (
        "missing-row",
        "extra-row",
        "receipt-digest",
        "advisory-href",
        "advisory-cve",
        "audit-projection",
        "applicable-id",
        "affected-range",
        "applicable-disposition",
        "head-package-bytes",
        "head-lock-bytes",
    ),
)
def test_brace_expansion_owner_evidence_fails_closed_on_inventory_drift(case: str) -> None:
    """A changed finite inventory or captured response identity must fail closed."""

    document = BRACE_EXPANSION_EVIDENCE_PATH.read_text(encoding="utf-8")
    head_artifact_blobs = {
        relative: (REPO_ROOT / relative).read_bytes()
        for relative in BRACE_EXPANSION_EXACT_HEAD_DIGESTS
    }
    if case == "missing-row":
        document = "\n".join(
            line for line in document.splitlines() if "GHSA-832h-xg76-4gv6" not in line
        )
    elif case == "extra-row":
        marker = "\n\nThe exact non-empty applicable subset"
        extra = (
            "\n| [`GHSA-0000-0000-0000`](https://github.com/advisories/"
            "GHSA-0000-0000-0000) | `<0` | Non-applicable | No governed occurrence |"
        )
        document = document.replace(marker, f"{extra}{marker}", 1)
    elif case == "receipt-digest":
        document = document.replace(BRACE_EXPANSION_EVIDENCE_RECEIPT_SHA256, "0" * 64, 1)
    elif case == "advisory-href":
        document = document.replace(
            "[`GHSA-3jxr-9vmj-r5cp`](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp)",
            "[`GHSA-3jxr-9vmj-r5cp`](https://example.invalid/GHSA-3jxr-9vmj-r5cp)",
            1,
        )
    elif case == "advisory-cve":
        document = document.replace(
            ") / `CVE-2026-13149` |",
            ") / `CVE-2026-99999` |",
            1,
        )
    elif case == "audit-projection":
        document = document.replace(
            "is not an overall audit PASS",
            "is an overall audit PASS",
            1,
        )
    elif case == "applicable-id":
        document = document.replace(
            "  GHSA-mh99-v99m-4gvg\n}",
            "  GHSA-f886-m6hf-6m8v\n}",
            1,
        )
    elif case == "affected-range":
        document = document.replace("`<1.1.7` | Non-applicable:", "`<1.1.8` | Non-applicable:", 1)
    elif case == "applicable-disposition":
        document = document.replace("| **Applicable**:", "| Non-applicable:", 1)
    elif case == "head-package-bytes":
        head_artifact_blobs["frontend/package.json"] += b"\n"
    elif case == "head-lock-bytes":
        head_artifact_blobs["frontend/package-lock.json"] += b"\n"
    else:
        raise AssertionError(f"unhandled owner evidence mutation: {case}")

    with pytest.raises(AssertionError):
        _assert_brace_expansion_owner_evidence(
            document,
            head_artifact_blobs=head_artifact_blobs,
        )


@pytest.mark.parametrize(
    "case",
    (
        "audit-exit-code-type",
        "audit-total-type",
        "audit-conclusion",
        "coordinated-omission",
    ),
)
def test_brace_expansion_owner_evidence_rejects_rehashed_semantic_drift(
    case: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new digest cannot bless a false receipt class or coordinated omission."""

    document = BRACE_EXPANSION_EVIDENCE_PATH.read_text(encoding="utf-8")
    receipt = deepcopy(_extract_brace_expansion_evidence_receipt(document))
    database = receipt["advisory_database"]
    audit = receipt["npm_audit"]
    assert isinstance(database, dict) and isinstance(audit, dict)
    base_audit = audit["base"]
    head_audit = audit["head"]
    assert isinstance(base_audit, dict) and isinstance(head_audit, dict)

    if case == "audit-exit-code-type":
        base_audit["exit_code"] = True
    elif case == "audit-total-type":
        head_audit["total"] = 9.0
    elif case == "audit-conclusion":
        audit["overall_audit_clean"] = True
    elif case == "coordinated-omission":
        omitted = "GHSA-832h-xg76-4gv6"
        records = database["records"]
        assert isinstance(records, list)
        database["records"] = [record for record in records if record["ghsa_id"] != omitted]
        database["record_count"] = 5
        document = "\n".join(line for line in document.splitlines() if omitted not in line)
        monkeypatch.setitem(
            globals(),
            "BRACE_EXPANSION_CUTOFF_ADVISORIES",
            BRACE_EXPANSION_CUTOFF_ADVISORIES - {omitted},
        )
        monkeypatch.setitem(
            globals(),
            "BRACE_EXPANSION_ADVISORY_RANGE_TEXT",
            {
                advisory: ranges
                for advisory, ranges in BRACE_EXPANSION_ADVISORY_RANGE_TEXT.items()
                if advisory != omitted
            },
        )
        monkeypatch.setitem(
            globals(),
            "BRACE_EXPANSION_ADVISORY_RANGES",
            {
                advisory: ranges
                for advisory, ranges in BRACE_EXPANSION_ADVISORY_RANGES.items()
                if advisory != omitted
            },
        )
    else:
        raise AssertionError(f"unhandled rehashed receipt mutation: {case}")

    document, new_digest = _replace_brace_expansion_evidence_receipt(document, receipt)
    monkeypatch.setitem(globals(), "BRACE_EXPANSION_EVIDENCE_RECEIPT_SHA256", new_digest)
    with pytest.raises(AssertionError):
        _assert_brace_expansion_owner_evidence(
            document,
            head_artifact_blobs={
                relative: (REPO_ROOT / relative).read_bytes()
                for relative in BRACE_EXPANSION_EXACT_HEAD_DIGESTS
            },
        )


def test_brace_expansion_postcondition_includes_base_non_applicable_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate outside A still blocks an affected governed head occurrence."""

    monkeypatch.setitem(
        BRACE_EXPANSION_ADVISORY_RANGES,
        "GHSA-f886-m6hf-6m8v",
        (SpecifierSet("==2.1.3"),),
    )
    with pytest.raises(AssertionError, match="GHSA-f886-m6hf-6m8v"):
        _assert_brace_expansion_head_postcondition({Version("2.1.3"), Version("5.0.8")})


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("below-floor", "below secure floor"),
        ("safe-nonexact", "lock output is not approved"),
        ("coordinated-safe-2", "override target/output set is not approved"),
        ("coordinated-safe-5", "override target/output set is not approved"),
        ("extra-override-carrier", "override target/output set is not approved"),
        ("missing-major", "major set must be exactly"),
        ("unexpected-major", "major set must be exactly"),
        ("schema", "packages must be an object"),
        ("path", "lock path must be relative"),
        ("traversal", "traversal segments"),
        ("name-alias", "alias/noncanonical installed path"),
        ("url-alias", "alias/noncanonical installed path"),
        ("schemeless-host-alias", "alias/noncanonical installed path"),
        ("scheme-backslash-alias", "alias/noncanonical installed path"),
        ("percent-encoded-path-alias", "alias/noncanonical installed path"),
        ("double-encoded-path-alias", "alias/noncanonical installed path"),
        ("dot-segment-path-alias", "alias/noncanonical installed path"),
        ("backslash-path-alias", "alias/noncanonical installed path"),
        ("query-alias", "alias/noncanonical installed path"),
        ("fragment-alias", "alias/noncanonical installed path"),
        ("params-alias", "alias/noncanonical installed path"),
        ("foreign-host-alias", "alias/noncanonical installed path"),
        ("http-alias", "alias/noncanonical installed path"),
        ("userinfo-alias", "alias/noncanonical installed path"),
        ("contradictory-name", "package name conflicts"),
        ("version", "malformed version"),
        ("provenance", "provenance mismatch"),
        ("integrity", "integrity missing"),
        ("manifest-lock", "override target/output set is not approved"),
        ("blanket", "blanket brace-expansion override is forbidden"),
        ("selector-override", "override target/output set is not approved"),
        ("empty-selector-override", "override target/output set is not approved"),
        ("alias-value", "override target/output set is not approved"),
    ),
)
def test_frontend_brace_expansion_class_fails_closed(case: str, message: str) -> None:
    """Falsify the class invariant rather than enumerating carrier names."""

    package_json, package_lock = _brace_expansion_guard_fixture()
    packages = package_lock["packages"]
    root = packages["node_modules/brace-expansion"]
    if case == "below-floor":
        packages["node_modules/future-carrier/node_modules/brace-expansion"] = _brace_entry("2.0.3")
    elif case == "safe-nonexact":
        root.update(_brace_entry("2.1.4"))
    elif case == "coordinated-safe-2":
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.4"
        root.update(_brace_entry("2.1.4"))
    elif case == "coordinated-safe-5":
        package_json["overrides"]["minimatch@10"]["brace-expansion"] = "5.0.9"
        packages["node_modules/glob/node_modules/brace-expansion"].update(_brace_entry("5.0.9"))
    elif case == "extra-override-carrier":
        package_json["overrides"]["future-carrier"] = {"nested": {"brace-expansion": "2.1.3"}}
    elif case == "missing-major":
        del packages["node_modules/glob/node_modules/brace-expansion"]
    elif case == "unexpected-major":
        packages["node_modules/other/node_modules/brace-expansion"] = _brace_entry("6.0.0")
    elif case == "schema":
        package_lock["packages"] = []
    elif case == "path":
        packages["/node_modules/brace-expansion"] = packages.pop("node_modules/brace-expansion")
    elif case == "traversal":
        packages["../node_modules/brace-expansion"] = packages.pop("node_modules/brace-expansion")
    elif case == "name-alias":
        packages["node_modules/brace-alias"] = {
            **_brace_entry("2.1.3"),
            "name": "brace-expansion",
            "resolved": "https://example.invalid/brace-expansion-2.1.3.tgz",
        }
    elif case == "url-alias":
        packages["node_modules/url-alias"] = _brace_entry("2.1.3")
    elif case == "schemeless-host-alias":
        alias = _brace_entry("2.0.3")
        alias["resolved"] = "registry.npmjs.org/brace-expansion/-/brace-expansion-2.0.3.tgz"
        packages["node_modules/schemeless-host-alias"] = alias
    elif case == "scheme-backslash-alias":
        alias = _brace_entry("2.0.3")
        alias["resolved"] = (
            "https:\\registry.npmjs.org\\brace-expansion\\-\\brace-expansion-2.0.3.tgz"
        )
        packages["node_modules/scheme-backslash-alias"] = alias
    elif case == "percent-encoded-path-alias":
        alias = _brace_entry("2.0.3")
        alias["resolved"] = (
            "https://registry.npmjs.org/%62race-expansion/-/" "brace-expansion-2.0.3.tgz"
        )
        packages["node_modules/percent-encoded-path-alias"] = alias
    elif case == "double-encoded-path-alias":
        alias = _brace_entry("2.0.3")
        alias["resolved"] = (
            "https://registry.npmjs.org/%2562race-expansion/-/" "brace-expansion-2.0.3.tgz"
        )
        packages["node_modules/double-encoded-path-alias"] = alias
    elif case == "dot-segment-path-alias":
        alias = _brace_entry("2.0.3")
        alias["resolved"] = (
            "https://registry.npmjs.org/other/../brace-expansion/-/" "brace-expansion-2.0.3.tgz"
        )
        packages["node_modules/dot-segment-path-alias"] = alias
    elif case == "backslash-path-alias":
        alias = _brace_entry("2.0.3")
        alias["resolved"] = (
            "https://registry.npmjs.org/other%5c..%5cbrace-expansion/-/" "brace-expansion-2.0.3.tgz"
        )
        packages["node_modules/backslash-path-alias"] = alias
    elif case in {
        "query-alias",
        "fragment-alias",
        "params-alias",
        "foreign-host-alias",
        "http-alias",
        "userinfo-alias",
    }:
        alias = _brace_entry("2.1.3")
        canonical = alias["resolved"]
        if case == "query-alias":
            alias["resolved"] = f"{canonical}?download=1"
        elif case == "fragment-alias":
            alias["resolved"] = f"{canonical}#fragment"
        elif case == "params-alias":
            alias["resolved"] = canonical.replace(".tgz", ".tgz;download")
        elif case == "foreign-host-alias":
            alias["resolved"] = canonical.replace(NPM_REGISTRY_HOST, "example.invalid")
        elif case == "http-alias":
            alias["resolved"] = canonical.replace("https://", "http://")
        else:
            alias["resolved"] = canonical.replace("https://", "https://user@")
        packages[f"node_modules/{case}"] = alias
    elif case == "contradictory-name":
        root["name"] = "not-brace-expansion"
    elif case == "version":
        root["version"] = "invalid"
    elif case == "provenance":
        root["resolved"] = "https://example.invalid/brace-expansion-2.1.3.tgz"
    elif case == "integrity":
        root["integrity"] = ""
    elif case == "manifest-lock":
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.4"
    elif case == "blanket":
        package_json["overrides"]["brace-expansion"] = "5.0.8"
    elif case == "selector-override":
        package_json["overrides"]["brace-expansion@<2.1.3"] = "2.1.3"
    elif case == "empty-selector-override":
        package_json["overrides"]["brace-expansion@"] = "2.1.3"
    elif case == "alias-value":
        package_json["overrides"]["future-carrier"] = {
            "renamed-package": "npm:brace-expansion@2.1.3"
        }
    else:
        raise AssertionError(f"unhandled brace-expansion falsification case: {case}")

    with pytest.raises(AssertionError, match=message):
        _assert_brace_expansion_security_class(
            package_json=package_json,
            package_lock=package_lock,
        )


def test_frontend_package_has_dompurify_override_floor() -> None:
    """RU/EN: package.json override must keep dompurify at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    dompurify_override = overrides.get("dompurify")
    assert isinstance(dompurify_override, str), "frontend/package.json: overrides.dompurify missing"
    assert Version(dompurify_override) >= MIN_DOMPURIFY_VERSION


def test_frontend_package_has_js_yaml_override_floor() -> None:
    """RU/EN: package.json override must keep js-yaml at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    js_yaml_override = overrides.get("js-yaml")
    assert isinstance(js_yaml_override, str), "frontend/package.json: overrides.js-yaml missing"
    assert Version(js_yaml_override) >= MIN_JS_YAML_VERSION


def test_frontend_package_has_undici_override_floor() -> None:
    """RU/EN: package.json override must keep undici at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    undici_override = overrides.get("undici")
    assert isinstance(undici_override, str), "frontend/package.json: overrides.undici missing"
    assert Version(undici_override) >= MIN_UNDICI_VERSION


def test_frontend_package_has_ws_override_floor() -> None:
    """RU/EN: package.json override must keep ws at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    ws_override = overrides.get("ws")
    assert isinstance(ws_override, str), "frontend/package.json: overrides.ws missing"
    assert Version(ws_override) >= MIN_WS_VERSION


def test_frontend_lock_resolves_dompurify_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve dompurify from npm registry."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    dompurify_pkg = package_lock.get("packages", {}).get("node_modules/dompurify", {})
    lock_version = dompurify_pkg.get("version")
    resolved = dompurify_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: dompurify version missing"
    assert Version(lock_version) >= MIN_DOMPURIFY_VERSION
    _assert_npm_registry_resolution(package_name="dompurify", resolved=resolved)


def test_frontend_lock_resolves_undici_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve undici from npm registry."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    undici_pkg = package_lock.get("packages", {}).get("node_modules/undici", {})
    lock_version = undici_pkg.get("version")
    resolved = undici_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: undici version missing"
    assert Version(lock_version) >= MIN_UNDICI_VERSION
    _assert_npm_registry_resolution(package_name="undici", resolved=resolved)


def test_frontend_lock_resolves_ws_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve ws from npm registry."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    ws_pkg = package_lock.get("packages", {}).get("node_modules/ws", {})
    lock_version = ws_pkg.get("version")
    resolved = ws_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: ws version missing"
    assert Version(lock_version) >= MIN_WS_VERSION
    _assert_npm_registry_resolution(package_name="ws", resolved=resolved)


def test_frontend_lock_resolves_all_js_yaml_entries_to_safe_npm_release() -> None:
    """RU/EN: every js-yaml package entry must use the secure npm release."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    packages = package_lock.get("packages", {})
    js_yaml_entries = {
        path: package
        for path, package in packages.items()
        if path == "node_modules/js-yaml" or path.endswith("/node_modules/js-yaml")
    }

    assert js_yaml_entries, "frontend/package-lock.json: js-yaml package entries missing"
    for path, package in js_yaml_entries.items():
        lock_version = package.get("version")
        resolved = package.get("resolved", "")
        assert isinstance(lock_version, str), f"{path}: js-yaml version missing"
        assert Version(lock_version) >= MIN_JS_YAML_VERSION, f"{path}: js-yaml below secure floor"
        _assert_npm_registry_resolution(package_name="js-yaml", resolved=resolved)
