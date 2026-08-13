"""Deterministic material-diff evidence and strict review-seal primitives.

The embedded Codex Security record is intentionally a human-asserted,
content-bound receipt.  Hashes of local plugin artifacts are useful integrity
evidence, but are not an independently verifiable CI attestation.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import shutil
import stat
import subprocess  # nosec B404: fixed absolute git only (remove-by: 2026-09-30, ref: PR-governance-seal)
import unicodedata
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from scripts.ci.dependabot_requirement_carriers import (
    is_protected_python_dependency_text_path,
)
from scripts.orchestration.review_source_status import (
    TERMINAL_NONBLOCKING_STATUSES,
    review_source_policy_projection,
)

if TYPE_CHECKING:
    from scripts.orchestration.pr_commit_identity import (
        CommitResolution,
        PrSnapshot,
        ReviewThreadEvidence,
    )

MATERIAL_SCHEMA_VERSION = "pulseplate.material-diff/v1"
MATERIAL_POLICY_VERSION = "pulseplate.material-classification/v1"
MATERIAL_DOMAIN = b"pulseplate-material-diff/v1\0"
REVIEW_FINGERPRINT_DOMAIN = b"pulseplate-review-finding/v1\0"
UNAVAILABLE_REVIEW_REF_CAUSE = "unavailable_review_ref_ancestry"
_OWNER_UNAVAILABLE_REF_REPLY_RE = re.compile(
    r"OWNER NOT-A-BUG: ignore unavailable reviewer ref "
    r"(?P<review_ref>[0-9a-f]{40}); authenticated live PR graph is authoritative\."
)
_OWNER_STALE_SEAL_FIXED_REPLY_RE = re.compile(
    r"OWNER FIXED: stale seal at (?P<stale_head>[0-9a-f]{40}) is corrected by "
    r"mapping-only reseal (?P<reseal>[0-9a-f]{40}); authenticated live PR graph "
    r"is authoritative\."
)
_MAX_REPOSITORY_ACTIVITY_PAGES = 100
_GITHUB_PAGINATION_QUERY_KEYS = frozenset({"after", "cursor", "page"})
TRIGGER_ONLY_COMMIT_SUBJECT_RE = re.compile(
    r"(?:^|\b)(trigger\s+ci|re-?run\s+ci|re-?run\s+checks)(?:\b|$)",
    re.IGNORECASE,
)
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
SELF_REVIEW_REPORT_SCHEMA_VERSION = "2.0.0"
SELF_REVIEW_ADVISORY_SCHEMA_VERSION = "pulseplate.self-review-advisory/v1"
REPO_NATIVE_SELF_REVIEW_AUTHORITY = "repo_native_pulseplate_pr_review_advisory"
REPO_NATIVE_SELF_REVIEW_TOOL = "pulseplate-pr-review"
REPO_NATIVE_SELF_REVIEW_STATUS = "advisory_report_attached"
SELF_REVIEW_ALLOWED_SEVERITIES = frozenset({"critical", "major", "minor", "note"})
SELF_REVIEW_ACTIONABLE_SEVERITIES = frozenset({"critical", "major", "minor"})
SELF_REVIEW_NONBLOCKING_NOTE_CODES = frozenset({"large_diff_review_risk"})
SELF_REVIEW_LARGE_DIFF_CHANGED_LINES = 300
SELF_REVIEW_VERY_LARGE_DIFF_CHANGED_LINES = 800
_REPO_ROOT = Path(__file__).resolve().parents[2]
SELF_REVIEW_DIAGNOSTIC_MIN_SEVERITY = {
    "blocking_review_source": "minor",
    "context_warning": "minor",
    "invalid_changed_lines": "minor",
    "invalid_fixed_mapping": "minor",
    "large_diff_review_risk": "note",
    "missing_pr_metadata": "minor",
    "missing_scoped_agents": "minor",
}
SELF_REVIEW_FINDING_KEYS = frozenset(
    {
        "category",
        "diagnostic_code",
        "disposition_candidate",
        "evidence",
        "file",
        "gate_to_run",
        "line",
        "role_agent",
        "severity",
        "suggested_fix",
    }
)
SELF_REVIEW_REPORT_KEYS = frozenset(
    {
        "actionable_findings_count",
        "base_ref_oid",
        "calibration",
        "coordinator_packet",
        "decision_log",
        "deferred_followups",
        "findings",
        "findings_count",
        "gate_plan",
        "generated_at_utc",
        "material_digest",
        "material_head_sha",
        "merge_base_sha",
        "mode",
        "review_source_status",
        "role_review",
        "schema_version",
        "scope_reviewed",
        "warnings",
    }
)
PROVIDER_NO_CLAIM_REVIEW_KEYS = frozenset(
    {
        "blocking",
        "material_digest",
        "material_head_sha",
        "output_required",
        "review_claim",
    }
)
REPO_NATIVE_SELF_REVIEW_KEYS = frozenset(
    {
        "actionable_findings_count",
        "authority",
        "blocking",
        "findings_count",
        "material_digest",
        "material_head_sha",
        "report_payload",
        "report_sha256",
        "review_claim",
        "review_tool",
        "schema_version",
        "status",
    }
)
PROVIDER_NO_CLAIM_SECURITY_KEYS = frozenset(
    {
        "base_revision",
        "blocking",
        "head_revision",
        "material_digest",
        "no_findings_claim",
        "output_required",
        "scan_claim",
    }
)
OPERATOR_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS = frozenset(
    {
        ".bandit",
        ".bandit.yaml",
        ".coveragerc",
        ".dockerignore",
        ".flake8",
        ".markdownlint.json",
        ".nvmrc",
        ".pre-commit-config.yaml",
        ".ruff.toml",
        ".secrets.baseline",
        ".trivyignore",
        ".yamllint",
        "AGENTS.md",
        "Dockerfile",
        "Makefile",
        "RUNBOOK_AGENT.md",
        "bmi_visualization.py",
        "conftest.py",
        "constraints.txt",
        "core/bmi/__init__.py",
        "core/bmi/engine.py",
        "core/bmi/query.py",
        "core/bmi/risk.py",
        "docs/design/figma-manifest.json",
        "docs/orchestration/AGENTS.md",
        "docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md",
        "docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md",
        "docs/orchestration/contracts/review_source_status.v1.json",
        "docs/telemetry/docker_image_baseline.production.json",
        "docs/telemetry/docker_image_budget.production.json",
        "pyproject.toml",
        "pytest_sharding.py",
        "pytest.ini",
        "pyrightconfig.json",
        "ruff.toml",
        "scripts/ci_bandit.sh",
        "scripts/ci_pip_audit.sh",
        "scripts/design_guard.py",
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
        "setup.cfg",
        "frontend/.npmrc",
        "tests/conftest.py",
        "tests/fixtures/dependency_security_schema.json",
        "tests/test_dependency_security_guard.py",
        "tests/test_repo_policy_guards.py",
        "tox.ini",
    }
)
OPERATOR_OUTAGE_TRUST_BOUNDARY_PREFIXES = (
    ".github/actions/",
    ".github/codeql/extensions/",
    ".github/workflows/",
    "scripts/ci/",
    "tests/guards/",
    "trivy/",
)
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
_FINDING_SHORT_REF_PATTERN = r"[0-9a-f]{7,39}"
_FINDING_ELLIPSIS_CARRIER_PATTERN = r"(?:\.{3}|…)"
_FINDING_ASCII_HEX_CORE_RE = re.compile(r"[0-9A-Fa-f]+")
_FINDING_VALID_SHORT_REF_TOKEN_RE = re.compile(
    rf"^(?P<short>{_FINDING_SHORT_REF_PATTERN}){_FINDING_ELLIPSIS_CARRIER_PATTERN}$"
)
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CANONICAL_CODEOWNERS_PATHS = frozenset(
    {
        ".github/CODEOWNERS",
        "CODEOWNERS",
        "docs/CODEOWNERS",
    }
)
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
_MAX_SELF_REVIEW_REPORT_BYTES = 8 * 1024 * 1024
_DUPLICATE_REPLY_KEYS = (
    "Disposition",
    "Fingerprint",
    "Duplicate-Of",
    "Evidence",
    "Reason",
)


class ReviewEvidenceError(RuntimeError):
    """Raised when material or review evidence is malformed or incomplete."""


class _GitCommandError(ReviewEvidenceError):
    """Raised when Git cannot supply the requested repository evidence."""


class _StaleSealEvidenceUnknown(ReviewEvidenceError):
    """Raised when stale-seal eligibility cannot be decided authoritatively."""


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
class MaterialDiffSummary:
    """Git-derived line totals for the exact no-renames material path set."""

    files: int
    additions: int
    deletions: int

    def __post_init__(self) -> None:
        for label, value in (
            ("files", self.files),
            ("additions", self.additions),
            ("deletions", self.deletions),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ReviewEvidenceError(
                    f"material diff summary {label} must be a non-negative integer"
                )

    @property
    def changed_lines(self) -> int:
        return self.additions + self.deletions

    def as_dict(self) -> dict[str, int]:
        return {
            "files": self.files,
            "additions": self.additions,
            "deletions": self.deletions,
            "changed_lines": self.changed_lines,
        }


@dataclass(frozen=True)
class MaterialManifest:
    base_ref_oid: str
    head_ref_oid: str
    merge_base_sha: str
    pr_number: int
    entries: tuple[MaterialEntry, ...]
    digest: str
    diff_summary: MaterialDiffSummary | None = None

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


def _reject_nonfinite_json_constant(value: str) -> None:
    raise ReviewEvidenceError(f"JSON contains non-finite number {value!r}")


def _load_json_bytes(raw: bytes, *, label: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewEvidenceError(f"{label} is not valid UTF-8 JSON") from exc


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ReviewEvidenceError("value cannot be rendered as canonical JSON") from exc


def review_thread_inventory(
    threads: tuple[ReviewThreadEvidence, ...],
) -> tuple[tuple[str, bool, tuple[tuple[str, ...], ...]], ...]:
    """Ignore outer thread order while preserving each comment sequence."""

    return tuple(
        sorted(
            (
                thread.node_id,
                thread.is_resolved,
                tuple(
                    (
                        comment.url,
                        comment.created_at,
                        comment.author_login,
                        comment.author_association,
                        comment.original_commit_sha or "",
                        hashlib.sha256(
                            comment.body.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
                        ).hexdigest(),
                    )
                    for comment in thread.comments
                ),
            )
            for thread in threads
        )
    )


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


def parse_owner_unavailable_ref_reply(body: str) -> str:
    """Return the ref from the exact one-line repository-owner contract."""

    if not isinstance(body, str):
        raise ReviewEvidenceError("owner unavailable-ref reply is malformed")
    try:
        if len(body.encode("utf-8")) > 1024:
            raise ReviewEvidenceError("owner unavailable-ref reply is malformed")
    except UnicodeEncodeError as exc:
        raise ReviewEvidenceError("owner unavailable-ref reply is malformed") from exc
    match = _OWNER_UNAVAILABLE_REF_REPLY_RE.fullmatch(body)
    if match is None:
        raise ReviewEvidenceError("owner unavailable-ref reply is malformed")
    return match.group("review_ref")


def parse_owner_stale_seal_fixed_reply(body: str) -> tuple[str, str]:
    """Return ``(stale_head, reseal)`` from the exact owner FIXED contract."""

    if not isinstance(body, str):
        raise ReviewEvidenceError("owner stale-seal FIXED reply is malformed")
    try:
        if len(body.encode("utf-8")) > 1024:
            raise ReviewEvidenceError("owner stale-seal FIXED reply is malformed")
    except UnicodeEncodeError as exc:
        raise ReviewEvidenceError("owner stale-seal FIXED reply is malformed") from exc
    match = _OWNER_STALE_SEAL_FIXED_REPLY_RE.fullmatch(body)
    if match is None:
        raise ReviewEvidenceError("owner stale-seal FIXED reply is malformed")
    stale_head = match.group("stale_head")
    reseal = match.group("reseal")
    if stale_head == reseal:
        raise ReviewEvidenceError("owner stale-seal FIXED reply must name two commits")
    return stale_head, reseal


def _is_finding_atom_char(char: str) -> bool:
    category = unicodedata.category(char)
    return (
        char == "_" or category[0] in {"L", "M", "N"} or (category[0] == "C" and not char.isspace())
    )


def _finding_atom_end(body: str, start: int) -> int:
    end = start
    while end < len(body):
        char = body[end]
        if not (_is_finding_atom_char(char) or char in {".", "…"}):
            break
        end += 1
    return end


def _finding_sha_like_tokens(body: str) -> tuple[str, ...]:
    """Return maximal standalone SHA-like atoms from one bounded finding."""

    tokens: list[str] = []
    position = 0
    while match := _FINDING_ASCII_HEX_CORE_RE.search(body, position):
        start, core_end = match.span()
        if start > 0 and _is_finding_atom_char(body[start - 1]):
            position = _finding_atom_end(body, core_end)
            continue
        has_carrier = body.startswith("...", core_end) or body.startswith("…", core_end)
        if core_end - start < 7 and not has_carrier:
            position = (
                _finding_atom_end(body, core_end)
                if core_end < len(body) and _is_finding_atom_char(body[core_end])
                else core_end
            )
            continue
        if core_end < len(body) and _is_finding_atom_char(body[core_end]):
            token_end = _finding_atom_end(body, core_end)
            tokens.append(body[start:token_end])
            position = token_end
            continue
        token_end = core_end
        if has_carrier:
            token_end = _finding_atom_end(body, core_end)
        tokens.append(body[start:token_end])
        position = token_end
    return tuple(tokens)


def review_finding_sha_candidates(body: str) -> tuple[str, ...]:
    """Return the bounded commit-ref class for an unambiguous ancestry finding."""

    if not isinstance(body, str):
        raise ReviewEvidenceError("review finding body is malformed")
    try:
        body_size = len(body.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ReviewEvidenceError("review finding body is malformed") from exc
    if body_size > 256 * 1024:
        raise ReviewEvidenceError("review finding body is malformed")
    lowered = body.lower()
    cause_terms = ("ancestry", "ancestor", "reachable", "commit graph", "merge-base")
    if not any(term in lowered for term in cause_terms):
        raise ReviewEvidenceError("review finding is not an ancestry cause")
    candidate_values: set[str] = set()
    for token in _finding_sha_like_tokens(body):
        if _SHA_RE.fullmatch(token):
            candidate_values.add(token)
            continue
        short_match = _FINDING_VALID_SHORT_REF_TOKEN_RE.fullmatch(token)
        if short_match is None:
            raise ReviewEvidenceError("review finding has ambiguous commit references")
        candidate_values.add(short_match.group("short"))
    candidates = tuple(sorted(candidate_values))
    if not candidates or len(candidates) > 4:
        raise ReviewEvidenceError("review finding has ambiguous commit references")
    return candidates


def _classify_finding_commit_candidate(
    candidate: str,
    snapshot: PrSnapshot,
    *,
    token: str,
) -> CommitResolution:
    """Resolve one finding-local short ref before canonical commit classification."""

    from scripts.orchestration.pr_commit_identity import (
        CommitIdentityError,
        CommitRefKind,
        GitHubHttpError,
        ReviewExecutionRef,
        classify_commit_ref,
        github_api_request,
    )

    if _SHA_RE.fullmatch(candidate):
        return classify_commit_ref(candidate, snapshot, token=token)

    repository_parts = snapshot.repository.strip().split("/")
    if len(repository_parts) != 2 or not all(
        re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in repository_parts
    ):
        return ReviewExecutionRef(
            value=candidate,
            kind=CommitRefKind.API_UNKNOWN,
            reason="repository identity is malformed",
        )
    owner, name = repository_parts
    known_matches = {
        sha
        for sha in {
            snapshot.base_sha,
            snapshot.head_sha,
            *snapshot.commit_shas,
        }
        if sha.startswith(candidate)
    }
    encoded_candidate = urllib.parse.quote(candidate, safe="")
    try:
        response = github_api_request(
            f"https://api.github.com/repos/{owner}/{name}/commits/{encoded_candidate}",
            token=token,
        )
    except GitHubHttpError as exc:
        if exc.status == 404:
            if known_matches:
                return ReviewExecutionRef(
                    value=candidate,
                    kind=CommitRefKind.API_UNKNOWN,
                    reason="Commit API contradicts the live PR snapshot",
                )
            return ReviewExecutionRef(
                value=candidate,
                kind=CommitRefKind.REVIEW_REF_UNAVAILABLE,
                reason="commit is unavailable from the GitHub Commit API",
            )
        return ReviewExecutionRef(
            value=candidate,
            kind=CommitRefKind.API_UNKNOWN,
            reason=f"Commit API failed with HTTP {exc.status}",
        )
    except (CommitIdentityError, OSError, TimeoutError, http.client.HTTPException) as exc:
        return ReviewExecutionRef(
            value=candidate,
            kind=CommitRefKind.API_UNKNOWN,
            reason=f"Commit API could not prove identity: {type(exc).__name__}",
        )
    if not isinstance(response, dict):
        return ReviewExecutionRef(
            value=candidate,
            kind=CommitRefKind.API_UNKNOWN,
            reason="Commit API response is malformed",
        )
    returned_sha = response.get("sha")
    if (
        not isinstance(returned_sha, str)
        or not _SHA_RE.fullmatch(returned_sha)
        or not returned_sha.startswith(candidate)
    ):
        return ReviewExecutionRef(
            value=candidate,
            kind=CommitRefKind.API_UNKNOWN,
            reason="Commit API did not uniquely bind the short reference",
        )
    if known_matches and known_matches != {returned_sha}:
        return ReviewExecutionRef(
            value=candidate,
            kind=CommitRefKind.API_UNKNOWN,
            reason="Commit API contradicts the live PR snapshot",
        )
    return classify_commit_ref(
        returned_sha,
        snapshot,
        token=token,
        request_json=lambda *_args, **_kwargs: response,
    )


def _review_finding_mentions_fix(candidates: tuple[str, ...], verified_fix: str) -> bool:
    return any(
        candidate == verified_fix
        or (len(candidate) < len(verified_fix) and verified_fix.startswith(candidate))
        for candidate in candidates
    )


def validated_duplicate_reply_urls(
    *,
    candidate_urls: set[str],
    threads: tuple[Any, ...],
    fingerprint_records: Mapping[str, Any],
    mapping_entries: Mapping[str, str],
    material_digest: str,
    material_head_sha: str,
    repo_root: Path,
    snapshot: Any,
    repository: str,
    token: str,
) -> set[str]:
    """Return candidate URLs covered by the closed v1 duplicate-reply contract."""

    from scripts.orchestration.pr_commit_identity import (
        CommitIdentityError,
        CommitRefKind,
        GitHubHttpError,
        RepositoryCommitRef,
        _require_repository,
        classify_commit_ref,
        github_api_request,
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

    def prepare_finding(
        verified_fix: str,
        thread: Any,
        finding_index: int,
        *,
        exact_original_commit: str | None = None,
    ) -> tuple[datetime, tuple[str, ...]]:
        finding = thread.comments[finding_index]
        if (
            not thread.is_resolved
            or finding.author_login.strip().lower() != "chatgpt-codex-connector"
            or not finding.original_commit_sha
            or finding.original_commit_sha not in snapshot.commit_shas
            or (
                exact_original_commit is not None
                and finding.original_commit_sha != exact_original_commit
            )
        ):
            raise ReviewEvidenceError(
                "unavailable-ref finding lacks trusted resolved live PR context"
            )
        if original_commit_digest(finding.original_commit_sha) != material_digest:
            raise ReviewEvidenceError(
                "unavailable-ref finding originalCommit has a different material digest"
            )
        candidates = review_finding_sha_candidates(finding.body)
        if not _review_finding_mentions_fix(candidates, verified_fix):
            raise ReviewEvidenceError("unavailable-ref finding does not cite verified FIX")
        return (
            _parse_timestamp(finding.created_at, label="review finding createdAt"),
            candidates,
        )

    def validate_finding_candidates(
        verified_fix: str,
        candidates: tuple[str, ...],
        *,
        accepted_repository_identities: tuple[set[str], ...],
    ) -> None:
        resolutions = [
            _classify_finding_commit_candidate(candidate, snapshot, token=token)
            for candidate in candidates
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
        if verified_fix not in repository_shas:
            raise ReviewEvidenceError("unavailable-ref finding does not cite verified FIX")
        if len(unavailable) != 1 or repository_shas not in accepted_repository_identities:
            raise ReviewEvidenceError("review finding ancestry cause is ambiguous")

    validated_records: dict[str, tuple[Any, datetime]] = {}
    for fingerprint, record in fingerprint_records.items():
        if record.material_digest != material_digest or len(record.urls) != 1:
            raise ReviewEvidenceError("canonical fingerprint record identity is invalid")
        location = comment_locations.get(record.urls[0])
        if location is None or location[1] != 0:
            raise ReviewEvidenceError("canonical fingerprint URL is not a live thread root")
        canonical_time, candidates = prepare_finding(record.verified_fix, location[0], location[1])
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
        validate_finding_candidates(
            record.verified_fix,
            candidates,
            accepted_repository_identities=(
                {record.verified_fix},
                {record.verified_fix, snapshot.base_sha, snapshot.head_sha},
            ),
        )
        validated_records[fingerprint] = (record, canonical_time)
    validated_fingerprint_urls = {
        record.urls[0] for record, _canonical_time in validated_records.values()
    }

    candidate_fingerprints: dict[str, str] = {}
    candidate_times: dict[str, datetime] = {}
    candidate_locations: dict[str, tuple[Any, int]] = {}
    for url in sorted(candidate_urls):
        location = comment_locations.get(url)
        if location is None:
            continue
        thread, finding_index = location
        finding = thread.comments[finding_index]
        finding_time = _parse_timestamp(finding.created_at, label="duplicate finding createdAt")
        valid_fingerprints: list[str] = []
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
        candidate_fingerprints[url] = valid_fingerprints[0]
        candidate_times[url] = finding_time
        candidate_locations[url] = location

    covered: set[str] = set()
    for url, fingerprint in candidate_fingerprints.items():
        validated = validated_records.get(fingerprint)
        if validated is None:
            continue
        thread, finding_index = candidate_locations[url]
        finding_time = candidate_times[url]
        record, canonical_time = validated
        if url == record.urls[0] or finding_time <= canonical_time:
            continue
        try:
            _, candidates = prepare_finding(record.verified_fix, thread, finding_index)
            validate_finding_candidates(
                record.verified_fix,
                candidates,
                accepted_repository_identities=(
                    {record.verified_fix},
                    {record.verified_fix, snapshot.base_sha, snapshot.head_sha},
                ),
            )
        except ReviewEvidenceError as exc:
            if "API_UNKNOWN" in str(exc):
                raise
            continue
        covered.add(url)

    validated_mapping_entries = {
        url: _require_sha(value, label="mapped FIXED SHA")
        for url, value in mapping_entries.items()
        if value
    }
    mapped_fixes = frozenset(validated_mapping_entries.values())
    commit_pushed_at = {commit.sha: commit.pushed_at for commit in snapshot.commits}
    eligible_recordless_by_fingerprint: dict[str, list[str]] = {}
    for url, fingerprint in candidate_fingerprints.items():
        if fingerprint in validated_records:
            continue
        thread, finding_index = candidate_locations[url]
        if finding_index != 0:
            continue
        try:
            validated_material_head = _require_sha(material_head_sha, label="material_head_sha")
            validate_mapping_only_closeout_successor(
                repo_root,
                material_head_sha=validated_material_head,
                live_head_sha=snapshot.head_sha,
                pr_number=snapshot.pr_number,
            )
            finding = thread.comments[finding_index]
            candidates = review_finding_sha_candidates(finding.body)
            cited_fixes = {
                sha for sha in mapped_fixes if _review_finding_mentions_fix(candidates, sha)
            }
            if len(cited_fixes) != 1:
                continue
            verified_fix = next(iter(cited_fixes))
            pushed_at_raw = commit_pushed_at.get(verified_fix)
            if pushed_at_raw is None:
                continue
            pushed_at = _parse_timestamp(pushed_at_raw, label="mapped FIX pushedAt")
            has_qualified_mapping_root = False
            for mapped_url, mapped_sha in validated_mapping_entries.items():
                if mapped_sha != verified_fix:
                    continue
                mapped_location = comment_locations.get(mapped_url)
                if (
                    mapped_location is None
                    or mapped_location[1] != 0
                    or not mapped_location[0].is_resolved
                ):
                    continue
                mapped_root_time = _parse_timestamp(
                    mapped_location[0].comments[0].created_at,
                    label="mapped FIX thread root createdAt",
                )
                if pushed_at > mapped_root_time:
                    has_qualified_mapping_root = True
                    break
            if not has_qualified_mapping_root:
                continue
            changed_files = _run_git(
                repo_root,
                ["show", "--name-only", "--pretty=format:", verified_fix],
            ).splitlines()
            if not any(path.strip() for path in changed_files):
                continue
            subject = (
                _run_git(
                    repo_root,
                    ["show", "-s", "--format=%s", verified_fix],
                )
                .decode("utf-8", errors="replace")
                .strip()
            )
            if TRIGGER_ONLY_COMMIT_SUBJECT_RE.search(subject):
                continue
            expected_fingerprint = unavailable_review_ref_fingerprint(
                pr_number=snapshot.pr_number,
                material_digest=material_digest,
                verified_real_fix_sha=verified_fix,
            )
            if fingerprint != expected_fingerprint:
                continue
            prepare_finding(
                verified_fix,
                thread,
                finding_index,
                exact_original_commit=snapshot.head_sha,
            )
            fix_resolution = classify_commit_ref(verified_fix, snapshot, token=token)
            if not isinstance(fix_resolution, RepositoryCommitRef) or fix_resolution.kind not in {
                CommitRefKind.PR_HEAD,
                CommitRefKind.PR_COMMIT,
            }:
                continue
            if not is_ancestor(
                fix_resolution,
                live_head,
                repository=repository,
                token=token,
            ):
                continue
            validate_finding_candidates(
                verified_fix,
                candidates,
                accepted_repository_identities=(
                    {verified_fix},
                    {verified_fix, validated_material_head},
                ),
            )
        except ReviewEvidenceError as exc:
            if "API_UNKNOWN" in str(exc):
                raise
            continue
        eligible_recordless_by_fingerprint.setdefault(fingerprint, []).append(url)
    for urls in eligible_recordless_by_fingerprint.values():
        if len(urls) == 1:
            covered.add(urls[0])

    # The owner-only class may coexist with unrelated canonical records, but it
    # must never replace an existing disposition for the same thread root.

    try:
        supplied_owner, supplied_name = _require_repository(repository)
        snapshot_owner, snapshot_name = _require_repository(snapshot.repository)
    except CommitIdentityError as exc:
        raise ReviewEvidenceError("owner unavailable-ref repository identity is malformed") from exc
    if (supplied_owner.lower(), supplied_name.lower()) != (
        snapshot_owner.lower(),
        snapshot_name.lower(),
    ):
        raise ReviewEvidenceError(
            "owner unavailable-ref repository does not match snapshot repository"
        )
    owner, name = snapshot_owner, snapshot_name
    canonical_mapping_path = f"docs/review/PR_{snapshot.pr_number}_FIXED_MAPPING.md"
    root_url_re = re.compile(
        r"https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/"
        r"(?P<name>[A-Za-z0-9_.-]+)/pull/"
        rf"{snapshot.pr_number}#discussion_r(?P<comment_id>[1-9][0-9]*)"
    )

    def root_body_has_bound_evidence(body: Any, *, selected_ref: str) -> bool:
        if not isinstance(body, str):
            return False
        try:
            if len(body.encode("utf-8")) > 256 * 1024:
                return False
        except UnicodeEncodeError:
            return False
        lowered = body.lower()
        if not any(
            term in lowered
            for term in ("ancestry", "commit graph", "commit-graph", "not an ancestor")
        ):
            return False

        def has_exact_token(value: str) -> bool:
            return (
                re.search(
                    rf"(?<![0-9A-Fa-f]){re.escape(value)}(?![0-9A-Fa-f])",
                    body,
                )
                is not None
            )

        return has_exact_token(material_head_sha) and has_exact_token(selected_ref)

    def root_has_canonical_mapping_path(url: str) -> bool:
        match = root_url_re.fullmatch(url)
        if match is None or (
            match.group("owner").lower(),
            match.group("name").lower(),
        ) != (owner.lower(), name.lower()):
            return False
        try:
            response = github_api_request(
                f"https://api.github.com/repos/{owner}/{name}/pulls/comments/"
                f"{match.group('comment_id')}",
                token=token,
            )
        except (
            GitHubHttpError,
            CommitIdentityError,
            OSError,
            TimeoutError,
            http.client.HTTPException,
        ) as exc:
            raise ReviewEvidenceError(
                "owner unavailable-ref review-comment identity is API_UNKNOWN"
            ) from exc
        if not isinstance(response, dict):
            raise ReviewEvidenceError(
                "owner unavailable-ref review-comment identity is API_UNKNOWN"
            )
        return response.get("html_url") == url and response.get("path") == canonical_mapping_path

    owner_eligible_urls: list[str] = []
    closeout_validated = False
    live_roots = sorted((thread.comments[0].url, thread) for thread in threads if thread.comments)
    for url, thread in live_roots:
        location = comment_locations.get(url)
        if (
            url in covered
            or url in validated_mapping_entries
            or url in validated_fingerprint_urls
            or location is None
            or location[0] is not thread
            or location[1] != 0
        ):
            continue
        finding_index = 0
        finding = thread.comments[finding_index]
        if (
            not thread.is_resolved
            or finding.author_login != "chatgpt-codex-connector"
            or finding.original_commit_sha != snapshot.head_sha
        ):
            continue
        finding_time = _parse_timestamp(
            finding.created_at,
            label="owner unavailable-ref finding createdAt",
        )
        owner_replies = [
            reply
            for reply in thread.comments[finding_index + 1 :]
            if reply.author_association == "OWNER"
        ]
        if len(owner_replies) != 1:
            continue
        owner_reply = owner_replies[0]
        try:
            selected_ref = parse_owner_unavailable_ref_reply(owner_reply.body)
        except ReviewEvidenceError:
            continue
        reply_time = _parse_timestamp(
            owner_reply.created_at,
            label="owner unavailable-ref reply createdAt",
        )
        if reply_time <= finding_time or not root_body_has_bound_evidence(
            finding.body,
            selected_ref=selected_ref,
        ):
            continue
        try:
            validated_material_head = _require_sha(
                material_head_sha,
                label="material_head_sha",
            )
            if not closeout_validated:
                validate_mapping_only_closeout_successor(
                    repo_root,
                    material_head_sha=validated_material_head,
                    live_head_sha=snapshot.head_sha,
                    pr_number=snapshot.pr_number,
                )
                if (
                    original_commit_digest(validated_material_head) != material_digest
                    or original_commit_digest(snapshot.head_sha) != material_digest
                ):
                    raise ReviewEvidenceError(
                        "owner unavailable-ref material digest does not recompute"
                    )
                closeout_validated = True
            if not root_has_canonical_mapping_path(url):
                continue
            if selected_ref in {
                snapshot.base_sha,
                snapshot.head_sha,
                *snapshot.commit_shas,
            }:
                continue
            try:
                selected_ref_resolution = classify_commit_ref(
                    selected_ref,
                    snapshot,
                    token=token,
                    request_json=github_api_request,
                )
            except http.client.HTTPException as exc:
                raise ReviewEvidenceError(
                    "owner unavailable-ref selected ref identity is API_UNKNOWN"
                ) from exc
            if selected_ref_resolution.kind is CommitRefKind.API_UNKNOWN:
                raise ReviewEvidenceError(
                    "owner unavailable-ref selected ref identity is API_UNKNOWN"
                )
            if selected_ref_resolution.kind is not CommitRefKind.REVIEW_REF_UNAVAILABLE:
                continue
        except ReviewEvidenceError as exc:
            if "API_UNKNOWN" in str(exc):
                raise
            continue
        owner_eligible_urls.append(url)
    if len(owner_eligible_urls) == 1 and owner_eligible_urls[0] in candidate_urls:
        covered.add(owner_eligible_urls[0])

    stale_seal_eligible_urls: list[str] = []
    current_stale_seal_closeout_validated = False
    historical_reseal_times: dict[tuple[str, str], datetime] = {}
    for url, thread in live_roots:
        location = comment_locations.get(url)
        if (
            url in covered
            or url in validated_mapping_entries
            or url in validated_fingerprint_urls
            or location is None
            or location[0] is not thread
            or location[1] != 0
        ):
            continue
        finding = thread.comments[0]
        if (
            not thread.is_resolved
            or finding.author_login != "chatgpt-codex-connector"
            or not finding.original_commit_sha
        ):
            continue
        owner_replies = [
            reply for reply in thread.comments[1:] if reply.author_association == "OWNER"
        ]
        if len(owner_replies) != 1:
            continue
        owner_reply = owner_replies[0]
        try:
            stale_head, reseal = parse_owner_stale_seal_fixed_reply(owner_reply.body)
        except ReviewEvidenceError:
            continue
        if finding.original_commit_sha != stale_head:
            continue
        try:
            finding_time = _parse_timestamp(
                finding.created_at,
                label="owner stale-seal finding createdAt",
            )
            reply_time = _parse_timestamp(
                owner_reply.created_at,
                label="owner stale-seal reply createdAt",
            )
            if reply_time <= finding_time:
                continue
            if not _validate_stale_seal_root_identity(
                url=url,
                finding=finding,
                stale_head_sha=stale_head,
                owner=owner,
                name=name,
                pr_number=snapshot.pr_number,
                token=token,
                request_json=github_api_request,
            ):
                continue
            if not current_stale_seal_closeout_validated:
                _validate_current_stale_seal_closeout(
                    repo_root=repo_root,
                    snapshot=snapshot,
                    repository=repository,
                    token=token,
                    material_digest=material_digest,
                    material_head_sha=material_head_sha,
                )
                current_stale_seal_closeout_validated = True
            reseal_time = historical_reseal_times.get((stale_head, reseal))
            if reseal_time is None:
                reseal_time = _validate_historical_stale_seal_reseal(
                    repo_root=repo_root,
                    snapshot=snapshot,
                    repository=repository,
                    token=token,
                    stale_head_sha=stale_head,
                    reseal_sha=reseal,
                    request_json=github_api_request,
                )
                historical_reseal_times[(stale_head, reseal)] = reseal_time
            if reseal_time <= finding_time or reseal_time > reply_time:
                continue
        except _StaleSealEvidenceUnknown:
            raise
        except ReviewEvidenceError:
            continue
        except (OSError, TimeoutError, http.client.HTTPException) as exc:
            raise _StaleSealEvidenceUnknown("owner stale-seal evidence is API_UNKNOWN") from exc
        stale_seal_eligible_urls.append(url)
    if len(stale_seal_eligible_urls) == 1 and stale_seal_eligible_urls[0] in candidate_urls:
        covered.add(stale_seal_eligible_urls[0])
    return covered


def _git_path() -> str:
    path = shutil.which("git")
    if not path:
        raise _GitCommandError("git not found in PATH")
    try:
        return str(Path(path).resolve(strict=True))
    except OSError as exc:
        raise _GitCommandError("git executable could not be resolved") from exc


def _git_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    return env


def _run_git(repo_root: Path, args: list[str], *, timeout: int = 30) -> bytes:
    git = _git_path()
    try:
        result = subprocess.run(  # nosec B603: absolute git plus validated fixed argv (remove-by: 2026-09-30, ref: PR-governance-seal)
            [git, *args],
            cwd=repo_root,
            env=_git_environment(),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _GitCommandError(f"git {' '.join(args[:2])} could not execute") from exc
    if result.returncode != 0:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        raise _GitCommandError(f"git {' '.join(args[:2])} failed: {diagnostic}")
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


def _parse_material_numstat(
    raw: bytes,
    *,
    excluded_path: str,
    material_paths: Iterable[str],
) -> MaterialDiffSummary:
    """Parse exact no-renames numstat output and bind it to manifest paths."""

    expected_paths = tuple(material_paths)
    stats: dict[str, tuple[int, int]] = {}
    seen_paths: set[str] = set()
    for record in raw.split(b"\0"):
        if not record:
            continue
        fields = record.split(b"\t", 2)
        if len(fields) != 3:
            raise ReviewEvidenceError("git diff numstat stream contains unsupported record")
        additions_raw, deletions_raw, path_bytes = fields
        if additions_raw == b"-" and deletions_raw == b"-":
            additions = 0
            deletions = 0
        elif additions_raw.isdigit() and deletions_raw.isdigit():
            additions = int(additions_raw)
            deletions = int(deletions_raw)
        else:
            raise ReviewEvidenceError("git diff numstat stream contains invalid line counts")
        path = _validate_material_path(path_bytes)
        if path in seen_paths:
            raise ReviewEvidenceError(f"git diff numstat emitted duplicate path {path!r}")
        seen_paths.add(path)
        if path == excluded_path:
            continue
        stats[path] = (additions, deletions)

    if len(expected_paths) != len(set(expected_paths)) or set(stats) != set(expected_paths):
        raise ReviewEvidenceError("git diff numstat paths do not match the exact material path set")
    return MaterialDiffSummary(
        files=len(expected_paths),
        additions=sum(additions for additions, _deletions in stats.values()),
        deletions=sum(deletions for _additions, deletions in stats.values()),
    )


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
    except _GitCommandError:
        raise
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
    numstat = _run_git(
        root,
        [
            "diff",
            "--numstat",
            "-z",
            "--no-renames",
            "--diff-algorithm=myers",
            "--no-ext-diff",
            "--no-textconv",
            merge_base,
            head_sha,
            "--",
        ],
    )
    diff_summary = _parse_material_numstat(
        numstat,
        excluded_path=excluded_path,
        material_paths=(entry.path for entry in entries),
    )
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
        diff_summary=diff_summary,
    )


def validate_mapping_only_closeout_successor(
    repo_root: Path,
    *,
    material_head_sha: str,
    live_head_sha: str,
    pr_number: int,
) -> None:
    """Require one direct commit that changes only the canonical mapping."""

    material_head = _require_sha(material_head_sha, label="material_head_sha")
    live_head = _require_sha(live_head_sha, label="live_head_sha")
    if pr_number <= 0:
        raise ReviewEvidenceError("pr_number must be positive")
    root = repo_root.resolve(strict=True)
    if not (root / ".git").exists():
        raise ReviewEvidenceError("repo_root is not a Git checkout")

    if material_head == live_head:
        raise ReviewEvidenceError("canonical mapping must be the sole closeout successor")
    _run_git(root, ["merge-base", "--is-ancestor", material_head, live_head])
    commit_count = (
        _run_git(root, ["rev-list", "--count", f"{material_head}..{live_head}"])
        .decode("ascii")
        .strip()
    )
    live_parents = (
        _run_git(root, ["rev-list", "--parents", "-n", "1", live_head])
        .decode("ascii")
        .strip()
        .split()
    )
    changed_after_seal = tuple(
        line
        for line in _run_git(
            root,
            ["diff", "--name-only", material_head, live_head, "--"],
        )
        .decode("utf-8")
        .splitlines()
        if line
    )
    mapping_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    if (
        commit_count != "1"
        or live_parents != [live_head, material_head]
        or changed_after_seal != (mapping_path,)
    ):
        raise ReviewEvidenceError(
            "live head must be the one mapping-only successor of sealed material"
        )


def _stale_seal_commit_parents(repo_root: Path, commit_sha: str) -> tuple[str, ...]:
    commit = _require_sha(commit_sha, label="stale-seal commit")
    try:
        raw = _run_git(repo_root, ["rev-list", "--parents", "-n", "1", commit])
        values = raw.decode("ascii").strip().split()
    except (_GitCommandError, UnicodeDecodeError) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    if not values or values[0] != commit:
        raise _StaleSealEvidenceUnknown("owner stale-seal commit parent evidence is API_UNKNOWN")
    try:
        return tuple(_require_sha(value, label="stale-seal commit parent") for value in values[1:])
    except ReviewEvidenceError as exc:
        raise _StaleSealEvidenceUnknown(
            "owner stale-seal commit parent evidence is API_UNKNOWN"
        ) from exc


def _stale_seal_commit_subject(repo_root: Path, commit_sha: str) -> str:
    commit = _require_sha(commit_sha, label="stale-seal commit")
    try:
        subject = _run_git(repo_root, ["show", "-s", "--format=%s", commit]).decode("utf-8")
    except (_GitCommandError, UnicodeDecodeError) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    subject = subject.removesuffix("\n")
    if not subject or "\n" in subject or "\r" in subject:
        raise ReviewEvidenceError("owner stale-seal reseal subject is malformed")
    return subject


def _stale_seal_mapping_blob(
    repo_root: Path,
    *,
    commit_sha: str,
    pr_number: int,
) -> str:
    commit = _require_sha(commit_sha, label="stale-seal mapping commit")
    mapping_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    try:
        tree_raw = _run_git(
            repo_root,
            [
                "ls-tree",
                "-z",
                "--full-tree",
                commit,
                "--",
                f":(literal){mapping_path}",
            ],
        )
    except _GitCommandError as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    tree_match = re.fullmatch(
        rb"100644 blob (?P<oid>[0-9a-f]{40})\t(?P<path>[^\0]+)\0",
        tree_raw,
    )
    if tree_match is None or tree_match.group("path") != mapping_path.encode("utf-8"):
        raise ReviewEvidenceError("owner stale-seal mapping must be one canonical regular blob")
    blob_oid = tree_match.group("oid").decode("ascii")
    try:
        size_raw = _run_git(repo_root, ["cat-file", "-s", blob_oid])
        size = int(size_raw.decode("ascii").strip())
        if not 0 < size <= _MAX_JSON_ARTIFACT_BYTES:
            raise ReviewEvidenceError("owner stale-seal mapping blob size is invalid")
        raw = _run_git(repo_root, ["cat-file", "blob", blob_oid])
        if len(raw) != size:
            raise ReviewEvidenceError("owner stale-seal mapping blob size changed")
        return raw.decode("utf-8")
    except (_GitCommandError, UnicodeDecodeError, ValueError) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    except ReviewEvidenceError as exc:
        if isinstance(exc, ReviewEvidenceError) and str(exc).startswith(
            "owner stale-seal mapping blob"
        ):
            raise
        raise


def _validate_stale_seal_mapping_only_edge(
    repo_root: Path,
    *,
    parent_sha: str,
    child_sha: str,
    pr_number: int,
    allow_mapping_add: bool,
    ban_trigger_only: bool = True,
) -> None:
    parent = _require_sha(parent_sha, label="mapping-only parent")
    child = _require_sha(child_sha, label="mapping-only child")
    if _stale_seal_commit_parents(repo_root, child) != (parent,):
        raise ReviewEvidenceError("owner stale-seal reseal is not one direct child")
    try:
        raw = _run_git(
            repo_root,
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
                parent,
                child,
                "--",
            ],
        )
    except _GitCommandError as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    try:
        entries = _parse_raw_diff(raw, excluded_path="\0not-a-repository-path")
    except ReviewEvidenceError as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    mapping_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    if len(entries) != 1 or entries[0].path != mapping_path:
        raise ReviewEvidenceError("owner stale-seal reseal is not mapping-only")
    entry = entries[0]
    expected_regular_shape = (
        entry.status == "M"
        and entry.base_mode == "100644"
        and entry.head_mode == "100644"
        and entry.base_blob_oid is not None
        and entry.head_blob_oid is not None
        and entry.base_blob_oid != entry.head_blob_oid
    )
    expected_add_shape = (
        allow_mapping_add
        and entry.status == "A"
        and entry.base_mode == "000000"
        and entry.head_mode == "100644"
        and entry.base_blob_oid is None
        and entry.head_blob_oid is not None
    )
    if not (expected_regular_shape or expected_add_shape):
        raise ReviewEvidenceError(
            "owner stale-seal reseal must change one regular canonical mapping blob"
        )
    if ban_trigger_only:
        subject = _stale_seal_commit_subject(repo_root, child)
        if TRIGGER_ONLY_COMMIT_SUBJECT_RE.search(subject):
            raise ReviewEvidenceError("owner stale-seal reseal must not be trigger-only")
    _stale_seal_mapping_blob(repo_root, commit_sha=child, pr_number=pr_number)


def _validate_stale_seal_projection(
    mapping_text: str,
    *,
    manifest: MaterialManifest,
    repository: str,
    pr_number: int,
    require_provider_no_claim: bool,
) -> dict[str, Any]:
    seal = parse_embedded_review_seal(mapping_text)
    if seal["repository"].casefold() != repository.casefold() or seal["pr_number"] != pr_number:
        raise ReviewEvidenceError("owner stale-seal repository/PR identity is stale")
    expected_material = {
        "base_ref_oid": manifest.base_ref_oid,
        "digest": manifest.digest,
        "material_head_sha": manifest.head_ref_oid,
        "merge_base_sha": manifest.merge_base_sha,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    if seal["material"] != expected_material:
        raise ReviewEvidenceError("owner stale-seal material projection does not recompute")
    if require_provider_no_claim:
        expected_review, expected_security = build_provider_no_claim_pair(
            base_revision=manifest.merge_base_sha,
            head_revision=manifest.head_ref_oid,
            material_digest=manifest.digest,
        )
        if seal["code_review"] != expected_review or seal["codex_security"] != expected_security:
            raise ReviewEvidenceError("owner stale-seal must use the exact provider-neutral pair")
    validate_review_seal(
        seal,
        material_paths=(entry.path for entry in manifest.entries),
        material_diff_summary=manifest.diff_summary,
    )
    return seal


def _stale_seal_manifests_match(
    material_manifest: MaterialManifest,
    closeout_manifest: MaterialManifest,
) -> bool:
    return (
        material_manifest.merge_base_sha == closeout_manifest.merge_base_sha
        and material_manifest.entries == closeout_manifest.entries
        and material_manifest.digest == closeout_manifest.digest
        and material_manifest.diff_summary == closeout_manifest.diff_summary
    )


def _stale_seal_material_manifest(
    repo_root: Path,
    *,
    base_ref_oid: str,
    head_ref_oid: str,
    pr_number: int,
) -> MaterialManifest:
    """Compute stale-seal material evidence, terminal on Git/object uncertainty."""

    try:
        return compute_material_manifest(
            repo_root,
            base_ref_oid=base_ref_oid,
            head_ref_oid=head_ref_oid,
            pr_number=pr_number,
        )
    except _GitCommandError as exc:
        raise _StaleSealEvidenceUnknown(
            "owner stale-seal material Git evidence is API_UNKNOWN"
        ) from exc
    except ReviewEvidenceError as exc:
        if str(exc) == "repo_root is not a Git checkout":
            raise _StaleSealEvidenceUnknown(
                "owner stale-seal material checkout evidence is API_UNKNOWN"
            ) from exc
        if str(exc).startswith(
            (
                "Git diff contains",
                "git diff-tree raw stream",
                "git diff numstat",
            )
        ):
            raise _StaleSealEvidenceUnknown(
                "owner stale-seal material object evidence is API_UNKNOWN"
            ) from exc
        raise


def _validated_github_bearer_token(token: Any) -> str:
    """Return an opaque printable token without exposing its contents in errors."""

    if (
        not isinstance(token, str)
        or not token.strip()
        or any(unicodedata.category(character).startswith("C") for character in token)
    ):
        raise _StaleSealEvidenceUnknown("owner stale-seal repository activity is API_UNKNOWN")
    return token


def _github_page_identity(
    url: str,
    *,
    expected_path: str | None = None,
    immutable_query: tuple[tuple[str, str], ...] | None = None,
) -> tuple[urllib.parse.ParseResult, tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    """Validate one same-endpoint GitHub pagination URL and return its identity."""

    try:
        parsed = urllib.parse.urlparse(url)
        query_pairs = urllib.parse.parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=32,
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN") from exc
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.github.com"
        or not parsed.path.startswith("/repos/")
        or parsed.params
        or parsed.fragment
        or expected_path is not None
        and parsed.path != expected_path
        or len(query_pairs) != len({key for key, _value in query_pairs})
        or any(
            not key
            or not value
            or any(unicodedata.category(character).startswith("C") for character in f"{key}{value}")
            for key, value in query_pairs
        )
    ):
        raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
    stable_query = tuple(
        sorted(
            (key, value) for key, value in query_pairs if key not in _GITHUB_PAGINATION_QUERY_KEYS
        )
    )
    if immutable_query is not None and stable_query != immutable_query:
        raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
    return parsed, stable_query, tuple(sorted(query_pairs))


def _github_api_paginated_pages(url: str, *, token: str) -> tuple[list[Any], ...]:
    """Fetch one bounded immutable GitHub REST feed through strict Link pages."""

    bearer_token = _validated_github_bearer_token(token)
    initial, immutable_query, _initial_query = _github_page_identity(url)
    expected_path = initial.path
    pages: list[list[Any]] = []
    next_url: str | None = url
    seen_page_identities: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for _page in range(_MAX_REPOSITORY_ACTIVITY_PAGES):
        if next_url is None:
            return tuple(pages)
        parsed, _stable_query, page_query = _github_page_identity(
            next_url,
            expected_path=expected_path,
            immutable_query=immutable_query,
        )
        page_identity = (parsed.path, page_query)
        if page_identity in seen_page_identities:
            raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
        seen_page_identities.add(page_identity)
        connection = http.client.HTTPSConnection("api.github.com", timeout=30)
        try:
            connection.request(
                "GET",
                parsed.path + (f"?{parsed.query}" if parsed.query else ""),
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {bearer_token}",
                    "User-Agent": "pulseplate-pr-review-evidence",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response = connection.getresponse()
            raw = response.read(4 * 1024 * 1024 + 1)
            if response.status != 200 or len(raw) > 4 * 1024 * 1024:
                raise _StaleSealEvidenceUnknown(
                    "owner stale-seal repository activity is API_UNKNOWN"
                )
            content_type = (response.getheader("Content-Type") or "").lower()
            if "json" not in content_type:
                raise _StaleSealEvidenceUnknown(
                    "owner stale-seal repository activity is API_UNKNOWN"
                )
            try:
                payload = _load_json_bytes(raw, label="GitHub repository activity page")
            except ReviewEvidenceError as exc:
                raise _StaleSealEvidenceUnknown(
                    "owner stale-seal repository activity is API_UNKNOWN"
                ) from exc
            if not isinstance(payload, list) or len(payload) > 100:
                raise _StaleSealEvidenceUnknown(
                    "owner stale-seal repository activity is API_UNKNOWN"
                )
            pages.append(payload)
            link_header = response.getheader("Link")
        except _StaleSealEvidenceUnknown:
            raise
        except (
            OSError,
            TimeoutError,
            ValueError,
            UnicodeEncodeError,
            http.client.HTTPException,
        ) as exc:
            raise _StaleSealEvidenceUnknown(
                "owner stale-seal repository activity is API_UNKNOWN"
            ) from exc
        finally:
            connection.close()
        next_candidates: list[str] = []
        link_targets: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
        if link_header:
            for raw_link in link_header.split(","):
                segments = [segment.strip() for segment in raw_link.split(";")]
                if len(segments) < 2 or not (
                    segments[0].startswith("<") and segments[0].endswith(">")
                ):
                    raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
                target = segments[0][1:-1]
                target_parsed, _target_stable, target_query = _github_page_identity(
                    target,
                    expected_path=expected_path,
                    immutable_query=immutable_query,
                )
                target_identity = (target_parsed.path, target_query)
                if target_identity in link_targets:
                    raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
                link_targets.add(target_identity)
                rel_parameters = [
                    segment.removeprefix("rel=")
                    for segment in segments[1:]
                    if segment.startswith("rel=")
                ]
                if len(rel_parameters) != 1:
                    raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
                rel_value = rel_parameters[0]
                if len(rel_value) < 2 or not (
                    rel_value.startswith('"') and rel_value.endswith('"')
                ):
                    raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
                relations = rel_value[1:-1].split()
                if not relations or len(relations) != len(set(relations)):
                    raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
                if "next" in relations:
                    next_candidates.append(target)
        if len(next_candidates) > 1:
            raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
        next_url = next_candidates[0] if next_candidates else None
    if next_url is not None:
        raise _StaleSealEvidenceUnknown("owner stale-seal pagination is API_UNKNOWN")
    return tuple(pages)


def _stale_seal_push_timestamp(activity: Mapping[str, Any]) -> datetime:
    timestamp = activity.get("timestamp")
    pushed_at = activity.get("pushed_at")
    if timestamp is not None and pushed_at is not None:
        parsed_timestamp = _parse_timestamp(
            timestamp,
            label="owner stale-seal repository activity timestamp",
        )
        parsed_pushed_at = _parse_timestamp(
            pushed_at,
            label="owner stale-seal repository activity pushed_at",
        )
        if parsed_timestamp != parsed_pushed_at:
            raise ReviewEvidenceError("owner stale-seal repository activity timestamps conflict")
        return parsed_timestamp
    return _parse_timestamp(
        pushed_at if pushed_at is not None else timestamp,
        label="owner stale-seal repository activity timestamp",
    )


def _fetch_stale_seal_reseal_pushed_at(
    *,
    snapshot: Any,
    repository: str,
    stale_head_sha: str,
    reseal_sha: str,
    token: str,
    request_json: Any,
) -> datetime:
    for commit in snapshot.commits:
        if commit.sha == reseal_sha and commit.pushed_at is not None:
            try:
                return _parse_timestamp(
                    commit.pushed_at,
                    label="owner stale-seal reseal pushedDate",
                )
            except ReviewEvidenceError as exc:
                raise _StaleSealEvidenceUnknown(
                    "owner stale-seal reseal pushedDate is API_UNKNOWN"
                ) from exc
    owner, name = repository.split("/", 1)
    try:
        pull = request_json(
            f"https://api.github.com/repos/{owner}/{name}/pulls/{snapshot.pr_number}",
            token=token,
        )
    except Exception as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal PR head evidence is API_UNKNOWN") from exc
    head = pull.get("head") if isinstance(pull, dict) else None
    base = pull.get("base") if isinstance(pull, dict) else None
    head_repo = head.get("repo") if isinstance(head, dict) else None
    head_repository = head_repo.get("full_name") if isinstance(head_repo, dict) else None
    head_ref = head.get("ref") if isinstance(head, dict) else None
    head_sha = head.get("sha") if isinstance(head, dict) else None
    base_sha = base.get("sha") if isinstance(base, dict) else None
    if (
        not isinstance(head_repository, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", head_repository)
        or not isinstance(head_ref, str)
        or not head_ref
        or any(unicodedata.category(character).startswith("C") for character in head_ref)
        or len(head_ref.encode("utf-8")) > 1024
        or head_repository.casefold() != snapshot.repository.casefold()
        or head_sha != snapshot.head_sha
        or base_sha != snapshot.base_sha
    ):
        raise _StaleSealEvidenceUnknown("owner stale-seal PR head evidence is API_UNKNOWN")
    expected_ref = f"refs/heads/{head_ref}"
    activity_query = urllib.parse.urlencode(
        {"ref": head_ref, "activity_type": "push", "per_page": 100}
    )
    activity_url = f"https://api.github.com/repos/{head_repository}/activity?{activity_query}"
    try:
        activity_pages = _github_api_paginated_pages(activity_url, token=token)
    except ReviewEvidenceError as exc:
        raise _StaleSealEvidenceUnknown(
            "owner stale-seal repository activity is API_UNKNOWN"
        ) from exc
    exact_times: list[datetime] = []
    for page in activity_pages:
        for activity in page:
            if not isinstance(activity, dict):
                raise _StaleSealEvidenceUnknown(
                    "owner stale-seal repository activity is API_UNKNOWN"
                )
            if (
                activity.get("activity_type") == "push"
                and activity.get("ref") == expected_ref
                and activity.get("before") == stale_head_sha
                and activity.get("after") == reseal_sha
            ):
                try:
                    exact_times.append(_stale_seal_push_timestamp(activity))
                except ReviewEvidenceError as exc:
                    raise _StaleSealEvidenceUnknown(
                        "owner stale-seal repository activity is API_UNKNOWN"
                    ) from exc
    if exact_times:
        return min(exact_times)
    events_url = f"https://api.github.com/repos/{head_repository}/events?per_page=100"
    try:
        event_pages = _github_api_paginated_pages(events_url, token=token)
    except ReviewEvidenceError as exc:
        raise _StaleSealEvidenceUnknown(
            "owner stale-seal repository events are API_UNKNOWN"
        ) from exc
    for page in event_pages:
        for event in page:
            if not isinstance(event, dict):
                raise _StaleSealEvidenceUnknown(
                    "owner stale-seal repository events are API_UNKNOWN"
                )
            payload = event.get("payload")
            if (
                event.get("type") == "PushEvent"
                and isinstance(payload, dict)
                and payload.get("ref") == expected_ref
                and payload.get("before") == stale_head_sha
                and payload.get("head") == reseal_sha
            ):
                try:
                    exact_times.append(
                        _parse_timestamp(
                            event.get("created_at"),
                            label="owner stale-seal PushEvent created_at",
                        )
                    )
                except ReviewEvidenceError as exc:
                    raise _StaleSealEvidenceUnknown(
                        "owner stale-seal repository events are API_UNKNOWN"
                    ) from exc
    if not exact_times:
        raise ReviewEvidenceError("owner stale-seal reseal lacks immutable server push evidence")
    return min(exact_times)


def _stale_seal_repository_commit(
    sha: str,
    *,
    snapshot: Any,
    token: str,
    require_pr_commit: bool,
) -> Any:
    from scripts.orchestration.pr_commit_identity import (
        CommitIdentityError,
        CommitRefKind,
        RepositoryCommitRef,
        classify_commit_ref,
    )

    try:
        resolution = classify_commit_ref(sha, snapshot, token=token)
    except (CommitIdentityError, OSError, TimeoutError, http.client.HTTPException) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal commit identity is API_UNKNOWN") from exc
    if getattr(resolution, "kind", None) is CommitRefKind.API_UNKNOWN:
        raise _StaleSealEvidenceUnknown("owner stale-seal commit identity is API_UNKNOWN")
    if (sha in snapshot.commit_shas or sha == snapshot.base_sha) and getattr(
        resolution, "kind", None
    ) is CommitRefKind.REVIEW_REF_UNAVAILABLE:
        raise _StaleSealEvidenceUnknown(
            "owner stale-seal snapshot commit identity conflicts with GitHub"
        )
    allowed_kinds = {CommitRefKind.PR_HEAD, CommitRefKind.PR_COMMIT}
    if not isinstance(resolution, RepositoryCommitRef) or (
        require_pr_commit and resolution.kind not in allowed_kinds
    ):
        raise ReviewEvidenceError("owner stale-seal commit is not a real live PR commit")
    return resolution


def _stale_seal_remote_ancestor(
    ancestor: Any,
    descendant: Any,
    *,
    repository: str,
    token: str,
) -> None:
    from scripts.orchestration.pr_commit_identity import CommitIdentityError, is_ancestor

    try:
        reachable = is_ancestor(
            ancestor,
            descendant,
            repository=repository,
            token=token,
        )
    except (CommitIdentityError, OSError, TimeoutError, http.client.HTTPException) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal ancestry is API_UNKNOWN") from exc
    if not reachable:
        raise ReviewEvidenceError("owner stale-seal commit is not remotely reachable")


def _stale_seal_remote_non_ancestor(
    ancestor: Any,
    descendant: Any,
    *,
    repository: str,
    token: str,
) -> None:
    """Require GitHub Compare to prove that one commit did not precede another."""

    from scripts.orchestration.pr_commit_identity import CommitIdentityError, is_ancestor

    try:
        reachable = is_ancestor(
            ancestor,
            descendant,
            repository=repository,
            token=token,
        )
    except (CommitIdentityError, OSError, TimeoutError, http.client.HTTPException) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal ancestry is API_UNKNOWN") from exc
    if reachable:
        raise ReviewEvidenceError(
            "owner stale-seal synchronized base already preceded prior closeout"
        )


def _stale_seal_local_ancestor(
    repo_root: Path,
    *,
    ancestor_sha: str,
    descendant_sha: str,
) -> None:
    try:
        git = _git_path()
        result = subprocess.run(  # nosec B603: absolute git plus validated fixed argv (remove-by: 2026-09-30, ref: PR-governance-seal)
            [git, "merge-base", "--is-ancestor", ancestor_sha, descendant_sha],
            cwd=repo_root,
            env=_git_environment(),
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (_GitCommandError, OSError, subprocess.TimeoutExpired) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    if result.returncode == 0:
        return
    if result.returncode == 1:
        raise ReviewEvidenceError("owner stale-seal commit is not locally reachable")
    raise _StaleSealEvidenceUnknown("owner stale-seal Git ancestry is API_UNKNOWN")


def _stale_seal_local_non_ancestor(
    repo_root: Path,
    *,
    ancestor_sha: str,
    descendant_sha: str,
) -> None:
    """Require local Git to prove that one commit did not precede another."""

    try:
        git = _git_path()
        result = subprocess.run(  # nosec B603: absolute git plus validated fixed argv (remove-by: 2026-09-30, ref: PR-governance-seal)
            [git, "merge-base", "--is-ancestor", ancestor_sha, descendant_sha],
            cwd=repo_root,
            env=_git_environment(),
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (_GitCommandError, OSError, subprocess.TimeoutExpired) as exc:
        raise _StaleSealEvidenceUnknown("owner stale-seal Git evidence is API_UNKNOWN") from exc
    if result.returncode == 1:
        return
    if result.returncode == 0:
        raise ReviewEvidenceError(
            "owner stale-seal synchronized base already preceded prior closeout"
        )
    raise _StaleSealEvidenceUnknown("owner stale-seal Git ancestry is API_UNKNOWN")


def _stale_seal_snapshot_children(
    repo_root: Path,
    *,
    snapshot: Any,
    parent_sha: str,
) -> tuple[str, ...]:
    children: list[str] = []
    for commit_sha in snapshot.commit_shas:
        if parent_sha in _stale_seal_commit_parents(repo_root, commit_sha):
            children.append(commit_sha)
    return tuple(sorted(children))


def _validate_historical_stale_seal_reseal(
    *,
    repo_root: Path,
    snapshot: Any,
    repository: str,
    token: str,
    stale_head_sha: str,
    reseal_sha: str,
    request_json: Any,
) -> datetime:
    from scripts.orchestration.pr_commit_identity import CommitRefKind, RepositoryCommitRef

    stale_head = _require_sha(stale_head_sha, label="owner stale-seal stale head")
    reseal = _require_sha(reseal_sha, label="owner stale-seal reseal")
    if stale_head == reseal or not {stale_head, reseal} <= snapshot.commit_shas:
        raise ReviewEvidenceError("owner stale-seal reply does not select two live PR commits")
    stale_ref = _stale_seal_repository_commit(
        stale_head,
        snapshot=snapshot,
        token=token,
        require_pr_commit=True,
    )
    reseal_ref = _stale_seal_repository_commit(
        reseal,
        snapshot=snapshot,
        token=token,
        require_pr_commit=True,
    )
    live_ref = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
    _stale_seal_remote_ancestor(
        stale_ref,
        reseal_ref,
        repository=repository,
        token=token,
    )
    _stale_seal_remote_ancestor(
        reseal_ref,
        live_ref,
        repository=repository,
        token=token,
    )

    stale_parents = _stale_seal_commit_parents(repo_root, stale_head)
    if len(stale_parents) != 2:
        raise ReviewEvidenceError("owner stale-seal stale head is not a two-parent base sync")
    prior_closeout, synchronized_base = stale_parents
    _validate_stale_seal_mapping_only_edge(
        repo_root,
        parent_sha=stale_head,
        child_sha=reseal,
        pr_number=snapshot.pr_number,
        allow_mapping_add=False,
    )
    if _stale_seal_snapshot_children(
        repo_root,
        snapshot=snapshot,
        parent_sha=stale_head,
    ) != (reseal,):
        raise ReviewEvidenceError("owner stale-seal reseal is not the sole direct PR child")

    synchronized_base_ref = _stale_seal_repository_commit(
        synchronized_base,
        snapshot=snapshot,
        token=token,
        require_pr_commit=False,
    )
    current_base_ref = _stale_seal_repository_commit(
        snapshot.base_sha,
        snapshot=snapshot,
        token=token,
        require_pr_commit=False,
    )
    _stale_seal_local_ancestor(
        repo_root,
        ancestor_sha=synchronized_base,
        descendant_sha=snapshot.base_sha,
    )
    _stale_seal_remote_ancestor(
        synchronized_base_ref,
        current_base_ref,
        repository=repository,
        token=token,
    )

    prior_mapping = _stale_seal_mapping_blob(
        repo_root,
        commit_sha=prior_closeout,
        pr_number=snapshot.pr_number,
    )
    inherited_mapping = _stale_seal_mapping_blob(
        repo_root,
        commit_sha=stale_head,
        pr_number=snapshot.pr_number,
    )
    resealed_mapping = _stale_seal_mapping_blob(
        repo_root,
        commit_sha=reseal,
        pr_number=snapshot.pr_number,
    )
    if prior_mapping != inherited_mapping or inherited_mapping == resealed_mapping:
        raise ReviewEvidenceError("owner stale-seal mapping inheritance/reseal is invalid")

    old_seal = parse_embedded_review_seal(prior_mapping)
    old_material_head = _require_sha(
        old_seal["material"]["material_head_sha"],
        label="owner stale-seal prior material head",
    )
    old_base = _require_sha(
        old_seal["material"]["base_ref_oid"],
        label="owner stale-seal prior base",
    )
    if old_base == synchronized_base:
        raise ReviewEvidenceError("owner stale-seal base sync did not advance the base")
    _validate_stale_seal_mapping_only_edge(
        repo_root,
        parent_sha=old_material_head,
        child_sha=prior_closeout,
        pr_number=snapshot.pr_number,
        allow_mapping_add=True,
        ban_trigger_only=False,
    )
    if _stale_seal_snapshot_children(
        repo_root,
        snapshot=snapshot,
        parent_sha=old_material_head,
    ) != (prior_closeout,):
        raise ReviewEvidenceError("owner stale-seal prior closeout is not the sole direct PR child")
    _stale_seal_repository_commit(
        old_material_head,
        snapshot=snapshot,
        token=token,
        require_pr_commit=False,
    )
    old_base_ref = _stale_seal_repository_commit(
        old_base,
        snapshot=snapshot,
        token=token,
        require_pr_commit=False,
    )
    _stale_seal_local_ancestor(
        repo_root,
        ancestor_sha=old_base,
        descendant_sha=synchronized_base,
    )
    _stale_seal_remote_ancestor(
        old_base_ref,
        synchronized_base_ref,
        repository=repository,
        token=token,
    )
    _stale_seal_local_non_ancestor(
        repo_root,
        ancestor_sha=synchronized_base,
        descendant_sha=prior_closeout,
    )
    _stale_seal_remote_non_ancestor(
        synchronized_base_ref,
        _stale_seal_repository_commit(
            prior_closeout,
            snapshot=snapshot,
            token=token,
            require_pr_commit=True,
        ),
        repository=repository,
        token=token,
    )
    prior_manifest = _stale_seal_material_manifest(
        repo_root,
        base_ref_oid=old_base,
        head_ref_oid=old_material_head,
        pr_number=snapshot.pr_number,
    )
    _validate_stale_seal_projection(
        prior_mapping,
        manifest=prior_manifest,
        repository=repository,
        pr_number=snapshot.pr_number,
        require_provider_no_claim=False,
    )

    stale_manifest = _stale_seal_material_manifest(
        repo_root,
        base_ref_oid=synchronized_base,
        head_ref_oid=stale_head,
        pr_number=snapshot.pr_number,
    )
    reseal_manifest = _stale_seal_material_manifest(
        repo_root,
        base_ref_oid=synchronized_base,
        head_ref_oid=reseal,
        pr_number=snapshot.pr_number,
    )
    if not _stale_seal_manifests_match(stale_manifest, reseal_manifest):
        raise ReviewEvidenceError("owner stale-seal reseal changes material identity")
    _validate_stale_seal_projection(
        resealed_mapping,
        manifest=stale_manifest,
        repository=repository,
        pr_number=snapshot.pr_number,
        require_provider_no_claim=True,
    )
    prior_material = old_seal["material"]
    if (
        prior_material["base_ref_oid"] == stale_manifest.base_ref_oid
        and prior_material["merge_base_sha"] == stale_manifest.merge_base_sha
        and prior_material["material_head_sha"] == stale_manifest.head_ref_oid
        and prior_material["digest"] == stale_manifest.digest
    ):
        raise ReviewEvidenceError("owner stale-seal prior seal was not stale at the sync")
    return _fetch_stale_seal_reseal_pushed_at(
        snapshot=snapshot,
        repository=repository,
        stale_head_sha=stale_head,
        reseal_sha=reseal,
        token=token,
        request_json=request_json,
    )


def _validate_current_stale_seal_closeout(
    *,
    repo_root: Path,
    snapshot: Any,
    repository: str,
    token: str,
    material_digest: str,
    material_head_sha: str,
) -> None:
    from scripts.orchestration.pr_commit_identity import CommitRefKind, RepositoryCommitRef

    expected_digest = _require_digest(material_digest, label="material_digest")
    expected_material_head = _require_sha(material_head_sha, label="material_head_sha")
    live_mapping = _stale_seal_mapping_blob(
        repo_root,
        commit_sha=snapshot.head_sha,
        pr_number=snapshot.pr_number,
    )
    live_seal = parse_embedded_review_seal(live_mapping)
    sealed_head = _require_sha(
        live_seal["material"]["material_head_sha"],
        label="owner stale-seal current material head",
    )
    if sealed_head != expected_material_head or live_seal["material"]["digest"] != expected_digest:
        raise ReviewEvidenceError("owner stale-seal current live seal is not caller-bound")
    sealed_ref = _stale_seal_repository_commit(
        sealed_head,
        snapshot=snapshot,
        token=token,
        require_pr_commit=True,
    )
    live_ref = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
    _stale_seal_remote_ancestor(
        sealed_ref,
        live_ref,
        repository=repository,
        token=token,
    )
    _validate_stale_seal_mapping_only_edge(
        repo_root,
        parent_sha=sealed_head,
        child_sha=snapshot.head_sha,
        pr_number=snapshot.pr_number,
        allow_mapping_add=False,
    )
    if _stale_seal_snapshot_children(
        repo_root,
        snapshot=snapshot,
        parent_sha=sealed_head,
    ) != (snapshot.head_sha,):
        raise ReviewEvidenceError("owner stale-seal current reseal is not the sole direct child")
    material_manifest = _stale_seal_material_manifest(
        repo_root,
        base_ref_oid=snapshot.base_sha,
        head_ref_oid=sealed_head,
        pr_number=snapshot.pr_number,
    )
    live_manifest = _stale_seal_material_manifest(
        repo_root,
        base_ref_oid=snapshot.base_sha,
        head_ref_oid=snapshot.head_sha,
        pr_number=snapshot.pr_number,
    )
    if not _stale_seal_manifests_match(material_manifest, live_manifest):
        raise ReviewEvidenceError("owner stale-seal current reseal changes material identity")
    _validate_stale_seal_projection(
        live_mapping,
        manifest=material_manifest,
        repository=repository,
        pr_number=snapshot.pr_number,
        require_provider_no_claim=True,
    )


def _validate_stale_seal_root_identity(
    *,
    url: str,
    finding: Any,
    stale_head_sha: str,
    owner: str,
    name: str,
    pr_number: int,
    token: str,
    request_json: Any,
) -> bool:
    match = re.fullmatch(
        rf"https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#discussion_r(?P<comment_id>[1-9][0-9]*)",
        url,
        flags=re.IGNORECASE,
    )
    if match is None:
        return False
    try:
        response = request_json(
            f"https://api.github.com/repos/{owner}/{name}/pulls/comments/"
            f"{match.group('comment_id')}",
            token=token,
        )
    except Exception as exc:
        raise _StaleSealEvidenceUnknown(
            "owner stale-seal review-comment identity is API_UNKNOWN"
        ) from exc
    if not isinstance(response, dict):
        raise _StaleSealEvidenceUnknown("owner stale-seal review-comment identity is API_UNKNOWN")
    required_fields = {
        "body",
        "created_at",
        "html_url",
        "id",
        "original_commit_id",
        "path",
        "pull_request_url",
        "updated_at",
        "user",
    }
    if not required_fields <= response.keys():
        raise _StaleSealEvidenceUnknown("owner stale-seal review-comment identity is API_UNKNOWN")
    user = response.get("user")
    if (
        not isinstance(response.get("id"), int)
        or isinstance(response.get("id"), bool)
        or not all(isinstance(response.get(key), str) for key in required_fields - {"id", "user"})
        or not isinstance(user, dict)
        or not {"id", "login", "type"} <= user.keys()
        or not isinstance(user.get("id"), int)
        or isinstance(user.get("id"), bool)
        or not isinstance(user.get("login"), str)
        or not isinstance(user.get("type"), str)
    ):
        raise _StaleSealEvidenceUnknown("owner stale-seal review-comment identity is API_UNKNOWN")
    expected_pr_url = f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}"
    expected_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    return (
        response.get("id") == int(match.group("comment_id"))
        and response.get("html_url") == url
        and response.get("pull_request_url") == expected_pr_url
        and response.get("path") == expected_path
        and response.get("original_commit_id") == stale_head_sha
        and response.get("body") == finding.body
        and response.get("created_at") == finding.created_at
        and response.get("updated_at") == finding.created_at
        and user.get("id") == 199_175_422
        and user.get("login") == "chatgpt-codex-connector[bot]"
        and user.get("type") == "Bot"
    )


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


def build_provider_no_claim_pair(
    *,
    base_revision: str,
    head_revision: str,
    material_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the exact provider-neutral no-claim pair for one material range."""

    code_review = {
        "blocking": False,
        "material_digest": material_digest,
        "material_head_sha": head_revision,
        "output_required": False,
        "review_claim": "none",
    }
    codex_security = {
        "base_revision": base_revision,
        "blocking": False,
        "head_revision": head_revision,
        "material_digest": material_digest,
        "no_findings_claim": False,
        "output_required": False,
        "scan_claim": "none",
    }
    _validate_code_review_receipt(code_review, material_digest=material_digest)
    _validate_security_receipt(codex_security)
    return code_review, codex_security


