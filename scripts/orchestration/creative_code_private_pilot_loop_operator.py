"""Local creative-code private-pilot lifecycle operator CLI.

Commands collect sanitized PR/check/review metadata, decide the next operator
action, and emit a checklist-only candidate plan. The CLI does not generate
patches, write branches, push, open PRs, edit fixed mapping, resolve threads,
call providers, call product runtime, or claim readiness.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess  # nosec B404: bounded gh CLI metadata reads only, via resolved absolute binary (remove-by: 2026-12-31, ref: PR-private-pilot-loop-operator)
import sys
import tempfile
from typing import Any, Mapping, cast
from urllib.parse import quote

from scripts.orchestration import pr_review_context
from scripts.orchestration.creative_code_private_pilot_loop_contract import (
    ARTIFACT_REF_TYPES,
    DEFAULT_TARGET_SURFACE,
    CreativeCodePrivatePilotContractError,
    build_candidate_plan,
    build_current_head_check_summary,
    build_private_pilot_state,
    classify_review_capacity,
    decide_next_action,
    read_json_object,
    reject_unsafe_private_pilot_value,
    validate_candidate_plan,
    validate_private_pilot_state,
)
from scripts.orchestration.creative_code_review_disposition_contract import (
    CreativeCodeReviewDispositionContractError,
    DISPOSITION_PACKET_TYPE,
    validate_creative_code_review_disposition_packet,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
PRIVATE_PILOT_ROOT = CREATIVE_CODE_ROOT / "private_pilot"

PILOT_STATE_FILE = "pilot_state.json"
CANDIDATE_PLAN_FILE = "candidate_plan.json"
SUCCESS_COLLECT_OUTPUT = "PASS: creative-code private-pilot state collected"
SUCCESS_CANDIDATE_PLAN_OUTPUT = "PASS: creative-code private-pilot candidate plan emitted"
GH_COMMAND_TIMEOUT_SECONDS = 60
STRICT_MERGE_STATE_BLOCKERS = frozenset(
    {"BEHIND", "BLOCKED", "DIRTY", "DRAFT", "UNKNOWN", "UNSTABLE"}
)
REVIEW_DECISION_BLOCKERS = frozenset({"CHANGES_REQUESTED", "REVIEW_REQUIRED"})


class CreativeCodePrivatePilotOperatorError(ValueError):
    """Raised when the private-pilot CLI cannot safely complete."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    components: list[Path] = []
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodePrivatePilotOperatorError(f"{label} must not traverse symlinks.")


def _ensure_private_pilot_root() -> Path:
    _reject_symlink_components(PRIVATE_PILOT_ROOT, label="private pilot root")
    try:
        PRIVATE_PILOT_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodePrivatePilotOperatorError(
            "private pilot root could not be created."
        ) from exc
    _reject_symlink_components(PRIVATE_PILOT_ROOT, label="private pilot root")
    root = PRIVATE_PILOT_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise CreativeCodePrivatePilotOperatorError("private pilot root must be a directory.")
    return root


def _resolve_output_dir(raw_output_dir: Path, *, pr_number: int, create: bool) -> Path:
    root = _ensure_private_pilot_root()
    expected_leaf = str(pr_number)
    if raw_output_dir.is_absolute():
        candidate = raw_output_dir
    elif raw_output_dir.parts[:4] == (
        "artifacts",
        "orchestration",
        "creative_code",
        "private_pilot",
    ):
        candidate = REPO_ROOT / raw_output_dir
    else:
        candidate = PRIVATE_PILOT_ROOT / raw_output_dir
    _reject_symlink_components(candidate, label="private pilot output directory")
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_candidate, root):
        raise CreativeCodePrivatePilotOperatorError(
            "output directory must stay under private pilot artifacts."
        )
    if resolved_candidate.name != expected_leaf:
        raise CreativeCodePrivatePilotOperatorError("output directory leaf must match PR number.")
    if create:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CreativeCodePrivatePilotOperatorError(
                "output directory could not be created."
            ) from exc
        _reject_symlink_components(candidate, label="private pilot output directory")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodePrivatePilotOperatorError("output directory must exist.") from exc
    if not _is_relative_to(resolved, root) or not resolved.is_dir():
        raise CreativeCodePrivatePilotOperatorError(
            "output directory must stay under private pilot artifacts."
        )
    return resolved


