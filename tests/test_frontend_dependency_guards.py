"""Deterministic frontend dependency security guards.

RU: Проверяем frontend security overrides.
EN: Ensure frontend security overrides are pinned to safe npm releases.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version
from tests.test_root_npm_dependency_guards import (
    _assert_lock_surface_canonical_provenance,
    _find_lock_occurrences,
    _find_manifest_occurrences,
    _find_opaque_npm_dependency_source_occurrences,
    _lock_path_package_identity,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
FRONTEND_LOCK_JSON = REPO_ROOT / "frontend" / "package-lock.json"
BRACE_EXPANSION_EVIDENCE_PATH = (
    REPO_ROOT / "docs" / "security" / "FRONTEND_BRACE_EXPANSION_REMEDIATION_CLASS.md"
)
BROWSERSLIST_EVIDENCE_PATH = (
    REPO_ROOT / "docs" / "security" / "FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md"
)
NPM_REGISTRY_HOST = "registry.npmjs.org"
NPM_SEMVER_MAX_LENGTH = 256
NPM_SEMVER_MAX_SAFE_INTEGER = 9_007_199_254_740_991
EXACT_NPM_SEMVER_RE = re.compile(
    r"(?P<core>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))"
    r"(?P<prerelease>-(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
MIN_DOMPURIFY_VERSION = Version("3.4.13")
MIN_JS_YAML_VERSION = Version("4.3.1")
MIN_POSTCSS_VERSION = Version("8.5.23")
MIN_STYLE_DICTIONARY_VERSION = Version("5.4.4")
MIN_UNDICI_VERSION = Version("7.29.0")
MIN_WS_VERSION = Version("8.21.0")
BRACE_EXPANSION_APPROVED_OUTPUTS = {2: "2.1.4", 5: "5.0.9"}
BRACE_EXPANSION_OVERRIDE_CARRIERS = {
    2: "minimatch@3",
    5: "minimatch@10",
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
BRACE_EXPANSION_CURRENT_ADVISORY_RANGE_TEXT = {
    **BRACE_EXPANSION_ADVISORY_RANGE_TEXT,
    "GHSA-rgw5-rvv9-x895": (
        "<1.1.18",
        ">=2.0.0,<2.1.4",
        ">=3.0.0,<3.0.6",
        ">=4.0.0,<5.0.9",
    ),
}
BRACE_EXPANSION_CURRENT_ADVISORY_RANGES = {
    advisory: tuple(SpecifierSet(value) for value in ranges)
    for advisory, ranges in BRACE_EXPANSION_CURRENT_ADVISORY_RANGE_TEXT.items()
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
BRACE_EXPANSION_CURRENT_ADVISORIES = frozenset(BRACE_EXPANSION_CURRENT_ADVISORY_RANGES)
BRACE_EXPANSION_APPLICABLE_ADVISORIES = frozenset({"GHSA-3jxr-9vmj-r5cp", "GHSA-mh99-v99m-4gvg"})
BROWSERSLIST_ADVISORY_RANGE_TEXT = {
    "GHSA-73wf-gq98-2v4g": ("<=4.28.6",),
    "GHSA-c83g-rgw3-j3cx": ("<=4.28.6",),
    "GHSA-w8qv-6jwh-64r5": (">=4.0.0,<4.16.5",),
}
BROWSERSLIST_EXPECTED_ADVISORIES = frozenset(BROWSERSLIST_ADVISORY_RANGE_TEXT)
BROWSERSLIST_EXPECTED_APPLICABLE_ADVISORIES = frozenset(
    {"GHSA-73wf-gq98-2v4g", "GHSA-c83g-rgw3-j3cx"}
)
BROWSERSLIST_ADVISORY_RANGES = {
    advisory: tuple(SpecifierSet(value) for value in ranges)
    for advisory, ranges in BROWSERSLIST_ADVISORY_RANGE_TEXT.items()
}
BROWSERSLIST_FIRST_PATCHED_VERSIONS = {
    "GHSA-73wf-gq98-2v4g": "4.28.7",
    "GHSA-c83g-rgw3-j3cx": "4.28.7",
    "GHSA-w8qv-6jwh-64r5": "4.16.5",
}
BROWSERSLIST_ADVISORY_BOUNDARY_CASES = (
    ("GHSA-73wf-gq98-2v4g", "<=4.28.6", "4.28.6", "4.28.7"),
    ("GHSA-c83g-rgw3-j3cx", "<=4.28.6", "4.28.6", "4.28.7"),
    ("GHSA-w8qv-6jwh-64r5", ">=4.0.0,<4.16.5", "4.16.4", "4.16.5"),
)
BROWSERSLIST_BASE_VERSION = Version("4.28.2")
TRANSITIVE_NPM_GAD_CUTOFF = "2026-09-03T03:39:19Z"
TRANSITIVE_NPM_GAD_QUERIES = {
    "browserslist": "GET /advisories?ecosystem=npm&affects=browserslist&per_page=100",
    "qs": "GET /advisories?ecosystem=npm&affects=qs&per_page=100",
}
TRANSITIVE_NPM_BATCH_RECEIPT_SCHEMA = "pulseplate.frontend-npm-security-batch-gad-receipt/v1"
TRANSITIVE_NPM_BATCH_RECEIPT_SHA256 = (
    "ad87c0e16f1cf4cc3ab847175fc3d5d6865b941b9b7540816b4dec0711367d8f"  # pragma: allowlist secret
)
TRANSITIVE_NPM_SCANNER_SNAPSHOT_SHA256 = (
    "c3aec6d46c57b693d2a9860838921fd51a16644dd76f32507a2aa3d8852419d4"  # pragma: allowlist secret
)
TRANSITIVE_NPM_BATCH_BASE_SHA = (
    "2bfb7ff96dfcc98a806de9c113eff5242bfbe479"  # pragma: allowlist secret
)
QS_ADVISORY_ENTRIES = {
    "GHSA-4mjr-xmp4-gh2g": ((">=2.2.5,<6.16.0", "6.16.0"),),
    "GHSA-6rw7-vpxm-498p": (("<6.14.1", "6.14.1"),),
    "GHSA-crvj-3gj9-gm2p": (("<1.0.0", "1.0.0"),),
    "GHSA-f9cm-p3w6-xvr3": (("<1.0.0", "1.0.0"),),
    "GHSA-gqgv-6jq5-jjj9": (
        ("<6.0.4", "6.0.4"),
        (">=6.1.0,<6.1.2", "6.1.2"),
        (">=6.2.0,<6.2.3", "6.2.3"),
        (">=6.3.0,<6.3.2", "6.3.2"),
    ),
    "GHSA-hrpp-h998-j3pp": (
        (">=6.10.0,<6.10.3", "6.10.3"),
        (">=6.9.0,<6.9.7", "6.9.7"),
        (">=6.8.0,<6.8.3", "6.8.3"),
        (">=6.7.0,<6.7.3", "6.7.3"),
        (">=6.6.0,<6.6.1", "6.6.1"),
        (">=6.5.0,<6.5.3", "6.5.3"),
        (">=6.4.0,<6.4.1", "6.4.1"),
        (">=6.3.0,<6.3.3", "6.3.3"),
        ("<6.2.4", "6.2.4"),
    ),
    "GHSA-jjv7-qpx3-h62q": (("<1.0.0", "1.0.0"),),
    "GHSA-q8mj-m7cp-5q26": ((">=6.11.1,<=6.15.1", "6.15.2"),),
    "GHSA-w7fw-mjwx-w883": ((">=6.7.0,<=6.14.1", "6.14.2"),),
    "GHSA-x5fp-wj9c-mxmx": ((">=6.14.2,<=6.15.3", "6.16.0"),),
}
QS_ADVISORY_RANGE_TEXT = {
    advisory: tuple(raw_range for raw_range, _ in entries)
    for advisory, entries in QS_ADVISORY_ENTRIES.items()
}
QS_ADVISORY_RANGES = {
    advisory: tuple(SpecifierSet(raw_range) for raw_range in ranges)
    for advisory, ranges in QS_ADVISORY_RANGE_TEXT.items()
}
QS_EXPECTED_ADVISORIES = frozenset(QS_ADVISORY_ENTRIES)
QS_EXPECTED_APPLICABLE_ADVISORIES = frozenset({"GHSA-x5fp-wj9c-mxmx", "GHSA-4mjr-xmp4-gh2g"})
QS_EXPECTED_WITHDRAWN = {"GHSA-crvj-3gj9-gm2p": "2020-06-16T21:32:53Z"}
QS_ADVISORY_BOUNDARY_CASES = (
    ("GHSA-4mjr-xmp4-gh2g", ">=2.2.5,<6.16.0", "6.15.2", "6.16.0"),
    ("GHSA-6rw7-vpxm-498p", "<6.14.1", "6.14.0", "6.14.1"),
    ("GHSA-crvj-3gj9-gm2p", "<1.0.0", "0.9.9", "1.0.0"),
    ("GHSA-f9cm-p3w6-xvr3", "<1.0.0", "0.9.9", "1.0.0"),
    ("GHSA-gqgv-6jq5-jjj9", "<6.0.4", "6.0.3", "6.0.4"),
    ("GHSA-gqgv-6jq5-jjj9", ">=6.1.0,<6.1.2", "6.1.1", "6.1.2"),
    ("GHSA-gqgv-6jq5-jjj9", ">=6.2.0,<6.2.3", "6.2.2", "6.2.3"),
    ("GHSA-gqgv-6jq5-jjj9", ">=6.3.0,<6.3.2", "6.3.1", "6.3.2"),
    ("GHSA-hrpp-h998-j3pp", ">=6.10.0,<6.10.3", "6.10.2", "6.10.3"),
    ("GHSA-hrpp-h998-j3pp", ">=6.9.0,<6.9.7", "6.9.6", "6.9.7"),
    ("GHSA-hrpp-h998-j3pp", ">=6.8.0,<6.8.3", "6.8.2", "6.8.3"),
    ("GHSA-hrpp-h998-j3pp", ">=6.7.0,<6.7.3", "6.7.2", "6.7.3"),
    ("GHSA-hrpp-h998-j3pp", ">=6.6.0,<6.6.1", "6.6.0", "6.6.1"),
    ("GHSA-hrpp-h998-j3pp", ">=6.5.0,<6.5.3", "6.5.2", "6.5.3"),
    ("GHSA-hrpp-h998-j3pp", ">=6.4.0,<6.4.1", "6.4.0", "6.4.1"),
    ("GHSA-hrpp-h998-j3pp", ">=6.3.0,<6.3.3", "6.3.2", "6.3.3"),
    ("GHSA-hrpp-h998-j3pp", "<6.2.4", "6.2.3", "6.2.4"),
    ("GHSA-jjv7-qpx3-h62q", "<1.0.0", "0.9.9", "1.0.0"),
    ("GHSA-q8mj-m7cp-5q26", ">=6.11.1,<=6.15.1", "6.15.1", "6.15.2"),
    ("GHSA-w7fw-mjwx-w883", ">=6.7.0,<=6.14.1", "6.14.1", "6.14.2"),
    ("GHSA-x5fp-wj9c-mxmx", ">=6.14.2,<=6.15.3", "6.15.3", "6.16.0"),
)
AUTHORIZED_TRANSITIVE_NPM_BATCH = frozenset({"browserslist", "qs"})
TRANSITIVE_NPM_HEAD_POLICIES = {
    "browserslist": BROWSERSLIST_ADVISORY_RANGES,
    "qs": QS_ADVISORY_RANGES,
}
TRANSITIVE_NPM_EVIDENCE_EXPECTATIONS = {
    "browserslist": {
        "base_version": BROWSERSLIST_BASE_VERSION,
        "applicable_advisories": BROWSERSLIST_EXPECTED_APPLICABLE_ADVISORIES,
    },
    "qs": {
        "base_version": Version("6.15.2"),
        "applicable_advisories": QS_EXPECTED_APPLICABLE_ADVISORIES,
    },
}
NPM_VIRTUAL_GRAPH_POLICY_ARGS = (
    "--global=false",
    "--workspaces=false",
    "--link=false",
    "--include=dev",
    "--include=optional",
    "--include=peer",
    "--legacy-peer-deps=false",
    "--strict-peer-deps=true",
)
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
BRACE_EXPANSION_HEAD_EVIDENCE_SCHEMA = "pulseplate.frontend-brace-expansion-head-evidence/v1"
BRACE_EXPANSION_RECORDED_HEAD = "".join(
    ("050a9712", "54bce406", "151baeb1", "ae99b35a", "074370dc")
)
BRACE_EXPANSION_HEAD_EVIDENCE_SHA256 = (
    "b908bb307e4b19629c657e566f0a0ce2b7fc46ffbdf2e4f26c4b8c8a8e60b21e"  # pragma: allowlist secret
)
NPM_SURFACE_BASENAMES = frozenset({"package.json", "package-lock.json", "npm-shrinkwrap.json"})
NPM_LOCK_SURFACE_BASENAMES = frozenset({"package-lock.json", "npm-shrinkwrap.json"})
FRONTEND_BRACE_EXPANSION_SURFACES = frozenset(
    {"frontend/package.json", "frontend/package-lock.json"}
)
FRONTEND_SECURITY_TARGETS = {
    "dompurify": {
        "manifest_path": ("overrides", "dompurify"),
        "manifest_value": "3.4.13",
        "floor": str(MIN_DOMPURIFY_VERSION),
        "selected": "3.4.13",
        "advisories": {
            "GHSA-c2j3-45gr-mqc4": ("<=3.4.11",),
            "GHSA-55q2-fjhq-7xh7": ("<=3.4.12",),
        },
    },
    "js-yaml": {
        "manifest_path": ("overrides", "js-yaml"),
        "manifest_value": "4.3.1",
        "floor": str(MIN_JS_YAML_VERSION),
        "selected": "4.3.1",
        "advisories": {
            "GHSA-52cp-r559-cp3m": (">=3.0.0,<3.15.0", ">=4.0.0,<4.3.0"),
            "GHSA-5p4m-2wfm-xmqj": (">=3.0.0,<3.15.1", ">=4.0.0,<4.3.1"),
        },
    },
    "postcss": {
        "manifest_path": ("devDependencies", "postcss"),
        "manifest_value": "^8.5.26",
        "floor": str(MIN_POSTCSS_VERSION),
        "selected": "8.5.26",
        "advisories": {
            "GHSA-r28c-9q8g-f849": ("<=8.5.17",),
            "GHSA-fxqj-rqcc-2cmp": ("<=8.5.22",),
        },
    },
    "style-dictionary": {
        "manifest_path": ("devDependencies", "style-dictionary"),
        "manifest_value": "5.4.4",
        "floor": str(MIN_STYLE_DICTIONARY_VERSION),
        "selected": "5.4.4",
        "advisories": {
            "GHSA-vj5c-m527-mpff": (">=4.3.0,<5.4.4",),
        },
    },
    "undici": {
        "manifest_path": ("overrides", "undici"),
        "manifest_value": "7.29.0",
        "floor": str(MIN_UNDICI_VERSION),
        "selected": "7.29.0",
        "advisories": {
            "GHSA-8xcm-r25x-g524": ("<6.28.0", ">=7.0.0,<7.29.0", ">=8.0.0,<8.9.0"),
            "GHSA-4cwx-7wf7-3272": (">=7.0.0,<7.29.0", ">=8.0.0,<8.9.0"),
            "GHSA-jr45-8vmc-qm54": (">=7.0.0,<7.29.0", ">=8.0.0,<8.9.0"),
            "GHSA-v3r7-h72x-cjcm": ("<6.28.0", ">=7.0.0,<7.29.0", ">=8.0.0,<8.9.0"),
            "GHSA-m8rv-5g2x-5cg5": ("<6.28.0", ">=7.0.0,<7.29.0", ">=8.0.0,<8.9.0"),
        },
    },
}
FRONTEND_SECURITY_BOUNDARY_CASES = (
    ("dompurify-below", "dompurify", "3.4.12", False),
    ("dompurify-floor", "dompurify", "3.4.13", True),
    ("dompurify-selected", "dompurify", "3.4.13", True),
    ("js-yaml-below", "js-yaml", "4.3.0", False),
    ("js-yaml-floor", "js-yaml", "4.3.1", True),
    ("js-yaml-selected", "js-yaml", "4.3.1", True),
    ("postcss-below", "postcss", "8.5.22", False),
    ("postcss-floor", "postcss", "8.5.23", True),
    ("postcss-selected", "postcss", "8.5.26", True),
    ("style-dictionary-below", "style-dictionary", "5.4.3", False),
    ("style-dictionary-floor", "style-dictionary", "5.4.4", True),
    ("style-dictionary-selected", "style-dictionary", "5.4.4", True),
    ("undici-below", "undici", "7.28.0", False),
    ("undici-floor", "undici", "7.29.0", True),
    ("undici-selected", "undici", "7.29.0", True),
)


def _load_json(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), f"{path}: npm surface must be a JSON object"
    return document


def _git_stdout(*args: str, repo_root: Path = REPO_ROOT) -> bytes:
    git_binary = shutil.which("git")
    assert git_binary is not None, "git is required for tracked dependency guards"
    assert Path(git_binary).is_absolute(), "git binary must resolve to an absolute path"
    child_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(
        [git_binary, "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        env=child_env,
        timeout=30,
    )
    return result.stdout


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
    match = (
        EXACT_NPM_SEMVER_RE.fullmatch(value)
        if len(value) <= NPM_SEMVER_MAX_LENGTH and value.isascii()
        else None
    )
    prerelease = match.group("prerelease") if match is not None else None
    if match is None or (
        any(
            int(component) > NPM_SEMVER_MAX_SAFE_INTEGER
            for component in match.group("core").split(".")
        )
        or (
            prerelease is not None
            and any(
                len(identifier) > 1 and identifier.startswith("0") and identifier.isdigit()
                for identifier in prerelease[1:].split(".")
            )
        )
    ):
        raise AssertionError(f"{source}: malformed version {value!r}")
    assert prerelease is None, f"{source}: prerelease output is not approved"
    try:
        return Version(value)
    except InvalidVersion as exc:
        raise AssertionError(f"{source}: malformed version {value!r}") from exc


def _is_frontend_target_lock_path(path: object, *, target: str) -> bool:
    if not isinstance(path, str):
        return False
    normalized = path.replace("\\", "/")
    return PurePosixPath(normalized).parts[-2:] == (
        "node_modules",
        target,
    )


def _is_brace_expansion_lock_path(path: object) -> bool:
    return _is_frontend_target_lock_path(path, target="brace-expansion")


def _fully_decode_url_path(path: str) -> str:
    """Decode a URL path to a finite fixed point and normalize path separators."""

    decoded = path.replace("\\", "/")
    for _ in range(len(decoded) + 1):
        next_value = unquote(decoded).replace("\\", "/")
        if next_value == decoded:
            return decoded
        decoded = next_value
    raise AssertionError("URL path percent-decoding did not converge")


def _has_registry_tarball_path_signal(value: object, *, target: str) -> bool:
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
    package_basename = target.rsplit("/", maxsplit=1)[-1]
    tarball_path_signal = f"/{target}/-/{package_basename}-"
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
    if _is_npm_alias_for_target(node, target=target) or _has_registry_tarball_path_signal(
        node, target=target
    ):
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


def _discover_frontend_target_lock_entries(
    packages: object,
    *,
    target: str,
) -> dict[str, dict]:
    """Enumerate one target through the existing path/name/tarball signals."""

    assert isinstance(packages, dict), "frontend/package-lock.json: packages must be an object"
    entries: dict[str, dict] = {}
    for raw_path, package in packages.items():
        canonical_path_signal = _is_frontend_target_lock_path(raw_path, target=target)
        name_signal = isinstance(package, dict) and package.get("name") == target
        url_signal = isinstance(package, dict) and _has_registry_tarball_path_signal(
            package.get("resolved"), target=target
        )
        if not (canonical_path_signal or name_signal or url_signal):
            continue
        assert isinstance(raw_path, str)
        assert canonical_path_signal, f"{raw_path}: {target} alias/noncanonical installed path"
        path = PurePosixPath(raw_path)
        assert "\\" not in raw_path, f"{raw_path}: lock path must use POSIX separators"
        assert not path.is_absolute(), f"{raw_path}: lock path must be relative"
        assert ".." not in path.parts, f"{raw_path}: lock path must not contain traversal segments"
        assert path.as_posix() == raw_path, f"{raw_path}: lock path must be canonical"
        assert path.parts[-2:] == (
            "node_modules",
            target,
        ), f"{raw_path}: malformed {target} lock path"
        assert isinstance(package, dict), f"{raw_path}: package entry must be an object"
        if "name" in package:
            assert (
                package["name"] == target
            ), f"{raw_path}: package name conflicts with {target} path"
        entries[raw_path] = package
    return entries


def _discover_brace_expansion_lock_entries(packages: object) -> dict[str, dict]:
    """Enumerate the finite lockfile candidate universe independently of validity."""

    return _discover_frontend_target_lock_entries(packages, target="brace-expansion")


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


def _brace_expansion_head_evidence_projection(
    *,
    package_json: dict[str, object],
    package_lock: dict[str, object],
) -> dict[str, object]:
    """Project only the validated, bounded head evidence for this dependency class."""

    _assert_brace_expansion_security_class(
        package_json=package_json,
        package_lock=package_lock,
    )
    overrides = package_json.get("overrides")
    assert isinstance(overrides, dict), "frontend/package.json: overrides must be an object"
    manifest_occurrences = _find_override_key_paths(
        overrides,
        target="brace-expansion",
    )
    lock_occurrences = _normalize_brace_expansion_lock_entries(
        _discover_brace_expansion_lock_entries(package_lock.get("packages"))
    )
    return {
        "schema": BRACE_EXPANSION_HEAD_EVIDENCE_SCHEMA,
        "surfaces": {
            "frontend/package.json": {
                "manifest_occurrences": [
                    {"path": list(path), "output": output}
                    for path, output in sorted(manifest_occurrences.items())
                ]
            },
            "frontend/package-lock.json": {
                "lock_occurrences": lock_occurrences,
            },
        },
    }


def _brace_expansion_head_evidence_digest(
    *,
    package_json: dict[str, object],
    package_lock: dict[str, object],
) -> str:
    projection = _brace_expansion_head_evidence_projection(
        package_json=package_json,
        package_lock=package_lock,
    )
    canonical = json.dumps(
        projection,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _version_is_affected(*, version: Version, advisory: str) -> bool:
    ranges = BRACE_EXPANSION_CURRENT_ADVISORY_RANGES[advisory]
    return any(version in affected_range for affected_range in ranges)


def _assert_brace_expansion_head_postcondition(versions: set[Version]) -> None:
    assert set(BRACE_EXPANSION_CURRENT_ADVISORY_RANGES) == BRACE_EXPANSION_CURRENT_ADVISORIES
    for advisory in BRACE_EXPANSION_CURRENT_ADVISORIES:
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
    assert (
        type(database["record_count"]) is int
    ), "owner evidence advisory_database.record_count must be an integer"
    assert (
        database["record_count"] == 6
    ), "owner evidence advisory_database.record_count must be exactly 6"
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
    assert (
        audit["overall_audit_clean"] is False
    ), "owner evidence npm_audit.overall_audit_clean must remain false"
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
        assert (
            type(snapshot["exit_code"]) is int
        ), f"owner evidence npm_audit.{snapshot_name}.exit_code must be an integer"
        assert snapshot["exit_code"] == expected["exit_code"]
        assert (
            type(snapshot["total"]) is int
        ), f"owner evidence npm_audit.{snapshot_name}.total must be an integer"
        assert snapshot["total"] == expected["total"]
        assert isinstance(vulnerability_keys, list)
        assert vulnerability_keys == sorted(set(vulnerability_keys))
        assert tuple(vulnerability_keys) == expected["vulnerability_keys"]
        assert snapshot["total"] == len(vulnerability_keys)
        assert snapshot["brace_expansion_present"] is ("brace-expansion" in vulnerability_keys)
    return record_map, audit


def _assert_brace_expansion_owner_evidence(document: str) -> None:
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
    assert (
        normalized.count(
            f"The immutable remediation head is commit `{BRACE_EXPANSION_RECORDED_HEAD}`."
        )
        == 1
    ), "owner evidence immutable head identity drift"

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
    targeted_claim = (
        "This digest binds only the canonical bounded `brace-expansion` evidence projection; "
        "it is not a whole-file digest or a completeness claim for unrelated manifest/lock "
        "content."
    )
    provider_claim = (
        "This repository evidence receipt makes no provider review, scan, approval, PASS, or "
        "no-findings claim."
    )
    assert normalized.count(targeted_claim) == 1, "owner targeted-evidence claim drift"
    assert normalized.count(provider_claim) == 1, "owner provider-neutral claim drift"
    digest_matches = re.findall(
        r"Canonical targeted head evidence SHA-256:\s*`([0-9a-f]{64})`",
        document,
    )
    assert digest_matches == [
        BRACE_EXPANSION_HEAD_EVIDENCE_SHA256
    ], "owner targeted-evidence digest marker drift"


def _is_governed_npm_surface(relative: PurePosixPath) -> bool:
    return relative.name in NPM_SURFACE_BASENAMES


def _enumerate_repo_npm_surfaces(*, root: Path = REPO_ROOT) -> frozenset[str]:
    tracked_paths = _git_stdout("ls-files", "--cached", "-z", repo_root=root)
    surfaces: set[str] = set()
    for raw_path in tracked_paths.split(b"\0"):
        if not raw_path:
            continue
        relative_text = raw_path.decode("utf-8")
        relative = PurePosixPath(relative_text)
        if not _is_governed_npm_surface(relative):
            continue
        path = root / relative_text
        assert path.exists(), f"{relative_text}: tracked npm surface missing"
        assert (
            path.is_file() and not path.is_symlink()
        ), f"{relative_text}: tracked npm surface must be a regular non-symlink file"
        surfaces.add(relative.as_posix())
    return frozenset(surfaces)


def _discover_brace_expansion_surface_occurrences(
    *,
    relative: str,
    document: dict,
    surfaces: dict[str, dict],
) -> tuple[dict[tuple[str, ...], object], dict[str, dict]]:
    basename = PurePosixPath(relative).name
    if basename == "package.json":
        return (
            _find_manifest_target_paths(
                document,
                target="brace-expansion",
                surface=relative,
                surfaces=surfaces,
            ),
            {},
        )
    assert (
        basename in NPM_LOCK_SURFACE_BASENAMES
    ), f"{relative}: unsupported npm surface basename reached occurrence discovery"
    return {}, _discover_brace_expansion_lock_entries(document.get("packages"))


def _tracked_local_manifest_path(*, surface: str, value: object) -> str | None:
    """Resolve one repository-relative local dependency to its manifest key."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().replace("\\", "/")
    parsed = urlparse(normalized)
    if parsed.scheme:
        if parsed.scheme != "file" or parsed.netloc:
            return None
        local_path = parsed.path
    elif normalized.startswith(("./", "../")):
        local_path = parsed.path
    else:
        return None
    decoded_path = _fully_decode_url_path(local_path)
    if not decoded_path or decoded_path.startswith("/"):
        return None
    manifest_parent = PurePosixPath(surface).parent
    resolved = PurePosixPath(posixpath.normpath((manifest_parent / decoded_path).as_posix()))
    if resolved.is_absolute() or ".." in resolved.parts:
        return None
    return (resolved / "package.json").as_posix()


