"""Deterministic material-diff evidence and strict review-seal primitives.

The embedded Codex Security record is intentionally a human-asserted,
content-bound receipt.  Hashes of local plugin artifacts are useful integrity
evidence, but are not an independently verifiable CI attestation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404: fixed absolute git only (remove-by: 2026-09-30, ref: PR-governance-seal)
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from scripts.orchestration.review_source_status import (
    TERMINAL_NONBLOCKING_STATUSES,
    review_source_policy_projection,
)

MATERIAL_SCHEMA_VERSION = "pulseplate.material-diff/v1"
MATERIAL_POLICY_VERSION = "pulseplate.material-classification/v1"
MATERIAL_DOMAIN = b"pulseplate-material-diff/v1\0"
REVIEW_FINGERPRINT_DOMAIN = b"pulseplate-review-finding/v1\0"
UNAVAILABLE_REVIEW_REF_CAUSE = "unavailable_review_ref_ancestry"
CODEX_REVIEW_SOURCE = "codex-github-review"
SEAL_SCHEMA_VERSION = "pulseplate.pr-review-seal/v1"
RECEIPT_AUTHORITY = "human_asserted_content_receipt"
OPERATOR_OUTAGE_AUTHORITY = "operator_outage_override"
OPERATOR_OUTAGE_CLASS = "codex_security_mcp_timeout"
OPERATOR_OUTAGE_ERROR_CODE = "-32001"
OPERATOR_OUTAGE_ERROR_MESSAGE = "Request timed out"
OPERATOR_OUTAGE_BOOTSTRAP_REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
OPERATOR_OUTAGE_BOOTSTRAP_PR = 2142
REVIEW_CREDIT_OUTAGE_AUTHORITY = "operator_review_credit_exhaustion_override"
REVIEW_CREDIT_OUTAGE_CLASS = "codex_review_credits_exhausted"
REVIEW_CREDIT_OUTAGE_BOOTSTRAP_REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
REVIEW_CREDIT_OUTAGE_BOOTSTRAP_PR = 2142
REVIEW_SOURCE_UNAVAILABILITY_SCHEMA_VERSION = "pulseplate.codex-review-source-unavailability/v1"
REVIEW_SOURCE_UNAVAILABILITY_AUTHORITY = "trusted_codex_review_source_unavailability"
REVIEW_SOURCE_UNAVAILABILITY_SOURCE = "codex_review"
REVIEW_SOURCE_POSITIVE_RESPONSE_SCHEMA_VERSION = (
    "pulseplate.codex-review-source-positive-response/v1"
)
REVIEW_SOURCE_POSITIVE_RESPONSE_AUTHORITY = "trusted_codex_review_source_positive_response"
REVIEW_SOURCE_POSITIVE_RESPONSE_SOURCE = "codex_review"
ADVISORY_CAPABILITY_SCHEMA_VERSION = "pulseplate.advisory-capability-source/v1"
ADVISORY_CAPABILITY_AUTHORITY = "advisory_capability_source"
SELF_REVIEW_SCHEMA_VERSION = "pulseplate.pr-self-review-receipt/v1"
SELF_REVIEW_AUTHORITY = "advisory_only_self_review"
SELF_REVIEW_PRODUCER = {"name": "pulseplate-pr-review", "version": "1.0.0"}
SELF_REVIEW_REPORT_DOMAIN = b"pulseplate-pr-self-review-report/v1\0"
SELF_REVIEW_RECEIPT_DOMAIN = b"pulseplate-pr-self-review-receipt/v1\0"
ADVISORY_CAPABILITY_MARKER_PATH = "docs/orchestration/contracts/advisory_capability_sources.v1.json"
ADVISORY_CAPABILITY_MARKER = {
    "activation": "authenticated_base_and_unique_merge_base",
    "authority": "advisory_only_no_claim",
    "connector": {
        "outputRequired": False,
        "reviewClaim": "none",
    },
    "policyVersion": "pulseplate.advisory-capability-sources/v1",
    "security": {
        "outputRequired": False,
        "scanClaim": "none",
        "substituteSecurityBundleRequired": True,
    },
}
OPERATOR_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS = frozenset(
    {
        ".bandit",
        ".bandit.yaml",
        ".pre-commit-config.yaml",
        ".secrets.baseline",
        ".trivyignore",
        "AGENTS.md",
        "Makefile",
        "RUNBOOK_AGENT.md",
        "constraints.txt",
        "docs/orchestration/AGENTS.md",
        "docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md",
        "docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
        ADVISORY_CAPABILITY_MARKER_PATH,
        "docs/orchestration/contracts/review_source_status.v1.json",
        "scripts/ci_bandit.sh",
        "scripts/ci_pip_audit.sh",
        "scripts/hooks/repo_python.sh",
        "scripts/run-backend-tests-pre-commit.sh",
        "scripts/orchestration/check_merge_ready.py",
        "scripts/orchestration/check_review_threads_disposition.py",
        "scripts/orchestration/pr_commit_identity.py",
        "scripts/orchestration/pr_review_closeout.py",
        "scripts/orchestration/pr_review_evidence.py",
        "scripts/orchestration/requested_agents.py",
        "scripts/orchestration/review_mapping_artifact.py",
        "scripts/orchestration/review_source_status.py",
        "scripts/orchestration/qoder_dispatch_bridge.py",
        "scripts/orchestration/render_codex_start_prompt.py",
        "scripts/orchestration/role_dispatch_bridge.py",
        "scripts/orchestration/task_bootstrap.py",
        "tests/fixtures/dependency_security_schema.json",
        "tests/test_dependency_security_guard.py",
        "tests/test_repo_policy_guards.py",
    }
)
OPERATOR_OUTAGE_TRUST_BOUNDARY_PREFIXES = (
    ".github/actions/",
    ".github/workflows/",
    "scripts/ci/",
    "tests/guards/",
    "trivy/",
)
ADVISORY_CAPABILITY_ADDITIONAL_AUTHORIZING_PATHS = frozenset(
    {
        ".agents/skills/pulseplate-pr-review/SKILL.md",
        ADVISORY_CAPABILITY_MARKER_PATH,
        "scripts/ci/check_pr_merge_readiness.py",
        "scripts/orchestration/pr_review_context.py",
        "scripts/orchestration/pr_review_report.py",
        "tools/codex_skills/pulseplate-pr-review/SKILL.md",
    }
)
ADVISORY_CAPABILITY_AUTHORIZING_PATHS = (
    OPERATOR_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS | ADVISORY_CAPABILITY_ADDITIONAL_AUTHORIZING_PATHS
)
ADVISORY_CAPABILITY_AUTHORIZING_PREFIXES = OPERATOR_OUTAGE_TRUST_BOUNDARY_PREFIXES
REVIEW_CREDIT_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS = frozenset(
    {
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md",
        "docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
        "scripts/ci/ci_risk_profile.py",
        "scripts/ci/check_current_head_pr_checks.py",
        "scripts/ci/check_pr_body_phase2_gates.py",
        "scripts/ci/check_pr_merge_readiness.py",
        "scripts/orchestration/check_merge_ready.py",
        "scripts/orchestration/check_review_threads_disposition.py",
        "scripts/orchestration/pr_commit_identity.py",
        "scripts/orchestration/pr_review_closeout.py",
        "scripts/orchestration/pr_review_evidence.py",
        "scripts/orchestration/review_mapping_artifact.py",
    }
)
REVIEW_CREDIT_OUTAGE_TRUST_BOUNDARY_PREFIXES = (
    ".github/actions/",
    ".github/workflows/",
)
SEAL_BEGIN = "\n".join(
    (
        "<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->",
        "<!-- pragma: allowlist nextline secret -->",
    )
)
SEAL_END = "<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_SELF_REVIEW_REPORT_ID_RE = re.compile(r"^self-review-[0-9a-f]{64}$")
_CANONICAL_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_ROOT_REQUIREMENTS_MANIFEST_RE = re.compile(r"^requirements(?:-[a-z0-9][a-z0-9-]*)?\.(?:in|txt)$")
_DEPENDENCY_MANIFEST_BASENAMES = frozenset(
    {
        "Cargo.lock",
        "Cargo.toml",
        "Gemfile",
        "Gemfile.lock",
        "Package.resolved",
        "Package.swift",
        "Pipfile",
        "Pipfile.lock",
        "Podfile",
        "Podfile.lock",
        "composer.json",
        "composer.lock",
        "constraints.txt",
        "go.mod",
        "go.sum",
        "npm-shrinkwrap.json",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pylock.toml",
        "pyproject.toml",
        "uv.lock",
        "yarn.lock",
    }
)
_SNAPSHOT_DIGEST_RE = re.compile(r"^codex-security-snapshot/v1:sha256:[0-9a-f]{64}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_RAW_HEADER_RE = re.compile(rb"^:([0-7]{6}) ([0-7]{6}) ([0-9a-f]{40}) ([0-9a-f]{40}) ([ADMT])$")
_ZERO_SHA = "0" * 40
_MAX_MANIFEST_BYTES = 2 * 1024 * 1024
_MAX_JSON_ARTIFACT_BYTES = 8 * 1024 * 1024
_MAX_LEDGER_BYTES = 32 * 1024 * 1024
_MAX_SCAN_ARTIFACTS = 64
_MAX_TOTAL_SCAN_ARTIFACT_BYTES = 64 * 1024 * 1024
_DUPLICATE_REPLY_KEYS = (
    "Disposition",
    "Fingerprint",
    "Duplicate-Of",
    "Evidence",
    "Reason",
)


class ReviewEvidenceError(RuntimeError):
    """Raised when material or review evidence is malformed or incomplete."""


@dataclass(frozen=True)
class MaterialEntry:
    status: str
    path: str
    base_mode: str
    base_blob_oid: str | None
    head_mode: str
    head_blob_oid: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "base_blob_oid": self.base_blob_oid,
            "base_mode": self.base_mode,
            "head_blob_oid": self.head_blob_oid,
            "head_mode": self.head_mode,
            "path": self.path,
            "status": self.status,
        }


@dataclass(frozen=True)
class MaterialManifest:
    base_ref_oid: str
    head_ref_oid: str
    merge_base_sha: str
    pr_number: int
    entries: tuple[MaterialEntry, ...]
    digest: str

    def identity_payload(self) -> dict[str, Any]:
        return {
            "entries": [entry.as_dict() for entry in self.entries],
            "merge_base_sha": self.merge_base_sha,
            "policy_version": MATERIAL_POLICY_VERSION,
            "schema_version": MATERIAL_SCHEMA_VERSION,
        }


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReviewEvidenceError(f"JSON contains duplicate key {key!r}")
        result[key] = value
    return result


def _load_json_bytes(raw: bytes, *, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewEvidenceError(f"{label} is not valid UTF-8 JSON") from exc


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ReviewEvidenceError(f"{label} keys mismatch: missing={missing!r} unknown={unknown!r}")


def _require_sha(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ReviewEvidenceError(f"{label} must be a full lowercase 40-character SHA")
    return value


def _require_digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ReviewEvidenceError(f"{label} must use sha256:<64 lowercase hex>")
    return value


def unavailable_review_ref_fingerprint(
    *, pr_number: int, material_digest: str, verified_real_fix_sha: str
) -> str:
    """Return the sole deterministic v1 duplicate-finding fingerprint."""

    if pr_number <= 0:
        raise ReviewEvidenceError("pr_number must be positive")
    digest = _require_digest(material_digest, label="material_digest")
    fix_sha = _require_sha(verified_real_fix_sha, label="verified_real_fix_sha")
    payload = {
        "cause": UNAVAILABLE_REVIEW_REF_CAUSE,
        "material_digest": digest,
        "pr_number": pr_number,
        "source": CODEX_REVIEW_SOURCE,
        "verified_real_fix_sha": fix_sha,
    }
    return (
        "sha256:"
        + hashlib.sha256(
            REVIEW_FINGERPRINT_DOMAIN + _canonical_json(payload).encode("utf-8")
        ).hexdigest()
    )


def parse_duplicate_disposition_reply(body: str) -> str:
    """Parse the exact closed reply contract and return its fingerprint."""

    if not isinstance(body, str) or len(body.encode("utf-8")) > 16 * 1024:
        raise ReviewEvidenceError("duplicate disposition reply is malformed")
    lines = body.strip().splitlines()
    if len(lines) != len(_DUPLICATE_REPLY_KEYS):
        raise ReviewEvidenceError("duplicate disposition reply must use five exact fields")
    values: dict[str, str] = {}
    for line, expected_key in zip(lines, _DUPLICATE_REPLY_KEYS, strict=True):
        prefix = f"{expected_key}:"
        if not line.startswith(prefix):
            raise ReviewEvidenceError(f"duplicate disposition reply expected {expected_key}:")
        value = line.removeprefix(prefix).strip()
        if not value:
            raise ReviewEvidenceError("duplicate disposition reply fields must not be empty")
        values[expected_key] = value
    fingerprint = values["Fingerprint"]
    if (
        values["Disposition"] != "NOT-A-BUG"
        or not _DIGEST_RE.fullmatch(fingerprint)
        or values["Duplicate-Of"] != fingerprint
        or values["Evidence"] != "material digest and verified FIX SHA"
        or values["Reason"] != "reviewer ref is unavailable; canonical disposition reused"
    ):
        raise ReviewEvidenceError("duplicate disposition reply does not match v1 contract")
    return fingerprint


def review_finding_sha_candidates(body: str) -> tuple[str, ...]:
    """Return bounded full SHA candidates only for an unambiguous ancestry finding."""

    if not isinstance(body, str) or len(body.encode("utf-8")) > 256 * 1024:
        raise ReviewEvidenceError("review finding body is malformed")
    lowered = body.lower()
    cause_terms = ("ancestry", "ancestor", "reachable", "commit graph", "merge-base")
    if not any(term in lowered for term in cause_terms):
        raise ReviewEvidenceError("review finding is not an ancestry cause")
    candidates = tuple(sorted(set(re.findall(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", body))))
    if not candidates or len(candidates) > 3:
        raise ReviewEvidenceError("review finding has ambiguous commit references")
    return candidates


def _review_finding_mentions_fix(body: str, verified_fix: str) -> bool:
    if verified_fix in body:
        return True
    for prefix in re.findall(r"(?<![0-9a-f])([0-9a-f]{7,39})(?:\.\.\.|…)", body):
        if verified_fix.startswith(prefix):
            return True
    return False


def validated_duplicate_reply_urls(
    *,
    candidate_urls: set[str],
    threads: tuple[Any, ...],
    fingerprint_records: Mapping[str, Any],
    material_digest: str,
    repo_root: Path,
    snapshot: Any,
    repository: str,
    token: str,
) -> set[str]:
    """Return candidate URLs covered by the closed v1 duplicate-reply contract."""

    from scripts.orchestration.pr_commit_identity import (
        CommitRefKind,
        RepositoryCommitRef,
        classify_commit_ref,
        is_ancestor,
    )

    comment_locations: dict[str, tuple[Any, int]] = {}
    for thread in threads:
        for index, comment in enumerate(thread.comments):
            if comment.url in comment_locations:
                raise ReviewEvidenceError("review comment URL appears in multiple threads")
            comment_locations[comment.url] = (thread, index)

    live_head = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
    authorized_associations = {"OWNER", "MEMBER", "COLLABORATOR"}
    original_commit_digests: dict[str, str] = {}

    def original_commit_digest(commit_sha: str) -> str:
        cached = original_commit_digests.get(commit_sha)
        if cached is not None:
            return cached
        digest = compute_material_manifest(
            repo_root,
            base_ref_oid=snapshot.base_sha,
            head_ref_oid=commit_sha,
            pr_number=snapshot.pr_number,
        ).digest
        original_commit_digests[commit_sha] = digest
        return digest

    def validate_finding(record: Any, thread: Any, finding_index: int) -> datetime:
        finding = thread.comments[finding_index]
        if (
            not thread.is_resolved
            or finding.author_login.strip().lower() != "chatgpt-codex-connector"
            or not finding.original_commit_sha
            or finding.original_commit_sha not in snapshot.commit_shas
        ):
            raise ReviewEvidenceError(
                "unavailable-ref finding lacks trusted resolved live PR context"
            )
        if original_commit_digest(finding.original_commit_sha) != material_digest:
            raise ReviewEvidenceError(
                "unavailable-ref finding originalCommit has a different material digest"
            )
        candidates = review_finding_sha_candidates(finding.body)
        if not _review_finding_mentions_fix(finding.body, record.verified_fix):
            raise ReviewEvidenceError("unavailable-ref finding does not cite verified FIX")
        resolutions = [
            classify_commit_ref(candidate, snapshot, token=token) for candidate in candidates
        ]
        if any(
            getattr(resolution, "kind", None) is CommitRefKind.API_UNKNOWN
            for resolution in resolutions
        ):
            raise ReviewEvidenceError("review finding commit identity is API_UNKNOWN")
        unavailable = [
            resolution
            for resolution in resolutions
            if getattr(resolution, "kind", None) is CommitRefKind.REVIEW_REF_UNAVAILABLE
        ]
        repository_shas = {
            resolution.sha
            for resolution in resolutions
            if isinstance(resolution, RepositoryCommitRef)
        }
        if len(unavailable) != 1 or repository_shas - {record.verified_fix}:
            raise ReviewEvidenceError("review finding ancestry cause is ambiguous")
        return _parse_timestamp(finding.created_at, label="review finding createdAt")

    validated_records: dict[str, tuple[Any, datetime]] = {}
    for fingerprint, record in fingerprint_records.items():
        if record.material_digest != material_digest or len(record.urls) != 1:
            raise ReviewEvidenceError("canonical fingerprint record identity is invalid")
        location = comment_locations.get(record.urls[0])
        if location is None or location[1] != 0:
            raise ReviewEvidenceError("canonical fingerprint URL is not a live thread root")
        fix_resolution = classify_commit_ref(record.verified_fix, snapshot, token=token)
        if not isinstance(fix_resolution, RepositoryCommitRef) or fix_resolution.kind not in {
            CommitRefKind.PR_HEAD,
            CommitRefKind.PR_COMMIT,
        }:
            raise ReviewEvidenceError("canonical verified FIX is not a real PR commit")
        if not is_ancestor(
            fix_resolution,
            live_head,
            repository=repository,
            token=token,
        ):
            raise ReviewEvidenceError("canonical verified FIX is not reachable from live head")
        canonical_time = validate_finding(record, location[0], location[1])
        validated_records[fingerprint] = (record, canonical_time)

    covered: set[str] = set()
    for url in sorted(candidate_urls):
        location = comment_locations.get(url)
        if location is None:
            continue
        thread, finding_index = location
        finding = thread.comments[finding_index]
        valid_fingerprints: list[str] = []
        finding_time = _parse_timestamp(finding.created_at, label="duplicate finding createdAt")
        for reply in thread.comments[finding_index + 1 :]:
            if reply.author_association not in authorized_associations:
                continue
            try:
                fingerprint = parse_duplicate_disposition_reply(reply.body)
            except ReviewEvidenceError:
                continue
            reply_time = _parse_timestamp(reply.created_at, label="duplicate reply createdAt")
            if reply_time > finding_time:
                valid_fingerprints.append(fingerprint)
        if len(valid_fingerprints) != 1:
            continue
        validated = validated_records.get(valid_fingerprints[0])
        if validated is None:
            continue
        record, canonical_time = validated
        if url == record.urls[0] or finding_time <= canonical_time:
            continue
        try:
            validate_finding(record, thread, finding_index)
        except ReviewEvidenceError as exc:
            if "API_UNKNOWN" in str(exc):
                raise
            continue
        covered.add(url)
    return covered


def _git_path() -> str:
    path = shutil.which("git")
    if not path:
        raise ReviewEvidenceError("git not found in PATH")
    try:
        return str(Path(path).resolve(strict=True))
    except OSError as exc:
        raise ReviewEvidenceError("git executable could not be resolved") from exc


def _git_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    return env


def _run_git(
    repo_root: Path,
    args: list[str],
    *,
    timeout: int = 30,
    input_bytes: bytes | None = None,
) -> bytes:
    git = _git_path()
    result = subprocess.run(  # nosec B603: absolute git plus validated fixed argv (remove-by: 2026-09-30, ref: PR-governance-seal)
        [git, *args],
        cwd=repo_root,
        env=_git_environment(),
        input=input_bytes,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewEvidenceError(f"git {' '.join(args[:2])} failed: {diagnostic}")
    return result.stdout


def _validate_material_path(path_bytes: bytes) -> str:
    try:
        path = path_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReviewEvidenceError("Git diff contains a non-UTF-8 path") from exc
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in PurePosixPath(path).parts)
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    ):
        raise ReviewEvidenceError(f"Git diff contains unsafe path {path!r}")
    return path


def _protected_material_paths(
    material_paths: Iterable[str],
    *,
    exact_paths: frozenset[str],
    prefixes: tuple[str, ...],
    include_dependency_manifests: bool = False,
) -> tuple[str, ...]:
    """Return the deterministic protected subset for one authority boundary."""

    return tuple(
        sorted(
            {
                path
                for path in material_paths
                if path in exact_paths
                or path.startswith(prefixes)
                or (
                    include_dependency_manifests
                    and (
                        PurePosixPath(path).name in _DEPENDENCY_MANIFEST_BASENAMES
                        or _ROOT_REQUIREMENTS_MANIFEST_RE.fullmatch(PurePosixPath(path).name)
                    )
                )
            }
        )
    )


def _parse_raw_diff(raw: bytes, *, excluded_path: str) -> tuple[MaterialEntry, ...]:
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 2:
        raise ReviewEvidenceError("git diff-tree raw stream has incomplete record")
    entries: list[MaterialEntry] = []
    seen_paths: set[str] = set()
    for index in range(0, len(fields), 2):
        header, path_bytes = fields[index], fields[index + 1]
        match = _RAW_HEADER_RE.fullmatch(header)
        if not match:
            raise ReviewEvidenceError("git diff-tree raw stream contains unsupported record")
        base_mode_b, head_mode_b, base_oid_b, head_oid_b, status_b = match.groups()
        base_mode = base_mode_b.decode("ascii")
        head_mode = head_mode_b.decode("ascii")
        base_oid = base_oid_b.decode("ascii")
        head_oid = head_oid_b.decode("ascii")
        status = status_b.decode("ascii")
        path = _validate_material_path(path_bytes)
        if path in seen_paths:
            raise ReviewEvidenceError(f"git diff-tree emitted duplicate path {path!r}")
        seen_paths.add(path)

        if status == "A":
            valid_shape = (
                base_mode == "000000"
                and base_oid == _ZERO_SHA
                and (head_mode != "000000" and head_oid != _ZERO_SHA)
            )
        elif status == "D":
            valid_shape = (
                head_mode == "000000"
                and head_oid == _ZERO_SHA
                and (base_mode != "000000" and base_oid != _ZERO_SHA)
            )
        else:
            valid_shape = (
                base_mode != "000000"
                and head_mode != "000000"
                and base_oid != _ZERO_SHA
                and head_oid != _ZERO_SHA
            )
        if not valid_shape:
            raise ReviewEvidenceError(f"git diff-tree emitted invalid {status} record for {path}")
        if path == excluded_path:
            continue
        entries.append(
            MaterialEntry(
                status=status,
                path=path,
                base_mode=base_mode,
                base_blob_oid=None if base_oid == _ZERO_SHA else base_oid,
                head_mode=head_mode,
                head_blob_oid=None if head_oid == _ZERO_SHA else head_oid,
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.path.encode("utf-8")))


def compute_material_manifest(
    repo_root: Path,
    *,
    base_ref_oid: str,
    head_ref_oid: str,
    pr_number: int,
) -> MaterialManifest:
    """Compute a content-addressed manifest from exact Git tree objects."""

    base_sha = _require_sha(base_ref_oid, label="base_ref_oid")
    head_sha = _require_sha(head_ref_oid, label="head_ref_oid")
    if pr_number <= 0:
        raise ReviewEvidenceError("pr_number must be positive")
    root = repo_root.resolve(strict=True)
    if not (root / ".git").exists():
        # Git worktrees use a .git file, so existence rather than directory is intentional.
        raise ReviewEvidenceError("repo_root is not a Git checkout")

    merge_base_raw = _run_git(root, ["merge-base", "--all", base_sha, head_sha])
    merge_bases = [line for line in merge_base_raw.decode("ascii").splitlines() if line]
    if len(merge_bases) != 1:
        raise ReviewEvidenceError("base/head must have exactly one merge base")
    merge_base = _require_sha(merge_bases[0], label="merge base")
    try:
        _run_git(root, ["merge-base", "--is-ancestor", merge_base, base_sha])
        _run_git(root, ["merge-base", "--is-ancestor", merge_base, head_sha])
    except ReviewEvidenceError as exc:
        raise ReviewEvidenceError(
            "computed merge base is not an ancestor of both live refs"
        ) from exc
    raw = _run_git(
        root,
        [
            "diff-tree",
            "-r",
            "--raw",
            "-z",
            "--full-index",
            "--no-abbrev",
            "--no-renames",
            "--no-commit-id",
            "--no-ext-diff",
            "--no-textconv",
            merge_base,
            head_sha,
            "--",
        ],
    )
    excluded_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    entries = _parse_raw_diff(raw, excluded_path=excluded_path)
    identity = {
        "entries": [entry.as_dict() for entry in entries],
        "merge_base_sha": merge_base,
        "policy_version": MATERIAL_POLICY_VERSION,
        "schema_version": MATERIAL_SCHEMA_VERSION,
    }
    digest = (
        "sha256:"
        + hashlib.sha256(MATERIAL_DOMAIN + _canonical_json(identity).encode("utf-8")).hexdigest()
    )
    return MaterialManifest(
        base_ref_oid=base_sha,
        head_ref_oid=head_sha,
        merge_base_sha=merge_base,
        pr_number=pr_number,
        entries=entries,
        digest=digest,
    )


def advisory_capability_marker_bytes() -> bytes:
    """Return the one byte-exact activation marker accepted by strict gates."""

    return (
        json.dumps(
            ADVISORY_CAPABILITY_MARKER,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _advisory_capability_inactive(detail: str) -> ReviewEvidenceError:
    return ReviewEvidenceError(
        "ADVISORY_CAPABILITY_INACTIVE: "
        f"{detail}; recovery: merge the prerequisite into the authenticated base, "
        "refresh the PR from that base so the marker is in the unique merge-base, "
        "then freeze and seal again"
    )


def _require_advisory_marker_at_revision(
    repo_root: Path,
    *,
    revision: str,
    label: str,
    expected_bytes: bytes,
    expected_oid: str,
) -> None:
    raw_entry = _run_git(
        repo_root,
        [
            "ls-tree",
            "-z",
            "--full-tree",
            revision,
            "--",
            ADVISORY_CAPABILITY_MARKER_PATH,
        ],
    )
    if not raw_entry:
        raise _advisory_capability_inactive(f"marker missing from {label}")
    if not raw_entry.endswith(b"\0"):
        raise _advisory_capability_inactive(f"marker tree entry is malformed in {label}")
    records = raw_entry[:-1].split(b"\0")
    if len(records) != 1:
        raise _advisory_capability_inactive(f"marker must be exactly one 100644 blob in {label}")
    try:
        metadata, path = records[0].split(b"\t", 1)
        mode, object_type, raw_oid = metadata.split(b" ")
        oid = raw_oid.decode("ascii")
    except (UnicodeDecodeError, ValueError) as exc:
        raise _advisory_capability_inactive(f"marker tree entry is malformed in {label}") from exc
    if (
        path != ADVISORY_CAPABILITY_MARKER_PATH.encode()
        or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", oid) is None
    ):
        raise _advisory_capability_inactive(f"marker tree entry is malformed in {label}")
    if mode != b"100644" or object_type != b"blob":
        raise _advisory_capability_inactive(f"marker must be exactly one 100644 blob in {label}")
    if oid != expected_oid:
        raise _advisory_capability_inactive(f"marker blob OID differs in {label}")
    try:
        marker = _run_git(repo_root, ["cat-file", "blob", oid])
    except ReviewEvidenceError as exc:
        raise _advisory_capability_inactive(f"marker blob is unavailable in {label}") from exc
    if marker != expected_bytes:
        raise _advisory_capability_inactive(f"marker bytes differ in {label}")


def validate_advisory_capability_activation(
    repo_root: Path,
    *,
    base_ref_oid: str,
    head_ref_oid: str,
    material_paths: Iterable[str],
) -> str:
    """Require an already-merged marker and deny changes to its authority path."""

    touched = _protected_material_paths(
        material_paths,
        exact_paths=ADVISORY_CAPABILITY_AUTHORIZING_PATHS,
        prefixes=ADVISORY_CAPABILITY_AUTHORIZING_PREFIXES,
        include_dependency_manifests=True,
    )
    if touched:
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_SELF_USE_DENIED: current material changes "
            "authorizing paths: " + ", ".join(touched)
        )
    base_sha = _require_sha(base_ref_oid, label="advisory capability base_ref_oid")
    head_sha = _require_sha(head_ref_oid, label="advisory capability head_ref_oid")
    root = repo_root.resolve(strict=True)
    merge_base_raw = _run_git(root, ["merge-base", "--all", base_sha, head_sha])
    merge_bases = [line for line in merge_base_raw.decode("ascii").splitlines() if line]
    if len(merge_bases) != 1:
        raise _advisory_capability_inactive("base/head must have exactly one unique merge-base")
    merge_base_sha = _require_sha(
        merge_bases[0],
        label="advisory capability merge base",
    )
    expected = advisory_capability_marker_bytes()
    raw_expected_oid = _run_git(
        root,
        ["hash-object", "--stdin"],
        input_bytes=expected,
    )
    expected_oid_lines = raw_expected_oid.decode("ascii", errors="replace").splitlines()
    if (
        len(expected_oid_lines) != 1
        or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected_oid_lines[0]) is None
    ):
        raise _advisory_capability_inactive("canonical marker blob OID is malformed")
    expected_oid = expected_oid_lines[0]
    for label, revision in (
        ("authenticated base", base_sha),
        ("unique merge-base", merge_base_sha),
    ):
        _require_advisory_marker_at_revision(
            root,
            revision=revision,
            label=label,
            expected_bytes=expected,
            expected_oid=expected_oid,
        )
    return merge_base_sha


def _require_canonical_mapping_blob_at_revision(
    repo_root: Path,
    *,
    revision: str,
    expected_path: str,
) -> None:
    """Require one regular canonical mapping blob at the accepted live revision."""

    raw_entry = _run_git(
        repo_root,
        [
            "ls-tree",
            "-z",
            "--full-tree",
            revision,
            "--",
            expected_path,
        ],
    )
    if not raw_entry:
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: canonical mapping artifact is missing at "
            f"{expected_path}"
        )
    if not raw_entry.endswith(b"\0"):
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: canonical mapping tree entry is malformed at "
            f"{expected_path}"
        )
    records = raw_entry[:-1].split(b"\0")
    if len(records) != 1:
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: canonical mapping artifact must be "
            f"exactly one regular 100644 blob at {expected_path}"
        )
    try:
        metadata, path = records[0].split(b"\t", 1)
        mode, object_type, raw_oid = metadata.split(b" ")
        oid = raw_oid.decode("ascii")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: canonical mapping tree entry is malformed at "
            f"{expected_path}"
        ) from exc
    if (
        path != expected_path.encode()
        or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", oid) is None
    ):
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: canonical mapping tree entry is malformed at "
            f"{expected_path}"
        )
    if mode != b"100644" or object_type != b"blob":
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: canonical mapping artifact must be "
            f"exactly one regular 100644 blob at {expected_path}"
        )


def validate_advisory_live_head_topology(
    repo_root: Path,
    *,
    material_head_sha: str,
    live_head_sha: str,
    pr_number: int,
    phase: str,
) -> None:
    """Require the exact pre-closeout head or one direct mapping-only child."""

    material_head = _require_sha(material_head_sha, label="advisory material head")
    live_head = _require_sha(live_head_sha, label="advisory live head")
    if pr_number <= 0:
        raise ReviewEvidenceError("pr_number must be positive")
    if phase not in {"pre_closeout", "final"}:
        raise ReviewEvidenceError("advisory live-head phase is unsupported")
    if phase == "pre_closeout":
        if live_head != material_head:
            raise ReviewEvidenceError(
                "ADVISORY_CAPABILITY_HEAD_INVALID: pre-closeout live head must equal material head"
            )
        return
    if live_head == material_head:
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: final live head must be one mapping-only child"
        )

    root = repo_root.resolve(strict=True)
    raw_parents = _run_git(root, ["rev-list", "--parents", "-n", "1", live_head])
    try:
        parent_lines = raw_parents.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: live commit parents are malformed"
        ) from exc
    if len(parent_lines) != 1 or parent_lines[0].split() != [live_head, material_head]:
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: final live head must be one direct child "
            "of material head"
        )

    expected_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    _require_canonical_mapping_blob_at_revision(
        root,
        revision=live_head,
        expected_path=expected_path,
    )
    raw_paths = _run_git(
        root,
        [
            "diff-tree",
            "-r",
            "--name-only",
            "-z",
            "--no-commit-id",
            "--no-renames",
            material_head,
            live_head,
            "--",
        ],
    )
    if raw_paths and not raw_paths.endswith(b"\0"):
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: mapping successor diff is malformed"
        )
    paths = tuple(
        _validate_material_path(path) for path in (raw_paths[:-1].split(b"\0") if raw_paths else ())
    )
    if paths != (expected_path,):
        raise ReviewEvidenceError(
            "ADVISORY_CAPABILITY_HEAD_INVALID: final child must change only " f"{expected_path}"
        )


def validate_live_advisory_capability_receipts(
    repo_root: Path,
    *,
    connector_receipt: Any,
    security_receipt: Any,
    self_review_receipt: Any,
    base_ref_oid: str,
    material_head_sha: str,
    live_head_sha: str,
    material_digest: str,
    pr_number: int,
    live_material_paths: Iterable[str],
    phase: str,
    self_review_semantic_digest: str,
) -> None:
    """Revalidate one linked advisory pair against live material and topology."""

    if not is_advisory_capability_connector_receipt(
        connector_receipt
    ) or not is_advisory_capability_security_receipt(security_receipt):
        raise ReviewEvidenceError(
            "advisory capability mode requires linked Connector and Security receipts"
        )
    validate_self_review_receipt(
        self_review_receipt,
        material_head_sha=material_head_sha,
        material_digest=material_digest,
        report_semantic_digest=self_review_semantic_digest,
    )
    validate_advisory_live_head_topology(
        repo_root,
        material_head_sha=material_head_sha,
        live_head_sha=live_head_sha,
        pr_number=pr_number,
        phase=phase,
    )
    material_manifest = compute_material_manifest(
        repo_root,
        base_ref_oid=base_ref_oid,
        head_ref_oid=material_head_sha,
        pr_number=pr_number,
    )
    if material_manifest.digest != material_digest:
        raise ReviewEvidenceError(
            "advisory capability material head has a different material digest"
        )
    activated_merge_base = validate_advisory_capability_activation(
        repo_root,
        base_ref_oid=base_ref_oid,
        head_ref_oid=live_head_sha,
        material_paths=live_material_paths,
    )
    expected_connector, expected_security = build_advisory_capability_receipts(
        base_revision=activated_merge_base,
        head_revision=material_head_sha,
        material_digest=material_digest,
    )
    if connector_receipt != expected_connector or security_receipt != expected_security:
        raise ReviewEvidenceError("advisory capability receipts are stale")


def _safe_relative_artifact_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ReviewEvidenceError("scan artifact path must be a non-empty POSIX path")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ReviewEvidenceError("scan artifact path escapes the scan root")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts:
        raise ReviewEvidenceError("scan artifact path escapes the scan root")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ReviewEvidenceError("scan artifact path contains control characters")
    return path


def _read_regular_descriptor(descriptor: int, *, max_bytes: int, label: str) -> bytes:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        raise ReviewEvidenceError(f"{label} must be a regular file")
    if before.st_size > max_bytes:
        raise ReviewEvidenceError(f"{label} exceeds size limit")
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining > 0:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    raw = b"".join(chunks)
    after = os.fstat(descriptor)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if len(raw) > max_bytes:
        raise ReviewEvidenceError(f"{label} exceeds size limit")
    if before_identity != after_identity or len(raw) != before.st_size:
        raise ReviewEvidenceError(f"{label} changed while it was read")
    return raw


def _open_scan_root(root: Path) -> int:
    try:
        return os.open(
            root,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise ReviewEvidenceError("scan root could not be opened safely") from exc


def _open_contained_artifact_descriptor(
    root_descriptor: int,
    relative: PurePosixPath,
) -> int:
    """Open one regular-file candidate beneath an immutable scan-root descriptor."""

    descriptor = os.dup(root_descriptor)
    try:
        for part in relative.parts[:-1]:
            try:
                next_descriptor = os.open(
                    part,
                    os.O_RDONLY
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_DIRECTORY", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=descriptor,
                )
            except OSError as exc:
                raise ReviewEvidenceError(
                    "scan artifact parent is missing, unsafe, or not a directory"
                ) from exc
            os.close(descriptor)
            descriptor = next_descriptor
        try:
            file_descriptor = os.open(
                relative.parts[-1],
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0),
                dir_fd=descriptor,
            )
        except OSError as exc:
            raise ReviewEvidenceError(
                "scan artifact path contains a symlink or is missing"
            ) from exc
        return file_descriptor
    finally:
        os.close(descriptor)


def _read_contained_artifact_from_descriptor(
    root_descriptor: int,
    relative: PurePosixPath,
    *,
    max_bytes: int,
) -> bytes:
    """Read beneath one immutable scan-root descriptor without following symlinks."""

    descriptor = _open_contained_artifact_descriptor(root_descriptor, relative)
    try:
        return _read_regular_descriptor(descriptor, max_bytes=max_bytes, label=str(relative))
    finally:
        os.close(descriptor)


def _hash_contained_artifact_from_descriptor(
    root_descriptor: int,
    relative: PurePosixPath,
    *,
    max_bytes: int,
) -> tuple[str, int]:
    """Hash one contained regular file without retaining its payload in memory."""

    descriptor = _open_contained_artifact_descriptor(root_descriptor, relative)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ReviewEvidenceError(f"{relative} must be a regular file")
        if before.st_size > max_bytes:
            raise ReviewEvidenceError(f"{relative} exceeds size limit")
        digest = hashlib.sha256()
        bytes_read = 0
        while bytes_read <= max_bytes:
            chunk = os.read(
                descriptor,
                min(1024 * 1024, max_bytes + 1 - bytes_read),
            )
            if not chunk:
                break
            digest.update(chunk)
            bytes_read += len(chunk)
        after = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if bytes_read > max_bytes:
            raise ReviewEvidenceError(f"{relative} exceeds size limit")
        if before_identity != after_identity or bytes_read != before.st_size:
            raise ReviewEvidenceError(f"{relative} changed while it was read")
        return digest.hexdigest(), bytes_read
    finally:
        os.close(descriptor)


def _parse_timestamp(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str):
        raise ReviewEvidenceError(f"{label} must be an ISO-8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReviewEvidenceError(f"{label} must be an ISO-8601 string") from exc
    if parsed.tzinfo is None:
        raise ReviewEvidenceError(f"{label} must include a timezone")
    return parsed


def _ingest_codex_security_receipt_from_descriptor(
    root_descriptor: int,
    *,
    expected_base_sha: str,
    expected_head_sha: str,
) -> dict[str, Any]:
    """Validate one completed bundle through a stable scan-root descriptor."""
    expected_base = _require_sha(expected_base_sha, label="expected_base_sha")
    expected_head = _require_sha(expected_head_sha, label="expected_head_sha")
    manifest_raw = _read_contained_artifact_from_descriptor(
        root_descriptor,
        PurePosixPath("scan-manifest.json"),
        max_bytes=_MAX_MANIFEST_BYTES,
    )
    manifest = _load_json_bytes(manifest_raw, label="scan-manifest.json")
    if not isinstance(manifest, dict):
        raise ReviewEvidenceError("scan-manifest.json must contain an object")
    _require_exact_keys(
        manifest,
        {"documentType", "scan", "schemaVersion"},
        label="scan manifest",
    )
    if (
        manifest["documentType"] != "codex-security.scan-manifest"
        or manifest["schemaVersion"] != "1.0"
        or not isinstance(manifest["scan"], dict)
    ):
        raise ReviewEvidenceError("unsupported Codex Security manifest schema")
    scan = manifest["scan"]
    _require_exact_keys(
        scan,
        {
            "artifacts",
            "completedAt",
            "coverageRef",
            "findingsRef",
            "id",
            "producer",
            "scope",
            "sealedAt",
            "startedAt",
            "status",
            "target",
            "threatModel",
        }
        | ({"hardening"} if "hardening" in scan else set()),
        label="scan",
    )
    if scan["status"] != "completed":
        raise ReviewEvidenceError("Codex Security scan is not completed")
    started = _parse_timestamp(scan["startedAt"], label="scan.startedAt")
    completed = _parse_timestamp(scan["completedAt"], label="scan.completedAt")
    sealed = _parse_timestamp(scan["sealedAt"], label="scan.sealedAt")
    if not started <= completed <= sealed:
        raise ReviewEvidenceError("Codex Security scan timestamps are inconsistent")
    scan_id = scan["id"]
    if not isinstance(scan_id, str) or not _UUID_RE.fullmatch(scan_id):
        raise ReviewEvidenceError("scan.id must be a lowercase UUID")
    if not isinstance(scan["scope"], dict) or not isinstance(scan["threatModel"], dict):
        raise ReviewEvidenceError("scan scope and threatModel must be objects")
    if "hardening" in scan:
        hardening = scan["hardening"]
        if not isinstance(hardening, dict):
            raise ReviewEvidenceError("scan.hardening must be an object")
        _require_exact_keys(hardening, {"portfolioPath"}, label="scan.hardening")
        if hardening["portfolioPath"] != "hardening/hardening.md":
            raise ReviewEvidenceError("scan.hardening must use the canonical portfolio path")

    producer = scan["producer"]
    if not isinstance(producer, dict):
        raise ReviewEvidenceError("scan.producer must be an object")
    _require_exact_keys(producer, {"name", "version"}, label="scan.producer")
    if (
        producer["name"] != "codex-security-plugin"
        or not isinstance(producer["version"], str)
        or not _VERSION_RE.fullmatch(producer["version"])
    ):
        raise ReviewEvidenceError("scan producer is not a supported Codex Security plugin")

    target = scan["target"]
    if not isinstance(target, dict):
        raise ReviewEvidenceError("scan.target must be an object")
    _require_exact_keys(
        target,
        {"baseRevision", "displayName", "headRevision", "kind", "snapshotDigest", "targetId"}
        | ({"remote"} if "remote" in target else set())
        | ({"revision"} if "revision" in target else set()),
        label="scan.target",
    )
    if (
        target["kind"] != "git_diff"
        or target["baseRevision"] != expected_base
        or target["headRevision"] != expected_head
        or not isinstance(target["snapshotDigest"], str)
        or not _SNAPSHOT_DIGEST_RE.fullmatch(target["snapshotDigest"])
        or not isinstance(target["targetId"], str)
        or not re.fullmatch(r"target_sha256_[0-9a-f]{64}", target["targetId"])
    ):
        raise ReviewEvidenceError("scan target does not match the expected Git diff")
    if "revision" in target and (
        not isinstance(target["revision"], str)
        or target["revision"] != target["headRevision"]
        or target["revision"] != expected_head
    ):
        raise ReviewEvidenceError(
            "scan.target.revision must exactly match the expected Git diff head"
        )
    if (
        "remote" in target
        and target["remote"] != "https://github.com/Katsiarynakavaleuskaya/PulsePlate"
    ):
        raise ReviewEvidenceError("scan.target.remote must use the canonical PulsePlate repository")

    if scan["coverageRef"] != "coverage.json" or scan["findingsRef"] != "findings.json":
        raise ReviewEvidenceError("scan coverage/findings refs must use canonical filenames")
    artifacts = scan["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) < 3:
        raise ReviewEvidenceError("scan must list the three canonical artifacts")
    if len(artifacts) > _MAX_SCAN_ARTIFACTS:
        raise ReviewEvidenceError("scan artifact count exceeds limit")
    artifact_specs: dict[str, tuple[str, str]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ReviewEvidenceError("scan artifact entry must be an object")
        _require_exact_keys(artifact, {"mediaType", "path", "sha256"}, label="scan artifact")
        path = str(_safe_relative_artifact_path(artifact["path"]))
        digest = artifact["sha256"]
        media_type = artifact["mediaType"]
        if path in artifact_specs:
            raise ReviewEvidenceError("scan artifact paths must be unique")
        if not isinstance(digest, str) or not _RAW_DIGEST_RE.fullmatch(digest):
            raise ReviewEvidenceError("scan artifact sha256 is malformed")
        if not isinstance(media_type, str) or not media_type:
            raise ReviewEvidenceError("scan artifact mediaType must be a non-empty string")
        artifact_specs[path] = (media_type, digest)
    expected_paths = {
        "coverage.json": "application/json",
        "findings.json": "application/json",
        "artifacts/02_discovery/work_ledger.jsonl": "application/octet-stream",
    }
    for path, media_type in expected_paths.items():
        if artifact_specs.get(path, (None, None))[0] != media_type:
            raise ReviewEvidenceError(
                "scan artifact inventory does not contain the v1 canonical artifacts"
            )

    canonical_payloads: dict[str, bytes] = {}
    total_artifact_bytes = 0
    for path, (_media_type, expected_digest) in artifact_specs.items():
        limit = _MAX_LEDGER_BYTES if path.endswith(".jsonl") else _MAX_JSON_ARTIFACT_BYTES
        if path in {"coverage.json", "findings.json"}:
            raw = _read_contained_artifact_from_descriptor(
                root_descriptor, PurePosixPath(path), max_bytes=limit
            )
            actual_digest = hashlib.sha256(raw).hexdigest()
            artifact_bytes = len(raw)
            canonical_payloads[path] = raw
        else:
            actual_digest, artifact_bytes = _hash_contained_artifact_from_descriptor(
                root_descriptor,
                PurePosixPath(path),
                max_bytes=limit,
            )
        total_artifact_bytes += artifact_bytes
        if total_artifact_bytes > _MAX_TOTAL_SCAN_ARTIFACT_BYTES:
            raise ReviewEvidenceError("scan artifact aggregate size exceeds limit")
        if actual_digest != expected_digest:
            raise ReviewEvidenceError(f"scan artifact hash mismatch for {path}")

    coverage = _load_json_bytes(canonical_payloads["coverage.json"], label="coverage.json")
    if not isinstance(coverage, dict):
        raise ReviewEvidenceError("coverage.json must contain an object")
    required_coverage_keys = {
        "completeness",
        "deferred",
        "documentType",
        "excludePaths",
        "explicitExclusions",
        "includePaths",
        "inventoryStrategy",
        "mode",
        "scanId",
        "schemaVersion",
        "surfaces",
    }
    optional_coverage_keys = {"openQuestions"}
    coverage_keys = set(coverage)
    missing_coverage_keys = sorted(required_coverage_keys - coverage_keys)
    unknown_coverage_keys = sorted(coverage_keys - required_coverage_keys - optional_coverage_keys)
    if missing_coverage_keys or unknown_coverage_keys:
        raise ReviewEvidenceError(
            "coverage keys mismatch: "
            f"missing={missing_coverage_keys!r} unknown={unknown_coverage_keys!r}"
        )
    if (
        coverage["documentType"] != "codex-security.coverage"
        or coverage["schemaVersion"] != "1.0"
        or coverage["scanId"] != scan_id
        or coverage["completeness"] != "complete"
        or coverage["deferred"] != []
        or coverage.get("openQuestions", []) != []
    ):
        raise ReviewEvidenceError("Codex Security coverage is incomplete or inconsistent")

    findings = _load_json_bytes(canonical_payloads["findings.json"], label="findings.json")
    if not isinstance(findings, dict):
        raise ReviewEvidenceError("findings.json must contain an object")
    _require_exact_keys(
        findings,
        {"documentType", "findings", "scanId", "schemaVersion"},
        label="findings",
    )
    if (
        findings["documentType"] != "codex-security.findings"
        or findings["schemaVersion"] != "1.0"
        or findings["scanId"] != scan_id
        or findings["findings"] != []
    ):
        raise ReviewEvidenceError("final Codex Security scan must contain zero findings")

    return {
        "artifacts": {
            "coverage_sha256": f"sha256:{artifact_specs['coverage.json'][1]}",
            "findings_sha256": f"sha256:{artifact_specs['findings.json'][1]}",
            "work_ledger_sha256": (
                "sha256:" + artifact_specs["artifacts/02_discovery/work_ledger.jsonl"][1]
            ),
        },
        "authority": RECEIPT_AUTHORITY,
        "base_revision": expected_base,
        "coverage_completeness": "complete",
        "findings_count": 0,
        "head_revision": expected_head,
        "manifest_sha256": "sha256:" + hashlib.sha256(manifest_raw).hexdigest(),
        "producer": {"name": producer["name"], "version": producer["version"]},
        "scan_id": scan_id,
        "snapshot_digest": target["snapshotDigest"],
    }


def ingest_codex_security_receipt(
    manifest_path: Path,
    *,
    expected_base_sha: str,
    expected_head_sha: str,
) -> dict[str, Any]:
    """Validate one completed plugin bundle and return a bounded human receipt."""

    if manifest_path.name != "scan-manifest.json":
        raise ReviewEvidenceError("Codex Security manifest must be named scan-manifest.json")
    root_descriptor = _open_scan_root(manifest_path.parent)
    try:
        return _ingest_codex_security_receipt_from_descriptor(
            root_descriptor,
            expected_base_sha=expected_base_sha,
            expected_head_sha=expected_head_sha,
        )
    finally:
        os.close(root_descriptor)


def _require_canonical_utc(value: Any, *, label: str) -> str:
    """Require a second-precision canonical UTC timestamp."""

    if not isinstance(value, str) or _CANONICAL_UTC_RE.fullmatch(value) is None:
        raise ReviewEvidenceError(f"{label} must use canonical YYYY-MM-DDTHH:MM:SSZ UTC")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ReviewEvidenceError(f"{label} must use canonical YYYY-MM-DDTHH:MM:SSZ UTC") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ReviewEvidenceError(f"{label} must use canonical YYYY-MM-DDTHH:MM:SSZ UTC")
    return value


def build_self_review_receipt(
    *,
    material_head_sha: str,
    material_digest: str,
    completed_at: str,
    unresolved_actionables: int,
    report_content_digest: str,
    report_semantic_digest: str,
) -> dict[str, Any]:
    """Build one closed exact-material repo-native self-review receipt."""

    if (
        not isinstance(unresolved_actionables, int)
        or isinstance(unresolved_actionables, bool)
        or unresolved_actionables != 0
    ):
        raise ReviewEvidenceError("self-review receipt requires zero unresolved actionables")
    payload = {
        "authority": SELF_REVIEW_AUTHORITY,
        "completed_at": _require_canonical_utc(
            completed_at,
            label="self_review.completed_at",
        ),
        "material_digest": _require_digest(
            material_digest,
            label="self_review.material_digest",
        ),
        "material_head_sha": _require_sha(
            material_head_sha,
            label="self_review.material_head_sha",
        ),
        "producer": dict(SELF_REVIEW_PRODUCER),
        "report_semantic_digest": _require_digest(
            report_semantic_digest,
            label="self-review report semantic digest",
        ),
        "schema_version": SELF_REVIEW_SCHEMA_VERSION,
        "status": "completed",
        "unresolved_actionables": unresolved_actionables,
    }
    report_digest = _require_digest(
        report_content_digest,
        label="self-review report content digest",
    )
    report_id = f"self-review-{report_digest.removeprefix('sha256:')}"
    receipt_digest = hashlib.sha256(
        SELF_REVIEW_RECEIPT_DOMAIN
        + _canonical_json({**payload, "report_id": report_id}).encode("utf-8")
    ).hexdigest()
    receipt = {
        **payload,
        "content_digest": f"sha256:{receipt_digest}",
        "report_id": report_id,
    }
    validate_self_review_receipt(receipt)
    return receipt


def self_review_report_content_digest(report: dict[str, Any]) -> str:
    """Hash canonical review-report content without its circular receipt field."""

    report_content = dict(report)
    report_content.pop("self_review_receipt", None)
    digest = hashlib.sha256(
        SELF_REVIEW_REPORT_DOMAIN + _canonical_json(report_content).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def self_review_report_semantic_digest(report: dict[str, Any]) -> str:
    """Hash deterministic review semantics while excluding execution metadata."""

    semantic = dict(report)
    semantic.pop("self_review_receipt", None)
    semantic.pop("generated_at_utc", None)
    semantic.pop("coordinator_packet", None)
    digest = hashlib.sha256(
        SELF_REVIEW_REPORT_DOMAIN + _canonical_json(semantic).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def validate_self_review_receipt(
    receipt: Any,
    *,
    material_head_sha: str | None = None,
    material_digest: str | None = None,
    report_content_digest: str | None = None,
    report_semantic_digest: str | None = None,
) -> dict[str, Any]:
    """Validate and optionally bind one closed self-review receipt."""

    if not isinstance(receipt, dict):
        raise ReviewEvidenceError("self_review must be an object")
    _require_exact_keys(
        receipt,
        {
            "authority",
            "completed_at",
            "content_digest",
            "material_digest",
            "material_head_sha",
            "producer",
            "report_id",
            "report_semantic_digest",
            "schema_version",
            "status",
            "unresolved_actionables",
        },
        label="self_review",
    )
    if (
        receipt["schema_version"] != SELF_REVIEW_SCHEMA_VERSION
        or receipt["authority"] != SELF_REVIEW_AUTHORITY
        or receipt["status"] != "completed"
        or receipt["producer"] != SELF_REVIEW_PRODUCER
    ):
        raise ReviewEvidenceError("self_review schema, authority, status, or producer is invalid")
    completed_at = _require_canonical_utc(
        receipt["completed_at"],
        label="self_review.completed_at",
    )
    head = _require_sha(
        receipt["material_head_sha"],
        label="self_review.material_head_sha",
    )
    digest = _require_digest(
        receipt["material_digest"],
        label="self_review.material_digest",
    )
    unresolved = receipt["unresolved_actionables"]
    if not isinstance(unresolved, int) or isinstance(unresolved, bool) or unresolved != 0:
        raise ReviewEvidenceError("self_review requires zero unresolved actionables")
    content_digest = _require_digest(
        receipt["content_digest"],
        label="self_review.content_digest",
    )
    report_id = receipt["report_id"]
    if not isinstance(report_id, str) or _SELF_REVIEW_REPORT_ID_RE.fullmatch(report_id) is None:
        raise ReviewEvidenceError("self_review.report_id is malformed")
    semantic_digest = _require_digest(
        receipt["report_semantic_digest"],
        label="self_review.report_semantic_digest",
    )
    payload = {
        "authority": receipt["authority"],
        "completed_at": completed_at,
        "material_digest": digest,
        "material_head_sha": head,
        "producer": receipt["producer"],
        "report_id": report_id,
        "report_semantic_digest": semantic_digest,
        "schema_version": receipt["schema_version"],
        "status": receipt["status"],
        "unresolved_actionables": unresolved,
    }
    expected_receipt_digest = hashlib.sha256(
        SELF_REVIEW_RECEIPT_DOMAIN + _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    if content_digest != f"sha256:{expected_receipt_digest}":
        raise ReviewEvidenceError("self_review content digest or report id is invalid")
    if report_content_digest is not None:
        expected_report_digest = _require_digest(
            report_content_digest,
            label="expected self-review report content digest",
        )
        expected_report_id = f"self-review-{expected_report_digest.removeprefix('sha256:')}"
        if report_id != expected_report_id:
            raise ReviewEvidenceError("self_review does not match canonical report content")
    if report_semantic_digest is not None and semantic_digest != _require_digest(
        report_semantic_digest,
        label="expected self-review report semantic digest",
    ):
        raise ReviewEvidenceError("self_review does not match canonical report semantics")
    if material_head_sha is not None and head != _require_sha(
        material_head_sha,
        label="expected self-review material head",
    ):
        raise ReviewEvidenceError("self_review does not match sealed material head")
    if material_digest is not None and digest != _require_digest(
        material_digest,
        label="expected self-review material digest",
    ):
        raise ReviewEvidenceError("self_review does not match sealed material digest")
    return receipt


def _report_unresolved_actionables(findings: Any) -> int:
    """Count unresolved actionable review findings, excluding planning notes."""

    if not isinstance(findings, list):
        raise ReviewEvidenceError("self-review report findings must be an array")
    unresolved = 0
    for finding in findings:
        if not isinstance(finding, dict):
            raise ReviewEvidenceError("self-review report finding must be an object")
        severity = finding.get("severity")
        disposition = finding.get("disposition_candidate")
        if severity in {"critical", "major", "minor"} and disposition == "NEEDS-HUMAN":
            unresolved += 1
    return unresolved


def ingest_self_review_report(
    report_path: Path,
    *,
    expected_head_sha: str,
    expected_material_digest: str,
    expected_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Safely ingest one repo-native self-review report and return its receipt."""

    if report_path.suffix != ".json":
        raise ReviewEvidenceError("self-review report must be a JSON file")
    root_descriptor = _open_scan_root(report_path.parent)
    try:
        raw = _read_contained_artifact_from_descriptor(
            root_descriptor,
            _safe_relative_artifact_path(report_path.name),
            max_bytes=_MAX_JSON_ARTIFACT_BYTES,
        )
    finally:
        os.close(root_descriptor)
    report = _load_json_bytes(raw, label="self-review report")
    if not isinstance(report, dict):
        raise ReviewEvidenceError("self-review report must contain an object")
    if report.get("schema_version") != "1.0.0" or report.get("mode") != "dry-run-report":
        raise ReviewEvidenceError("self-review report schema or mode is unsupported")
    report_digest = self_review_report_content_digest(report)
    semantic_digest = self_review_report_semantic_digest(report)
    receipt = validate_self_review_receipt(
        report.get("self_review_receipt"),
        material_head_sha=expected_head_sha,
        material_digest=expected_material_digest,
        report_content_digest=report_digest,
        report_semantic_digest=semantic_digest,
    )
    if report.get("generated_at_utc") != receipt["completed_at"]:
        raise ReviewEvidenceError("self-review report timestamp does not match its receipt")
    if _report_unresolved_actionables(report.get("findings")) != 0:
        raise ReviewEvidenceError("self-review report contains unresolved actionables")
    if expected_report is not None and self_review_report_semantic_digest(
        report
    ) != self_review_report_semantic_digest(expected_report):
        raise ReviewEvidenceError("self-review report does not match canonical live review context")
    return receipt