def is_provider_no_claim_review_receipt(receipt: Any) -> bool:
    """Return whether the receipt is the exact provider-neutral review no-claim form."""

    return (
        isinstance(receipt, dict)
        and frozenset(receipt) == PROVIDER_NO_CLAIM_REVIEW_KEYS
        and receipt.get("review_claim") == "none"
        and receipt.get("output_required") is False
        and receipt.get("blocking") is False
    )


def is_provider_no_claim_security_receipt(receipt: Any) -> bool:
    """Return whether the receipt is the exact provider-neutral scan no-claim form."""

    return (
        isinstance(receipt, dict)
        and frozenset(receipt) == PROVIDER_NO_CLAIM_SECURITY_KEYS
        and receipt.get("scan_claim") == "none"
        and receipt.get("no_findings_claim") is False
        and receipt.get("output_required") is False
        and receipt.get("blocking") is False
    )


def _applicable_scoped_agents(
    material_paths: Iterable[str],
    *,
    material_head_sha: str,
) -> list[str]:
    """Return every AGENTS.md ancestor present in the exact material-head tree."""

    candidates = {"AGENTS.md"}
    for raw_path in material_paths:
        path = _validate_material_path(raw_path.encode("utf-8"))
        current = PurePosixPath(path).parent
        while current != PurePosixPath("."):
            candidates.add((current / "AGENTS.md").as_posix())
            current = current.parent

    head_sha = _require_sha(material_head_sha, label="material_head_sha")
    raw = _run_git(
        _REPO_ROOT,
        [
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            "--full-tree",
            head_sha,
            "--",
            *(f":(literal){path}" for path in sorted(candidates)),
        ],
    )
    discovered: set[str] = set()
    for path_bytes in raw.split(b"\0"):
        if not path_bytes:
            continue
        path = _validate_material_path(path_bytes)
        if path not in candidates or path in discovered:
            raise ReviewEvidenceError(
                "material-head AGENTS.md discovery returned an unexpected path"
            )
        discovered.add(path)
    return sorted(discovered)