def _find_tracked_local_manifest_target_paths(
    *,
    surface: str,
    document: dict,
    surfaces: dict[str, dict],
    target: str,
) -> dict[tuple[str, ...], object]:
    """Find renamed local carriers whose exact tracked manifest owns the target."""
    found: dict[tuple[str, ...], object] = {}

    def record_if_target(path: tuple[str, ...], value: object) -> None:
        target_surface = _tracked_local_manifest_path(surface=surface, value=value)
        target_document = surfaces.get(target_surface) if target_surface is not None else None
        if isinstance(target_document, dict) and target_document.get("name") == target:
            found[path] = value

    for field in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    ):
        values = document.get(field)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            record_if_target((field, str(key)), value)

    def walk_overrides(value: object, path: tuple[str, ...]) -> None:
        if not isinstance(value, dict):
            return
        for key, child in value.items():
            child_path = (*path, str(key))
            record_if_target(child_path, child)
            walk_overrides(child, child_path)

    walk_overrides(document.get("overrides"), ("overrides",))
    return found


def _find_manifest_target_paths(
    document: dict,
    *,
    target: str,
    surface: str | None = None,
    surfaces: dict[str, dict] | None = None,
) -> dict[tuple[str, ...], object]:
    """Find direct, aliased, tarball, bundled, and override target carriers."""
    found: dict[tuple[str, ...], object] = {}
    for field in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    ):
        values = document.get(field)
        if not isinstance(values, dict):
            continue
        found.update(
            _find_override_key_paths(
                values,
                target=target,
                path=(field,),
            )
        )

    found.update(
        _find_override_key_paths(
            document.get("overrides"),
            target=target,
            path=("overrides",),
        )
    )
    for field in ("bundleDependencies", "bundledDependencies"):
        bundled = document.get(field)
        if not isinstance(bundled, list):
            continue
        for index, value in enumerate(bundled):
            if value == target:
                found[(field, f"[{index}]")] = value
    if surface is not None and surfaces is not None:
        found.update(
            _find_tracked_local_manifest_target_paths(
                surface=surface,
                document=document,
                surfaces=surfaces,
                target=target,
            )
        )
    return found