def _resolve_artifact_file(raw_path: Path, *, expected_filename: str, for_write: bool) -> Path:
    root = _ensure_private_pilot_root()
    path = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    if path.name != expected_filename:
        raise CreativeCodePrivatePilotOperatorError(
            f"private pilot artifact filename must be {expected_filename}."
        )
    _reject_symlink_components(path.parent, label="private pilot artifact parent")
    parent = path.parent.resolve(strict=False)
    if not _is_relative_to(parent, root):
        raise CreativeCodePrivatePilotOperatorError(
            "private pilot artifact path must stay under private pilot artifacts."
        )
    if for_write:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CreativeCodePrivatePilotOperatorError(
                "private pilot artifact parent could not be created."
            ) from exc
        _reject_symlink_components(path.parent, label="private pilot artifact parent")
    try:
        resolved_parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodePrivatePilotOperatorError(
            "private pilot artifact parent missing."
        ) from exc
    if not _is_relative_to(resolved_parent, root):
        raise CreativeCodePrivatePilotOperatorError(
            "private pilot artifact path must stay under private pilot artifacts."
        )
    if path.exists() or path.is_symlink():
        if path.is_symlink():
            raise CreativeCodePrivatePilotOperatorError(
                "private pilot artifact file must not be a symlink."
            )
        if not path.is_file():
            raise CreativeCodePrivatePilotOperatorError(
                "private pilot artifact path must be a file."
            )
    return resolved_parent / path.name


