#!/usr/bin/env python3
"""Atomic authoring and validation for one material-bound PR closeout.

The draft and frozen manifest stay under gitignored ``artifacts/``.  Only the
``seal`` command writes the canonical mapping artifact, so review dispositions
and the content-bound security receipt can be published in one closeout commit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404: bounded absolute git commands are required (remove-by: 2026-09-30, ref: PR-governance-material-seal)
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, cast

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
    is_ancestor,
    verify_codex_review_reference,
)
from scripts.orchestration.pr_review_evidence import (  # noqa: E402
    MATERIAL_POLICY_VERSION,
    RECEIPT_AUTHORITY,
    SEAL_SCHEMA_VERSION,
    UNAVAILABLE_REVIEW_REF_CAUSE,
    ReviewEvidenceError,
    compute_material_manifest,
    ingest_codex_security_receipt,
    parse_embedded_review_seal,
    render_embedded_review_seal,
    unavailable_review_ref_fingerprint,
)
from scripts.orchestration.review_mapping_artifact import (  # noqa: E402
    NO_ACTIONABLE_LINE,
    mapping_artifact_path,
    validate_mapping_artifact_text,
)

DRAFT_SCHEMA_VERSION = "pulseplate.pr-review-closeout-draft/v1"
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
            else "Not applicable: no retained coordinator packet was supplied."
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
        raise CloseoutError("Codex review must be machine-bound to the exact frozen material head")
    receipt = ingest_codex_security_receipt(
        Path(args.scan_manifest),
        expected_base_sha=manifest.merge_base_sha,
        expected_head_sha=snapshot.head_sha,
    )
    seal = {
        "authority": RECEIPT_AUTHORITY,
        "code_review": {
            "review_commit_ref": review_commit.sha,
            "review_commit_ref_kind": "repository_commit",
            "review_reference": review_ref,
            "reviewed_material_digest": manifest.digest,
            "status": "completed",
        },
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
    tracked = _git("ls-tree", "--name-only", "HEAD", str(target.relative_to(REPO_ROOT)))
    if tracked:
        raise CloseoutError(
            "canonical mapping is already committed; use a structured duplicate reply"
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
    seal = cast(dict[str, Any], parse_embedded_review_seal(text))
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
    seal.add_argument("--review-ref", required=True)
    seal.add_argument("--scan-manifest", required=True)
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