def _validate_self_review_report_payload(
    report: Any,
    *,
    base_ref_oid: str,
    merge_base_sha: str,
    material_head_sha: str,
    material_digest: str,
    material_paths: Iterable[str] | None = None,
    material_diff_summary: MaterialDiffSummary | None = None,
) -> dict[str, Any]:
    expected_material_paths = None if material_paths is None else tuple(material_paths)
    if not isinstance(report, dict):
        raise ReviewEvidenceError("pulseplate-pr-review report must be an object")
    _require_exact_keys(
        report,
        set(SELF_REVIEW_REPORT_KEYS),
        label="pulseplate-pr-review report",
    )
    findings = report["findings"]
    findings_count = report["findings_count"]
    actionable_findings_count = report["actionable_findings_count"]
    scope = report["scope_reviewed"]
    if (
        report["schema_version"] != SELF_REVIEW_REPORT_SCHEMA_VERSION
        or report["mode"] != "dry-run-report"
        or not isinstance(findings, list)
        or not isinstance(findings_count, int)
        or isinstance(findings_count, bool)
        or findings_count < 0
        or findings_count != len(findings)
        or not isinstance(actionable_findings_count, int)
        or isinstance(actionable_findings_count, bool)
        or actionable_findings_count < 0
        or not isinstance(scope, dict)
    ):
        raise ReviewEvidenceError("pulseplate-pr-review report contract is malformed")

    if material_diff_summary is not None:
        if not isinstance(material_diff_summary, MaterialDiffSummary):
            raise ReviewEvidenceError("material diff summary evidence is malformed")
        diff_summary = scope.get("diff_summary")
        expected_diff_summary = material_diff_summary.as_dict()
        if not isinstance(diff_summary, dict) or any(
            not isinstance(diff_summary.get(key), int)
            or isinstance(diff_summary.get(key), bool)
            or diff_summary[key] < 0
            or diff_summary[key] != expected_diff_summary[key]
            for key in ("files", "additions", "deletions", "changed_lines")
        ):
            raise ReviewEvidenceError(
                "pulseplate-pr-review diff summary does not match the exact material"
            )

    severity_rank = {"note": 0, "minor": 1, "major": 2, "critical": 3}
    for finding in findings:
        if not isinstance(finding, dict):
            raise ReviewEvidenceError("pulseplate-pr-review finding must be an object")
        _require_exact_keys(
            finding,
            set(SELF_REVIEW_FINDING_KEYS),
            label="pulseplate-pr-review finding",
        )
        for key in (
            "category",
            "diagnostic_code",
            "disposition_candidate",
            "evidence",
            "file",
            "gate_to_run",
            "role_agent",
            "severity",
            "suggested_fix",
        ):
            if not isinstance(finding[key], str) or not finding[key].strip():
                raise ReviewEvidenceError(
                    f"pulseplate-pr-review finding {key} must be a non-empty string"
                )
        line = finding["line"]
        if line is not None and (not isinstance(line, int) or isinstance(line, bool) or line <= 0):
            raise ReviewEvidenceError(
                "pulseplate-pr-review finding line must be null or a positive integer"
            )
        severity = finding["severity"]
        diagnostic_code = finding["diagnostic_code"]
        minimum_severity = SELF_REVIEW_DIAGNOSTIC_MIN_SEVERITY.get(diagnostic_code)
        if (
            severity not in SELF_REVIEW_ALLOWED_SEVERITIES
            or minimum_severity is None
            or severity_rank[severity] < severity_rank[minimum_severity]
            or (severity == "note" and diagnostic_code not in SELF_REVIEW_NONBLOCKING_NOTE_CODES)
            or (
                finding["disposition_candidate"] == "NEEDS-HUMAN"
                and severity not in SELF_REVIEW_ACTIONABLE_SEVERITIES
            )
        ):
            raise ReviewEvidenceError(
                "pulseplate-pr-review finding severity or diagnostic code is invalid"
            )
        if diagnostic_code == "large_diff_review_risk":
            diff_summary = scope.get("diff_summary")
            changed_lines = (
                diff_summary.get("changed_lines") if isinstance(diff_summary, dict) else None
            )
            if (
                severity != "note"
                or finding["disposition_candidate"] != "NOT-A-BUG"
                or finding["role_agent"] != "bug-hunter"
                or finding["category"] != "tests"
                or finding["file"] != "docs/roadmap/BACKLOG_LEDGER.md"
                or finding["gate_to_run"] != "make validate-changed"
                or not isinstance(changed_lines, int)
                or isinstance(changed_lines, bool)
                or changed_lines <= SELF_REVIEW_LARGE_DIFF_CHANGED_LINES
            ):
                raise ReviewEvidenceError(
                    "large_diff_review_risk note does not match its advisory contract"
                )
            threshold = (
                SELF_REVIEW_VERY_LARGE_DIFF_CHANGED_LINES
                if changed_lines > SELF_REVIEW_VERY_LARGE_DIFF_CHANGED_LINES
                else SELF_REVIEW_LARGE_DIFF_CHANGED_LINES
            )
            if finding["evidence"] != (
                f"Diff contains {changed_lines} changed lines, "
                f"above review-risk threshold {threshold}."
            ):
                raise ReviewEvidenceError(
                    "large_diff_review_risk evidence does not match report scope"
                )

    def diagnostic_evidence(code: str) -> list[str]:
        return sorted(
            finding["evidence"] for finding in findings if finding["diagnostic_code"] == code
        )

    warnings = report["warnings"]
    if (
        not isinstance(warnings, list)
        or any(not isinstance(warning, str) or not warning.strip() for warning in warnings)
        or len(warnings) != len(set(warnings))
        or diagnostic_evidence("context_warning") != sorted(warnings)
    ):
        raise ReviewEvidenceError("pulseplate-pr-review warnings must remain actionable findings")

    pr_metadata_available = scope.get("pr_metadata_available")
    if not isinstance(pr_metadata_available, bool):
        raise ReviewEvidenceError(
            "pulseplate-pr-review scope pr_metadata_available must be boolean"
        )
    expected_missing_metadata = (
        [] if pr_metadata_available else ["PR metadata is unavailable in the supplied context."]
    )
    if diagnostic_evidence("missing_pr_metadata") != expected_missing_metadata:
        raise ReviewEvidenceError("pulseplate-pr-review missing PR metadata must remain actionable")

    scoped_agents = scope.get("scoped_agents_md")
    if (
        not isinstance(scoped_agents, list)
        or any(not isinstance(path, str) or not path for path in scoped_agents)
        or len(scoped_agents) != len(set(scoped_agents))
    ):
        raise ReviewEvidenceError("pulseplate-pr-review scoped AGENTS.md coverage is malformed")
    expected_missing_agents = (
        []
        if scoped_agents
        else ["No scoped AGENTS.md files were discovered for the changed files."]
    )
    if diagnostic_evidence("missing_scoped_agents") != expected_missing_agents:
        raise ReviewEvidenceError(
            "pulseplate-pr-review missing scoped AGENTS.md must remain actionable"
        )

    fixed_mapping_errors = scope.get("fixed_mapping_errors")
    if (
        not isinstance(fixed_mapping_errors, list)
        or any(not isinstance(error, str) or not error for error in fixed_mapping_errors)
        or len(fixed_mapping_errors) != len(set(fixed_mapping_errors))
        or diagnostic_evidence("invalid_fixed_mapping") != sorted(fixed_mapping_errors)
    ):
        raise ReviewEvidenceError(
            "pulseplate-pr-review fixed-mapping uncertainty must remain actionable"
        )

    review_source_status = report["review_source_status"]
    if not isinstance(review_source_status, list) or any(
        not isinstance(source, dict) for source in review_source_status
    ):
        raise ReviewEvidenceError("pulseplate-pr-review source status is malformed")
    expected_blocking_sources = sorted(
        "Review source has explicit blocking status: "
        f"{source.get('source')}={source.get('status')}"
        for source in review_source_status
        if bool(source.get("blocking"))
    )
    if diagnostic_evidence("blocking_review_source") != expected_blocking_sources:
        raise ReviewEvidenceError("pulseplate-pr-review blocking source must remain actionable")

    diff_summary = scope.get("diff_summary")
    changed_lines = diff_summary.get("changed_lines") if isinstance(diff_summary, dict) else None
    changed_lines_is_valid = isinstance(changed_lines, int) and not isinstance(changed_lines, bool)
    expected_invalid_changed_lines = (
        []
        if changed_lines_is_valid
        else ["diff.summary.changed_lines is not numeric; " "treated as 0 for advisory planning."]
    )
    if diagnostic_evidence("invalid_changed_lines") != expected_invalid_changed_lines:
        raise ReviewEvidenceError("pulseplate-pr-review diff uncertainty must remain actionable")
    expected_large_diff: list[str] = []
    if (
        isinstance(changed_lines, int)
        and not isinstance(changed_lines, bool)
        and changed_lines > SELF_REVIEW_LARGE_DIFF_CHANGED_LINES
    ):
        threshold = (
            SELF_REVIEW_VERY_LARGE_DIFF_CHANGED_LINES
            if changed_lines > SELF_REVIEW_VERY_LARGE_DIFF_CHANGED_LINES
            else SELF_REVIEW_LARGE_DIFF_CHANGED_LINES
        )
        expected_large_diff.append(
            f"Diff contains {changed_lines} changed lines, "
            f"above review-risk threshold {threshold}."
        )
    if diagnostic_evidence("large_diff_review_risk") != expected_large_diff:
        raise ReviewEvidenceError(
            "pulseplate-pr-review large-diff diagnostic does not match report scope"
        )

    computed_actionable = sum(
        finding["severity"] in SELF_REVIEW_ACTIONABLE_SEVERITIES for finding in findings
    )
    if actionable_findings_count != computed_actionable:
        raise ReviewEvidenceError(
            "pulseplate-pr-review actionable findings counter is inconsistent"
        )
    if actionable_findings_count:
        raise ReviewEvidenceError(
            "pulseplate-pr-review report contains unresolved actionable findings; "
            "fix or disposition them and regenerate the exact-material report"
        )

    report_base_ref = _require_sha(
        report["base_ref_oid"],
        label="pulseplate-pr-review report base_ref_oid",
    )
    report_merge_base = _require_sha(
        report["merge_base_sha"],
        label="pulseplate-pr-review report merge_base_sha",
    )
    report_material_head = _require_sha(
        report["material_head_sha"],
        label="pulseplate-pr-review report material_head_sha",
    )
    report_material_digest = _require_digest(
        report["material_digest"],
        label="pulseplate-pr-review report material_digest",
    )
    if (
        report_base_ref != base_ref_oid
        or report_merge_base != merge_base_sha
        or report_material_head != material_head_sha
        or report_material_digest != material_digest
    ):
        raise ReviewEvidenceError("pulseplate-pr-review report is stale for the exact material")

    changed_files = scope.get("changed_files")
    if (
        not isinstance(changed_files, list)
        or any(not isinstance(path, str) or not path for path in changed_files)
        or len(changed_files) != len(set(changed_files))
    ):
        raise ReviewEvidenceError("pulseplate-pr-review report changed-file coverage is malformed")
    if expected_material_paths is not None and sorted(changed_files) != sorted(
        set(expected_material_paths)
    ):
        raise ReviewEvidenceError(
            "pulseplate-pr-review report does not cover the exact material path set"
        )
    if expected_material_paths is not None and sorted(scoped_agents) != (
        _applicable_scoped_agents(
            expected_material_paths,
            material_head_sha=material_head_sha,
        )
    ):
        raise ReviewEvidenceError(
            "pulseplate-pr-review scoped AGENTS.md coverage does not match "
            "the exact material paths"
        )
    return report