def _write_json_atomic(path: Path, payload: Mapping[str, Any], *, expected_filename: str) -> None:
    reject_unsafe_private_pilot_value(dict(payload), label="output")
    output = _resolve_artifact_file(path, expected_filename=expected_filename, for_write=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(payload, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, output)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise CreativeCodePrivatePilotOperatorError(f"Missing required binary: {name}")
    return path


def _run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(  # nosec B603: argv uses resolved gh path with fixed read-only metadata subcommands only (remove-by: 2026-12-31, ref: PR-private-pilot-loop-operator)
            args,
            cwd=str(cwd),
            text=True,
            check=False,
            capture_output=True,
            timeout=GH_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        command = shlex.join(args).replace(str(cwd), "<repo-root>")
        raise CreativeCodePrivatePilotOperatorError(f"Command timed out ({command}).") from exc
    if completed.returncode != 0:
        command = shlex.join(args).replace(str(cwd), "<repo-root>")
        stderr = completed.stderr.strip().replace(str(cwd), "<repo-root>")
        raise CreativeCodePrivatePilotOperatorError(f"Command failed ({command}): {stderr}")
    return completed


def _run_json_command(args: list[str], *, cwd: Path) -> Any:
    raw = _run_command(args, cwd=cwd).stdout.strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CreativeCodePrivatePilotOperatorError(
            "GitHub metadata response was not JSON."
        ) from exc


def _gh_pr_view(*, pr_number: int, repo_root: Path) -> dict[str, Any]:
    gh_binary = _binary("gh")
    payload = _run_json_command(
        [
            gh_binary,
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,url,state,isDraft,baseRefName,baseRefOid,headRefOid,mergeStateStatus,reviewDecision",
        ],
        cwd=repo_root,
    )
    if not isinstance(payload, dict):
        raise CreativeCodePrivatePilotOperatorError("PR metadata response must be an object.")
    return payload


def _gh_api_json(path: str, *, repo_root: Path) -> Any:
    gh_binary = _binary("gh")
    return _run_json_command([gh_binary, "api", path], cwd=repo_root)


def _required_check_names(
    *, repo: str, base_ref: str, repo_root: Path
) -> tuple[list[str], bool, bool]:
    try:
        encoded_base_ref = quote(base_ref, safe="")
        payload = _gh_api_json(
            f"repos/{repo}/branches/{encoded_base_ref}/protection/required_status_checks",
            repo_root=repo_root,
        )
    except CreativeCodePrivatePilotOperatorError:
        return [], False, False
    if not isinstance(payload, dict):
        return [], False, False
    names: set[str] = set()
    for item in payload.get("contexts") or []:
        if isinstance(item, str) and item.strip():
            names.add(f"status_context:{item.strip()}")
    for item in payload.get("checks") or []:
        if isinstance(item, dict):
            context = str(item.get("context") or "").strip()
            app_id = str(item.get("app_id") or "").strip()
            if context:
                names.add(f"app_id:{app_id}:{context}" if app_id else f"check_run:{context}")
    return sorted(names), True, bool(payload.get("strict"))


def _strict_merge_state_requires_wait(*, strict_required: bool, merge_state: str) -> bool:
    return strict_required and merge_state.upper() in STRICT_MERGE_STATE_BLOCKERS


def _strict_merge_state_check(*, pr_url: Any, head_sha: str) -> dict[str, Any]:
    return {
        "name": "branch-protection-strict-update",
        "workflow": "github_branch_protection",
        "status": "in_progress",
        "conclusion": "",
        "head_sha": head_sha,
        "details_url": pr_url if isinstance(pr_url, str) else None,
        "required": True,
    }


def _github_pr_review_sources(
    pr_view: Mapping[str, Any],
    *,
    strict_required: bool,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    review_decision = str(pr_view.get("reviewDecision") or "").strip().upper()
    if review_decision in REVIEW_DECISION_BLOCKERS:
        sources.append(
            {
                "source": "github_review_decision",
                "status": "unresolved_threads",
                "source_degraded": True,
                "blocking": True,
            }
        )
    merge_state = str(pr_view.get("mergeStateStatus") or "").strip().upper()
    if _strict_merge_state_requires_wait(
        strict_required=strict_required,
        merge_state=merge_state,
    ):
        sources.append(
            {
                "source": "github_merge_state",
                "status": "failed_required_check",
                "source_degraded": True,
                "blocking": True,
            }
        )
    return sources


def _current_head_raw_checks(*, repo: str, head_sha: str, repo_root: Path) -> list[dict[str, Any]]:
    raw_checks: list[dict[str, Any]] = []
    check_runs = _gh_api_json(
        f"repos/{repo}/commits/{head_sha}/check-runs?per_page=100",
        repo_root=repo_root,
    )
    if isinstance(check_runs, dict):
        for item in check_runs.get("check_runs") or []:
            if not isinstance(item, dict):
                continue
            app = item.get("app") if isinstance(item.get("app"), dict) else {}
            raw_checks.append(
                {
                    "name": item.get("name") or "unknown",
                    "workflow": (app or {}).get("name") or "",
                    "app_id": (app or {}).get("id") or "",
                    "status": item.get("status") or "",
                    "conclusion": item.get("conclusion") or "",
                    "head_sha": item.get("head_sha") or "",
                    "details_url": item.get("details_url") or None,
                    "started_at": item.get("started_at") or None,
                    "completed_at": item.get("completed_at") or None,
                    "required": False,
                }
            )
    status_payload = _gh_api_json(f"repos/{repo}/commits/{head_sha}/status", repo_root=repo_root)
    if isinstance(status_payload, dict):
        for item in status_payload.get("statuses") or []:
            if not isinstance(item, dict):
                continue
            raw_checks.append(
                {
                    "name": item.get("context") or "unknown",
                    "workflow": "status_context",
                    "status": item.get("state") or "",
                    "conclusion": item.get("state") or "",
                    "head_sha": head_sha,
                    "details_url": item.get("target_url") or None,
                    "created_at": item.get("created_at") or None,
                    "required": False,
                }
            )
    return raw_checks


def _artifact_fingerprint(path: Path) -> str | None:
    if not path.is_file() or path.is_symlink():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    return path.resolve(strict=False).relative_to(repo_root.resolve(strict=True)).as_posix()


def _safe_artifact_repo_path(path: Path, *, root: Path, repo_root: Path) -> str | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        resolved_path = path.resolve(strict=True)
        resolved_path.relative_to(root.resolve(strict=True))
        return resolved_path.relative_to(repo_root.resolve(strict=True)).as_posix()
    except (FileNotFoundError, ValueError):
        return None


def _artifact_refs(
    *,
    repo_root: Path,
    pattern: str,
    artifact_type: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if artifact_type not in ARTIFACT_REF_TYPES:
        raise CreativeCodePrivatePilotOperatorError(
            f"Unsupported artifact ref type: {artifact_type}"
        )
    root = repo_root / "artifacts" / "orchestration" / "creative_code"
    refs: list[dict[str, Any]] = []
    for path in sorted(root.glob(pattern))[:limit]:
        repo_path = _safe_artifact_repo_path(path, root=root, repo_root=repo_root)
        if repo_path is None:
            continue
        refs.append(
            {
                "artifact_type": artifact_type,
                "repo_path": repo_path,
                "exists": True,
                "fingerprint": _artifact_fingerprint(path),
            }
        )
    return refs


def _typed_artifact_refs(
    *,
    repo_root: Path,
    pattern: str,
    artifact_type: str,
    type_key: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    root = repo_root / "artifacts" / "orchestration" / "creative_code"
    for path in sorted(root.glob(pattern)):
        repo_path = _safe_artifact_repo_path(path, root=root, repo_root=repo_root)
        if repo_path is None:
            continue
        try:
            payload = read_json_object(path)
        except CreativeCodePrivatePilotContractError:
            refs.append(
                {
                    "artifact_type": artifact_type,
                    "repo_path": repo_path,
                    "exists": True,
                    "fingerprint": _artifact_fingerprint(path),
                }
            )
            continue
        if payload.get(type_key) != artifact_type:
            continue
        refs.append(
            {
                "artifact_type": artifact_type,
                "repo_path": repo_path,
                "exists": True,
                "fingerprint": _artifact_fingerprint(path),
            }
        )
    return refs


def _fixed_mapping_ref(context: Mapping[str, Any], *, pr_number: int) -> dict[str, Any]:
    raw_mapping = context.get("fixed_mapping")
    mapping = raw_mapping if isinstance(raw_mapping, Mapping) else {}
    entries = mapping.get("entries")
    errors = mapping.get("errors")
    mapping_degraded = bool(errors) if isinstance(errors, list) else False
    if mapping.get("exists") and mapping.get("present_in_pr_diff") is not True:
        mapping_degraded = True
    entry_count = len(entries) if isinstance(entries, Mapping) else 0
    no_actionable = bool(mapping.get("no_actionable"))
    has_disposition_proof = entry_count > 0 or no_actionable
    return {
        "required": True,
        "present": bool(mapping.get("exists")) and not mapping_degraded and has_disposition_proof,
        "repo_path": str(
            mapping.get("repo_path") or f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
        ),
        "entry_count": entry_count,
        "no_actionable": no_actionable,
    }


def _blocker_counts_from_pr5_refs(
    *,
    repo_root: Path,
    refs: list[dict[str, Any]],
    repository: str,
    pr_number: int,
    head_sha: str,
) -> dict[str, int]:
    counts = {
        "actionable_review_count": 0,
        "security_blocker_count": 0,
        "governance_blocker_count": 0,
    }
    for ref in refs:
        if not ref.get("exists"):
            continue
        repo_path = str(ref.get("repo_path") or "")
        path = repo_root / repo_path
        try:
            payload = read_json_object(path)
            packet = validate_creative_code_review_disposition_packet(payload)
        except (
            CreativeCodePrivatePilotContractError,
            CreativeCodeReviewDispositionContractError,
        ):
            counts["governance_blocker_count"] += 1
            continue

        source_context = packet["source_context"]
        packet_repository = source_context["repository"]
        packet_pr_number = source_context["pr_number"]
        if packet_repository != repository or packet_pr_number != pr_number:
            continue
        if packet["actual_head_sha"] != head_sha:
            counts["governance_blocker_count"] += 1
            continue

        for record in packet["feedback_records"]:
            classification = record["classification"]
            disposition = classification["candidate_disposition"]
            reason_code = classification["reason_code"]
            if disposition == "security_blocker":
                counts["security_blocker_count"] += 1
            elif classification["requires_repair"] or disposition == "simple_fix":
                counts["actionable_review_count"] += 1
            if reason_code in {"fixed_mapping_governance", "head_sha_drift"}:
                counts["governance_blocker_count"] += 1
        if packet["head_sha_drift"]:
            counts["governance_blocker_count"] += 1
    return counts


def collect_private_pilot_state(
    *,
    pr_number: int,
    output_dir: Path,
    repo_root: Path = REPO_ROOT,
) -> tuple[Path, dict[str, Any]]:
    """Collect sanitized state and write `pilot_state.json` under output_dir."""

    output = _resolve_output_dir(output_dir, pr_number=pr_number, create=True)
    repo = pr_review_context.infer_repo_name(repo_root)
    if not repo:
        raise CreativeCodePrivatePilotOperatorError("Repository slug unavailable.")
    pr_view = _gh_pr_view(pr_number=pr_number, repo_root=repo_root)
    head_sha = str(pr_view.get("headRefOid") or "")
    base_ref = str(pr_view.get("baseRefName") or "")
    base_sha = str(pr_view.get("baseRefOid") or "")
    if not head_sha:
        raise CreativeCodePrivatePilotOperatorError("PR head SHA unavailable.")

    context = pr_review_context.collect_review_context(
        repo_root=repo_root,
        pr_number=pr_number,
        repo=repo,
        base_ref=base_sha or base_ref,
        head_ref=head_sha,
    )
    required_names, required_metadata_available, strict_required = _required_check_names(
        repo=repo,
        base_ref=base_ref,
        repo_root=repo_root,
    )
    raw_checks = _current_head_raw_checks(repo=repo, head_sha=head_sha, repo_root=repo_root)
    if _strict_merge_state_requires_wait(
        strict_required=strict_required,
        merge_state=str(pr_view.get("mergeStateStatus") or ""),
    ):
        raw_checks.append(_strict_merge_state_check(pr_url=pr_view.get("url"), head_sha=head_sha))
    checks = build_current_head_check_summary(
        pr_head_sha=head_sha,
        raw_checks=raw_checks,
        required_check_names=required_names,
        required_metadata_available=required_metadata_available,
    )
    review_sources = context.get("review_source_status")
    review_source_list = cast(
        list[Mapping[str, Any]],
        review_sources if isinstance(review_sources, list) else [],
    )
    review_source_list = [
        *review_source_list,
        *_github_pr_review_sources(pr_view, strict_required=strict_required),
    ]
    review_capacity = classify_review_capacity(review_source_list)
    fixed_mapping = _fixed_mapping_ref(context, pr_number=pr_number)
    pr5_refs = _typed_artifact_refs(
        repo_root=repo_root,
        pattern="review_disposition/*.json",
        artifact_type=DISPOSITION_PACKET_TYPE,
        type_key="packet_type",
    )
    disposition_blockers = _blocker_counts_from_pr5_refs(
        repo_root=repo_root,
        refs=pr5_refs,
        repository=repo,
        pr_number=pr_number,
        head_sha=head_sha,
    )
    blockers = {
        "actionable_review_count": disposition_blockers["actionable_review_count"],
        "security_blocker_count": disposition_blockers["security_blocker_count"],
        "governance_blocker_count": disposition_blockers["governance_blocker_count"],
        "fixed_mapping_required": True,
        "fixed_mapping_present": fixed_mapping["present"],
    }
    governance_refs = {
        "target_surface": [DEFAULT_TARGET_SURFACE],
        "fixed_mapping": fixed_mapping,
        "pr4_telemetry_refs": _artifact_refs(
            repo_root=repo_root,
            pattern="telemetry/*.json",
            artifact_type="creative_code_telemetry_event",
        ),
        "pr5_disposition_refs": pr5_refs,
        "pr6_run_plan_refs": _artifact_refs(
            repo_root=repo_root,
            pattern="applied_candidates/*/run_plan.json",
            artifact_type="creative_code_applied_candidate_run_plan",
        ),
    }
    state = build_private_pilot_state(
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_pr={
            "repository": repo,
            "pr_number": pr_number,
            "url": pr_view.get("url") or None,
            "state": str(pr_view.get("state") or "unknown").lower(),
            "draft": bool(pr_view.get("isDraft")),
            "base_ref": base_ref or "main",
            "base_sha": base_sha or None,
            "head_sha": head_sha,
        },
        current_head_checks=checks,
        review_capacity=review_capacity,
        blockers=blockers,
        governance_refs=governance_refs,
    )
    output_path = output / PILOT_STATE_FILE
    _write_json_atomic(output_path, state, expected_filename=PILOT_STATE_FILE)
    return output_path, state


def read_pilot_state(path: Path) -> dict[str, Any]:
    resolved = _resolve_artifact_file(path, expected_filename=PILOT_STATE_FILE, for_write=False)
    try:
        payload = read_json_object(resolved)
        validated_state: dict[str, Any] = validate_private_pilot_state(payload)
        return validated_state
    except CreativeCodePrivatePilotContractError as exc:
        raise CreativeCodePrivatePilotOperatorError(str(exc)) from exc


def write_candidate_plan(*, state_path: Path) -> tuple[Path, dict[str, Any]]:
    state = read_pilot_state(state_path)
    try:
        plan = build_candidate_plan(state)
    except CreativeCodePrivatePilotContractError as exc:
        raise CreativeCodePrivatePilotOperatorError(str(exc)) from exc
    output_path = state_path.parent / CANDIDATE_PLAN_FILE
    _write_json_atomic(output_path, plan, expected_filename=CANDIDATE_PLAN_FILE)
    return output_path, validate_candidate_plan(plan)


def render_status_summary(state: Mapping[str, Any]) -> str:
    normalized = validate_private_pilot_state(state)
    checks = normalized["current_head_checks"]
    summary = checks["summary"]
    stale = checks["stale_diagnostics"]
    lines = [
        f"Creative-code private pilot PR #{normalized['source_pr']['pr_number']}",
        f"head: {normalized['source_pr']['head_sha'][:12]}",
        f"decision: {normalized['decision']}",
        (
            "checks: "
            f"{summary['current_failing']} failing, "
            f"{summary['current_pending']} pending, "
            f"{stale['total']} stale diagnostic"
        ),
        f"review friction: {normalized['review_capacity']['friction']}",
        f"next action: {normalized['decision']}",
    ]
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Operate the local creative-code private-pilot lifecycle loop."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Print a safe state summary.")
    status.add_argument("--pilot-state", required=True, type=Path)

    collect = subparsers.add_parser("collect", help="Collect sanitized private-pilot state.")
    collect.add_argument("--pr-number", required=True, type=int)
    collect.add_argument("--output-dir", required=True, type=Path)

    decide = subparsers.add_parser("decide-next", help="Print the next lifecycle decision.")
    decide.add_argument("--pilot-state", required=True, type=Path)

    prepare = subparsers.add_parser(
        "prepare-next-candidate",
        help="Emit checklist-only candidate_plan.json next to pilot_state.json.",
    )
    prepare.add_argument("--pilot-state", required=True, type=Path)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "collect":
            output_path, _state = collect_private_pilot_state(
                pr_number=args.pr_number,
                output_dir=args.output_dir,
            )
            print(f"{SUCCESS_COLLECT_OUTPUT}: {output_path.relative_to(REPO_ROOT)}")
            return 0
        if args.command == "status":
            print(render_status_summary(read_pilot_state(args.pilot_state)))
            return 0
        if args.command == "decide-next":
            print(decide_next_action(read_pilot_state(args.pilot_state)))
            return 0
        if args.command == "prepare-next-candidate":
            output_path, _plan = write_candidate_plan(state_path=args.pilot_state)
            print(f"{SUCCESS_CANDIDATE_PLAN_OUTPUT}: {output_path.relative_to(REPO_ROOT)}")
            return 0
    except (CreativeCodePrivatePilotOperatorError, CreativeCodePrivatePilotContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