def _assert_brace_expansion_surface_ownership(
    *,
    root: Path = REPO_ROOT,
) -> frozenset[str]:
    """Reject target carriers outside the finite frontend owner surfaces."""
    discovered_surfaces: set[str] = set()
    surfaces = {
        relative: _load_json(root / relative)
        for relative in _enumerate_repo_npm_surfaces(root=root)
    }
    for relative, document in surfaces.items():
        manifest_occurrences, lock_entries = _discover_brace_expansion_surface_occurrences(
            relative=relative,
            document=document,
            surfaces=surfaces,
        )
        if manifest_occurrences or lock_entries:
            discovered_surfaces.add(relative)
        if relative in FRONTEND_BRACE_EXPANSION_SURFACES:
            continue
        assert not manifest_occurrences, (
            f"head:{relative}: brace-expansion manifest occurrence belongs to a "
            "separate surface/class"
        )
        assert not lock_entries, (
            f"head:{relative}: brace-expansion lock occurrence belongs to a separate "
            "surface/class"
        )
    return frozenset(discovered_surfaces)


def _assert_brace_expansion_security_class(
    *,
    package_json: dict,
    package_lock: dict,
    surface: str = "frontend/package.json",
    surfaces: dict[str, dict] | None = None,
) -> None:
    """Validate every current occurrence, while allowing executable absence."""

    if "overrides" in package_json:
        overrides = package_json["overrides"]
        assert isinstance(overrides, dict), "frontend/package.json: overrides must be an object"
    allowed_override_paths: dict[tuple[str, ...], int] = {
        ("overrides", carrier, "brace-expansion"): major
        for major, carrier in BRACE_EXPANSION_OVERRIDE_CARRIERS.items()
    }
    discovered_override_outputs = _find_manifest_target_paths(
        package_json,
        target="brace-expansion",
        surface=surface,
        surfaces=surfaces or {surface: package_json},
    )
    unexpected_override_paths = set(discovered_override_outputs) - set(allowed_override_paths)
    assert not unexpected_override_paths, (
        "frontend/package.json: brace-expansion manifest occurrence is not approved; "
        f"found {sorted(unexpected_override_paths)!r}"
    )

    manifest_versions: set[Version] = set()
    for path, exact_output in discovered_override_outputs.items():
        major = allowed_override_paths[path]
        parsed_output = _parse_version(
            value=exact_output,
            source=f"frontend/package.json: overrides.{'.'.join(path)}",
        )
        assert not parsed_output.is_prerelease, f"{path}: prerelease output is not approved"
        assert parsed_output.major == major, f"{path}: brace-expansion major mismatch"
        manifest_versions.add(parsed_output)

    packages = package_lock.get("packages")
    discovered_entries = _discover_brace_expansion_lock_entries(packages)
    lock_versions: set[Version] = set()
    for raw_path, package in discovered_entries.items():
        parsed_version = _parse_version(value=package.get("version"), source=raw_path)
        assert not parsed_version.is_prerelease, f"{raw_path}: prerelease output is not approved"
        resolved = package.get("resolved")
        raw_version = package.get("version")
        assert isinstance(raw_version, str)
        expected_resolved = (
            "https://registry.npmjs.org/brace-expansion/-/" f"brace-expansion-{raw_version}.tgz"
        )
        assert resolved == expected_resolved, f"{raw_path}: brace-expansion provenance mismatch"
        integrity = package.get("integrity")
        assert isinstance(integrity, str) and integrity.strip(), f"{raw_path}: integrity missing"
        lock_versions.add(parsed_version)

    missing_lock_outputs = manifest_versions - lock_versions
    assert not missing_lock_outputs, (
        "frontend manifest brace-expansion output does not match any installed lock occurrence; "
        f"missing {sorted(str(version) for version in missing_lock_outputs)!r}"
    )
    _assert_brace_expansion_head_postcondition(manifest_versions | lock_versions)


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
                "minimatch@3": {"brace-expansion": "2.1.4"},
                "minimatch@10": {"brace-expansion": "5.0.9"},
            }
        },
        {
            "packages": {
                "node_modules/brace-expansion": _brace_entry("2.1.4"),
                "node_modules/glob/node_modules/brace-expansion": _brace_entry("5.0.9"),
            }
        },
    )


def _assert_frontend_security_target_version(*, target: str, raw_version: object) -> Version:
    """Require one stable comparable version outside the target's full cutoff."""

    policy = FRONTEND_SECURITY_TARGETS[target]
    version = _parse_version(value=raw_version, source=f"{target} governed occurrence")
    floor = Version(policy["floor"])
    assert version >= floor, f"{target}: {version} is below security floor {floor}"
    advisories = policy["advisories"]
    assert isinstance(advisories, dict)
    for advisory, raw_ranges in advisories.items():
        assert isinstance(raw_ranges, tuple)
        affected_ranges = tuple(SpecifierSet(raw_range) for raw_range in raw_ranges)
        assert all(
            version not in affected_range for affected_range in affected_ranges
        ), f"{target}/{advisory}: governed occurrence remains affected"
    return version


def _assert_transitive_npm_head_postcondition(
    *, target: str, raw_version: object, source: str
) -> Version:
    """Require one stable target occurrence outside its frozen advisory inventory."""

    assert target in AUTHORIZED_TRANSITIVE_NPM_BATCH
    version = _parse_version(value=raw_version, source=source)
    for advisory, affected_ranges in TRANSITIVE_NPM_HEAD_POLICIES[target].items():
        assert all(
            version not in affected_range for affected_range in affected_ranges
        ), f"{target}/{advisory}: governed occurrence remains affected"
    return version


def _assert_sha512_integrity(*, value: object, source: str) -> None:
    """Require one syntactically valid 64-byte sha512 SRI digest."""

    assert isinstance(value, str) and value.startswith(
        "sha512-"
    ), f"{source}: integrity must use sha512 SRI"
    encoded = value.removeprefix("sha512-")
    try:
        digest = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AssertionError(f"{source}: integrity must contain valid base64") from exc
    assert len(digest) == 64, f"{source}: integrity sha512 digest must be 64 bytes"


def _assert_manifest_dependency_container_shapes(*, document: dict, surface: str) -> None:
    """Keep JSON structure local while npm owns dependency-source semantics."""

    for field in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
        "overrides",
    ):
        if field in document:
            assert isinstance(document[field], dict), f"{surface}:{field} must be an object"
    for field in ("bundleDependencies", "bundledDependencies"):
        if field not in document:
            continue
        bundled = document[field]
        if type(bundled) is bool:
            continue
        assert isinstance(bundled, list), f"{surface}:{field} must be an array"
        assert all(
            isinstance(value, str) and value for value in bundled
        ), f"{surface}:{field} entries must be non-empty package names"
    peer_metadata = document.get("peerDependenciesMeta", {})
    assert isinstance(peer_metadata, dict), f"{surface}: peerDependenciesMeta must be an object"
    for peer, metadata in peer_metadata.items():
        assert isinstance(peer, str) and peer, f"{surface}: peer metadata name must be text"
        assert isinstance(metadata, dict), f"{surface}:{peer}: peer metadata must be an object"
        assert set(metadata) <= {"optional"}, f"{surface}:{peer}: unknown peer metadata field"
        assert (
            type(metadata.get("optional", False)) is bool
        ), f"{surface}:{peer}: peer optional must be an exact boolean"


def _load_transitive_npm_surface(path: Path) -> dict:
    """Load raw npm JSON without allowing duplicate members to erase evidence."""

    document = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_brace_expansion_receipt_keys,
    )
    assert isinstance(document, dict), f"{path}: npm surface must be a JSON object"
    return document


def _npm_virtual_graph_environment() -> dict[str, str]:
    """Remove ambient Node/npm graph controls before the delegated invocation."""

    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
        and key not in {"NODE_ENV", "NODE_OPTIONS", "NODE_PATH"}
        and not key.casefold().startswith("npm_config_")
    }