def _self_review_report_sha256(report: Mapping[str, Any]) -> str:
    canonical = _canonical_json(report).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def ingest_repo_native_self_review_receipt(
    report_path: Path,
    *,
    material_manifest: MaterialManifest,
) -> dict[str, Any]:
    """Bind one executable pulseplate-pr-review report to exact material."""

    material_paths = tuple(entry.path for entry in material_manifest.entries)
    material_diff_summary = material_manifest.diff_summary
    if not isinstance(
        material_diff_summary, MaterialDiffSummary
    ) or material_diff_summary.files != len(material_paths):
        raise ReviewEvidenceError("material manifest is missing Git-derived diff summary evidence")
    try:
        descriptor = os.open(
            report_path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0),
        )
    except OSError as exc:
        raise ReviewEvidenceError(
            "pulseplate-pr-review report is missing, unsafe, or unreadable"
        ) from exc
    try:
        raw = _read_regular_descriptor(
            descriptor,
            max_bytes=_MAX_SELF_REVIEW_REPORT_BYTES,
            label="pulseplate-pr-review report",
        )
    finally:
        os.close(descriptor)
    report = _validate_self_review_report_payload(
        _load_json_bytes(raw, label="pulseplate-pr-review report"),
        base_ref_oid=material_manifest.base_ref_oid,
        merge_base_sha=material_manifest.merge_base_sha,
        material_head_sha=material_manifest.head_ref_oid,
        material_digest=material_manifest.digest,
        material_paths=material_paths,
        material_diff_summary=material_diff_summary,
    )
    receipt = {
        "actionable_findings_count": report["actionable_findings_count"],
        "authority": REPO_NATIVE_SELF_REVIEW_AUTHORITY,
        "blocking": False,
        "findings_count": report["findings_count"],
        "material_digest": _require_digest(
            material_manifest.digest,
            label="self_review.material_digest",
        ),
        "material_head_sha": _require_sha(
            material_manifest.head_ref_oid,
            label="self_review.material_head_sha",
        ),
        "report_payload": report,
        "report_sha256": _self_review_report_sha256(report),
        "review_claim": "none",
        "review_tool": REPO_NATIVE_SELF_REVIEW_TOOL,
        "schema_version": SELF_REVIEW_ADVISORY_SCHEMA_VERSION,
        "status": REPO_NATIVE_SELF_REVIEW_STATUS,
    }
    _validate_repo_native_self_review_receipt(
        receipt,
        base_ref_oid=material_manifest.base_ref_oid,
        merge_base_sha=material_manifest.merge_base_sha,
        material_head_sha=material_manifest.head_ref_oid,
        material_digest=material_manifest.digest,
        material_paths=material_paths,
        material_diff_summary=material_diff_summary,
    )
    return receipt