def build_advisory_capability_receipts(
    *,
    base_revision: str,
    head_revision: str,
    material_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build two closed no-claim receipts for optional capability outputs."""

    connector = {
        "authority": ADVISORY_CAPABILITY_AUTHORITY,
        "binding_kind": "seal_context_only",
        "blocking": False,
        "capability_source": "codex_connector",
        "material_digest": material_digest,
        "material_head_sha": head_revision,
        "output_required": False,
        "review_claim": "none",
        "schema_version": ADVISORY_CAPABILITY_SCHEMA_VERSION,
        "status": "advisory_optional",
    }
    security = {
        "authority": ADVISORY_CAPABILITY_AUTHORITY,
        "base_revision": base_revision,
        "binding_kind": "seal_context_only",
        "blocking": False,
        "capability_source": "codex_security_plugin",
        "head_revision": head_revision,
        "material_digest": material_digest,
        "no_findings_claim": False,
        "output_required": False,
        "scan_claim": "none",
        "scan_id": None,
        "schema_version": ADVISORY_CAPABILITY_SCHEMA_VERSION,
        "status": "advisory_optional",
        "substitute_security_bundle_required": True,
    }
    _validate_code_review_receipt(connector, material_digest=material_digest)
    _validate_security_receipt(security)
    return connector, security


def is_advisory_capability_connector_receipt(receipt: Any) -> bool:
    return (
        isinstance(receipt, dict)
        and receipt.get("schema_version") == ADVISORY_CAPABILITY_SCHEMA_VERSION
        and receipt.get("authority") == ADVISORY_CAPABILITY_AUTHORITY
        and receipt.get("capability_source") == "codex_connector"
    )


def is_advisory_capability_security_receipt(receipt: Any) -> bool:
    return (
        isinstance(receipt, dict)
        and receipt.get("schema_version") == ADVISORY_CAPABILITY_SCHEMA_VERSION
        and receipt.get("authority") == ADVISORY_CAPABILITY_AUTHORITY
        and receipt.get("capability_source") == "codex_security_plugin"
    )


def build_security_outage_override_receipt(
    *,
    base_revision: str,
    head_revision: str,
    material_digest: str,
    override_reference: str,
    created_at: str,
    operator_user_id: int,
    operator_login: str,
    operator_association: str,
) -> dict[str, Any]:
    """Build one validated, distinct operator-outage evidence receipt."""

    receipt = {
        "authority": OPERATOR_OUTAGE_AUTHORITY,
        "base_revision": base_revision,
        "created_at": created_at,
        "error_code": OPERATOR_OUTAGE_ERROR_CODE,
        "error_message": OPERATOR_OUTAGE_ERROR_MESSAGE,
        "head_revision": head_revision,
        "material_digest": material_digest,
        "operator_association": operator_association,
        "operator_login": operator_login,
        "operator_user_id": operator_user_id,
        "outage_class": OPERATOR_OUTAGE_CLASS,
        "override_reference": override_reference,
        "scan_id": None,
        "status": "tooling_unavailable",
    }
    _validate_security_receipt(receipt)
    return receipt


def build_review_credit_outage_receipt(
    *,
    material_digest: str,
    material_head_sha: str,
    override_reference: str,
    override_created_at: str,
    quota_reference: str,
    quota_created_at: str,
    prior_review_reference: str,
    prior_review_submitted_at: str,
    prior_review_commit_ref: str,
    operator_review_reference: str,
    operator_review_submitted_at: str,
    operator_user_id: int,
    operator_login: str,
    operator_association: str,
) -> dict[str, Any]:
    """Build a closed receipt for one independently evidenced credit outage."""

    receipt = {
        "authority": REVIEW_CREDIT_OUTAGE_AUTHORITY,
        "operator_association": operator_association,
        "operator_login": operator_login,
        "operator_review_submitted_at": operator_review_submitted_at,
        "operator_user_id": operator_user_id,
        "outage_class": REVIEW_CREDIT_OUTAGE_CLASS,
        "override_created_at": override_created_at,
        "override_reference": override_reference,
        "prior_review_commit_ref": prior_review_commit_ref,
        "prior_review_reference": prior_review_reference,
        "prior_review_submitted_at": prior_review_submitted_at,
        "quota_created_at": quota_created_at,
        "quota_reference": quota_reference,
        "review_commit_ref": material_head_sha,
        "review_commit_ref_kind": "repository_commit",
        "review_reference": operator_review_reference,
        "reviewed_material_digest": material_digest,
        "status": "tooling_unavailable",
    }
    _validate_code_review_receipt(receipt, material_digest=material_digest)
    return receipt


def build_review_source_unavailability_receipt(
    *,
    material_digest: str,
    material_head_sha: str,
    quota_reference: str,
    quota_created_at: str,
    quota_body_sha256: str,
    source_status: str,
) -> dict[str, Any]:
    """Build a material-context receipt for one trusted terminal quota response."""

    policy = review_source_policy_projection()
    terminal = policy["terminal_unavailability"]
    if not isinstance(terminal, dict):
        raise ReviewEvidenceError("review-source policy projection is malformed")
    receipt = {
        "authority": REVIEW_SOURCE_UNAVAILABILITY_AUTHORITY,
        "binding_kind": "seal_context_only",
        "blocking": terminal["blocking"],
        "fallback_required": terminal["fallback_required"],
        "material_digest": material_digest,
        "material_head_sha": material_head_sha,
        "quota_body_sha256": quota_body_sha256,
        "quota_created_at": quota_created_at,
        "quota_reference": quota_reference,
        "review_claim": terminal["review_claim"],
        "schema_version": REVIEW_SOURCE_UNAVAILABILITY_SCHEMA_VERSION,
        "source": REVIEW_SOURCE_UNAVAILABILITY_SOURCE,
        "source_degraded": terminal["source_degraded"],
        "source_status": source_status,
        "status": "tooling_unavailable",
    }
    _validate_code_review_receipt(receipt, material_digest=material_digest)
    return receipt


def build_review_source_positive_response_receipt(
    *,
    material_digest: str,
    material_head_sha: str,
    response_reference: str,
    response_created_at: str,
    response_content: str,
) -> dict[str, Any]:
    """Build a material-context receipt for one trusted positive response."""

    receipt = {
        "authority": REVIEW_SOURCE_POSITIVE_RESPONSE_AUTHORITY,
        "binding_kind": "seal_context_only",
        "blocking": False,
        "fallback_required": False,
        "material_digest": material_digest,
        "material_head_sha": material_head_sha,
        "response_content": response_content,
        "response_created_at": response_created_at,
        "response_reference": response_reference,
        "review_claim": "none",
        "schema_version": REVIEW_SOURCE_POSITIVE_RESPONSE_SCHEMA_VERSION,
        "source": REVIEW_SOURCE_POSITIVE_RESPONSE_SOURCE,
        "source_degraded": False,
        "source_status": "positive_response",
        "status": "completed",
    }
    _validate_code_review_receipt(receipt, material_digest=material_digest)
    return receipt


def is_review_source_unavailability_receipt(receipt: Any) -> bool:
    """Return whether code-review evidence uses the tagged quota variant."""

    return (
        isinstance(receipt, dict)
        and receipt.get("schema_version") == REVIEW_SOURCE_UNAVAILABILITY_SCHEMA_VERSION
        and receipt.get("authority") == REVIEW_SOURCE_UNAVAILABILITY_AUTHORITY
    )


def is_review_source_positive_response_receipt(receipt: Any) -> bool:
    """Return whether code-review evidence uses the positive-response variant."""

    return (
        isinstance(receipt, dict)
        and receipt.get("schema_version") == REVIEW_SOURCE_POSITIVE_RESPONSE_SCHEMA_VERSION
        and receipt.get("authority") == REVIEW_SOURCE_POSITIVE_RESPONSE_AUTHORITY
    )


def is_mapping_only_positive_response_successor(
    receipt: Any,
    *,
    response_reference: str,
    response_created_at: str,
    response_content: str,
) -> bool:
    """Accept a newer live response only after the sealed response was replaced."""

    if not is_review_source_positive_response_receipt(receipt):
        return False
    try:
        sealed_created = _parse_timestamp(
            receipt.get("response_created_at"),
            label="code_review.response_created_at",
        )
        successor_created = _parse_timestamp(
            response_created_at,
            label="successor response_created_at",
        )
    except ReviewEvidenceError:
        return False
    return (
        response_reference != receipt.get("response_reference")
        and response_content == receipt.get("response_content")
        and successor_created > sealed_created
    )


def is_review_credit_outage_receipt(receipt: Any) -> bool:
    """Return whether code-review evidence uses the credit-outage variant."""

    return isinstance(receipt, dict) and receipt.get("authority") == REVIEW_CREDIT_OUTAGE_AUTHORITY


def validate_review_credit_outage_scope(
    *, repository: str, pr_number: int, material_paths: Iterable[str]
) -> None:
    """Keep the historical credit-outage receipt live-valid only for PR #2142."""

    touched = _protected_material_paths(
        material_paths,
        exact_paths=REVIEW_CREDIT_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS,
        prefixes=REVIEW_CREDIT_OUTAGE_TRUST_BOUNDARY_PREFIXES,
    )
    is_bootstrap = (
        repository.casefold() == REVIEW_CREDIT_OUTAGE_BOOTSTRAP_REPOSITORY.casefold()
        and pr_number == REVIEW_CREDIT_OUTAGE_BOOTSTRAP_PR
    )
    if is_bootstrap:
        return
    touched_suffix = " Material paths: " + ", ".join(touched) + "." if touched else ""
    raise ReviewEvidenceError(
        "Historical Codex review credit-outage receipts are live-valid only for "
        f"{REVIEW_CREDIT_OUTAGE_BOOTSTRAP_REPOSITORY} PR "
        f"#{REVIEW_CREDIT_OUTAGE_BOOTSTRAP_PR}; later PRs cannot authenticate "
        f"the legacy receipt.{touched_suffix}"
    )


def is_security_outage_override_receipt(receipt: Any) -> bool:
    """Return whether a validated receipt uses the operator-outage variant."""

    return isinstance(receipt, dict) and receipt.get("authority") == OPERATOR_OUTAGE_AUTHORITY


def validate_security_outage_override_scope(
    *, repository: str, pr_number: int, material_paths: Iterable[str]
) -> None:
    """Deny outage self-authorization outside the one reviewed bootstrap PR."""

    touched = _protected_material_paths(
        material_paths,
        exact_paths=OPERATOR_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS,
        prefixes=OPERATOR_OUTAGE_TRUST_BOUNDARY_PREFIXES,
        include_dependency_manifests=True,
    )
    if not touched:
        return
    is_bootstrap = (
        repository.casefold() == OPERATOR_OUTAGE_BOOTSTRAP_REPOSITORY.casefold()
        and pr_number == OPERATOR_OUTAGE_BOOTSTRAP_PR
    )
    if not is_bootstrap:
        raise ReviewEvidenceError(
            "Codex Security outage override cannot authorize trust-boundary changes: "
            + ", ".join(touched)
        )


def _validate_security_receipt(receipt: Any) -> None:
    if not isinstance(receipt, dict):
        raise ReviewEvidenceError("codex_security must be an object")
    if is_advisory_capability_security_receipt(receipt):
        _require_exact_keys(
            receipt,
            {
                "authority",
                "base_revision",
                "binding_kind",
                "blocking",
                "capability_source",
                "head_revision",
                "material_digest",
                "no_findings_claim",
                "output_required",
                "scan_claim",
                "scan_id",
                "schema_version",
                "status",
                "substitute_security_bundle_required",
            },
            label="codex_security advisory capability",
        )
        _require_sha(receipt["base_revision"], label="codex_security.base_revision")
        _require_sha(receipt["head_revision"], label="codex_security.head_revision")
        _require_digest(receipt["material_digest"], label="codex_security.material_digest")
        if (
            receipt["binding_kind"] != "seal_context_only"
            or receipt["blocking"] is not False
            or receipt["no_findings_claim"] is not False
            or receipt["output_required"] is not False
            or receipt["scan_claim"] != "none"
            or receipt["scan_id"] is not None
            or receipt["status"] != "advisory_optional"
            or receipt["substitute_security_bundle_required"] is not True
        ):
            raise ReviewEvidenceError("Codex Security advisory capability receipt is malformed")
        return
    if receipt.get("authority") == OPERATOR_OUTAGE_AUTHORITY:
        _require_exact_keys(
            receipt,
            {
                "authority",
                "base_revision",
                "created_at",
                "error_code",
                "error_message",
                "head_revision",
                "material_digest",
                "operator_association",
                "operator_login",
                "operator_user_id",
                "outage_class",
                "override_reference",
                "scan_id",
                "status",
            },
            label="codex_security operator outage override",
        )
        _require_sha(receipt["base_revision"], label="codex_security.base_revision")
        _require_sha(receipt["head_revision"], label="codex_security.head_revision")
        _require_digest(receipt["material_digest"], label="codex_security.material_digest")
        _parse_timestamp(receipt["created_at"], label="codex_security.created_at")
        if (
            receipt["outage_class"] != OPERATOR_OUTAGE_CLASS
            or receipt["error_code"] != OPERATOR_OUTAGE_ERROR_CODE
            or receipt["error_message"] != OPERATOR_OUTAGE_ERROR_MESSAGE
            or receipt["scan_id"] is not None
            or receipt["status"] != "tooling_unavailable"
            or receipt["operator_association"] not in {"OWNER", "MEMBER"}
            or not isinstance(receipt["operator_user_id"], int)
            or isinstance(receipt["operator_user_id"], bool)
            or receipt["operator_user_id"] <= 0
            or not isinstance(receipt["operator_login"], str)
            or not 1 <= len(receipt["operator_login"]) <= 100
            or any(ord(ch) < 32 for ch in receipt["operator_login"])
            or not isinstance(receipt["override_reference"], str)
            or not 1 <= len(receipt["override_reference"]) <= 500
            or any(ord(ch) < 32 for ch in receipt["override_reference"])
        ):
            raise ReviewEvidenceError("Codex Security operator outage override is malformed")
        return
    _require_exact_keys(
        receipt,
        {
            "artifacts",
            "authority",
            "base_revision",
            "coverage_completeness",
            "findings_count",
            "head_revision",
            "manifest_sha256",
            "producer",
            "scan_id",
            "snapshot_digest",
        },
        label="codex_security",
    )
    if receipt["authority"] != RECEIPT_AUTHORITY:
        raise ReviewEvidenceError("Codex Security receipt must remain human-asserted")
    _require_sha(receipt["base_revision"], label="codex_security.base_revision")
    _require_sha(receipt["head_revision"], label="codex_security.head_revision")
    _require_digest(receipt["manifest_sha256"], label="codex_security.manifest_sha256")
    if (
        receipt["coverage_completeness"] != "complete"
        or receipt["findings_count"] != 0
        or not isinstance(receipt["scan_id"], str)
        or not _UUID_RE.fullmatch(receipt["scan_id"])
        or not isinstance(receipt["snapshot_digest"], str)
        or not _SNAPSHOT_DIGEST_RE.fullmatch(receipt["snapshot_digest"])
    ):
        raise ReviewEvidenceError("Codex Security receipt is malformed")
    producer = receipt["producer"]
    if not isinstance(producer, dict):
        raise ReviewEvidenceError("codex_security.producer must be an object")
    _require_exact_keys(producer, {"name", "version"}, label="codex_security.producer")
    if (
        producer["name"] != "codex-security-plugin"
        or not isinstance(producer["version"], str)
        or not _VERSION_RE.fullmatch(producer["version"])
    ):
        raise ReviewEvidenceError("Codex Security receipt producer is malformed")
    artifacts = receipt["artifacts"]
    if not isinstance(artifacts, dict):
        raise ReviewEvidenceError("codex_security.artifacts must be an object")
    _require_exact_keys(
        artifacts,
        {"coverage_sha256", "findings_sha256", "work_ledger_sha256"},
        label="codex_security.artifacts",
    )
    for key, value in artifacts.items():
        _require_digest(value, label=f"codex_security.artifacts.{key}")


def _validate_code_review_receipt(receipt: Any, *, material_digest: str) -> None:
    if not isinstance(receipt, dict):
        raise ReviewEvidenceError("review seal code_review must be an object")
    if is_advisory_capability_connector_receipt(receipt):
        _require_exact_keys(
            receipt,
            {
                "authority",
                "binding_kind",
                "blocking",
                "capability_source",
                "material_digest",
                "material_head_sha",
                "output_required",
                "review_claim",
                "schema_version",
                "status",
            },
            label="review seal code_review advisory capability",
        )
        _require_sha(
            receipt["material_head_sha"],
            label="code_review.material_head_sha",
        )
        _require_digest(
            receipt["material_digest"],
            label="code_review.material_digest",
        )
        if (
            receipt["material_digest"] != material_digest
            or receipt["binding_kind"] != "seal_context_only"
            or receipt["blocking"] is not False
            or receipt["output_required"] is not False
            or receipt["review_claim"] != "none"
            or receipt["status"] != "advisory_optional"
        ):
            raise ReviewEvidenceError(
                "review seal code_review advisory capability receipt is malformed"
            )
        return
    has_source_schema = receipt.get("schema_version") == REVIEW_SOURCE_UNAVAILABILITY_SCHEMA_VERSION
    has_source_authority = receipt.get("authority") == REVIEW_SOURCE_UNAVAILABILITY_AUTHORITY
    if has_source_schema != has_source_authority:
        raise ReviewEvidenceError("review seal code_review tagged-union identity is ambiguous")
    has_positive_schema = (
        receipt.get("schema_version") == REVIEW_SOURCE_POSITIVE_RESPONSE_SCHEMA_VERSION
    )
    has_positive_authority = receipt.get("authority") == REVIEW_SOURCE_POSITIVE_RESPONSE_AUTHORITY
    if has_positive_schema != has_positive_authority:
        raise ReviewEvidenceError("review seal code_review tagged-union identity is ambiguous")
    if has_source_schema and has_positive_schema:
        raise ReviewEvidenceError("review seal code_review tagged-union identity is ambiguous")
    if has_positive_schema:
        _require_exact_keys(
            receipt,
            {
                "authority",
                "binding_kind",
                "blocking",
                "fallback_required",
                "material_digest",
                "material_head_sha",
                "response_content",
                "response_created_at",
                "response_reference",
                "review_claim",
                "schema_version",
                "source",
                "source_degraded",
                "source_status",
                "status",
            },
            label="review seal code_review source positive response",
        )
        _require_sha(receipt["material_head_sha"], label="code_review.material_head_sha")
        _require_digest(receipt["material_digest"], label="code_review.material_digest")
        _parse_timestamp(
            receipt["response_created_at"],
            label="code_review.response_created_at",
        )
        if (
            receipt["material_digest"] != material_digest
            or receipt["source"] != REVIEW_SOURCE_POSITIVE_RESPONSE_SOURCE
            or receipt["source_status"] != "positive_response"
            or receipt["status"] != "completed"
            or receipt["binding_kind"] != "seal_context_only"
            or receipt["review_claim"] != "none"
            or receipt["source_degraded"] is not False
            or receipt["fallback_required"] is not False
            or receipt["blocking"] is not False
            or not isinstance(receipt["response_content"], str)
            or receipt["response_content"] not in {"+1", "heart", "hooray", "rocket"}
            or not isinstance(receipt["response_reference"], str)
            or not 1 <= len(receipt["response_reference"]) <= 500
            or any(ord(ch) < 32 for ch in receipt["response_reference"])
        ):
            raise ReviewEvidenceError(
                "review seal code_review source positive response is malformed or stale"
            )
        return
    if has_source_schema:
        _require_exact_keys(
            receipt,
            {
                "authority",
                "binding_kind",
                "blocking",
                "fallback_required",
                "material_digest",
                "material_head_sha",
                "quota_body_sha256",
                "quota_created_at",
                "quota_reference",
                "review_claim",
                "schema_version",
                "source",
                "source_degraded",
                "source_status",
                "status",
            },
            label="review seal code_review source unavailability",
        )
        _require_sha(
            receipt["material_head_sha"],
            label="code_review.material_head_sha",
        )
        _require_digest(
            receipt["material_digest"],
            label="code_review.material_digest",
        )
        _require_digest(
            receipt["quota_body_sha256"],
            label="code_review.quota_body_sha256",
        )
        _parse_timestamp(
            receipt["quota_created_at"],
            label="code_review.quota_created_at",
        )
        if (
            receipt["material_digest"] != material_digest
            or receipt["source"] != REVIEW_SOURCE_UNAVAILABILITY_SOURCE
            or not isinstance(receipt["source_status"], str)
            or receipt["source_status"] not in TERMINAL_NONBLOCKING_STATUSES
            or receipt["status"] != "tooling_unavailable"
            or receipt["binding_kind"] != "seal_context_only"
            or receipt["review_claim"] != "none"
            or receipt["source_degraded"] is not True
            or receipt["fallback_required"] is not False
            or receipt["blocking"] is not False
            or not isinstance(receipt["quota_reference"], str)
            or not 1 <= len(receipt["quota_reference"]) <= 500
            or any(ord(ch) < 32 for ch in receipt["quota_reference"])
        ):
            raise ReviewEvidenceError(
                "review seal code_review source unavailability is malformed or stale"
            )
        return
    if is_review_credit_outage_receipt(receipt):
        _require_exact_keys(
            receipt,
            {
                "authority",
                "operator_association",
                "operator_login",
                "operator_review_submitted_at",
                "operator_user_id",
                "outage_class",
                "override_created_at",
                "override_reference",
                "prior_review_commit_ref",
                "prior_review_reference",
                "prior_review_submitted_at",
                "quota_created_at",
                "quota_reference",
                "review_commit_ref",
                "review_commit_ref_kind",
                "review_reference",
                "reviewed_material_digest",
                "status",
            },
            label="review seal code_review credit outage override",
        )
        _require_sha(receipt["review_commit_ref"], label="code_review.review_commit_ref")
        _require_sha(
            receipt["prior_review_commit_ref"],
            label="code_review.prior_review_commit_ref",
        )
        _parse_timestamp(
            receipt["override_created_at"],
            label="code_review.override_created_at",
        )
        _parse_timestamp(
            receipt["quota_created_at"],
            label="code_review.quota_created_at",
        )
        _parse_timestamp(
            receipt["prior_review_submitted_at"],
            label="code_review.prior_review_submitted_at",
        )
        _parse_timestamp(
            receipt["operator_review_submitted_at"],
            label="code_review.operator_review_submitted_at",
        )
        references = (
            receipt["review_reference"],
            receipt["override_reference"],
            receipt["quota_reference"],
            receipt["prior_review_reference"],
        )
        if (
            receipt["status"] != "tooling_unavailable"
            or receipt["outage_class"] != REVIEW_CREDIT_OUTAGE_CLASS
            or receipt["reviewed_material_digest"] != material_digest
            or receipt["review_commit_ref_kind"] != "repository_commit"
            or receipt["operator_association"] not in {"OWNER", "MEMBER"}
            or not isinstance(receipt["operator_user_id"], int)
            or isinstance(receipt["operator_user_id"], bool)
            or receipt["operator_user_id"] <= 0
            or not isinstance(receipt["operator_login"], str)
            or not 1 <= len(receipt["operator_login"]) <= 100
            or any(ord(ch) < 32 for ch in receipt["operator_login"])
            or any(
                not isinstance(reference, str)
                or not 1 <= len(reference) <= 500
                or any(ord(ch) < 32 for ch in reference)
                for reference in references
            )
        ):
            raise ReviewEvidenceError(
                "review seal code_review credit outage override is malformed or stale"
            )
        return

    _require_exact_keys(
        receipt,
        {
            "review_commit_ref",
            "review_commit_ref_kind",
            "review_reference",
            "reviewed_material_digest",
            "status",
        },
        label="review seal code_review",
    )
    if (
        receipt["status"] != "completed"
        or receipt["reviewed_material_digest"] != material_digest
        or receipt["review_commit_ref_kind"] != "repository_commit"
        or not isinstance(receipt["review_reference"], str)
        or not 1 <= len(receipt["review_reference"]) <= 500
        or any(ord(ch) < 32 for ch in receipt["review_reference"])
    ):
        raise ReviewEvidenceError("review seal code_review is malformed or stale")
    _require_sha(receipt["review_commit_ref"], label="code_review.review_commit_ref")


def validate_review_seal(seal: Any) -> dict[str, Any]:
    """Validate the closed v1 embedded seal schema and return it unchanged."""

    if not isinstance(seal, dict):
        raise ReviewEvidenceError("review seal must be an object")
    base_keys = {
        "authority",
        "code_review",
        "codex_security",
        "material",
        "pr_number",
        "repository",
        "schema_version",
    }
    actual_keys = frozenset(seal)
    if actual_keys not in {frozenset(base_keys), frozenset((*base_keys, "self_review"))}:
        _require_exact_keys(seal, base_keys, label="review seal")
    if seal["schema_version"] != SEAL_SCHEMA_VERSION or seal["authority"] != RECEIPT_AUTHORITY:
        raise ReviewEvidenceError("unsupported review seal schema or authority")
    if (
        not isinstance(seal["repository"], str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", seal["repository"])
        or not isinstance(seal["pr_number"], int)
        or isinstance(seal["pr_number"], bool)
        or seal["pr_number"] <= 0
    ):
        raise ReviewEvidenceError("review seal repository/pr_number is malformed")
    material = seal["material"]
    if not isinstance(material, dict):
        raise ReviewEvidenceError("review seal material must be an object")
    _require_exact_keys(
        material,
        {"base_ref_oid", "digest", "material_head_sha", "merge_base_sha", "policy_version"},
        label="review seal material",
    )
    _require_sha(material["base_ref_oid"], label="material.base_ref_oid")
    _require_sha(material["material_head_sha"], label="material.material_head_sha")
    _require_sha(material["merge_base_sha"], label="material.merge_base_sha")
    material_digest = _require_digest(material["digest"], label="material.digest")
    if material["policy_version"] != MATERIAL_POLICY_VERSION:
        raise ReviewEvidenceError("review seal material policy version is unsupported")
    code_review = seal["code_review"]
    _validate_code_review_receipt(code_review, material_digest=material_digest)
    advisory_connector = is_advisory_capability_connector_receipt(code_review)
    advisory_security = is_advisory_capability_security_receipt(seal["codex_security"])
    if advisory_connector != advisory_security:
        raise ReviewEvidenceError(
            "advisory capability mode requires linked Connector and Security receipts"
        )
    self_review = seal.get("self_review")
    if self_review is not None:
        if not advisory_connector:
            raise ReviewEvidenceError("self_review is permitted only for advisory capability seals")
        validate_self_review_receipt(
            self_review,
            material_head_sha=material["material_head_sha"],
            material_digest=material_digest,
        )
    if (
        is_review_source_unavailability_receipt(code_review)
        or is_review_source_positive_response_receipt(code_review)
        or advisory_connector
    ) and (code_review["material_head_sha"] != material["material_head_sha"]):
        raise ReviewEvidenceError(
            "review-source context receipt does not match sealed material head"
        )
    _validate_security_receipt(seal["codex_security"])
    if (
        seal["codex_security"]["base_revision"] != material["merge_base_sha"]
        or seal["codex_security"]["head_revision"] != material["material_head_sha"]
    ):
        raise ReviewEvidenceError("Codex Security receipt does not match sealed material range")
    if is_security_outage_override_receipt(seal["codex_security"]) and (
        seal["codex_security"]["material_digest"] != material_digest
    ):
        raise ReviewEvidenceError(
            "Codex Security operator outage override does not match sealed material digest"
        )
    if advisory_security and seal["codex_security"]["material_digest"] != material_digest:
        raise ReviewEvidenceError(
            "Codex Security advisory capability receipt does not match sealed material digest"
        )
    return seal


def render_embedded_review_seal(seal: Mapping[str, Any]) -> str:
    """Render the sole canonical one-line JSON seal block."""

    validated = validate_review_seal(dict(seal))
    return f"{SEAL_BEGIN}\n{_canonical_json(validated)}\n{SEAL_END}"


def parse_embedded_review_seal(markdown_text: str) -> dict[str, Any]:
    """Parse exactly one canonical v1 seal block from a mapping artifact."""

    if markdown_text.count(SEAL_BEGIN) != 1 or markdown_text.count(SEAL_END) != 1:
        raise ReviewEvidenceError("mapping artifact must contain exactly one v1 review seal")
    begin = markdown_text.index(SEAL_BEGIN) + len(SEAL_BEGIN)
    end = markdown_text.index(SEAL_END, begin)
    if markdown_text.find(SEAL_END, begin, end) != -1:
        raise ReviewEvidenceError("mapping artifact contains nested review seal markers")
    payload_text = markdown_text[begin:end]
    if not payload_text.startswith("\n") or not payload_text.endswith("\n"):
        raise ReviewEvidenceError("embedded review seal must use canonical line boundaries")
    payload_text = payload_text[1:-1]
    if not payload_text or "\n" in payload_text or "\r" in payload_text:
        raise ReviewEvidenceError("embedded review seal JSON must occupy one line")
    payload = _load_json_bytes(payload_text.encode("utf-8"), label="embedded review seal")
    validated = validate_review_seal(payload)
    if payload_text != _canonical_json(validated):
        raise ReviewEvidenceError("embedded review seal JSON is not canonical")
    return validated