def _assert_npm_virtual_lock_graphs(*, root: Path, surfaces: dict[str, dict]) -> None:
    """Delegate every lock-bearing project graph to the active repository npm."""

    wrapper = REPO_ROOT / "scripts" / "frontend_npm.sh"
    assert wrapper.is_file() and os.access(
        wrapper, os.X_OK
    ), "repository npm wrapper must be an executable file"
    lock_roots: dict[PurePosixPath, str] = {}
    dependency_roots: set[PurePosixPath] = set()
    for relative, document in surfaces.items():
        path = PurePosixPath(relative)
        if path.name == "package.json":
            if any(
                isinstance(document.get(field), dict) and bool(document[field])
                for field in (
                    "dependencies",
                    "devDependencies",
                    "optionalDependencies",
                    "peerDependencies",
                    "overrides",
                )
            ):
                dependency_roots.add(path.parent)
            continue
        if path.name not in NPM_LOCK_SURFACE_BASENAMES:
            continue
        project_relative = path.parent
        assert (
            project_relative not in lock_roots
        ), f"{relative}: multiple npm lock authorities share one project root"
        manifest_relative = (project_relative / "package.json").as_posix()
        assert (
            manifest_relative in surfaces
        ), f"{relative}: lock-bearing project must have a tracked package.json"
        lock_roots[project_relative] = relative

    missing_lock_roots = dependency_roots - set(lock_roots)
    assert not missing_lock_roots, (
        "dependency-bearing manifest must have one same-root lock authority; "
        f"missing {sorted(path.as_posix() for path in missing_lock_roots)!r}"
    )

    for project_relative, lock_surface in lock_roots.items():
        manifest_surface = (project_relative / "package.json").as_posix()
        manifest = surfaces[manifest_surface]
        lock = surfaces[lock_surface]
        packages = lock.get("packages")
        assert isinstance(packages, dict), f"{lock_surface}: packages must be an object"
        root_package = packages.get("")
        assert isinstance(
            root_package, dict
        ), f"{lock_surface}: packages must contain an object root entry"
        for field in (
            "dependencies",
            "devDependencies",
            "optionalDependencies",
            "peerDependencies",
            "peerDependenciesMeta",
        ):
            manifest_dependencies = manifest.get(field, {})
            lock_dependencies = root_package.get(field, {})
            assert isinstance(
                lock_dependencies, dict
            ), f"{lock_surface}: root {field} must be an object"
            assert manifest_dependencies == lock_dependencies, (
                f"{lock_surface}: root {field} must exactly match " f"{manifest_surface}"
            )

    npm_env = _npm_virtual_graph_environment()
    with tempfile.TemporaryDirectory(prefix="pulseplate-npm-config-") as config_directory:
        config_root = Path(config_directory)
        user_config = config_root / "user.npmrc"
        global_config = config_root / "global.npmrc"
        user_config.write_text("", encoding="utf-8")
        global_config.write_text("", encoding="utf-8")
        for project_relative, lock_surface in sorted(
            lock_roots.items(),
            key=lambda item: item[0].as_posix(),
        ):
            project_root = root.joinpath(*project_relative.parts)
            try:
                result = subprocess.run(
                    [
                        str(wrapper),
                        "--prefix",
                        str(project_root),
                        "ls",
                        "--all",
                        "--package-lock-only",
                        "--json",
                        "--userconfig",
                        str(user_config),
                        "--globalconfig",
                        str(global_config),
                        *NPM_VIRTUAL_GRAPH_POLICY_ARGS,
                    ],
                    check=False,
                    capture_output=True,
                    env=npm_env,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise AssertionError(f"{lock_surface}: npm virtual graph execution failed") from exc
            assert result.returncode == 0, f"{lock_surface}: npm virtual graph rejected"
            try:
                graph = json.loads(result.stdout.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise AssertionError(
                    f"{lock_surface}: npm virtual graph returned invalid JSON"
                ) from exc
            assert isinstance(graph, dict), f"{lock_surface}: npm virtual graph must be an object"
            assert (
                graph.get("error") is None
            ), f"{lock_surface}: npm virtual graph returned an error"
            assert (
                graph.get("problems", []) == []
            ), f"{lock_surface}: npm virtual graph has problems"


def _assert_transitive_npm_occurrence(
    *, target: str, surface: str, path: str, package: dict
) -> None:
    """Apply only target identity, advisory, provenance, and SRI policy."""

    source = f"{surface}:{path}"
    assert (
        _lock_path_package_identity(path) == target
    ), f"{source}: {target} alias/noncanonical installed path"
    assert "link" not in package, f"{source}: symbolic link lock occurrence is forbidden"
    in_bundle = package.get("inBundle", False)
    assert type(in_bundle) is bool, f"{source}: inBundle must be boolean when present"
    assert not in_bundle, f"{source}: bundled lock occurrence is forbidden"
    raw_version = package.get("version")
    _assert_transitive_npm_head_postcondition(
        target=target,
        raw_version=raw_version,
        source=source,
    )
    assert isinstance(raw_version, str)
    expected_resolved = f"https://registry.npmjs.org/{target}/-/{target}-{raw_version}.tgz"
    assert (
        package.get("resolved") == expected_resolved
    ), f"{source}: {target} canonical provenance mismatch"
    _assert_sha512_integrity(value=package.get("integrity"), source=source)


def _assert_transitive_npm_security_batch(*, root: Path = REPO_ROOT) -> dict[str, frozenset[str]]:
    """Enforce the exact authorized target batch after shared npm admission."""

    assert frozenset(TRANSITIVE_NPM_HEAD_POLICIES) == AUTHORIZED_TRANSITIVE_NPM_BATCH
    assert frozenset(TRANSITIVE_NPM_EVIDENCE_EXPECTATIONS) == AUTHORIZED_TRANSITIVE_NPM_BATCH
    surfaces = {
        relative: _load_transitive_npm_surface(root / relative)
        for relative in _enumerate_repo_npm_surfaces(root=root)
    }
    lock_occurrences: dict[str, dict[tuple[str, str], dict]] = {
        target: {} for target in AUTHORIZED_TRANSITIVE_NPM_BATCH
    }
    for relative, document in surfaces.items():
        basename = PurePosixPath(relative).name
        if basename == "package.json":
            _assert_manifest_dependency_container_shapes(document=document, surface=relative)
            for target in AUTHORIZED_TRANSITIVE_NPM_BATCH:
                target_occurrences = _find_manifest_occurrences(document, target=target)
                assert not target_occurrences, (
                    f"{relative}: direct {target} manifest authority is forbidden; "
                    f"found {target_occurrences!r}"
                )
            opaque_occurrences = _find_opaque_npm_dependency_source_occurrences(document)
            assert not opaque_occurrences, (
                f"{relative}: opaque dependency source blocks batch absence; "
                f"found {opaque_occurrences!r}"
            )
            continue

        assert basename in NPM_LOCK_SURFACE_BASENAMES
        assert (
            document.get("lockfileVersion") == 3
        ), f"{relative}: transitive batch supports only npm lockfileVersion 3"
        _assert_lock_surface_canonical_provenance(surface=relative, document=document)
        packages = document.get("packages")
        assert isinstance(packages, dict), f"{relative}: packages must be an object"
        for package_path, package in packages.items():
            assert isinstance(package_path, str), f"{relative}: package path must be text"
            assert isinstance(
                package, dict
            ), f"{relative}:{package_path}: package must be an object"
            _assert_manifest_dependency_container_shapes(
                document=package, surface=f"{relative}:{package_path}"
            )
            has_shrinkwrap = package.get("hasShrinkwrap", False)
            assert (
                type(has_shrinkwrap) is bool
            ), f"{relative}:{package_path}: hasShrinkwrap must be an exact boolean"
            assert (
                not has_shrinkwrap
            ), f"{relative}:{package_path}: published nested shrinkwrap blocks batch admission"
            for field in ("bundleDependencies", "bundledDependencies"):
                assert not package.get(field, []), (
                    f"{relative}:{package_path}: published bundled dependencies "
                    "block batch admission"
                )
            in_bundle = package.get("inBundle", False)
            assert (
                type(in_bundle) is bool
            ), f"{relative}:{package_path}: inBundle must be boolean when present"
            assert not in_bundle, f"{relative}:{package_path}: bundled lock occurrence is forbidden"
        for target in AUTHORIZED_TRANSITIVE_NPM_BATCH:
            for path, package in _find_lock_occurrences(
                document,
                target=target,
            ).items():
                _assert_transitive_npm_occurrence(
                    target=target,
                    surface=relative,
                    path=path,
                    package=package,
                )
                lock_occurrences[target][(relative, path)] = package

    _assert_npm_virtual_lock_graphs(root=root, surfaces=surfaces)
    return {
        target: frozenset(relative for relative, _ in target_occurrences)
        for target, target_occurrences in lock_occurrences.items()
    }


def _assert_browserslist_head_postcondition(*, raw_version: object, source: str) -> Version:
    """Compatibility wrapper for existing Browserslist boundary controls."""

    return _assert_transitive_npm_head_postcondition(
        target="browserslist",
        raw_version=raw_version,
        source=source,
    )


def _assert_browserslist_occurrence(*, surface: str, path: str, package: dict) -> None:
    """Compatibility wrapper for existing Browserslist occurrence controls."""

    _assert_transitive_npm_occurrence(
        target="browserslist",
        surface=surface,
        path=path,
        package=package,
    )


def _assert_browserslist_security_class(*, root: Path = REPO_ROOT) -> frozenset[str]:
    """Compatibility wrapper returning the Browserslist batch projection."""

    return _assert_transitive_npm_security_batch(root=root)["browserslist"]


def _extract_transitive_npm_batch_receipt(document: str) -> dict[str, object]:
    """Parse the retained batch receipt without accepting ambiguous JSON objects."""

    marker = "The retained normalized batch receipt is:\n\n```json\n"
    assert document.count(marker) == 1, "batch owner must retain exactly one GAD receipt"
    start = document.index(marker) + len(marker)
    end = document.index("\n```", start)
    receipt = json.loads(
        document[start:end],
        object_pairs_hook=_reject_duplicate_brace_expansion_receipt_keys,
    )
    assert isinstance(receipt, dict), "batch GAD receipt must be a JSON object"
    return receipt


def _assert_frontend_security_targets() -> None:
    """Validate the five non-brace targets across every tracked npm surface."""

    surfaces = {
        relative: _load_json(REPO_ROOT / relative) for relative in _enumerate_repo_npm_surfaces()
    }
    for target, policy in FRONTEND_SECURITY_TARGETS.items():
        manifest_occurrences: dict[tuple[str, ...], object] = {}
        lock_occurrences: dict[tuple[str, str], dict] = {}
        for relative, document in surfaces.items():
            basename = PurePosixPath(relative).name
            if basename == "package.json":
                for path, value in _find_manifest_target_paths(
                    document,
                    target=target,
                    surface=relative,
                    surfaces=surfaces,
                ).items():
                    manifest_occurrences[(relative, *path)] = value
                continue
            assert basename in NPM_LOCK_SURFACE_BASENAMES
            for path, package in _discover_frontend_target_lock_entries(
                document.get("packages"), target=target
            ).items():
                lock_occurrences[(relative, path)] = package

        manifest_path = policy["manifest_path"]
        assert isinstance(manifest_path, tuple)
        expected_manifest_occurrences = {
            ("frontend/package.json", *manifest_path): policy["manifest_value"]
        }
        assert manifest_occurrences == expected_manifest_occurrences, (
            f"{target}: manifest carriers disagree with the approved current owner; "
            f"found {manifest_occurrences!r}"
        )
        assert lock_occurrences, f"{target}: governed lock occurrence missing"
        assert {relative for relative, _ in lock_occurrences} == {
            "frontend/package-lock.json"
        }, f"{target}: unexpected tracked lock owner"

        selected = policy["selected"]
        assert isinstance(selected, str)
        lock_versions: set[Version] = set()
        for (relative, path), package in lock_occurrences.items():
            raw_version = package.get("version")
            parsed_version = _assert_frontend_security_target_version(
                target=target,
                raw_version=raw_version,
            )
            assert raw_version == selected, f"{relative}:{path}: {target} selected target drift"
            expected_resolved = f"https://registry.npmjs.org/{target}/-/{target}-{selected}.tgz"
            assert (
                package.get("resolved") == expected_resolved
            ), f"{relative}:{path}: {target} canonical provenance mismatch"
            integrity = package.get("integrity")
            assert (
                isinstance(integrity, str) and integrity.strip()
            ), f"{relative}:{path}: integrity missing"
            lock_versions.add(parsed_version)
        assert lock_versions == {Version(selected)}, f"{target}: manifest/lock target disagreement"


def test_parse_version_accepts_exact_npm_semver() -> None:
    assert _parse_version(value="2.1.4", source="fixture") == Version("2.1.4")


@pytest.mark.parametrize(
    ("case_id", "version", "allowed"),
    (
        ("brace-2-below", "2.1.3", False),
        ("brace-2-floor", "2.1.4", True),
        ("brace-2-selected", "2.1.4", True),
        ("brace-5-below", "5.0.8", False),
        ("brace-5-floor", "5.0.9", True),
        ("brace-5-selected", "5.0.9", True),
    ),
)
def test_brace_expansion_current_advisory_boundaries(
    case_id: str,
    version: str,
    allowed: bool,
) -> None:
    """The successor advisory owns both exact floor and selected-target controls."""

    assert case_id
    if allowed:
        _assert_brace_expansion_head_postcondition({Version(version)})
        return
    with pytest.raises(AssertionError, match="GHSA-rgw5-rvv9-x895"):
        _assert_brace_expansion_head_postcondition({Version(version)})


def test_parse_version_accepts_number_max_safe_integer_component() -> None:
    value = f"2.{NPM_SEMVER_MAX_SAFE_INTEGER}.0"

    assert _parse_version(value=value, source="fixture") == Version(value)


def test_parse_version_rejects_component_above_number_max_safe_integer() -> None:
    value = f"2.{NPM_SEMVER_MAX_SAFE_INTEGER + 1}.0"

    with pytest.raises(AssertionError, match="malformed version"):
        _parse_version(value=value, source="fixture")


@pytest.mark.parametrize("value", ("2.1.3.post1", "2.1.3rc1"))
def test_parse_version_rejects_pep440_only_spelling(value: str) -> None:
    with pytest.raises(AssertionError, match="malformed version"):
        _parse_version(value=value, source="fixture")


def test_frontend_brace_expansion_class_covers_all_lock_variants() -> None:
    """All current 2.x/5.x carrier outputs share one invariant."""

    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    surfaces = {
        relative: _load_json(REPO_ROOT / relative) for relative in _enumerate_repo_npm_surfaces()
    }
    _assert_brace_expansion_security_class(
        package_json=package_json,
        package_lock=package_lock,
        surfaces=surfaces,
    )


def test_brace_expansion_is_absent_from_other_repo_npm_surfaces() -> None:
    """Enumerate current tracked surfaces and reject an unowned target graph."""
    assert _assert_brace_expansion_surface_ownership() <= FRONTEND_BRACE_EXPANSION_SURFACES


@pytest.mark.parametrize("unsafe", (False, True))
def test_brace_expansion_surface_ownership_tracks_safe_repo_growth(
    tmp_path: Path,
    unsafe: bool,
) -> None:
    """A safe new tracked manifest is allowed; an unowned carrier fails closed."""
    _git_stdout("init", repo_root=tmp_path)
    manifest_path = tmp_path / "tools" / "build" / "package.json"
    manifest_path.parent.mkdir(parents=True)
    document: dict[str, object] = {"name": "safe-build-tool"}
    if unsafe:
        document["dependencies"] = {"brace-expansion": "2.1.3"}
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    _git_stdout("add", "--", "tools/build/package.json", repo_root=tmp_path)

    if unsafe:
        with pytest.raises(AssertionError, match="separate surface/class"):
            _assert_brace_expansion_surface_ownership(root=tmp_path)
    else:
        assert _assert_brace_expansion_surface_ownership(root=tmp_path) == frozenset()


def test_npm_surface_discovery_catches_lockfile_v3_and_shrinkwrap(tmp_path: Path) -> None:
    """Both npm lock basenames must expose lockfile-v3 package occurrences."""

    _git_stdout("init", repo_root=tmp_path)
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
    _git_stdout("add", "--", *sorted(relative_surfaces), repo_root=tmp_path)

    assert _enumerate_repo_npm_surfaces(root=tmp_path) == relative_surfaces
    for relative in relative_surfaces:
        manifest_occurrences, lock_entries = _discover_brace_expansion_surface_occurrences(
            relative=relative,
            document=_load_json(tmp_path / relative),
            surfaces={relative: _load_json(tmp_path / relative)},
        )
        assert manifest_occurrences == {}
        assert set(lock_entries) == {"node_modules/brace-expansion"}


@pytest.mark.parametrize("basename", sorted(NPM_LOCK_SURFACE_BASENAMES))
def test_lock_surface_dependency_edges_are_not_installed_occurrences(basename: str) -> None:
    """Resolver edges in lock documents are not manifest or installed occurrences."""

    relative = f"graph/{basename}"
    document = {
        "lockfileVersion": 3,
        "packages": {"": {"dependencies": {"brace-expansion": "^2.0.1"}}},
    }
    manifest_occurrences, lock_entries = _discover_brace_expansion_surface_occurrences(
        relative=relative,
        document=document,
        surfaces={relative: document},
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


def test_manifest_target_discovery_ignores_non_dependency_metadata() -> None:
    """Scripts, descriptions, and tool metadata are not npm dependency carriers."""

    document = {
        "description": "brace-expansion",
        "scripts": {
            "audit": "npm:brace-expansion@2.1.3",
            "download": (
                "https://registry.npmjs.org/brace-expansion/-/" "brace-expansion-2.1.3.tgz"
            ),
        },
        "config": {"brace-expansion": "2.1.3"},
    }

    assert not _find_manifest_target_paths(document, target="brace-expansion")


@pytest.mark.parametrize(
    ("field", "key", "value"),
    (
        ("dependencies", "brace-expansion", "2.1.3"),
        ("devDependencies", "renamed-brace", "npm:brace-expansion@2.1.3"),
        (
            "optionalDependencies",
            "renamed-brace",
            ("https://registry.npmjs.org/brace-expansion/-/" "brace-expansion-2.1.3.tgz"),
        ),
    ),
)
def test_manifest_target_discovery_keeps_dependency_carriers(
    field: str,
    key: str,
    value: str,
) -> None:
    """Direct, alias, and tarball dependency carriers remain in the candidate set."""

    assert _find_manifest_target_paths(
        {field: {key: value}},
        target="brace-expansion",
    ) == {(field, key): value}


@pytest.mark.parametrize(
    "local_spec",
    (
        "file:../vendor/brace-expansion",
        "../vendor/brace-expansion",
        r"file:..\vendor\brace-expansion",
        "file:../vendor/%62race-expansion",
    ),
)
def test_manifest_target_discovery_resolves_renamed_tracked_local_carrier(
    local_spec: str,
) -> None:
    """A local dependency inherits identity only from its exact tracked manifest."""
    surface = "frontend/package.json"
    document = {"dependencies": {"renamed-brace": local_spec}}
    surfaces = {
        surface: document,
        "vendor/brace-expansion/package.json": {
            "name": "brace-expansion",
            "version": "5.0.8",
        },
    }

    assert _find_manifest_target_paths(
        document,
        target="brace-expansion",
        surface=surface,
        surfaces=surfaces,
    ) == {("dependencies", "renamed-brace"): local_spec}


@pytest.mark.parametrize(
    ("local_spec", "target_document"),
    (
        ("file:../vendor/brace-expansion", {"name": "other-package"}),
        ("file:../vendor/missing", None),
        ("file://remote.example/brace-expansion", {"name": "brace-expansion"}),
        ("https://example.invalid/brace-expansion", {"name": "brace-expansion"}),
        ("file:/absolute/brace-expansion", {"name": "brace-expansion"}),
        ("file:../../outside/brace-expansion", {"name": "brace-expansion"}),
        ("file:..%2F..%2Foutside%2Fbrace-expansion", {"name": "brace-expansion"}),
    ),
)
def test_manifest_local_carrier_rejects_untracked_or_unowned_near_miss(
    local_spec: str,
    target_document: dict[str, str] | None,
) -> None:
    """Remote, escaping, missing, and wrong-name local specs supply no identity."""
    surface = "frontend/package.json"
    document = {"dependencies": {"renamed-brace": local_spec}}
    surfaces = {surface: document}
    if target_document is not None:
        surfaces["vendor/brace-expansion/package.json"] = target_document

    assert not _find_manifest_target_paths(
        document,
        target="brace-expansion",
        surface=surface,
        surfaces=surfaces,
    )


def test_frontend_guard_rejects_unapproved_tracked_local_brace_carrier() -> None:
    """The approved frontend owner cannot hide a renamed local target carrier."""
    package_json, package_lock = _brace_expansion_guard_fixture()
    package_json["dependencies"] = {"renamed-brace": "file:../vendor/brace-expansion"}
    surfaces = {
        "frontend/package.json": package_json,
        "vendor/brace-expansion/package.json": {
            "name": "brace-expansion",
            "version": "5.0.8",
        },
    }

    with pytest.raises(AssertionError, match="manifest occurrence is not approved"):
        _assert_brace_expansion_security_class(
            package_json=package_json,
            package_lock=package_lock,
            surfaces=surfaces,
        )


def test_surface_ownership_rejects_renamed_tracked_local_brace_carrier(
    tmp_path: Path,
) -> None:
    """An unowned manifest cannot hide brace-expansion behind a local alias name."""
    _git_stdout("init", repo_root=tmp_path)
    consumer = tmp_path / "tools" / "build" / "package.json"
    target = tmp_path / "tools" / "vendor" / "brace" / "package.json"
    consumer.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    consumer.write_text(
        json.dumps({"dependencies": {"renamed-brace": "file:../vendor/brace"}}),
        encoding="utf-8",
    )
    target.write_text(
        json.dumps({"name": "brace-expansion", "version": "5.0.8"}),
        encoding="utf-8",
    )
    _git_stdout(
        "add",
        "--",
        "tools/build/package.json",
        "tools/vendor/brace/package.json",
        repo_root=tmp_path,
    )

    with pytest.raises(AssertionError, match="separate surface/class"):
        _assert_brace_expansion_surface_ownership(root=tmp_path)


@pytest.mark.parametrize(
    "case",
    (
        "executable-absence",
        "remove-overrides-container",
        "remove-one-carrier",
        "safe-patch-2",
        "safe-patch-5",
        "safe-new-lock-major",
    ),
)
def test_brace_expansion_current_postcondition_allows_safe_graph_evolution(case: str) -> None:
    """A later authorized graph change is governed by current safety, not old delta paths."""

    package_json, package_lock = _brace_expansion_guard_fixture()
    packages = package_lock["packages"]
    if case == "executable-absence":
        del package_json["overrides"]["minimatch@3"]
        del package_json["overrides"]["minimatch@10"]
        packages.clear()
    elif case == "remove-overrides-container":
        del package_json["overrides"]
        packages.clear()
    elif case == "remove-one-carrier":
        del package_json["overrides"]["minimatch@3"]
        del packages["node_modules/brace-expansion"]
    elif case == "safe-patch-2":
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.5"
        packages["node_modules/brace-expansion"].update(_brace_entry("2.1.5"))
    elif case == "safe-patch-5":
        package_json["overrides"]["minimatch@10"]["brace-expansion"] = "5.0.10"
        packages["node_modules/glob/node_modules/brace-expansion"].update(_brace_entry("5.0.10"))
    elif case == "safe-new-lock-major":
        packages["node_modules/future/node_modules/brace-expansion"] = _brace_entry("6.0.0")
    else:
        raise AssertionError(f"unhandled safe graph evolution case: {case}")

    _assert_brace_expansion_security_class(
        package_json=package_json,
        package_lock=package_lock,
    )


def test_brace_expansion_owner_evidence_binds_cutoff_and_replay() -> None:
    """The sole owner must carry the exact finite inventory and replay evidence."""

    _assert_brace_expansion_owner_evidence(
        BRACE_EXPANSION_EVIDENCE_PATH.read_text(encoding="utf-8")
    )


def test_brace_expansion_targeted_head_evidence_ignores_unrelated_json_drift() -> None:
    """Unrelated manifest/lock edits must not invalidate the bounded evidence receipt."""

    package_json, package_lock = _brace_expansion_guard_fixture()
    expected = _brace_expansion_head_evidence_digest(
        package_json=package_json,
        package_lock=package_lock,
    )

    package_json["unrelated-targeted-evidence-control"] = True
    package_lock["unrelated-targeted-evidence-control"] = True
    reparsed_package = json.loads(json.dumps(package_json, indent=4, sort_keys=True))
    reparsed_lock = json.loads(json.dumps(package_lock, indent=4, sort_keys=True))

    assert (
        _brace_expansion_head_evidence_digest(
            package_json=reparsed_package,
            package_lock=reparsed_lock,
        )
        == expected
    )


@pytest.mark.parametrize(
    "case",
    (
        "integrity",
        "engines",
        "metadata",
    ),
)
def test_brace_expansion_targeted_head_evidence_binds_discovered_records(case: str) -> None:
    """Every field on a discovered lock record remains content-bound."""

    package_json, package_lock = _brace_expansion_guard_fixture()
    expected = _brace_expansion_head_evidence_digest(
        package_json=package_json,
        package_lock=package_lock,
    )
    discovered = _discover_brace_expansion_lock_entries(package_lock["packages"])
    root_path = "node_modules/brace-expansion"
    assert root_path in discovered, "expected the discovered root brace-expansion record"
    root = discovered[root_path]
    nested_records = {path: record for path, record in discovered.items() if path != root_path}
    assert len(nested_records) == 1, "expected exactly one discovered nested brace-expansion record"
    nested_path, nested = next(iter(nested_records.items()))
    assert (
        nested.get("version") == BRACE_EXPANSION_APPROVED_OUTPUTS[5]
    ), f"{nested_path}: expected the approved nested brace-expansion record"

    if case == "integrity":
        root["integrity"] += "-drift"
    elif case == "engines":
        nested["engines"] = {"node": ">=99"}
    elif case == "metadata":
        root["license"] = "UNRELATED-TO-RECORD"
    else:
        raise AssertionError(f"unhandled targeted head evidence case: {case}")

    assert (
        _brace_expansion_head_evidence_digest(
            package_json=package_json,
            package_lock=package_lock,
        )
        != expected
    )


@pytest.mark.parametrize(
    ("case", "expected_message"),
    (
        ("manifest-alias", "manifest occurrence is not approved"),
        ("lock-name", "alias/noncanonical installed path"),
        ("lock-query", "alias/noncanonical installed path"),
        ("lock-fragment", "alias/noncanonical installed path"),
    ),
)
def test_brace_expansion_targeted_head_evidence_rejects_extra_carriers(
    case: str,
    expected_message: str,
) -> None:
    """New bounded identity signals must fail validation before evidence hashing."""

    package_json, package_lock = _brace_expansion_guard_fixture()
    packages = package_lock["packages"]
    extra = _brace_entry("2.1.3")

    if case == "manifest-alias":
        package_json["overrides"]["future-carrier"] = {
            "renamed-package": "npm:brace-expansion@2.1.3"
        }
    elif case == "lock-name":
        extra["name"] = "brace-expansion"
        packages["node_modules/renamed-brace"] = extra
    elif case == "lock-query":
        extra["resolved"] += "?download=1"
        packages["node_modules/query-brace"] = extra
    elif case == "lock-fragment":
        extra["resolved"] += "#fragment"
        packages["node_modules/fragment-brace"] = extra
    else:
        raise AssertionError(f"unhandled targeted carrier case: {case}")

    with pytest.raises(AssertionError, match=expected_message):
        _brace_expansion_head_evidence_digest(
            package_json=package_json,
            package_lock=package_lock,
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
        _assert_brace_expansion_owner_evidence(document)


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
        "head-evidence-digest",
    ),
)
def test_brace_expansion_owner_evidence_fails_closed_on_inventory_drift(case: str) -> None:
    """A changed finite inventory or captured response identity must fail closed."""

    document = BRACE_EXPANSION_EVIDENCE_PATH.read_text(encoding="utf-8")
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
    elif case == "head-evidence-digest":
        document = document.replace(BRACE_EXPANSION_HEAD_EVIDENCE_SHA256, "0" * 64, 1)
    else:
        raise AssertionError(f"unhandled owner evidence mutation: {case}")

    with pytest.raises(AssertionError):
        _assert_brace_expansion_owner_evidence(document)


@pytest.mark.parametrize(
    ("case", "expected_message"),
    (
        (
            "audit-exit-code-type",
            "owner evidence npm_audit.base.exit_code must be an integer",
        ),
        (
            "audit-total-type",
            "owner evidence npm_audit.head.total must be an integer",
        ),
        (
            "audit-conclusion",
            "owner evidence npm_audit.overall_audit_clean must remain false",
        ),
        (
            "coordinated-omission",
            "owner evidence advisory_database.record_count must be exactly 6",
        ),
    ),
)
def test_brace_expansion_owner_evidence_rejects_rehashed_semantic_drift(
    case: str,
    expected_message: str,
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
        monkeypatch.setitem(
            globals(),
            "BRACE_EXPANSION_RENDERED_PROJECTIONS",
            {
                advisory: projection
                for advisory, projection in BRACE_EXPANSION_RENDERED_PROJECTIONS.items()
                if advisory != omitted
            },
        )
    else:
        raise AssertionError(f"unhandled rehashed receipt mutation: {case}")

    document, new_digest = _replace_brace_expansion_evidence_receipt(document, receipt)
    monkeypatch.setitem(globals(), "BRACE_EXPANSION_EVIDENCE_RECEIPT_SHA256", new_digest)
    with pytest.raises(AssertionError, match=expected_message):
        _assert_brace_expansion_owner_evidence(document)


def test_brace_expansion_postcondition_includes_base_non_applicable_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate outside A still blocks an affected governed head occurrence."""

    monkeypatch.setitem(
        BRACE_EXPANSION_CURRENT_ADVISORY_RANGES,
        "GHSA-f886-m6hf-6m8v",
        (SpecifierSet("==2.1.4"),),
    )
    with pytest.raises(AssertionError, match="GHSA-f886-m6hf-6m8v"):
        _assert_brace_expansion_head_postcondition({Version("2.1.4"), Version("5.0.9")})


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("affected-lock-output", "governed head occurrence remains affected"),
        ("lock-only-safe-patch", "does not match any installed lock occurrence"),
        ("extra-override-carrier", "manifest occurrence is not approved"),
        ("missing-lock-output", "does not match any installed lock occurrence"),
        ("manifest-prerelease", "prerelease output is not approved"),
        ("lock-prerelease", "prerelease output is not approved"),
        ("numeric-prerelease-normalization", "prerelease output is not approved"),
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
        ("manifest-lock", "does not match any installed lock occurrence"),
        ("blanket", "manifest occurrence is not approved"),
        ("selector-override", "manifest occurrence is not approved"),
        ("empty-selector-override", "manifest occurrence is not approved"),
        ("alias-value", "manifest occurrence is not approved"),
        ("direct-manifest", "manifest occurrence is not approved"),
        ("optional-alias", "manifest occurrence is not approved"),
        ("peer-tarball", "manifest occurrence is not approved"),
        ("bundled-manifest", "manifest occurrence is not approved"),
    ),
)
def test_frontend_brace_expansion_class_fails_closed(case: str, message: str) -> None:
    """Falsify the class invariant rather than enumerating carrier names."""

    package_json, package_lock = _brace_expansion_guard_fixture()
    packages = package_lock["packages"]
    root = packages["node_modules/brace-expansion"]
    if case == "affected-lock-output":
        packages["node_modules/future-carrier/node_modules/brace-expansion"] = _brace_entry("2.0.3")
    elif case == "lock-only-safe-patch":
        root.update(_brace_entry("2.1.5"))
    elif case == "extra-override-carrier":
        package_json["overrides"]["future-carrier"] = {"nested": {"brace-expansion": "2.1.3"}}
    elif case == "missing-lock-output":
        del packages["node_modules/glob/node_modules/brace-expansion"]
    elif case == "manifest-prerelease":
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.4-rc.1"
    elif case == "lock-prerelease":
        root.update(_brace_entry("2.1.4-rc.1"))
    elif case == "numeric-prerelease-normalization":
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.4-0"
        root.update(_brace_entry("2.1.4-0"))
        root["resolved"] = (
            "https://registry.npmjs.org/brace-expansion/-/" "brace-expansion-2.1.4.post0.tgz"
        )
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
        package_json["overrides"]["minimatch@3"]["brace-expansion"] = "2.1.5"
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
    elif case == "direct-manifest":
        package_json["dependencies"] = {"brace-expansion": "2.1.3"}
    elif case == "optional-alias":
        package_json["optionalDependencies"] = {"renamed-brace": "npm:brace-expansion@2.1.3"}
    elif case == "peer-tarball":
        package_json["peerDependencies"] = {
            "renamed-brace": (
                "https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.1.3.tgz"
            )
        }
    elif case == "bundled-manifest":
        package_json["bundleDependencies"] = ["brace-expansion"]
    else:
        raise AssertionError(f"unhandled brace-expansion falsification case: {case}")

    with pytest.raises(AssertionError, match=message):
        _assert_brace_expansion_security_class(
            package_json=package_json,
            package_lock=package_lock,
        )


def _transitive_npm_entry(*, target: str, version: str) -> dict[str, str]:
    return {
        "version": version,
        "resolved": f"https://registry.npmjs.org/{target}/-/{target}-{version}.tgz",
        "integrity": (
            "sha512-V2NpofLblG64mfOtSgDhOJESZEGogzDMBv/q+W6oc4LXWP/q75eOXoOaaOu1EOadB9U4Bwx/e0yzbvwKH8zalA=="  # pragma: allowlist secret
        ),
    }


def _browserslist_entry(version: str) -> dict[str, str]:
    return _transitive_npm_entry(target="browserslist", version=version)


def _write_browserslist_repo(
    root: Path,
    *,
    package_json: dict[str, object] | None = None,
    package_lock: dict[str, object] | None = None,
    write_lock: bool = True,
) -> None:
    """Create one tracked, lock-bearing npm project for delegated guard tests."""

    _git_stdout("init", repo_root=root)
    frontend = root / "frontend"
    frontend.mkdir(parents=True)
    manifest = package_json or {"name": "fixture", "version": "1.0.0"}
    lock = package_lock or {
        "name": "fixture",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "requires": True,
        "packages": {"": {"name": "fixture", "version": "1.0.0"}},
    }
    (frontend / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    tracked = ["frontend/package.json"]
    if write_lock:
        (frontend / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
        tracked.append("frontend/package-lock.json")
    _git_stdout("add", "--", *tracked, repo_root=root)


def test_browserslist_class_covers_every_current_tracked_surface() -> None:
    """The current repository graph satisfies the delegated universal postcondition."""

    assert _assert_browserslist_security_class() == frozenset({"frontend/package-lock.json"})


def test_transitive_npm_batch_covers_exact_authorized_targets() -> None:
    """The current graph satisfies both and only the two authorized target policies."""

    assert frozenset(TRANSITIVE_NPM_HEAD_POLICIES) == AUTHORIZED_TRANSITIVE_NPM_BATCH
    assert frozenset(TRANSITIVE_NPM_EVIDENCE_EXPECTATIONS) == AUTHORIZED_TRANSITIVE_NPM_BATCH
    assert _assert_transitive_npm_security_batch() == {
        "browserslist": frozenset({"frontend/package-lock.json"}),
        "qs": frozenset({"frontend/package-lock.json"}),
    }


@pytest.mark.parametrize(
    ("present_target", "safe_version", "absent_target"),
    (("browserslist", "4.28.8", "qs"), ("qs", "6.16.0", "browserslist")),
)
def test_transitive_npm_batch_allows_per_identity_executable_absence(
    tmp_path: Path,
    present_target: str,
    safe_version: str,
    absent_target: str,
) -> None:
    """Each conjunct may prove absence while the other target remains installed."""

    root_dependencies = {"carrier": "1.0.0"}
    carrier_dependencies = {present_target: safe_version}
    _write_browserslist_repo(
        tmp_path,
        package_json={
            "name": "fixture",
            "version": "1.0.0",
            "dependencies": root_dependencies,
        },
        package_lock={
            "name": "fixture",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "fixture",
                    "version": "1.0.0",
                    "dependencies": root_dependencies,
                },
                "node_modules/carrier": {
                    **_transitive_npm_entry(target="carrier", version="1.0.0"),
                    "dependencies": carrier_dependencies,
                    "hasShrinkwrap": False,
                },
                f"node_modules/{present_target}": _transitive_npm_entry(
                    target=present_target,
                    version=safe_version,
                ),
            },
        },
    )
    assert _assert_transitive_npm_security_batch(root=tmp_path) == {
        present_target: frozenset({"frontend/package-lock.json"}),
        absent_target: frozenset(),
    }
    lock_path = tmp_path / "frontend/package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    carrier = lock["packages"]["node_modules/carrier"]
    assert isinstance(carrier, dict)
    for value, message in (
        (True, "published nested shrinkwrap blocks batch admission"),
        ("false", "hasShrinkwrap must be an exact boolean"),
    ):
        carrier["hasShrinkwrap"] = value
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        with pytest.raises(AssertionError, match=message):
            _assert_transitive_npm_security_batch(root=tmp_path)
    carrier["hasShrinkwrap"] = False
    for field in ("bundleDependencies", "bundledDependencies"):
        for value in ([], False):
            carrier[field] = value
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            assert (
                _assert_transitive_npm_security_batch(root=tmp_path)[absent_target] == frozenset()
            )
        for value, message in (
            ([absent_target], "published bundled dependencies block batch admission"),
            (True, "published bundled dependencies block batch admission"),
            ("false", f"{field} must be an array"),
            ({}, f"{field} must be an array"),
            (None, f"{field} must be an array"),
            ([1], f"{field} entries must be non-empty package names"),
        ):
            carrier[field] = value
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            with pytest.raises(AssertionError, match=message):
                _assert_transitive_npm_security_batch(root=tmp_path)
        del carrier[field]
    for value, message in (
        (True, "bundled lock occurrence is forbidden"),
        ("false", "inBundle must be boolean when present"),
        (1, "inBundle must be boolean when present"),
    ):
        carrier["inBundle"] = value
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        with pytest.raises(AssertionError, match=message):
            _assert_transitive_npm_security_batch(root=tmp_path)
    carrier["inBundle"] = False
    carrier["peerDependencies"] = {absent_target: "*"}
    carrier["peerDependenciesMeta"] = {absent_target: {"optional": True}}
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    assert _assert_transitive_npm_security_batch(root=tmp_path)[absent_target] == frozenset()
    for metadata in ({}, {"optional": False}):
        carrier["peerDependenciesMeta"] = {absent_target: metadata}
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        with pytest.raises(AssertionError, match="npm virtual graph rejected"):
            _assert_transitive_npm_security_batch(root=tmp_path)
    for optional in ("true", 1, {}, None, [], 0):
        carrier["peerDependenciesMeta"] = {absent_target: {"optional": optional}}
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        with pytest.raises(AssertionError, match="peer optional must be an exact boolean"):
            _assert_transitive_npm_security_batch(root=tmp_path)


def test_browserslist_class_allows_delegated_executable_absence(tmp_path: Path) -> None:
    """Absence is valid only after opaque-source and npm virtual-graph admission."""

    _write_browserslist_repo(tmp_path)
    assert _assert_transitive_npm_security_batch(root=tmp_path) == {
        "browserslist": frozenset(),
        "qs": frozenset(),
    }
    assert _assert_browserslist_security_class(root=tmp_path) == frozenset()


def test_browserslist_class_rejects_missing_virtual_dependency(tmp_path: Path) -> None:
    """npm, not handwritten ancestor logic, owns missing-edge rejection."""

    dependency = {"carrier": "^1.0.0"}
    _write_browserslist_repo(
        tmp_path,
        package_json={"name": "fixture", "version": "1.0.0", "dependencies": dependency},
        package_lock={
            "name": "fixture",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "fixture",
                    "version": "1.0.0",
                    "dependencies": dependency,
                }
            },
        },
    )
    with pytest.raises(AssertionError, match="npm virtual graph rejected"):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_class_rejects_dependency_manifest_without_lock(tmp_path: Path) -> None:
    """A registry-only manifest does not prove an absent executable graph by itself."""

    _write_browserslist_repo(
        tmp_path,
        package_json={
            "name": "fixture",
            "version": "1.0.0",
            "dependencies": {"carrier": "^1.0.0"},
        },
        write_lock=False,
    )
    with pytest.raises(AssertionError, match="same-root lock authority"):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_class_rejects_root_lock_manifest_drift(tmp_path: Path) -> None:
    """A root lock demand cannot invent dependency authority absent from its manifest."""

    _write_browserslist_repo(
        tmp_path,
        package_lock={
            "name": "fixture",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "fixture",
                    "version": "1.0.0",
                    "dependencies": {"browserslist": "^4.28.7"},
                }
            },
        },
    )
    with pytest.raises(AssertionError, match="must exactly match"):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_class_rejects_lockfile_v2_compatibility_tree(tmp_path: Path) -> None:
    """The class stops at v3 instead of partially parsing the v2 compatibility tree."""

    _write_browserslist_repo(
        tmp_path,
        package_lock={
            "name": "fixture",
            "version": "1.0.0",
            "lockfileVersion": 2,
            "requires": True,
            "packages": {"": {"name": "fixture", "version": "1.0.0"}},
            "dependencies": {
                "browserslist": {
                    "version": "4.28.6",
                    "resolved": "https://registry.npmjs.org/browserslist/-/browserslist-4.28.6.tgz",
                }
            },
        },
    )
    with pytest.raises(AssertionError, match="supports only npm lockfileVersion 3"):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_virtual_graph_ignores_ambient_npm_omit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ambient npm omit settings cannot weaken delegated full-graph admission."""

    dependency = {"carrier": "^1.0.0"}
    _write_browserslist_repo(
        tmp_path,
        package_json={
            "name": "fixture",
            "version": "1.0.0",
            "devDependencies": dependency,
        },
        package_lock={
            "name": "fixture",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "fixture",
                    "version": "1.0.0",
                    "devDependencies": dependency,
                }
            },
        },
    )
    monkeypatch.setenv("npm_config_omit", "dev")
    (tmp_path / "frontend/.npmrc").write_text(
        "omit=dev\nglobal=true\nlink=true\nlegacy-peer-deps=true\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="npm virtual graph rejected"):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_virtual_graph_configuration_is_hermetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One boundary strips ambient graph controls and fixes the complete-graph policy."""

    blocked = {
        "NODE_ENV": "production",
        "NODE_OPTIONS": "--invalid-option",
        "NODE_PATH": "/tmp/untrusted-node-path",
        "npm_config_omit": "dev",
        "NpM_CoNfIg_Link": "true",
    }
    for key, value in blocked.items():
        monkeypatch.setenv(key, value)
    delegated_env = _npm_virtual_graph_environment()
    assert not set(blocked).intersection(delegated_env)
    assert NPM_VIRTUAL_GRAPH_POLICY_ARGS == (
        "--global=false",
        "--workspaces=false",
        "--link=false",
        "--include=dev",
        "--include=optional",
        "--include=peer",
        "--legacy-peer-deps=false",
        "--strict-peer-deps=true",
    )


@pytest.mark.parametrize(
    ("target", "safe_version"),
    (("browserslist", "4.28.8"), ("qs", "6.16.0")),
)
@pytest.mark.parametrize("carrier", ("direct", "alias", "override", "bundle"))
def test_transitive_npm_batch_rejects_direct_manifest_authority(
    tmp_path: Path,
    target: str,
    safe_version: str,
    carrier: str,
) -> None:
    """The lock-only class never acquires a direct target owner."""

    if carrier == "direct":
        manifest: dict[str, object] = {"dependencies": {target: safe_version}}
    elif carrier == "alias":
        manifest = {"devDependencies": {"renamed": f"npm:{target}@{safe_version}"}}
    elif carrier == "override":
        manifest = {"overrides": {"carrier": {target: safe_version}}}
    elif carrier == "bundle":
        manifest = {"bundleDependencies": [target]}
    else:
        raise AssertionError(f"unhandled target carrier: {carrier}")
    _write_browserslist_repo(
        tmp_path,
        package_json={"name": "fixture", "version": "1.0.0", **manifest},
    )
    with pytest.raises(AssertionError, match=rf"direct {target} manifest authority"):
        _assert_transitive_npm_security_batch(root=tmp_path)


@pytest.mark.parametrize(
    "opaque_source",
    (
        "github:browserslist/browserslist",
        "git+https://github.com/browserslist/browserslist.git#v4.28.8",
        "git+file:///vendor/browserslist.git",
        "file:../vendor/browserslist",
        "../vendor/browserslist",
        "vendor/pkg/browserslist",
        "https://example.invalid/browserslist.tgz",
        "latest",
    ),
)
def test_browserslist_class_rejects_opaque_manifest_sources(
    tmp_path: Path,
    opaque_source: str,
) -> None:
    """One delegated classifier closes every opaque source family."""

    _write_browserslist_repo(
        tmp_path,
        package_json={
            "name": "fixture",
            "version": "1.0.0",
            "dependencies": {"renamed": opaque_source},
        },
    )
    with pytest.raises(AssertionError, match="opaque dependency source"):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_class_rejects_workspace_source(tmp_path: Path) -> None:
    """Workspace topology is opaque rather than another package-specific grammar."""

    _write_browserslist_repo(
        tmp_path,
        package_json={"name": "fixture", "version": "1.0.0", "workspaces": ["packages/*"]},
    )
    with pytest.raises(AssertionError, match="opaque dependency source"):
        _assert_browserslist_security_class(root=tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("dependencies", ["browserslist"], "dependencies must be an object"),
        ("overrides", ["browserslist"], "overrides must be an object"),
        ("bundleDependencies", "browserslist", "bundleDependencies must be an array"),
        ("peerDependenciesMeta", [], "peerDependenciesMeta must be an object"),
        ("peerDependenciesMeta", {"carrier": True}, "peer metadata must be an object"),
        (
            "peerDependenciesMeta",
            {"carrier": {"optionl": True}},
            "unknown peer metadata field",
        ),
    ),
)
def test_browserslist_class_rejects_malformed_manifest_containers(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    """Malformed JSON containers cannot create an absence claim."""

    _write_browserslist_repo(
        tmp_path,
        package_json={"name": "fixture", "version": "1.0.0", field: value},
    )
    with pytest.raises(AssertionError, match=message):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_class_rejects_duplicate_npm_surface_keys(tmp_path: Path) -> None:
    """A later duplicate JSON member cannot erase an earlier vulnerable record."""

    _write_browserslist_repo(tmp_path)
    (tmp_path / "frontend/package-lock.json").write_text(
        """{
  "name": "fixture",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "packages": {"node_modules/browserslist": {"version": "4.28.6"}},
  "packages": {"": {"name": "fixture", "version": "1.0.0"}}
}
""",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="duplicate JSON key: packages"):
        _assert_browserslist_security_class(root=tmp_path)


def test_browserslist_lock_discovery_includes_every_nested_occurrence() -> None:
    """A safe root record cannot hide a vulnerable nested raw lock record."""

    document = {
        "lockfileVersion": 3,
        "packages": {
            "": {"name": "fixture", "version": "1.0.0"},
            "node_modules/browserslist": _browserslist_entry("4.28.8"),
            "node_modules/carrier/node_modules/browserslist": _browserslist_entry("4.28.6"),
        },
    }
    occurrences = _find_lock_occurrences(document, target="browserslist")
    assert set(occurrences) == {
        "node_modules/browserslist",
        "node_modules/carrier/node_modules/browserslist",
    }
    with pytest.raises(AssertionError, match="governed occurrence remains affected"):
        for path, package in occurrences.items():
            _assert_browserslist_occurrence(
                surface="fixture/package-lock.json",
                path=path,
                package=package,
            )


@pytest.mark.parametrize(
    ("target", "safe_version", "affected_version"),
    (("browserslist", "4.28.8", "4.28.6"), ("qs", "6.16.0", "6.15.3")),
)
def test_transitive_npm_batch_rejects_every_nested_affected_occurrence(
    tmp_path: Path,
    target: str,
    safe_version: str,
    affected_version: str,
) -> None:
    """A safe root occurrence cannot hide an affected nested target from the executor."""

    carrier_dependencies = {target: affected_version}
    _write_browserslist_repo(
        tmp_path,
        package_json={
            "name": "fixture",
            "version": "1.0.0",
            "dependencies": {"carrier": "1.0.0"},
        },
        package_lock={
            "name": "fixture",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "fixture",
                    "version": "1.0.0",
                    "dependencies": {"carrier": "1.0.0"},
                },
                "node_modules/carrier": {
                    **_transitive_npm_entry(target="carrier", version="1.0.0"),
                    "dependencies": carrier_dependencies,
                },
                f"node_modules/{target}": _transitive_npm_entry(
                    target=target,
                    version=safe_version,
                ),
                f"node_modules/carrier/node_modules/{target}": _transitive_npm_entry(
                    target=target,
                    version=affected_version,
                ),
            },
        },
    )
    with pytest.raises(AssertionError, match=rf"{target}/.+governed occurrence remains affected"):
        _assert_transitive_npm_security_batch(root=tmp_path)