def protected_trust_boundary_paths(material_paths: Iterable[str]) -> tuple[str, ...]:
    """Return protected paths using the existing outage trust-boundary detector."""

    return tuple(
        sorted(
            {
                path
                for path in material_paths
                if path in OPERATOR_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS
                or path in _CANONICAL_CODEOWNERS_PATHS
                or path.startswith(OPERATOR_OUTAGE_TRUST_BOUNDARY_PREFIXES)
                or PurePosixPath(path).name in _DEPENDENCY_MANIFEST_BASENAMES
                or is_protected_python_dependency_text_path(path)
            }
        )
    )


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

    touched = sorted(
        {
            path
            for path in material_paths
            if path in REVIEW_CREDIT_OUTAGE_TRUST_BOUNDARY_EXACT_PATHS
            or path.startswith(REVIEW_CREDIT_OUTAGE_TRUST_BOUNDARY_PREFIXES)
        }
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

    touched = protected_trust_boundary_paths(material_paths)
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


def _validate_repo_native_self_review_receipt(
    receipt: Any,
    *,
    base_ref_oid: str,
    merge_base_sha: str,
    material_head_sha: str,
    material_digest: str,
    material_paths: Iterable[str] | None = None,
    material_diff_summary: MaterialDiffSummary | None = None,
) -> None:
    if not isinstance(receipt, dict):
        raise ReviewEvidenceError("self_review must be an object")
    _require_exact_keys(
        receipt,
        set(REPO_NATIVE_SELF_REVIEW_KEYS),
        label="self_review",
    )
    if (
        receipt["schema_version"] != SELF_REVIEW_ADVISORY_SCHEMA_VERSION
        or receipt["authority"] != REPO_NATIVE_SELF_REVIEW_AUTHORITY
        or receipt["review_tool"] != REPO_NATIVE_SELF_REVIEW_TOOL
        or receipt["status"] != REPO_NATIVE_SELF_REVIEW_STATUS
        or receipt["review_claim"] != "none"
        or receipt["blocking"] is not False
        or not isinstance(receipt["findings_count"], int)
        or isinstance(receipt["findings_count"], bool)
        or receipt["findings_count"] < 0
        or not isinstance(receipt["actionable_findings_count"], int)
        or isinstance(receipt["actionable_findings_count"], bool)
        or receipt["actionable_findings_count"] != 0
        or _require_sha(
            receipt["material_head_sha"],
            label="self_review.material_head_sha",
        )
        != material_head_sha
        or _require_digest(
            receipt["material_digest"],
            label="self_review.material_digest",
        )
        != material_digest
    ):
        raise ReviewEvidenceError("self_review receipt is malformed or stale")
    report = _validate_self_review_report_payload(
        receipt["report_payload"],
        base_ref_oid=base_ref_oid,
        merge_base_sha=merge_base_sha,
        material_head_sha=material_head_sha,
        material_digest=material_digest,
        material_paths=material_paths,
        material_diff_summary=material_diff_summary,
    )
    if (
        receipt["findings_count"] != report["findings_count"]
        or receipt["actionable_findings_count"] != report["actionable_findings_count"]
        or _require_digest(
            receipt["report_sha256"],
            label="self_review.report_sha256",
        )
        != _self_review_report_sha256(report)
    ):
        raise ReviewEvidenceError("self_review report payload integrity check failed")


def _validate_security_receipt(receipt: Any) -> None:
    if not isinstance(receipt, dict):
        raise ReviewEvidenceError("codex_security must be an object")
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
    if {
        "blocking",
        "material_digest",
        "no_findings_claim",
        "output_required",
        "scan_claim",
    } & receipt.keys():
        _require_exact_keys(
            receipt,
            set(PROVIDER_NO_CLAIM_SECURITY_KEYS),
            label="provider-neutral security no-claim receipt",
        )
        _require_sha(receipt["base_revision"], label="codex_security.base_revision")
        _require_sha(receipt["head_revision"], label="codex_security.head_revision")
        _require_digest(receipt["material_digest"], label="codex_security.material_digest")
        if (
            receipt["scan_claim"] != "none"
            or receipt["no_findings_claim"] is not False
            or receipt["output_required"] is not False
            or receipt["blocking"] is not False
        ):
            raise ReviewEvidenceError(
                "provider-neutral security no-claim receipt is malformed or escalating"
            )
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

    if {
        "blocking",
        "material_digest",
        "material_head_sha",
        "output_required",
        "review_claim",
    } & receipt.keys():
        _require_exact_keys(
            receipt,
            set(PROVIDER_NO_CLAIM_REVIEW_KEYS),
            label="provider-neutral review no-claim receipt",
        )
        _require_sha(receipt["material_head_sha"], label="code_review.material_head_sha")
        _require_digest(receipt["material_digest"], label="code_review.material_digest")
        if (
            receipt["material_digest"] != material_digest
            or receipt["review_claim"] != "none"
            or receipt["output_required"] is not False
            or receipt["blocking"] is not False
        ):
            raise ReviewEvidenceError(
                "provider-neutral review no-claim receipt is malformed, stale, or escalating"
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


def validate_review_seal(
    seal: Any,
    *,
    material_paths: Iterable[str] | None = None,
    material_diff_summary: MaterialDiffSummary | None = None,
) -> dict[str, Any]:
    """Validate the closed v1 embedded seal schema and return it unchanged."""

    if not isinstance(seal, dict):
        raise ReviewEvidenceError("review seal must be an object")
    legacy_keys = {
        "authority",
        "code_review",
        "codex_security",
        "material",
        "pr_number",
        "repository",
        "schema_version",
    }
    if frozenset(seal) not in {
        frozenset(legacy_keys),
        frozenset({*legacy_keys, "self_review"}),
    }:
        raise ReviewEvidenceError("review seal has unknown or missing fields")
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
    if (
        is_review_source_unavailability_receipt(code_review)
        or is_review_source_positive_response_receipt(code_review)
        or is_provider_no_claim_review_receipt(code_review)
    ) and (code_review["material_head_sha"] != material["material_head_sha"]):
        raise ReviewEvidenceError(
            "review-source context receipt does not match sealed material head"
        )
    security_receipt = seal["codex_security"]
    _validate_security_receipt(security_receipt)
    review_no_claim = is_provider_no_claim_review_receipt(code_review)
    security_no_claim = is_provider_no_claim_security_receipt(security_receipt)
    if review_no_claim != security_no_claim:
        raise ReviewEvidenceError(
            "provider-neutral no-claim evidence must be an exact symmetric pair"
        )
    if review_no_claim:
        if "self_review" not in seal:
            raise ReviewEvidenceError(
                "provider-neutral no-claim requires an exact-material repo-native "
                "self-review advisory artifact"
            )
        _validate_repo_native_self_review_receipt(
            seal["self_review"],
            base_ref_oid=material["base_ref_oid"],
            merge_base_sha=material["merge_base_sha"],
            material_head_sha=material["material_head_sha"],
            material_digest=material_digest,
            material_paths=material_paths,
            material_diff_summary=material_diff_summary,
        )
    elif "self_review" in seal:
        raise ReviewEvidenceError(
            "repo-native self-review advisory artifact is reserved for "
            "provider-neutral no-claim seals"
        )
    if (
        security_receipt["base_revision"] != material["merge_base_sha"]
        or security_receipt["head_revision"] != material["material_head_sha"]
    ):
        raise ReviewEvidenceError("Codex Security receipt does not match sealed material range")
    if (
        is_security_outage_override_receipt(security_receipt) or security_no_claim
    ) and security_receipt["material_digest"] != material_digest:
        raise ReviewEvidenceError(
            "Codex Security context receipt does not match sealed material digest"
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
