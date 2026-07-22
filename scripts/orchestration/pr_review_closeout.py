#!/usr/bin/env python3
"""Atomic authoring and validation for one material-bound PR closeout.

The draft and frozen manifest stay under gitignored ``artifacts/``.  Only the
``seal`` command writes the canonical mapping artifact, so review dispositions
and the content-bound security receipt can be published in one closeout commit.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess  # nosec B404: bounded absolute git commands are required (remove-by: 2026-09-30, ref: PR-governance-material-seal)
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, cast


def _load_posix_locking_backend() -> Any | None:
    try:
        return importlib.import_module("fcntl")
    except ImportError:
        return None


_FCNTL = _load_posix_locking_backend()

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.pr_commit_identity import (  # noqa: E402
    CommitIdentityError,
    CommitRefKind,
    RepositoryCommitRef,
    assert_snapshot_unchanged,
    classify_commit_ref,
    fetch_pr_snapshot,
    github_api_request,
    is_ancestor,
    verify_codex_review_reference,
    verify_codex_review_source_unavailability_reference,
    verify_review_credit_outage_references,
    verify_security_outage_override_reference,
)
from scripts.orchestration.pr_review_evidence import (  # noqa: E402
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    SEAL_SCHEMA_VERSION,
    UNAVAILABLE_REVIEW_REF_CAUSE,
    ReviewEvidenceError,
    build_review_credit_outage_receipt,
    build_review_source_unavailability_receipt,
    build_security_outage_override_receipt,
    compute_material_manifest,
    ingest_codex_security_receipt,
    is_review_credit_outage_receipt,
    is_review_source_unavailability_receipt,
    is_security_outage_override_receipt,
    parse_embedded_review_seal,
    render_embedded_review_seal,
    unavailable_review_ref_fingerprint,
    validate_review_credit_outage_scope,
    validate_security_outage_override_scope,
)
from scripts.orchestration.review_mapping_artifact import (  # noqa: E402
    NO_ACTIONABLE_LINE,
    extract_fixed_mapping_section,
    mapping_artifact_path,
    validate_mapping_artifact_text,
)

DRAFT_SCHEMA_VERSION = "pulseplate.pr-review-closeout-draft/v1"
FINAL_SECURITY_PREPARATION_SCHEMA_VERSION = "pulseplate.final-security-preparation/v2"
STATE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "pr_review_closeout"
BACKLOG_LEDGER_PATH = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
VALID_DISPOSITIONS = frozenset({"FIXED", "NOT-A-BUG", "DEFERRED"})
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BACKLOG_REFERENCE_RE = re.compile(
    r"^docs/roadmap/BACKLOG_LEDGER\.md#(?P<anchor>ledger-[a-z0-9-]+)$"
)
_BACKLOG_FIELD_RE = re.compile(
    r"^  - (?P<label>Owner|Priority|Target PR|Reason(?: \(EN\))?|Links|DoD):\s*(?P<value>.*)$"
)
_MATERIAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_APPROVAL_CLOCK_SKEW = timedelta(minutes=5)
FINAL_SECURITY_ATTEMPT_OUTCOMES = frozenset({"completed", "incomplete", "safety_block", "timeout"})


class CloseoutError(RuntimeError):
    """Raised for invalid local authoring state or stale live evidence."""


def _token() -> str:
    token = (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        raise CloseoutError("GH_TOKEN or GITHUB_TOKEN is required")
    return token


def _state_dir(pr_number: int) -> Path:
    if pr_number <= 0:
        raise CloseoutError("pr_number must be positive")
    return STATE_ROOT / f"PR_{pr_number}"


def _state_path(pr_number: int) -> Path:
    return _state_dir(pr_number) / "draft.json"


def _final_security_state_path(pr_number: int) -> Path:
    return _state_dir(pr_number) / "final_security_preparations.json"


def _final_security_lock_path(pr_number: int) -> Path:
    return _state_dir(pr_number) / ".final_security_preparations.lock"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def _write_state(state: Mapping[str, Any]) -> None:
    pr_number = state.get("pr_number")
    if not isinstance(pr_number, int) or isinstance(pr_number, bool):
        raise CloseoutError("draft pr_number is malformed")
    _atomic_write(_state_path(pr_number), _canonical_json(dict(state)) + "\n")


def _load_state(pr_number: int) -> dict[str, Any]:
    path = _state_path(pr_number)
    try:
        raw = path.read_text(encoding="utf-8")
        state = json.loads(raw)
    except FileNotFoundError as exc:
        raise CloseoutError(f"missing local draft; run init first: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"local draft is malformed: {path}") from exc
    if not isinstance(state, dict):
        raise CloseoutError("local draft must be a JSON object")
    expected = {
        "dispositions",
        "experiment_result",
        "freeze",
        "packet",
        "pr_number",
        "repository",
        "schema_version",
    }
    if set(state) != expected:
        raise CloseoutError("local draft has unknown or missing fields")
    if state["schema_version"] != DRAFT_SCHEMA_VERSION or state["pr_number"] != pr_number:
        raise CloseoutError("local draft identity does not match the requested PR")
    if not _REPOSITORY_RE.fullmatch(str(state["repository"])):
        raise CloseoutError("local draft repository is malformed")
    if not isinstance(state["dispositions"], list):
        raise CloseoutError("local draft dispositions must be a list")
    return state


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CloseoutError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise CloseoutError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CloseoutError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise CloseoutError("preparation timestamp must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@contextmanager
def _final_security_lock(pr_number: int) -> Iterator[None]:
    if _FCNTL is None:
        raise CloseoutError("final-security attempt reservation requires POSIX fcntl.flock support")
    path = _final_security_lock_path(pr_number)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        _FCNTL.flock(handle.fileno(), _FCNTL.LOCK_EX)
        try:
            yield
        finally:
            _FCNTL.flock(handle.fileno(), _FCNTL.LOCK_UN)


def _validated_final_security_approval(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise CloseoutError("final-security operator approval record is malformed")
    expected = {
        "author_association",
        "author_login",
        "author_user_id",
        "comment_id",
        "created_at",
        "reference",
    }
    if set(value) != expected:
        raise CloseoutError("final-security operator approval record has unknown fields")
    if (
        not isinstance(value["author_user_id"], int)
        or isinstance(value["author_user_id"], bool)
        or value["author_user_id"] <= 0
        or not isinstance(value["comment_id"], int)
        or isinstance(value["comment_id"], bool)
        or value["comment_id"] <= 0
        or not isinstance(value["author_login"], str)
        or not value["author_login"]
        or value["author_association"] not in {"OWNER", "MEMBER"}
        or not isinstance(value["reference"], str)
        or not value["reference"]
    ):
        raise CloseoutError("final-security operator approval identity is malformed")
    _parse_utc_timestamp(value["created_at"], field="operator approval created_at")
    return dict(value)


def _validated_final_security_review_evidence(
    value: object,
    *,
    repository: str,
    pr_number: int,
    material_head_sha: str,
    material_digest: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CloseoutError("final-security review evidence is malformed")
    reference_prefix = f"https://github.com/{repository}/pull/{pr_number}#"
    if is_review_source_unavailability_receipt(value):
        try:
            expected = build_review_source_unavailability_receipt(
                material_digest=value["material_digest"],
                material_head_sha=value["material_head_sha"],
                quota_reference=value["quota_reference"],
                quota_created_at=value["quota_created_at"],
                quota_body_sha256=value["quota_body_sha256"],
                source_status=value["source_status"],
            )
        except (KeyError, TypeError, ReviewEvidenceError) as exc:
            raise CloseoutError("final-security source-unavailable evidence is malformed") from exc
        if (
            value != expected
            or value["material_head_sha"] != material_head_sha
            or value["material_digest"] != material_digest
            or not str(value["quota_reference"]).startswith(reference_prefix + "issuecomment-")
        ):
            raise CloseoutError(
                "final-security source-unavailable evidence is not bound to the material"
            )
        return dict(value)

    expected_fields = {
        "kind",
        "review_commit_sha",
        "review_reference",
        "review_submitted_at",
    }
    if set(value) != expected_fields:
        raise CloseoutError("final-security completed-review evidence has unknown fields")
    if (
        value["kind"] != "completed_review"
        or not isinstance(value["review_commit_sha"], str)
        or _SHA_RE.fullmatch(value["review_commit_sha"]) is None
        or value["review_commit_sha"] != material_head_sha
        or not isinstance(value["review_reference"], str)
        or not value["review_reference"].startswith(reference_prefix)
    ):
        raise CloseoutError("final-security completed-review evidence is malformed")
    _parse_utc_timestamp(
        value["review_submitted_at"],
        field="preparation review_submitted_at",
    )
    return dict(value)


def _load_final_security_state(*, repository: str, pr_number: int) -> dict[str, Any] | None:
    path = _final_security_state_path(pr_number)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        state = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"final-security preparation state is malformed: {path}") from exc
    expected = {"preparations", "pr_number", "repository", "schema_version"}
    if not isinstance(state, dict) or set(state) != expected:
        raise CloseoutError("final-security preparation state has unknown or missing fields")
    if (
        state["schema_version"] != FINAL_SECURITY_PREPARATION_SCHEMA_VERSION
        or state["repository"] != repository
        or state["pr_number"] != pr_number
        or not isinstance(state["preparations"], list)
        or not state["preparations"]
    ):
        raise CloseoutError("final-security preparation state identity is malformed")
    expected_record_fields = {
        "attempt_completed_at",
        "attempt_outcome",
        "attempt_status",
        "material_digest",
        "material_head_sha",
        "operator_approval",
        "outcome_evidence_ref",
        "pr_number",
        "prepared_at",
        "repository",
        "review_evidence",
    }
    for index, record in enumerate(state["preparations"]):
        if not isinstance(record, dict) or set(record) != expected_record_fields:
            raise CloseoutError("final-security preparation record has unknown or missing fields")
        if (
            record["repository"] != repository
            or record["pr_number"] != pr_number
            or not isinstance(record["material_head_sha"], str)
            or _SHA_RE.fullmatch(record["material_head_sha"]) is None
            or not isinstance(record["material_digest"], str)
            or _MATERIAL_DIGEST_RE.fullmatch(record["material_digest"]) is None
            or record["attempt_status"] not in {"reserved", "completed"}
        ):
            raise CloseoutError("final-security preparation record identity is malformed")
        _parse_utc_timestamp(record["prepared_at"], field="preparation prepared_at")
        _validated_final_security_review_evidence(
            record["review_evidence"],
            repository=repository,
            pr_number=pr_number,
            material_head_sha=record["material_head_sha"],
            material_digest=record["material_digest"],
        )
        if record["attempt_status"] == "reserved":
            if any(
                record[field] is not None
                for field in (
                    "attempt_completed_at",
                    "attempt_outcome",
                    "outcome_evidence_ref",
                )
            ):
                raise CloseoutError("reserved final-security attempt has terminal fields")
        else:
            if record["attempt_outcome"] not in FINAL_SECURITY_ATTEMPT_OUTCOMES:
                raise CloseoutError("completed final-security attempt has invalid outcome")
            _parse_utc_timestamp(
                record["attempt_completed_at"],
                field="preparation attempt_completed_at",
            )
            if (
                not isinstance(record["outcome_evidence_ref"], str)
                or not record["outcome_evidence_ref"]
            ):
                raise CloseoutError("completed final-security attempt lacks outcome evidence")
        approval = _validated_final_security_approval(record["operator_approval"])
        if index == 0 and approval is not None:
            raise CloseoutError("first final-security preparation must not claim operator approval")
        if index > 0 and approval is None:
            raise CloseoutError("later final-security preparation lacks operator approval")
    return state


def _require_completed_final_security_preparation(
    *,
    repository: str,
    pr_number: int,
    material_head_sha: str,
    material_digest: str,
) -> None:
    state = _load_final_security_state(
        repository=repository,
        pr_number=pr_number,
    )
    if state is None:
        raise CloseoutError("prepare and record final security before sealing a scan manifest")
    latest = state["preparations"][-1]
    if (
        latest["material_head_sha"] != material_head_sha
        or latest["material_digest"] != material_digest
    ):
        raise CloseoutError("latest final-security preparation does not match frozen material")
    if latest["attempt_status"] != "completed" or latest["attempt_outcome"] != "completed":
        raise CloseoutError("latest final-security preparation lacks a completed scan outcome")


def _git_path() -> str:
    path = shutil.which("git")
    if not path:
        raise CloseoutError("git not found in PATH")
    try:
        return str(Path(path).resolve(strict=True))
    except OSError as exc:
        raise CloseoutError("git executable could not be resolved") from exc


def _git(*args: str) -> str:
    result = subprocess.run(  # nosec B603: argv starts with resolved git and fixed subcommands (remove-by: 2026-09-30, ref: PR-governance-material-seal)
        [_git_path(), *args],
        cwd=REPO_ROOT,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise CloseoutError(f"git {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _require_clean_live_head(live_head: str) -> None:
    local_head = _git("rev-parse", "HEAD")
    if local_head != live_head:
        raise CloseoutError(f"local HEAD {local_head} does not match live PR head {live_head}")
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise CloseoutError("freeze/seal requires a clean worktree")


def _single_line(value: str | None, *, label: str, required: bool) -> str | None:
    if value is None:
        if required:
            raise CloseoutError(f"{label} is required")
        return None
    stripped = value.strip()
    if not stripped and required:
        raise CloseoutError(f"{label} must not be empty")
    if "\n" in stripped or "\r" in stripped or len(stripped) > 2_000:
        raise CloseoutError(f"{label} must be one bounded line")
    return stripped or None


def _required_line(value: str | None, *, label: str) -> str:
    result = _single_line(value, label=label, required=True)
    if result is None:
        raise CloseoutError(f"{label} is required")
    return result


def _validated_backlog_reference(value: str | None) -> str:
    reference = _required_line(value, label="backlog")
    match = _BACKLOG_REFERENCE_RE.fullmatch(reference)
    if match is None:
        raise CloseoutError("backlog must be docs/roadmap/BACKLOG_LEDGER.md#ledger-<entry>")
    try:
        ledger_text = BACKLOG_LEDGER_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CloseoutError("canonical backlog ledger could not be read") from exc

    marker = f'<a id="{match.group("anchor")}"></a>'
    if ledger_text.count(marker) != 1:
        raise CloseoutError("backlog anchor must identify exactly one canonical ledger entry")
    entry_start = ledger_text.index(marker)
    next_entry = ledger_text.find('\n<a id="ledger-', entry_start + len(marker))
    entry = ledger_text[entry_start : next_entry if next_entry >= 0 else len(ledger_text)]

    fields: dict[str, list[str]] = {}
    lines = entry.splitlines()
    for index, line in enumerate(lines):
        field_match = _BACKLOG_FIELD_RE.match(line)
        if field_match is None:
            continue
        label = field_match.group("label")
        normalized_label = "Reason" if label.startswith("Reason") else label
        values = [field_match.group("value").strip()]
        for continuation in lines[index + 1 :]:
            if continuation.startswith("  - ") or continuation.startswith('<a id="ledger-'):
                break
            if continuation.strip():
                values.append(continuation.strip())
        if normalized_label in fields:
            raise CloseoutError(f"backlog entry contains duplicate {normalized_label} metadata")
        fields[normalized_label] = values

    required = {"Owner", "Priority", "Target PR", "Reason", "Links", "DoD"}
    missing = sorted(
        label for label in required if label not in fields or not " ".join(fields[label]).strip()
    )
    if missing:
        raise CloseoutError("backlog entry is missing required metadata: " + ", ".join(missing))
    priority = " ".join(fields["Priority"]).strip()
    if priority not in {"P0", "P1", "P2"}:
        raise CloseoutError("backlog entry Priority must be P0, P1, or P2")
    return reference


def _thread_url(repository: str, pr_number: int, value: str) -> str:
    url = _required_line(value, label="url")
    prefix = f"https://github.com/{repository}/pull/{pr_number}#"
    if not url.startswith(prefix) or not re.fullmatch(r"https://github\.com/[^\s]+", url):
        raise CloseoutError("url must identify a thread in the requested GitHub PR")
    return url


def _local_artifact_reference(value: str | None, *, prefix: str) -> str | None:
    if value is None:
        return None
    reference = _required_line(value, label="artifact reference")
    if (
        not reference.startswith(prefix)
        or not reference.endswith(".json")
        or ".." in Path(reference).parts
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", reference)
    ):
        raise CloseoutError(f"artifact reference must stay under {prefix}")
    return reference


def _proof_real_fix(
    *, repository: str, pr_number: int, fix_sha: str, token: str
) -> tuple[Any, RepositoryCommitRef]:
    if not _SHA_RE.fullmatch(fix_sha):
        raise CloseoutError("FIXED proof must use a full lowercase 40-character SHA")
    snapshot = fetch_pr_snapshot(repository, pr_number, token=token)
    resolution = classify_commit_ref(fix_sha, snapshot, token=token)
    if not isinstance(resolution, RepositoryCommitRef) or resolution.kind not in {
        CommitRefKind.PR_HEAD,
        CommitRefKind.PR_COMMIT,
    }:
        raise CloseoutError("FIXED proof must be a real commit in the live PR commit set")
    head = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
    if not is_ancestor(
        resolution,
        head,
        repository=repository,
        token=token,
    ):
        raise CloseoutError("FIXED proof is not an ancestor of the live PR head")
    assert_snapshot_unchanged(snapshot, token=token)
    return snapshot, resolution


def _cmd_init(args: argparse.Namespace) -> None:
    repository = args.repo.strip()
    if not _REPOSITORY_RE.fullmatch(repository):
        raise CloseoutError("--repo must be owner/name")
    state = {
        "dispositions": [],
        "experiment_result": _local_artifact_reference(
            args.experiment_result,
            prefix="artifacts/orchestration/experiments/results/",
        ),
        "freeze": None,
        "packet": _local_artifact_reference(
            args.packet, prefix="artifacts/orchestration/task_packets/"
        ),
        "pr_number": args.pr_number,
        "repository": repository,
        "schema_version": DRAFT_SCHEMA_VERSION,
    }
    path = _state_path(args.pr_number)
    if path.exists():
        if _load_state(args.pr_number) != state:
            raise CloseoutError("existing draft differs; resume it instead of overwriting")
        print(f"closeout-init: unchanged {path}")
        return
    _write_state(state)
    print(f"closeout-init: wrote {path}")


def _cmd_freeze(args: argparse.Namespace) -> None:
    state = _load_state(args.pr_number)
    if state["repository"] != args.repo:
        raise CloseoutError("--repo does not match local draft")
    snapshot = fetch_pr_snapshot(args.repo, args.pr_number, token=_token())
    _require_clean_live_head(snapshot.head_sha)
    manifest = compute_material_manifest(
        REPO_ROOT,
        base_ref_oid=snapshot.base_sha,
        head_ref_oid=snapshot.head_sha,
        pr_number=args.pr_number,
    )
    new_freeze = {
        "base_ref_oid": snapshot.base_sha,
        "digest": manifest.digest,
        "material_head_sha": snapshot.head_sha,
        "merge_base_sha": manifest.merge_base_sha,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    if state["freeze"] != new_freeze:
        state["dispositions"] = []
    state["freeze"] = new_freeze
    assert_snapshot_unchanged(snapshot, token=_token())
    _write_state(state)
    print(f"MATERIAL_FROZEN {manifest.digest}")


def render_final_security_approval_comment(
    *,
    repository: str,
    pr_number: int,
    material_head_sha: str,
    material_digest: str,
) -> str:
    """Render the exact operator approval body for one additional preparation."""

    return (
        "Codex Security rerun approved: "
        f"repo={repository}; pr={pr_number}; head={material_head_sha}; "
        f"material_digest={material_digest}"
    )


def _verify_final_material_review(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    material_head_sha: str,
    snapshot: Any,
    token: str,
) -> dict[str, str]:
    """Bind preparation to completed exact-head review evidence."""

    review = verify_codex_review_reference(
        reference,
        repository=repository,
        pr_number=pr_number,
        token=token,
        expected_commit_ref=material_head_sha,
    )
    commit = classify_commit_ref(review.commit_ref, snapshot, token=token)
    if (
        not isinstance(commit, RepositoryCommitRef)
        or commit.kind is not CommitRefKind.PR_HEAD
        or commit.sha != material_head_sha
    ):
        raise CloseoutError("final-material review is not bound to the live exact head")
    submitted_at = _format_utc_timestamp(
        _parse_utc_timestamp(
            review.submitted_at,
            field="final-material review submitted_at",
        )
    )
    return {
        "kind": "completed_review",
        "review_commit_sha": commit.sha,
        "review_reference": reference,
        "review_submitted_at": submitted_at,
    }


def _verify_final_material_review_source_unavailability(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    material_head_sha: str,
    material_digest: str,
    token: str,
) -> dict[str, Any]:
    """Bind preparation to terminal source evidence without claiming a review."""

    source_evidence = verify_codex_review_source_unavailability_reference(
        reference,
        repository=repository,
        pr_number=pr_number,
        token=token,
    )
    return cast(
        dict[str, Any],
        build_review_source_unavailability_receipt(
            material_digest=material_digest,
            material_head_sha=material_head_sha,
            quota_reference=source_evidence.reference,
            quota_created_at=source_evidence.created_at,
            quota_body_sha256=source_evidence.body_sha256,
            source_status=source_evidence.source_status,
        ),
    )


def _verify_final_security_approval(
    reference: str,
    *,
    repository: str,
    pr_number: int,
    material_head_sha: str,
    material_digest: str,
    previous_attempt_completed_at: str,
    used_references: set[str],
    token: str,
    now: datetime,
) -> dict[str, Any]:
    owner, name = repository.split("/", maxsplit=1)
    pattern = re.compile(
        rf"^https://github\.com/{re.escape(owner)}/{re.escape(name)}/pull/"
        rf"{pr_number}#issuecomment-(\d+)$"
    )
    match = pattern.fullmatch(reference)
    if match is None:
        raise CloseoutError(
            "operator approval must be an issue comment on the exact repository and PR"
        )
    if reference in used_references:
        raise CloseoutError("operator approval comment was already consumed locally")
    comment_id = int(match.group(1))
    if comment_id <= 0:
        raise CloseoutError("operator approval comment id must be positive")
    api_url = f"https://api.github.com/repos/{owner}/{name}/issues/comments/{comment_id}"
    response = github_api_request(api_url, token=token)
    if not isinstance(response, dict):
        raise CloseoutError("GitHub operator approval response is malformed")
    user = response.get("user")
    user_id = user.get("id") if isinstance(user, dict) else None
    login = user.get("login") if isinstance(user, dict) else None
    user_type = user.get("type") if isinstance(user, dict) else None
    association = response.get("author_association")
    response_id = response.get("id")
    expected_issue_url = f"https://api.github.com/repos/{owner}/{name}/issues/{pr_number}"
    if (
        not isinstance(response_id, int)
        or isinstance(response_id, bool)
        or response_id != comment_id
        or response.get("url") != api_url
        or response.get("html_url") != reference
        or response.get("issue_url") != expected_issue_url
        or not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id <= 0
        or not isinstance(login, str)
        or not login
        or user_type != "User"
        or association not in {"OWNER", "MEMBER"}
        or "performed_via_github_app" not in response
        or response.get("performed_via_github_app") is not None
    ):
        raise CloseoutError("issue comment is not trusted operator approval evidence")
    created_at = response.get("created_at")
    updated_at = response.get("updated_at")
    if not isinstance(created_at, str) or updated_at != created_at:
        raise CloseoutError("operator approval comment was edited after creation")
    created = _parse_utc_timestamp(created_at, field="operator approval created_at")
    updated = _parse_utc_timestamp(updated_at, field="operator approval updated_at")
    if created != updated:
        raise CloseoutError("operator approval comment was edited after creation")
    previous_attempt_completed = _parse_utc_timestamp(
        previous_attempt_completed_at,
        field="previous attempt completed_at",
    )
    if created <= previous_attempt_completed:
        raise CloseoutError(
            "operator approval comment must be newer than the prior completed attempt"
        )
    if created > now.astimezone(timezone.utc) + _APPROVAL_CLOCK_SKEW:
        raise CloseoutError("operator approval comment timestamp is in the future")
    expected_body = render_final_security_approval_comment(
        repository=repository,
        pr_number=pr_number,
        material_head_sha=material_head_sha,
        material_digest=material_digest,
    )
    body = response.get("body")
    if not isinstance(body, str) or body != expected_body:
        raise CloseoutError("operator approval body does not exactly match the frozen material")
    return {
        "author_association": association,
        "author_login": login,
        "author_user_id": user_id,
        "comment_id": comment_id,
        "created_at": _format_utc_timestamp(created),
        "reference": reference,
    }


def _cmd_prepare_final_security(args: argparse.Namespace) -> None:
    repository = args.repo.strip()
    if not _REPOSITORY_RE.fullmatch(repository):
        raise CloseoutError("--repo must be owner/name")
    state = _load_state(args.pr_number)
    if state["repository"] != repository:
        raise CloseoutError("--repo does not match local draft")
    freeze = state["freeze"]
    if not isinstance(freeze, dict):
        raise CloseoutError("run freeze before preparing final security")

    token = _token()
    snapshot = fetch_pr_snapshot(repository, args.pr_number, token=token)
    _require_clean_live_head(snapshot.head_sha)
    manifest = compute_material_manifest(
        REPO_ROOT,
        base_ref_oid=snapshot.base_sha,
        head_ref_oid=snapshot.head_sha,
        pr_number=args.pr_number,
    )
    expected_freeze = {
        "base_ref_oid": snapshot.base_sha,
        "digest": manifest.digest,
        "material_head_sha": snapshot.head_sha,
        "merge_base_sha": manifest.merge_base_sha,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    if freeze != expected_freeze:
        raise CloseoutError(
            "material state changed after freeze; freeze and exact-head review again"
        )
    if (args.review_ref is None) == (args.review_source_unavailable_ref is None):
        raise CloseoutError(
            "provide exactly one of --review-ref or --review-source-unavailable-ref"
        )
    if args.review_source_unavailable_ref is not None:
        source_reference = _required_line(
            args.review_source_unavailable_ref,
            label="review-source-unavailable-ref",
        )
        review_evidence = _verify_final_material_review_source_unavailability(
            source_reference,
            repository=repository,
            pr_number=args.pr_number,
            material_head_sha=snapshot.head_sha,
            material_digest=manifest.digest,
            token=token,
        )
    else:
        review_reference = _required_line(args.review_ref, label="review-ref")
        review_evidence = _verify_final_material_review(
            review_reference,
            repository=repository,
            pr_number=args.pr_number,
            material_head_sha=snapshot.head_sha,
            snapshot=snapshot,
            token=token,
        )
    assert_snapshot_unchanged(snapshot, token=token)

    approval_reference = _single_line(
        args.operator_approval_ref,
        label="operator-approval-ref",
        required=False,
    )
    with _final_security_lock(args.pr_number):
        preparation_state = _load_final_security_state(
            repository=repository,
            pr_number=args.pr_number,
        )
        preparations = preparation_state["preparations"] if preparation_state is not None else []
        if not preparations and approval_reference is not None:
            raise CloseoutError(
                "--operator-approval-ref is only valid after the first local preparation"
            )
        if preparations and approval_reference is None:
            raise CloseoutError(
                "final security was already prepared in this checkout; a fresh "
                "OWNER/MEMBER --operator-approval-ref is required"
            )
        if preparations and preparations[-1]["attempt_status"] != "completed":
            raise CloseoutError(
                "the prior final-security attempt is still reserved; record its "
                "terminal outcome before requesting another preparation"
            )

        now = _utc_now()
        if now.tzinfo is None:
            raise CloseoutError("preparation time must include a timezone")
        approval: dict[str, Any] | None = None
        if preparations:
            used_references = {
                str(record["operator_approval"]["reference"])
                for record in preparations
                if isinstance(record.get("operator_approval"), dict)
            }
            approval = _verify_final_security_approval(
                approval_reference or "",
                repository=repository,
                pr_number=args.pr_number,
                material_head_sha=snapshot.head_sha,
                material_digest=manifest.digest,
                previous_attempt_completed_at=str(preparations[-1]["attempt_completed_at"]),
                used_references=used_references,
                token=token,
                now=now,
            )
        assert_snapshot_unchanged(snapshot, token=token)
        record = {
            "attempt_completed_at": None,
            "attempt_outcome": None,
            "attempt_status": "reserved",
            "material_digest": manifest.digest,
            "material_head_sha": snapshot.head_sha,
            "operator_approval": approval,
            "outcome_evidence_ref": None,
            "pr_number": args.pr_number,
            "prepared_at": _format_utc_timestamp(now),
            "repository": repository,
            "review_evidence": review_evidence,
        }
        if preparation_state is None:
            preparation_state = {
                "preparations": [],
                "pr_number": args.pr_number,
                "repository": repository,
                "schema_version": FINAL_SECURITY_PREPARATION_SCHEMA_VERSION,
            }
        preparation_state["preparations"].append(record)
        _atomic_write(
            _final_security_state_path(args.pr_number),
            _canonical_json(preparation_state) + "\n",
        )

    print(
        "FINAL_SECURITY_PREPARED "
        f"repo={repository} pr={args.pr_number} head={snapshot.head_sha} "
        f"material_digest={manifest.digest}"
    )
    print(
        "LOCAL_ADVISORY_ONLY: no Codex Security plugin call or GitHub mutation was made; "
        "checkout-local state is not global authority and cannot prove cross-machine "
        "request consumption."
    )
    print(
        "REQUEST_POLICY: automatic_budget=1 automatic_retries=0; timeout/incomplete "
        "consumes the request; every later local preparation requires a fresh unedited "
        "OWNER/MEMBER approval comment."
    )
    print(
        "NEXT: after the operator-issued request reaches a terminal outcome, run "
        "`record-final-security-outcome` before any approved additional preparation."
    )


def _cmd_record_final_security_outcome(args: argparse.Namespace) -> None:
    repository = args.repo.strip()
    if not _REPOSITORY_RE.fullmatch(repository):
        raise CloseoutError("--repo must be owner/name")
    outcome = args.outcome.strip()
    if outcome not in FINAL_SECURITY_ATTEMPT_OUTCOMES:
        raise CloseoutError("unsupported final-security outcome")
    evidence_ref = _required_line(args.evidence_ref, label="evidence-ref")
    now = _utc_now()
    if now.tzinfo is None:
        raise CloseoutError("attempt completion time must include a timezone")

    with _final_security_lock(args.pr_number):
        state = _load_final_security_state(
            repository=repository,
            pr_number=args.pr_number,
        )
        if state is None:
            raise CloseoutError("prepare final security before recording an outcome")
        record = state["preparations"][-1]
        if record["attempt_status"] != "reserved":
            raise CloseoutError("latest final-security attempt already has a terminal outcome")
        prepared_at = _parse_utc_timestamp(
            record["prepared_at"],
            field="preparation prepared_at",
        )
        if now < prepared_at:
            raise CloseoutError("attempt completion time cannot predate preparation")
        record.update(
            {
                "attempt_completed_at": _format_utc_timestamp(now),
                "attempt_outcome": outcome,
                "attempt_status": "completed",
                "outcome_evidence_ref": evidence_ref,
            }
        )
        _atomic_write(
            _final_security_state_path(args.pr_number),
            _canonical_json(state) + "\n",
        )

    print(
        "FINAL_SECURITY_OUTCOME_RECORDED "
        f"repo={repository} pr={args.pr_number} outcome={outcome}"
    )
    print(
        "LOCAL_ADVISORY_ONLY: this terminal record consumes the checkout-local "
        "reservation but is not scan or global-provider evidence."
    )


def _cmd_add_disposition(args: argparse.Namespace) -> None:
    state = _load_state(args.pr_number)
    freeze = state["freeze"]
    if not isinstance(freeze, dict):
        raise CloseoutError("run freeze before adding dispositions")
    repository = str(state["repository"])
    url = _thread_url(repository, args.pr_number, args.url)
    if any(item.get("url") == url for item in state["dispositions"] if isinstance(item, dict)):
        raise CloseoutError("this thread URL already has a disposition")
    disposition = args.disposition
    if disposition not in VALID_DISPOSITIONS:
        raise CloseoutError("unsupported disposition")

    item: dict[str, Any] = {"disposition": disposition, "url": url}
    if disposition == "FIXED":
        commit = _required_line(args.commit, label="commit")
        evidence = _required_line(args.evidence, label="evidence")
        _proof_real_fix(
            repository=repository,
            pr_number=args.pr_number,
            fix_sha=commit,
            token=_token(),
        )
        item.update({"commit": commit, "evidence": evidence})
    elif disposition == "NOT-A-BUG":
        evidence = _required_line(args.evidence, label="evidence")
        reason = _required_line(args.reason, label="reason")
        item.update({"evidence": evidence, "reason": reason})
    else:
        backlog = _validated_backlog_reference(args.backlog)
        item["backlog"] = backlog

    cause = _single_line(args.cause, label="cause", required=False)
    if cause is not None:
        if disposition != "NOT-A-BUG" or cause != UNAVAILABLE_REVIEW_REF_CAUSE:
            raise CloseoutError("v1 fingerprint is limited to NOT-A-BUG unavailable ancestry")
        review_ref = _required_line(args.review_ref, label="review-ref")
        verified_fix = _required_line(args.verified_fix, label="verified-fix")
        snapshot, fix_resolution = _proof_real_fix(
            repository=repository,
            pr_number=args.pr_number,
            fix_sha=verified_fix,
            token=_token(),
        )
        review_resolution = classify_commit_ref(review_ref, snapshot, token=_token())
        if review_resolution.kind is not CommitRefKind.REVIEW_REF_UNAVAILABLE:
            raise CloseoutError("review-ref is not proven unavailable by GitHub")
        item.update(
            {
                "cause": cause,
                "fingerprint": unavailable_review_ref_fingerprint(
                    pr_number=args.pr_number,
                    material_digest=str(freeze["digest"]),
                    verified_real_fix_sha=fix_resolution.sha,
                ),
                "material_digest": freeze["digest"],
                "verified_fix": fix_resolution.sha,
            }
        )

    unexpected = {
        "commit": args.commit,
        "evidence": args.evidence,
        "reason": args.reason,
        "backlog": args.backlog,
    }
    allowed = {
        "FIXED": {"commit", "evidence"},
        "NOT-A-BUG": {"evidence", "reason"},
        "DEFERRED": {"backlog"},
    }[disposition]
    invalid = sorted(key for key, value in unexpected.items() if value and key not in allowed)
    if invalid:
        raise CloseoutError(f"fields not valid for {disposition}: {', '.join(invalid)}")
    state["dispositions"].append(item)
    state["dispositions"].sort(key=lambda entry: (entry["disposition"], entry["url"]))
    _write_state(state)
    print(f"closeout-disposition: recorded {disposition} for {url}")


def _render_mapping(state: Mapping[str, Any], seal: Mapping[str, Any]) -> str:
    pr_number = int(state["pr_number"])
    packet = state.get("packet")
    experiment = state.get("experiment_result")
    lines = [
        f"# PR {pr_number} — Review Governance",
        "",
        "Review-Seal-Version: v1",
        "",
        "## Lane Start Provenance",
        (
            f"Packet: `{packet}`"
            if packet
            else "Exception: no retained coordinator packet was supplied."
        ),
        "",
        "## Experiment Runner Evidence",
        (
            f"Artifact: `{experiment}`"
            if experiment
            else "Not applicable: Experiment Runner did not materially contribute."
        ),
        "",
        "## Discussion Thread Pass",
        "- [x] Discussion-thread pass completed",
        "- [x] Fixed in commit mapping completed",
        "",
        "## Fixed in Commit Mapping",
    ]
    dispositions = state["dispositions"]
    if not dispositions:
        lines.append(NO_ACTIONABLE_LINE)
    for item in dispositions:
        lines.extend(["", f"Disposition: {item['disposition']}"])
        for field, label in (
            ("commit", "Commit"),
            ("evidence", "Evidence"),
            ("reason", "Reason"),
            ("backlog", "Backlog"),
            ("fingerprint", "Fingerprint"),
            ("cause", "Cause"),
            ("material_digest", "Material-Digest"),
            ("verified_fix", "Verified-Fix"),
        ):
            if field in item:
                lines.append(f"{label}: {item[field]}")
        if item["disposition"] == "FIXED":
            lines.append(f"- {item['url']} -> {item['commit']}")
        else:
            lines.append(f"- {item['url']}")
    lines.extend(["", "## Review Material Seal", render_embedded_review_seal(seal), ""])
    return "\n".join(lines)


def _mapping_proof_blocks(markdown: str) -> set[str]:
    section = extract_fixed_mapping_section(markdown)
    return {
        block.strip()
        for block in section.split("\n\n")
        if block.strip() and block.strip() != NO_ACTIONABLE_LINE
    }


def _validate_reseal_transition(
    existing_markdown: str,
    replacement_markdown: str,
    *,
    repository: str,
    pr_number: int,
    expected_freeze: Mapping[str, Any],
) -> str:
    errors = validate_mapping_artifact_text(existing_markdown)
    if errors:
        raise CloseoutError("existing canonical mapping is invalid: " + "; ".join(errors))
    existing_seal = parse_embedded_review_seal(existing_markdown)
    if existing_seal["repository"] != repository or existing_seal["pr_number"] != pr_number:
        raise CloseoutError("existing canonical mapping identity does not match this PR")
    existing_material = existing_seal["material"]
    if existing_material["digest"] == expected_freeze["digest"]:
        raise CloseoutError(
            "canonical mapping already seals this material; use a structured duplicate reply"
        )
    if existing_material["policy_version"] != expected_freeze["policy_version"]:
        raise CloseoutError(
            "existing canonical mapping policy_version changed; automatic reseal is unsafe"
        )
    base_changed = (
        existing_material["base_ref_oid"] != expected_freeze["base_ref_oid"]
        or existing_material["merge_base_sha"] != expected_freeze["merge_base_sha"]
    )
    if base_changed:
        previous_base = str(existing_material["base_ref_oid"])
        previous_merge_base = str(existing_material["merge_base_sha"])
        next_base = str(expected_freeze["base_ref_oid"])
        next_merge_base = str(expected_freeze["merge_base_sha"])
        previous_head = str(existing_material["material_head_sha"])
        next_head = str(expected_freeze["material_head_sha"])
        if (
            previous_base != previous_merge_base
            or next_base != next_merge_base
            or _git("merge-base", previous_base, next_base) != previous_base
            or _git("merge-base", previous_head, next_head) != previous_head
        ):
            raise CloseoutError(
                "existing canonical mapping base changed without a proven "
                "fast-forward base/material-head advance"
            )
    missing_blocks = sorted(
        _mapping_proof_blocks(existing_markdown) - _mapping_proof_blocks(replacement_markdown)
    )
    if missing_blocks:
        raise CloseoutError("replacement mapping would drop existing disposition proof")
    return str(existing_material["material_head_sha"])


def _cmd_seal(args: argparse.Namespace) -> None:
    state = _load_state(args.pr_number)
    if state["repository"] != args.repo:
        raise CloseoutError("--repo does not match local draft")
    freeze = state["freeze"]
    if not isinstance(freeze, dict):
        raise CloseoutError("run freeze before sealing")
    token = _token()
    snapshot = fetch_pr_snapshot(args.repo, args.pr_number, token=token)
    _require_clean_live_head(snapshot.head_sha)
    manifest = compute_material_manifest(
        REPO_ROOT,
        base_ref_oid=snapshot.base_sha,
        head_ref_oid=snapshot.head_sha,
        pr_number=args.pr_number,
    )
    expected_freeze = {
        "base_ref_oid": snapshot.base_sha,
        "digest": manifest.digest,
        "material_head_sha": snapshot.head_sha,
        "merge_base_sha": manifest.merge_base_sha,
        "policy_version": MATERIAL_POLICY_VERSION,
    }
    if freeze != expected_freeze:
        raise CloseoutError("material state changed after freeze; freeze and review again")
    if args.review_source_unavailable_ref:
        source_evidence = verify_codex_review_source_unavailability_reference(
            _required_line(
                args.review_source_unavailable_ref,
                label="review-source-unavailable-ref",
            ),
            repository=args.repo,
            pr_number=args.pr_number,
            token=token,
        )
        code_review_receipt = build_review_source_unavailability_receipt(
            material_digest=manifest.digest,
            material_head_sha=snapshot.head_sha,
            quota_reference=source_evidence.reference,
            quota_created_at=source_evidence.created_at,
            quota_body_sha256=source_evidence.body_sha256,
            source_status=source_evidence.source_status,
        )
    else:
        review_ref = _required_line(args.review_ref, label="review-ref")
        review_prefix = f"https://github.com/{args.repo}/pull/{args.pr_number}#"
        if not review_ref.startswith(review_prefix):
            raise CloseoutError("review-ref must identify the requested GitHub PR")
        review_evidence = verify_codex_review_reference(
            review_ref,
            repository=args.repo,
            pr_number=args.pr_number,
            token=token,
            expected_commit_ref=snapshot.head_sha,
        )
        review_commit = classify_commit_ref(review_evidence.commit_ref, snapshot, token=token)
        if (
            not isinstance(review_commit, RepositoryCommitRef)
            or review_commit.kind is not CommitRefKind.PR_HEAD
            or review_commit.sha != snapshot.head_sha
        ):
            raise CloseoutError(
                "Codex review must be machine-bound to the exact frozen material head"
            )
        code_review_receipt = {
            "review_commit_ref": review_commit.sha,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": review_ref,
            "reviewed_material_digest": manifest.digest,
            "status": "completed",
        }
    if args.scan_manifest:
        _require_completed_final_security_preparation(
            repository=args.repo,
            pr_number=args.pr_number,
            material_head_sha=snapshot.head_sha,
            material_digest=manifest.digest,
        )
        receipt = ingest_codex_security_receipt(
            Path(args.scan_manifest),
            expected_base_sha=manifest.merge_base_sha,
            expected_head_sha=snapshot.head_sha,
        )
    else:
        validate_security_outage_override_scope(
            repository=args.repo,
            pr_number=args.pr_number,
            material_paths=(entry.path for entry in manifest.entries),
        )
        outage_evidence = verify_security_outage_override_reference(
            _required_line(
                args.security_outage_override_ref,
                label="security-outage-override-ref",
            ),
            repository=args.repo,
            pr_number=args.pr_number,
            token=token,
            expected_material_head_sha=snapshot.head_sha,
            expected_material_digest=manifest.digest,
        )
        receipt = build_security_outage_override_receipt(
            base_revision=manifest.merge_base_sha,
            head_revision=snapshot.head_sha,
            material_digest=manifest.digest,
            override_reference=outage_evidence.reference,
            created_at=outage_evidence.created_at,
            operator_user_id=outage_evidence.operator_user_id,
            operator_login=outage_evidence.operator_login,
            operator_association=outage_evidence.operator_association,
        )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": code_review_receipt,
        "codex_security": receipt,
        "material": expected_freeze,
        "pr_number": args.pr_number,
        "repository": args.repo,
        "schema_version": SEAL_SCHEMA_VERSION,
    }
    markdown = _render_mapping(state, seal)
    errors = validate_mapping_artifact_text(markdown)
    if errors:
        raise CloseoutError("generated mapping is invalid: " + "; ".join(errors))
    target = mapping_artifact_path(args.pr_number)
    relative_target = str(target.relative_to(REPO_ROOT))
    tracked = _git("ls-tree", "--name-only", "HEAD", relative_target)
    if tracked:
        committed_blob = _git("rev-parse", f"HEAD:{relative_target}")
        worktree_blob = _git("hash-object", "--", str(target))
        if committed_blob != worktree_blob:
            raise CloseoutError("canonical mapping has uncommitted changes")
        previous_material_head = _validate_reseal_transition(
            target.read_text(encoding="utf-8"),
            markdown,
            repository=args.repo,
            pr_number=args.pr_number,
            expected_freeze=expected_freeze,
        )
        previous_resolution = classify_commit_ref(
            previous_material_head,
            snapshot,
            token=token,
        )
        if (
            not isinstance(previous_resolution, RepositoryCommitRef)
            or previous_resolution.kind not in {CommitRefKind.PR_HEAD, CommitRefKind.PR_COMMIT}
            or not is_ancestor(
                previous_resolution,
                RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD),
                repository=args.repo,
                token=token,
            )
        ):
            raise CloseoutError(
                "existing canonical mapping material head is not reachable from live PR head"
            )
    _atomic_write(target, markdown)
    assert_snapshot_unchanged(snapshot, token=token)
    print(f"CONTENT_BOUND_RECEIPT_VALID {manifest.digest}")
    print(f"closeout-seal: wrote {target}")


def validate_live_mapping(*, repository: str, pr_number: int, token: str | None) -> dict[str, Any]:
    """Validate the tracked v1 artifact and, when authenticated, its live binding."""

    target = mapping_artifact_path(pr_number)
    try:
        text = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CloseoutError(f"missing canonical mapping artifact: {target}") from exc
    errors = validate_mapping_artifact_text(text)
    if errors:
        raise CloseoutError("invalid mapping artifact: " + "; ".join(errors))
    seal: dict[str, Any] = parse_embedded_review_seal(text)
    if seal["repository"] != repository or seal["pr_number"] != pr_number:
        raise CloseoutError("review seal repository/PR identity mismatch")
    if token is None:
        return seal
    snapshot = fetch_pr_snapshot(repository, pr_number, token=token)
    local_head = _git("rev-parse", "HEAD")
    if local_head != snapshot.head_sha:
        raise CloseoutError("local checkout does not match the live PR head")
    manifest = compute_material_manifest(
        REPO_ROOT,
        base_ref_oid=snapshot.base_sha,
        head_ref_oid=snapshot.head_sha,
        pr_number=pr_number,
    )
    material = seal["material"]
    if (
        material["base_ref_oid"] != snapshot.base_sha
        or material["merge_base_sha"] != manifest.merge_base_sha
        or material["digest"] != manifest.digest
    ):
        raise CloseoutError("review seal is stale for the live material state")
    material_head = classify_commit_ref(material["material_head_sha"], snapshot, token=token)
    if not isinstance(material_head, RepositoryCommitRef) or material_head.kind not in {
        CommitRefKind.PR_HEAD,
        CommitRefKind.PR_COMMIT,
    }:
        raise CloseoutError("sealed material head is not a real live PR commit")
    code_review = seal["code_review"]
    if is_review_source_unavailability_receipt(code_review):
        unavailable_manifest = compute_material_manifest(
            REPO_ROOT,
            base_ref_oid=snapshot.base_sha,
            head_ref_oid=material_head.sha,
            pr_number=pr_number,
        )
        if unavailable_manifest.digest != material["digest"]:
            raise CloseoutError(
                "review-source unavailable material head has a different material digest"
            )
        source_evidence = verify_codex_review_source_unavailability_reference(
            code_review["quota_reference"],
            repository=repository,
            pr_number=pr_number,
            token=token,
        )
        expected_code_review = build_review_source_unavailability_receipt(
            material_digest=material["digest"],
            material_head_sha=material_head.sha,
            quota_reference=source_evidence.reference,
            quota_created_at=source_evidence.created_at,
            quota_body_sha256=source_evidence.body_sha256,
            source_status=source_evidence.source_status,
        )
        if code_review != expected_code_review:
            raise CloseoutError("Codex review-source unavailability receipt is stale")
    elif is_review_credit_outage_receipt(code_review):
        review_prefix = f"https://github.com/{repository}/pull/{pr_number}#"
        review_reference = code_review["review_reference"]
        if not review_reference.startswith(review_prefix):
            raise CloseoutError("code-review reference belongs to another PR")
        validate_review_credit_outage_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=(entry.path for entry in manifest.entries),
        )
        credit_evidence = verify_review_credit_outage_references(
            override_reference=code_review["override_reference"],
            quota_reference=code_review["quota_reference"],
            prior_review_reference=code_review["prior_review_reference"],
            operator_review_reference=review_reference,
            repository=repository,
            pr_number=pr_number,
            token=token,
            snapshot=snapshot,
            expected_material_head_sha=material_head.sha,
            expected_material_digest=material["digest"],
        )
        expected_code_review = build_review_credit_outage_receipt(
            material_digest=material["digest"],
            material_head_sha=material_head.sha,
            override_reference=credit_evidence.override_reference,
            override_created_at=credit_evidence.override_created_at,
            quota_reference=credit_evidence.quota_reference,
            quota_created_at=credit_evidence.quota_created_at,
            prior_review_reference=credit_evidence.prior_review_reference,
            prior_review_submitted_at=credit_evidence.prior_review_submitted_at,
            prior_review_commit_ref=credit_evidence.prior_review_commit_ref,
            operator_review_reference=credit_evidence.operator_review_reference,
            operator_review_submitted_at=credit_evidence.operator_review_submitted_at,
            operator_user_id=credit_evidence.operator_user_id,
            operator_login=credit_evidence.operator_login,
            operator_association=credit_evidence.operator_association,
        )
        if code_review != expected_code_review:
            raise CloseoutError("Codex review credit-outage receipt is stale")
    else:
        review_prefix = f"https://github.com/{repository}/pull/{pr_number}#"
        review_reference = code_review["review_reference"]
        if not review_reference.startswith(review_prefix):
            raise CloseoutError("code-review reference belongs to another PR")
        review_evidence = verify_codex_review_reference(
            review_reference,
            repository=repository,
            pr_number=pr_number,
            token=token,
            expected_commit_ref=material_head.sha,
        )
        if (
            code_review["review_commit_ref_kind"] != "repository_commit"
            or review_evidence.commit_ref != code_review["review_commit_ref"]
            or review_evidence.commit_ref != material_head.sha
        ):
            raise CloseoutError("Codex review is not bound to the sealed material head")
        reviewed_manifest = compute_material_manifest(
            REPO_ROOT,
            base_ref_oid=snapshot.base_sha,
            head_ref_oid=review_evidence.commit_ref,
            pr_number=pr_number,
        )
        if reviewed_manifest.digest != material["digest"]:
            raise CloseoutError("Codex review commit has a different material digest")
    security_receipt = seal["codex_security"]
    if (
        security_receipt["base_revision"] != manifest.merge_base_sha
        or security_receipt["head_revision"] != material_head.sha
    ):
        raise CloseoutError("Codex Security receipt range is stale")
    if is_security_outage_override_receipt(security_receipt):
        validate_security_outage_override_scope(
            repository=repository,
            pr_number=pr_number,
            material_paths=(entry.path for entry in manifest.entries),
        )
        outage_evidence = verify_security_outage_override_reference(
            security_receipt["override_reference"],
            repository=repository,
            pr_number=pr_number,
            token=token,
            expected_material_head_sha=material_head.sha,
            expected_material_digest=material["digest"],
        )
        expected_receipt = build_security_outage_override_receipt(
            base_revision=manifest.merge_base_sha,
            head_revision=material_head.sha,
            material_digest=material["digest"],
            override_reference=outage_evidence.reference,
            created_at=outage_evidence.created_at,
            operator_user_id=outage_evidence.operator_user_id,
            operator_login=outage_evidence.operator_login,
            operator_association=outage_evidence.operator_association,
        )
        if security_receipt != expected_receipt:
            raise CloseoutError("Codex Security operator outage override receipt is stale")
    live_head = RepositoryCommitRef(snapshot.head_sha, CommitRefKind.PR_HEAD)
    if not is_ancestor(
        material_head,
        live_head,
        repository=repository,
        token=token,
    ):
        raise CloseoutError("sealed material head is not an ancestor of live PR head")
    assert_snapshot_unchanged(snapshot, token=token)
    return seal


def _cmd_validate(args: argparse.Namespace) -> None:
    token = _token() if args.require_auth else None
    seal = validate_live_mapping(
        repository=args.repo,
        pr_number=args.pr_number,
        token=token,
    )
    print(f"CONTENT_BOUND_RECEIPT_VALID {seal['material']['digest']}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--repo", required=True)
    init.add_argument("--pr-number", required=True, type=int)
    init.add_argument("--packet")
    init.add_argument("--experiment-result")
    init.set_defaults(handler=_cmd_init)

    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--repo", required=True)
    freeze.add_argument("--pr-number", required=True, type=int)
    freeze.set_defaults(handler=_cmd_freeze)

    prepare_final_security = subparsers.add_parser("prepare-final-security")
    prepare_final_security.add_argument("--repo", required=True)
    prepare_final_security.add_argument("--pr-number", required=True, type=int)
    final_review_evidence = prepare_final_security.add_mutually_exclusive_group(required=True)
    final_review_evidence.add_argument("--review-ref")
    final_review_evidence.add_argument("--review-source-unavailable-ref")
    prepare_final_security.add_argument("--operator-approval-ref")
    prepare_final_security.set_defaults(handler=_cmd_prepare_final_security)

    record_final_security = subparsers.add_parser("record-final-security-outcome")
    record_final_security.add_argument("--repo", required=True)
    record_final_security.add_argument("--pr-number", required=True, type=int)
    record_final_security.add_argument(
        "--outcome",
        required=True,
        choices=sorted(FINAL_SECURITY_ATTEMPT_OUTCOMES),
    )
    record_final_security.add_argument("--evidence-ref", required=True)
    record_final_security.set_defaults(handler=_cmd_record_final_security_outcome)

    disposition = subparsers.add_parser("add-disposition")
    disposition.add_argument("--pr-number", required=True, type=int)
    disposition.add_argument("--url", required=True)
    disposition.add_argument("--disposition", required=True, choices=sorted(VALID_DISPOSITIONS))
    disposition.add_argument("--commit")
    disposition.add_argument("--evidence")
    disposition.add_argument("--reason")
    disposition.add_argument("--backlog")
    disposition.add_argument("--cause")
    disposition.add_argument("--review-ref")
    disposition.add_argument("--verified-fix")
    disposition.set_defaults(handler=_cmd_add_disposition)

    seal = subparsers.add_parser("seal")
    seal.add_argument("--repo", required=True)
    seal.add_argument("--pr-number", required=True, type=int)
    review_evidence = seal.add_mutually_exclusive_group(required=True)
    review_evidence.add_argument("--review-ref")
    review_evidence.add_argument("--review-source-unavailable-ref")
    security_evidence = seal.add_mutually_exclusive_group(required=True)
    security_evidence.add_argument("--scan-manifest")
    security_evidence.add_argument("--security-outage-override-ref")
    seal.set_defaults(handler=_cmd_seal)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--repo", required=True)
    validate.add_argument("--pr-number", required=True, type=int)
    validate.add_argument("--require-auth", action="store_true")
    validate.set_defaults(handler=_cmd_validate)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        args.handler(args)
    except (CloseoutError, CommitIdentityError, ReviewEvidenceError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