@pytest.mark.parametrize(
    ("affected_target", "affected_version", "safe_target", "safe_version"),
    (
        ("browserslist", "4.28.6", "qs", "6.16.0"),
        ("qs", "6.15.3", "browserslist", "4.28.8"),
    ),
)
def test_transitive_npm_batch_is_conjunctive_for_mixed_safe_and_affected_targets(
    tmp_path: Path,
    affected_target: str,
    affected_version: str,
    safe_target: str,
    safe_version: str,
) -> None:
    """One safe target never masks the other target's affected occurrence."""

    root_dependencies = {"carrier": "1.0.0"}
    carrier_dependencies = {
        affected_target: affected_version,
        safe_target: safe_version,
    }
    _write_browserslist_repo(
        tmp_path,
        package_json={
            "name": "fixture",
            "version": "1.0.0",
            "dependencies": root_dependencies,
        },
        package_lock={
            "name": "fixture",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "fixture",
                    "version": "1.0.0",
                    "dependencies": root_dependencies,
                },
                "node_modules/carrier": {
                    **_transitive_npm_entry(target="carrier", version="1.0.0"),
                    "dependencies": carrier_dependencies,
                },
                f"node_modules/{affected_target}": _transitive_npm_entry(
                    target=affected_target,
                    version=affected_version,
                ),
                f"node_modules/{safe_target}": _transitive_npm_entry(
                    target=safe_target,
                    version=safe_version,
                ),
            },
        },
    )
    with pytest.raises(
        AssertionError,
        match=rf"{affected_target}/.+governed occurrence remains affected",
    ):
        _assert_transitive_npm_security_batch(root=tmp_path)


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("prerelease", "prerelease output is not approved"),
        ("foreign-registry", "canonical provenance mismatch"),
        ("alias-path", "alias/noncanonical installed path"),
        ("missing-integrity", "integrity must use sha512 SRI"),
        ("malformed-integrity", "integrity must contain valid base64"),
        ("short-integrity", "integrity sha512 digest must be 64 bytes"),
        ("symbolic-link", "symbolic link lock occurrence is forbidden"),
        ("bundled-record", "bundled lock occurrence is forbidden"),
        ("malformed-bundle-flag", "inBundle must be boolean when present"),
    ),
)
@pytest.mark.parametrize(
    ("target", "safe_version"),
    (("browserslist", "4.28.8"), ("qs", "6.16.0")),
)
def test_transitive_npm_occurrence_policy_fails_closed(
    case: str,
    message: str,
    target: str,
    safe_version: str,
) -> None:
    """Target policy owns only version, path, provenance, link, and SRI checks."""

    path = f"node_modules/{target}"
    package: dict[str, object] = _transitive_npm_entry(
        target=target,
        version=safe_version,
    )
    if case == "prerelease":
        package = _transitive_npm_entry(target=target, version=f"{safe_version}-rc.1")
    elif case == "foreign-registry":
        package["resolved"] = f"https://example.invalid/{target}-{safe_version}.tgz"
    elif case == "alias-path":
        path = "node_modules/renamed"
        package["name"] = target
    elif case == "missing-integrity":
        package.pop("integrity")
    elif case == "malformed-integrity":
        package["integrity"] = "sha512-***"
    elif case == "short-integrity":
        package["integrity"] = "sha512-Zml4dHVyZQ=="
    elif case == "symbolic-link":
        package["link"] = True
    elif case == "bundled-record":
        package["inBundle"] = True
    elif case == "malformed-bundle-flag":
        package["inBundle"] = "false"
    else:
        raise AssertionError(f"unhandled transitive npm occurrence case: {case}")

    with pytest.raises(AssertionError, match=message):
        _assert_transitive_npm_occurrence(
            target=target,
            surface="fixture/package-lock.json",
            path=path,
            package=package,
        )


def test_browserslist_advisory_inventory_is_exact_and_complete() -> None:
    """Equal ranges cannot let one advisory identity disappear silently."""

    assert BROWSERSLIST_EXPECTED_ADVISORIES == frozenset(BROWSERSLIST_ADVISORY_RANGE_TEXT)
    derived_applicable = frozenset(
        advisory
        for advisory, affected_ranges in BROWSERSLIST_ADVISORY_RANGES.items()
        if any(BROWSERSLIST_BASE_VERSION in affected for affected in affected_ranges)
    )
    assert derived_applicable == BROWSERSLIST_EXPECTED_APPLICABLE_ADVISORIES
    assert derived_applicable < BROWSERSLIST_EXPECTED_ADVISORIES
    boundary_rows = {
        (advisory, raw_range, patched)
        for advisory, raw_range, _affected, patched in BROWSERSLIST_ADVISORY_BOUNDARY_CASES
    }
    assert len(boundary_rows) == len(BROWSERSLIST_ADVISORY_BOUNDARY_CASES) == 3
    assert boundary_rows == {
        (advisory, raw_range, BROWSERSLIST_FIRST_PATCHED_VERSIONS[advisory])
        for advisory, raw_ranges in BROWSERSLIST_ADVISORY_RANGE_TEXT.items()
        for raw_range in raw_ranges
    }


@pytest.mark.parametrize(
    ("advisory", "raw_range", "affected", "patched"),
    BROWSERSLIST_ADVISORY_BOUNDARY_CASES,
)
def test_browserslist_every_advisory_retains_affected_and_patched_boundary(
    advisory: str,
    raw_range: str,
    affected: str,
    patched: str,
) -> None:
    """Each historical or current Browserslist range retains its own boundary proof."""

    assert raw_range in BROWSERSLIST_ADVISORY_RANGE_TEXT[advisory]
    assert BROWSERSLIST_FIRST_PATCHED_VERSIONS[advisory] == patched
    affected_range = SpecifierSet(raw_range)
    assert Version(affected) in affected_range
    assert Version(patched) not in affected_range


@pytest.mark.parametrize(
    ("version", "allowed"),
    (
        ("4.16.4", False),
        ("4.16.5", False),
        ("4.28.2", False),
        ("4.28.6", False),
        ("4.28.7", True),
        ("4.28.8", True),
    ),
)
def test_browserslist_advisory_boundaries(version: str, allowed: bool) -> None:
    """All three frozen advisory ranges retain explicit boundary controls."""

    if allowed:
        assert _assert_browserslist_head_postcondition(
            raw_version=version,
            source="fixture",
        ) == Version(version)
        return
    with pytest.raises(AssertionError, match="governed occurrence remains affected"):
        _assert_browserslist_head_postcondition(raw_version=version, source="fixture")


def test_qs_advisory_inventory_is_exact_complete_and_base_derived() -> None:
    """The ten-record, twenty-one-row qs inventory retains exact applicability."""

    assert len(QS_EXPECTED_ADVISORIES) == 10
    assert sum(len(entries) for entries in QS_ADVISORY_ENTRIES.values()) == 21
    assert frozenset(QS_ADVISORY_RANGES) == QS_EXPECTED_ADVISORIES
    base_version = TRANSITIVE_NPM_EVIDENCE_EXPECTATIONS["qs"]["base_version"]
    assert isinstance(base_version, Version)
    derived_applicable = frozenset(
        advisory
        for advisory, affected_ranges in QS_ADVISORY_RANGES.items()
        if any(base_version in affected for affected in affected_ranges)
    )
    assert derived_applicable == QS_EXPECTED_APPLICABLE_ADVISORIES
    assert derived_applicable < QS_EXPECTED_ADVISORIES
    assert QS_EXPECTED_WITHDRAWN == {"GHSA-crvj-3gj9-gm2p": "2020-06-16T21:32:53Z"}
    assert len(QS_ADVISORY_BOUNDARY_CASES) == 21
    boundary_rows = {
        (advisory, raw_range, patched)
        for advisory, raw_range, _affected, patched in QS_ADVISORY_BOUNDARY_CASES
    }
    assert len(boundary_rows) == len(QS_ADVISORY_BOUNDARY_CASES)
    assert boundary_rows == {
        (advisory, raw_range, patched)
        for advisory, entries in QS_ADVISORY_ENTRIES.items()
        for raw_range, patched in entries
    }


@pytest.mark.parametrize(
    ("advisory", "raw_range", "affected", "patched"),
    QS_ADVISORY_BOUNDARY_CASES,
)
def test_qs_every_advisory_row_retains_affected_and_patched_boundary(
    advisory: str,
    raw_range: str,
    affected: str,
    patched: str,
) -> None:
    """Every retained range row remains independently comparable and lossless."""

    assert (raw_range, patched) in QS_ADVISORY_ENTRIES[advisory]
    affected_range = SpecifierSet(raw_range)
    assert Version(affected) in affected_range
    assert Version(patched) not in affected_range


@pytest.mark.parametrize(
    ("version", "allowed"),
    (
        ("6.15.1", False),
        ("6.15.2", False),
        ("6.15.3", False),
        ("6.15.4", False),
        ("6.16.0", True),
        ("6.16.1", True),
    ),
)
def test_qs_conjunctive_advisory_boundaries(version: str, allowed: bool) -> None:
    """Current and future stable qs versions satisfy all ten advisory records."""

    if allowed:
        assert _assert_transitive_npm_head_postcondition(
            target="qs",
            raw_version=version,
            source="fixture",
        ) == Version(version)
        return
    with pytest.raises(AssertionError, match="qs/.+: governed occurrence remains affected"):
        _assert_transitive_npm_head_postcondition(
            target="qs",
            raw_version=version,
            source="fixture",
        )


def test_transitive_npm_batch_receipt_digest_and_projection_are_bound() -> None:
    """One receipt binds exact authorization, scanner set, and both GAD inventories."""

    document = BROWSERSLIST_EVIDENCE_PATH.read_text(encoding="utf-8")
    receipt = _extract_transitive_npm_batch_receipt(document)
    canonical = json.dumps(
        receipt,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    assert digest == TRANSITIVE_NPM_BATCH_RECEIPT_SHA256
    assert f"Canonical batch receipt SHA-256:\n\n```text\n{digest}\n```" in document
    assert set(receipt) == {
        "authorized_dependency_identities",
        "gad_cutoff",
        "operator_authorization",
        "scanner_snapshot",
        "scanner_snapshot_sha256",
        "schema",
        "targets",
    }
    assert receipt["schema"] == TRANSITIVE_NPM_BATCH_RECEIPT_SCHEMA
    assert receipt["authorized_dependency_identities"] == ["npm:browserslist", "npm:qs"]
    assert receipt["operator_authorization"] == "exact_finite_batch_confirmed_2026-09-03"
    assert receipt["gad_cutoff"] == TRANSITIVE_NPM_GAD_CUTOFF
    scanner = _require_exact_object(
        receipt["scanner_snapshot"],
        keys=frozenset(
            {"base_sha", "observed_at", "roots", "terminal", "vulnerable_dependency_identities"}
        ),
        label="batch scanner snapshot",
    )
    scanner_canonical = json.dumps(
        scanner,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    scanner_digest = hashlib.sha256(scanner_canonical).hexdigest()
    assert scanner_digest == TRANSITIVE_NPM_SCANNER_SNAPSHOT_SHA256
    assert receipt["scanner_snapshot_sha256"] == scanner_digest
    assert scanner["base_sha"] == TRANSITIVE_NPM_BATCH_BASE_SHA
    assert scanner["terminal"] is True
    assert scanner["vulnerable_dependency_identities"] == [
        "npm:browserslist",
        "npm:qs",
    ]
    assert scanner["observed_at"] == TRANSITIVE_NPM_GAD_CUTOFF
    assert scanner["roots"] == [
        {
            "command": "npm audit --package-lock-only --json",
            "exit_code": 0,
            "lock": "package-lock.json",
            "project": ".",
            "severity_counts": {
                "critical": 0,
                "high": 0,
                "info": 0,
                "low": 0,
                "moderate": 0,
                "total": 0,
            },
            "vulnerability_keys": [],
        },
        {
            "command": "npm audit --package-lock-only --json",
            "exit_code": 1,
            "lock": "frontend/package-lock.json",
            "project": "frontend",
            "severity_counts": {
                "critical": 0,
                "high": 1,
                "info": 0,
                "low": 0,
                "moderate": 1,
                "total": 2,
            },
            "vulnerability_keys": ["browserslist", "qs"],
        },
    ]

    targets = receipt["targets"]
    assert isinstance(targets, dict)
    assert frozenset(targets) == AUTHORIZED_TRANSITIVE_NPM_BATCH
    expected_entries = {
        "browserslist": {
            advisory: tuple(
                (raw_range, BROWSERSLIST_FIRST_PATCHED_VERSIONS[advisory])
                for raw_range in raw_ranges
            )
            for advisory, raw_ranges in BROWSERSLIST_ADVISORY_RANGE_TEXT.items()
        },
        "qs": QS_ADVISORY_ENTRIES,
    }
    expected_metadata = {
        "browserslist": {
            "GHSA-73wf-gq98-2v4g": (
                "CVE-2026-73088",
                "high",
                "2026-09-01T16:41:54Z",
                "2026-09-01T16:41:55Z",
                None,
            ),
            "GHSA-c83g-rgw3-j3cx": (
                "CVE-2026-73089",
                "high",
                "2026-09-01T16:42:13Z",
                "2026-09-01T16:42:15Z",
                None,
            ),
            "GHSA-w8qv-6jwh-64r5": (
                "CVE-2021-23364",
                "medium",
                "2021-05-24T19:52:40Z",
                "2023-08-17T05:02:30Z",
                None,
            ),
        },
        "qs": {
            "GHSA-4mjr-xmp4-gh2g": (
                "CVE-2026-82417",
                "medium",
                "2026-09-02T14:45:13Z",
                "2026-09-02T14:45:15Z",
                None,
            ),
            "GHSA-6rw7-vpxm-498p": (
                "CVE-2025-15284",
                "medium",
                "2025-12-30T21:02:54Z",
                "2026-03-02T22:05:33Z",
                None,
            ),
            "GHSA-crvj-3gj9-gm2p": (
                None,
                "high",
                "2018-10-09T00:44:29Z",
                "2023-01-09T05:02:51Z",
                "2020-06-16T21:32:53Z",
            ),
            "GHSA-f9cm-p3w6-xvr3": (
                "CVE-2014-10064",
                "high",
                "2018-10-09T00:38:48Z",
                "2023-01-09T05:02:52Z",
                None,
            ),
            "GHSA-gqgv-6jq5-jjj9": (
                "CVE-2017-1000048",
                "high",
                "2020-04-30T17:16:47Z",
                "2023-01-09T05:02:30Z",
                None,
            ),
            "GHSA-hrpp-h998-j3pp": (
                "CVE-2022-24999",
                "high",
                "2022-11-27T00:30:50Z",
                "2025-04-29T15:41:45Z",
                None,
            ),
            "GHSA-jjv7-qpx3-h62q": (
                "CVE-2014-7191",
                "high",
                "2017-10-24T18:33:36Z",
                "2023-04-11T00:27:35Z",
                None,
            ),
            "GHSA-q8mj-m7cp-5q26": (
                "CVE-2026-8723",
                "medium",
                "2026-05-22T17:27:19Z",
                "2026-05-22T17:27:20Z",
                None,
            ),
            "GHSA-w7fw-mjwx-w883": (
                "CVE-2026-2391",
                "low",
                "2026-02-12T17:04:39Z",
                "2026-02-12T20:08:00Z",
                None,
            ),
            "GHSA-x5fp-wj9c-mxmx": (
                "CVE-2026-82562",
                "medium",
                "2026-09-02T14:46:57Z",
                "2026-09-02T14:46:58Z",
                None,
            ),
        },
    }
    from datetime import datetime

    assert frozenset(expected_metadata) == AUTHORIZED_TRANSITIVE_NPM_BATCH
    timestamp_format = "%Y-%m-%dT%H:%M:%SZ"
    cutoff_timestamp = datetime.strptime(TRANSITIVE_NPM_GAD_CUTOFF, timestamp_format)
    expected_counts = {"browserslist": (3, 3), "qs": (10, 21)}
    total_records = 0
    total_ranges = 0
    for target, target_receipt in targets.items():
        target_receipt = _require_exact_object(
            target_receipt,
            keys=frozenset(
                {
                    "cutoff",
                    "next_page",
                    "observed_at",
                    "page_count",
                    "query",
                    "range_count",
                    "record_count",
                    "records",
                }
            ),
            label=f"{target} batch target receipt",
        )
        assert target_receipt["cutoff"] == TRANSITIVE_NPM_GAD_CUTOFF
        assert target_receipt["observed_at"] == TRANSITIVE_NPM_GAD_CUTOFF
        assert target_receipt["query"] == TRANSITIVE_NPM_GAD_QUERIES[target]
        records = target_receipt["records"]
        assert isinstance(records, list)
        record_count, range_count = expected_counts[target]
        assert type(target_receipt["record_count"]) is int
        assert type(target_receipt["range_count"]) is int
        assert target_receipt["record_count"] == len(records) == record_count
        assert type(target_receipt["page_count"]) is int
        assert target_receipt["page_count"] == 1
        assert target_receipt["next_page"] is None
        records_by_advisory = {record["ghsa_id"]: record for record in records}
        assert len(records_by_advisory) == len(records)
        assert set(records_by_advisory) == set(expected_entries[target])
        assert set(records_by_advisory) == set(expected_metadata[target])
        retained_entries: dict[str, tuple[tuple[str, str], ...]] = {}
        for advisory, record in records_by_advisory.items():
            assert set(record) == {
                "cve_id",
                "ghsa_id",
                "published_at",
                "severity",
                "updated_at",
                "vulnerabilities",
                "withdrawn_at",
            }
            cve_id = record["cve_id"]
            severity = record["severity"]
            published_text = record["published_at"]
            updated_text = record["updated_at"]
            withdrawn_text = record["withdrawn_at"]
            assert cve_id is None or (
                isinstance(cve_id, str) and re.fullmatch(r"CVE-\d{4}-\d{4,}", cve_id)
            )
            assert isinstance(severity, str)
            assert severity in {"low", "medium", "high", "critical"}
            assert isinstance(published_text, str)
            assert isinstance(updated_text, str)
            published_at = datetime.strptime(published_text, timestamp_format)
            updated_at = datetime.strptime(updated_text, timestamp_format)
            assert published_at <= updated_at <= cutoff_timestamp
            if withdrawn_text is not None:
                assert isinstance(withdrawn_text, str)
                withdrawn_at = datetime.strptime(withdrawn_text, timestamp_format)
                assert published_at <= withdrawn_at <= updated_at
            assert (
                cve_id,
                severity,
                published_text,
                updated_text,
                withdrawn_text,
            ) == expected_metadata[target][advisory]
            vulnerabilities = record["vulnerabilities"]
            assert isinstance(vulnerabilities, list) and vulnerabilities
            retained_rows: list[tuple[str, str]] = []
            for vulnerability in vulnerabilities:
                assert isinstance(vulnerability, dict)
                assert set(vulnerability) == {
                    "ecosystem",
                    "first_patched_version",
                    "package",
                    "vulnerable_version_range",
                }
                assert vulnerability["ecosystem"] == "npm"
                assert vulnerability["package"] == target
                raw_range = vulnerability["vulnerable_version_range"]
                patched = vulnerability["first_patched_version"]
                assert isinstance(raw_range, str) and raw_range
                assert isinstance(patched, str) and patched
                _parse_version(
                    value=patched,
                    source=f"{target}/{advisory} first patched version",
                )
                retained_rows.append((re.sub(r"\s+", "", raw_range), patched))
            retained_entries[advisory] = tuple(sorted(retained_rows))
        assert retained_entries == {
            advisory: tuple(sorted(entries))
            for advisory, entries in expected_entries[target].items()
        }
        actual_range_count = sum(len(entries) for entries in retained_entries.values())
        assert target_receipt["range_count"] == actual_range_count == range_count
        total_records += record_count
        total_ranges += range_count

    assert total_records == 13
    assert total_ranges == 24
    withdrawn = targets["qs"]["records"]
    assert {
        record["ghsa_id"]: record["withdrawn_at"]
        for record in withdrawn
        if record["withdrawn_at"] is not None
    } == QS_EXPECTED_WITHDRAWN
    for root in scanner["roots"]:
        assert isinstance(root, dict)
        assert type(root["exit_code"]) is int
        severity_counts = root["severity_counts"]
        assert isinstance(severity_counts, dict)
        assert all(type(value) is int and value >= 0 for value in severity_counts.values())


def test_transitive_npm_batch_receipt_rejects_duplicate_json_keys() -> None:
    """Canonicalization cannot erase an ambiguous duplicate receipt key."""

    document = BROWSERSLIST_EVIDENCE_PATH.read_text(encoding="utf-8")
    original = '      "record_count": 10,'
    assert document.count(original) == 1
    ambiguous = document.replace(
        original,
        '      "record_count": 999,\n      "record_count": 10,',
    )
    with pytest.raises(AssertionError, match="duplicate JSON key: record_count"):
        _extract_transitive_npm_batch_receipt(ambiguous)


def test_frontend_security_targets_cover_all_current_tracked_surfaces() -> None:
    """Every non-brace batch target has one bounded carrier and universal postcondition."""

    _assert_frontend_security_targets()


@pytest.mark.parametrize(
    ("case_id", "target", "version", "allowed"),
    FRONTEND_SECURITY_BOUNDARY_CASES,
    ids=[case[0] for case in FRONTEND_SECURITY_BOUNDARY_CASES],
)
def test_frontend_security_target_boundaries(
    case_id: str,
    target: str,
    version: str,
    allowed: bool,
) -> None:
    """Every below/floor/selected control is explicit and independently executable."""

    assert case_id
    if allowed:
        assert _assert_frontend_security_target_version(
            target=target,
            raw_version=version,
        ) == Version(version)
        return
    with pytest.raises(AssertionError, match="below security floor|remains affected"):
        _assert_frontend_security_target_version(target=target, raw_version=version)


@pytest.mark.parametrize("target", tuple(FRONTEND_SECURITY_TARGETS))
def test_frontend_security_targets_reject_prerelease_false_green(target: str) -> None:
    """A later-looking prerelease cannot bypass a stable advisory boundary."""

    with pytest.raises(AssertionError, match="prerelease output is not approved"):
        _assert_frontend_security_target_version(target=target, raw_version="99.0.0-rc.1")


def test_frontend_package_has_ws_override_floor() -> None:
    """RU/EN: package.json override must keep ws at secure floor version."""
    package_json = _load_json(FRONTEND_PACKAGE_JSON)
    overrides = package_json.get("overrides", {})
    ws_override = overrides.get("ws")
    assert isinstance(ws_override, str), "frontend/package.json: overrides.ws missing"
    assert Version(ws_override) >= MIN_WS_VERSION


def test_frontend_lock_resolves_ws_to_safe_npm_release() -> None:
    """RU/EN: package-lock must resolve ws from npm registry."""
    package_lock = _load_json(FRONTEND_LOCK_JSON)
    ws_pkg = package_lock.get("packages", {}).get("node_modules/ws", {})
    lock_version = ws_pkg.get("version")
    resolved = ws_pkg.get("resolved", "")

    assert isinstance(lock_version, str), "frontend/package-lock.json: ws version missing"
    assert Version(lock_version) >= MIN_WS_VERSION
    _assert_npm_registry_resolution(package_name="ws", resolved=resolved)
