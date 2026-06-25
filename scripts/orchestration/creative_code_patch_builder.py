"""CLI for PR-2 sandboxed creative-code candidate patch building."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, cast

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
    build_creative_code_patch_result,
    read_creative_code_patch_build_request,
    validate_creative_code_patch_build_request,
)
from scripts.orchestration.creative_code_patch_executor import (
    CreativeCodePatchExecutorError,
    run_codex_exec,
)
from scripts.orchestration.creative_code_patch_workspace import (
    REPO_ROOT,
    CreativeCodePatchWorkspaceError,
    cleanup_run_dir,
    destroy_generation_checkout,
    generation_checkout,
    prepare_generation_checkout,
    read_json,
    resolve_run_dir,
    resolve_run_file,
    run_git,
    shared_tree_status,
    write_json_atomic,
)
from scripts.orchestration.creative_code_specification import (
    read_creative_code_specification_bundle,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.experiment_bootstrap import build_experiment_packet
from scripts.orchestration.experiment_runner import evaluate_candidate

PREPARE_SUCCESS_OUTPUT = "PASS: creative-code patch prepare complete"
GENERATE_SUCCESS_OUTPUT = "PASS: creative-code patch generate complete"
EVALUATE_SUCCESS_OUTPUT = "PASS: creative-code patch evaluate complete"
CLEANUP_SUCCESS_OUTPUT = "PASS: creative-code patch cleanup complete"

STATE_FILE = "state.json"
REQUEST_FILE = "request.json"
SOURCE_BUNDLE_FILE = "source_bundle.json"
SELECTED_VARIANT_FILE = "selected_variant.json"
PATCH_METADATA_FILE = "patch_metadata.json"
CANDIDATE_PATCH_FILE = "candidate.patch"
EXPERIMENT_PACKET_FILE = "experiment_packet.json"
RESULT_FILE = "result.json"

ALLOWED_DIFF_STATUSES = frozenset({"A", "M"})
REJECTED_DIFF_STATUS_PREFIXES = ("D", "R", "C", "T", "U", "X", "B")
REJECTED_MODES = frozenset({"120000", "160000"})
SAFE_DIFF_FLAGS = ("--no-ext-diff", "--no-textconv")


class CreativeCodePatchBuilderError(ValueError):
    """Raised when the PR-2 patch builder fails closed."""


def _load_run_state(run_id: str) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    run_dir = resolve_run_dir(run_id, create=False)
    state = read_json(resolve_run_file(run_dir, STATE_FILE))
    request = read_json(resolve_run_file(run_dir, REQUEST_FILE))
    bundle = read_json(resolve_run_file(run_dir, SOURCE_BUNDLE_FILE))
    if not isinstance(state, dict) or not isinstance(request, dict) or not isinstance(bundle, dict):
        raise CreativeCodePatchBuilderError("run artifacts must be JSON objects.")
    return run_dir, state, request, bundle


def _selected_variant(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_creative_code_specification_bundle(bundle)
    selected_id = normalized["synthesis"]["selected_variant_id"]
    selected_fingerprint = normalized["synthesis"]["selected_variant_fingerprint"]
    for variant in normalized["variants"]:
        if (
            variant["variant_id"] == selected_id
            and variant["variant_fingerprint"] == selected_fingerprint
        ):
            return dict(variant)
    raise CreativeCodePatchBuilderError("selected variant is not present in source bundle.")


def _write_text_atomic(path: Path, content: str) -> None:
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def prepare(*, spec_bundle_path: Path, request_path: Path, run_id: str) -> dict[str, Any]:
    """Validate source artifacts and create the isolated generation checkout."""

    run_dir = resolve_run_dir(run_id, create=True)
    if any(run_dir.iterdir()):
        raise CreativeCodePatchBuilderError("run directory must be empty before prepare.")
    source_bundle = read_creative_code_specification_bundle(spec_bundle_path)
    request = read_creative_code_patch_build_request(str(request_path))
    normalized_request = validate_creative_code_patch_build_request(
        request,
        source_bundle=source_bundle,
    )
    normalized_bundle = validate_creative_code_specification_bundle(source_bundle)
    selected_variant = _selected_variant(normalized_bundle)
    workspace_summary = prepare_generation_checkout(
        run_dir=run_dir,
        base_commit_sha=normalized_request["base_commit_sha"],
    )
    state = {
        "run_id": run_id,
        "request_id": normalized_request["request_id"],
        "source_bundle_id": normalized_request["source_bundle_id"],
        "selected_variant_id": normalized_request["selected_variant_id"],
        "base_commit_sha": normalized_request["base_commit_sha"],
        "workspace": workspace_summary,
        "candidate_patch_generated": False,
        "candidate_patch_evaluated": False,
    }
    write_json_atomic(resolve_run_file(run_dir, REQUEST_FILE, for_write=True), normalized_request)
    write_json_atomic(
        resolve_run_file(run_dir, SOURCE_BUNDLE_FILE, for_write=True), normalized_bundle
    )
    write_json_atomic(
        resolve_run_file(run_dir, SELECTED_VARIANT_FILE, for_write=True),
        selected_variant,
    )
    write_json_atomic(resolve_run_file(run_dir, STATE_FILE, for_write=True), state)
    return state


def _build_generation_prompt(*, request: dict[str, Any], variant: dict[str, Any]) -> str:
    steps = "\n".join(f"- {step}" for step in variant["implementation_steps"])
    target_paths = "\n".join(f"- {path}" for path in variant["target_paths"])
    allowed_existing = "\n".join(f"- {path}" for path in request["allowed_existing_paths"])
    allowed_new = "\n".join(f"- {path}" for path in request["allowed_new_paths"]) or "- none"
    tests_to_add = "\n".join(f"- {path}" for path in variant["tests_to_add"])
    return (
        "You are generating a local candidate patch inside an isolated checkout.\n"
        "Do not run network commands, read secrets, create branches, commit, push, open PRs, "
        "or edit paths outside the allowlist.\n"
        "Implement the selected PR-1 creative-code specification only.\n\n"
        f"Selected variant: {variant['variant_id']}\n"
        f"Problem statement:\n{variant['problem_statement']}\n\n"
        f"Implementation steps:\n{steps}\n\n"
        f"Selected target paths:\n{target_paths}\n\n"
        f"Allowed existing paths:\n{allowed_existing}\n\n"
        f"Allowed new paths:\n{allowed_new}\n\n"
        f"Tests expected by the specification (do not add them in this PR-2 patch unless "
        f"they are also explicitly allowlisted as mutable targets):\n{tests_to_add}\n\n"
        "Leave the checkout dirty with only the candidate source changes. The wrapper will "
        "validate and export the patch."
    )


def _status_entries(checkout: Path) -> list[tuple[str, str]]:
    status = run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"],
        cwd=checkout,
    ).stdout
    entries: list[tuple[str, str]] = []
    for line in status.splitlines():
        if not line:
            continue
        status_code = line[:2]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append((status_code, path))
    return entries


def _add_intent_for_untracked(checkout: Path, allowed_new_paths: set[str]) -> None:
    for status_code, path in _status_entries(checkout):
        if status_code == "??":
            if path not in allowed_new_paths:
                raise CreativeCodePatchBuilderError(f"untracked path is not allowed: {path}")
            run_git(["add", "-N", "--", path], cwd=checkout)
        elif "U" in status_code:
            raise CreativeCodePatchBuilderError("candidate checkout has unmerged paths.")


def _parse_name_status(output: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        entries.append((status, path))
    return entries


def _reject_forbidden_name_status(checkout: Path) -> None:
    detected = run_git(["diff", *SAFE_DIFF_FLAGS, "--name-status", "HEAD"], cwd=checkout).stdout
    for status, path in _parse_name_status(detected):
        if status.startswith(REJECTED_DIFF_STATUS_PREFIXES):
            raise CreativeCodePatchBuilderError(
                f"candidate patch has forbidden status {status}: {path}"
            )


def _changed_paths_by_status(checkout: Path) -> dict[str, str]:
    no_renames = run_git(
        ["diff", *SAFE_DIFF_FLAGS, "--name-status", "--no-renames", "HEAD"],
        cwd=checkout,
    ).stdout
    changed: dict[str, str] = {}
    for status, path in _parse_name_status(no_renames):
        if status not in ALLOWED_DIFF_STATUSES:
            raise CreativeCodePatchBuilderError(f"candidate patch status is not allowed: {status}")
        changed[path] = status
    return changed


def _reject_binary_numstat(checkout: Path) -> None:
    numstat = run_git(["diff", *SAFE_DIFF_FLAGS, "--numstat", "HEAD"], cwd=checkout).stdout
    for line in numstat.splitlines():
        if not line.strip():
            continue
        added, deleted, path = line.split("\t", 2)
        if added == "-" or deleted == "-":
            raise CreativeCodePatchBuilderError(
                f"candidate patch must not contain binary diff: {path}"
            )


def _reject_modes(checkout: Path) -> None:
    raw = run_git(["diff", *SAFE_DIFF_FLAGS, "--raw", "HEAD"], cwd=checkout).stdout
    for line in raw.splitlines():
        if not line.startswith(":"):
            continue
        header, _, path = line.partition("\t")
        parts = header.split()
        if len(parts) < 5:
            raise CreativeCodePatchBuilderError("unable to parse git diff raw output.")
        old_mode = parts[0][1:]
        new_mode = parts[1]
        status = parts[4]
        if old_mode in REJECTED_MODES or new_mode in REJECTED_MODES:
            raise CreativeCodePatchBuilderError(f"candidate patch has forbidden mode for {path}.")
        if (old_mode == "000000" or status.startswith("A")) and new_mode != "100644":
            raise CreativeCodePatchBuilderError(
                f"candidate patch creates forbidden mode for {path}."
            )
        if old_mode != new_mode and old_mode != "000000":
            raise CreativeCodePatchBuilderError(f"candidate patch changes file mode for {path}.")
        if status.startswith("D"):
            raise CreativeCodePatchBuilderError(f"candidate patch deletes a file: {path}")
    summary = run_git(["diff", *SAFE_DIFF_FLAGS, "--summary", "HEAD"], cwd=checkout).stdout
    if (
        "mode change" in summary
        or "create mode 120000" in summary
        or "create mode 160000" in summary
    ):
        raise CreativeCodePatchBuilderError("candidate patch contains forbidden mode summary.")


def _validate_paths(
    *,
    changed_by_status: dict[str, str],
    request: dict[str, Any],
    bundle: dict[str, Any],
) -> list[str]:
    existing_allowed = set(request["allowed_existing_paths"])
    new_allowed = set(request["allowed_new_paths"])
    allowed_all = existing_allowed | new_allowed
    selected_variant = _selected_variant(bundle)
    target_paths = selected_variant["target_paths"]
    changed_paths = sorted(changed_by_status)
    if not changed_paths:
        raise CreativeCodePatchBuilderError("candidate patch is empty.")
    if len(changed_paths) > request["budgets"]["max_changed_files"]:
        raise CreativeCodePatchBuilderError("candidate patch exceeds max_changed_files budget.")
    for path in changed_paths:
        if path not in allowed_all:
            raise CreativeCodePatchBuilderError(f"candidate patch touches unapproved path: {path}")
        if changed_by_status[path] == "A" and path not in new_allowed:
            raise CreativeCodePatchBuilderError(f"new file path is not approved: {path}")
        if changed_by_status[path] == "M" and path not in existing_allowed:
            raise CreativeCodePatchBuilderError(f"modified path is not approved: {path}")
        if not any(
            path == target or path.startswith(f"{target.rstrip('/')}/") for target in target_paths
        ):
            raise CreativeCodePatchBuilderError(
                f"path is outside selected variant target paths: {path}"
            )
        for oracle_path in bundle["immutable_oracles"]:
            if isinstance(oracle_path, str) and (
                path == oracle_path
                or path.startswith(f"{oracle_path.rstrip('/')}/")
                or oracle_path.startswith(f"{path.rstrip('/')}/")
            ):
                raise CreativeCodePatchBuilderError(
                    "candidate patch overlaps immutable oracle paths."
                )
    return changed_paths


def _check_patch_applies_cleanly(*, patch_text: str, base_commit_sha: str, run_dir: Path) -> None:
    validation_checkout = run_dir / "validation_checkout"
    if validation_checkout.exists() or validation_checkout.is_symlink():
        raise CreativeCodePatchBuilderError("validation checkout already exists.")
    try:
        run_git(
            ["clone", "--no-hardlinks", str(REPO_ROOT), str(validation_checkout)], cwd=REPO_ROOT
        )
        run_git(["checkout", "--detach", base_commit_sha], cwd=validation_checkout)
        remotes = run_git(["remote"], cwd=validation_checkout).stdout.strip()
        if remotes:
            run_git(["remote", "remove", "origin"], cwd=validation_checkout)
        run_git(["apply", "--check"], cwd=validation_checkout, input_text=patch_text)
    finally:
        if validation_checkout.exists() and not validation_checkout.is_symlink():
            import shutil

            shutil.rmtree(validation_checkout)


def _patch_metadata(
    *,
    checkout: Path,
    run_dir: Path,
    request: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    _add_intent_for_untracked(checkout, set(request["allowed_new_paths"]))
    _reject_forbidden_name_status(checkout)
    changed_by_status = _changed_paths_by_status(checkout)
    _reject_binary_numstat(checkout)
    _reject_modes(checkout)
    run_git(["diff", *SAFE_DIFF_FLAGS, "--check", "HEAD"], cwd=checkout)
    changed_paths = _validate_paths(
        changed_by_status=changed_by_status, request=request, bundle=bundle
    )
    patch_text = run_git(["diff", *SAFE_DIFF_FLAGS, "--binary", "HEAD"], cwd=checkout).stdout
    if not patch_text.strip():
        raise CreativeCodePatchBuilderError("candidate patch is empty.")
    patch_bytes = len(patch_text.encode("utf-8"))
    diff_lines = len(patch_text.splitlines())
    if patch_bytes > request["budgets"]["max_patch_bytes"]:
        raise CreativeCodePatchBuilderError("candidate patch exceeds max_patch_bytes budget.")
    if diff_lines > request["budgets"]["max_diff_lines"]:
        raise CreativeCodePatchBuilderError("candidate patch exceeds max_diff_lines budget.")
    _check_patch_applies_cleanly(
        patch_text=patch_text,
        base_commit_sha=request["base_commit_sha"],
        run_dir=run_dir,
    )
    patch_file = resolve_run_file(run_dir, CANDIDATE_PATCH_FILE, for_write=True)
    _write_text_atomic(patch_file, patch_text)
    return {
        "changed_paths": changed_paths,
        "changed_path_statuses": changed_by_status,
        "patch_fingerprint": fingerprint_payload({"candidate_patch": patch_text}),
        "patch_bytes": patch_bytes,
        "diff_lines": diff_lines,
    }


def generate(*, run_id: str) -> dict[str, Any]:
    """Run Codex in the generation checkout and write a validated candidate patch."""

    run_dir, state, request, bundle = _load_run_state(run_id)
    normalized_request = validate_creative_code_patch_build_request(request, source_bundle=bundle)
    selected_variant = read_json(resolve_run_file(run_dir, SELECTED_VARIANT_FILE))
    if not isinstance(selected_variant, dict):
        raise CreativeCodePatchBuilderError("selected variant artifact must be a JSON object.")
    checkout = generation_checkout(run_dir)
    checkout_destroyed = False
    try:
        prompt = _build_generation_prompt(request=normalized_request, variant=selected_variant)
        run_codex_exec(
            checkout=checkout,
            prompt=prompt,
            timeout_seconds=normalized_request["budgets"]["generation_timeout_seconds"],
        )
        metadata = _patch_metadata(
            checkout=checkout,
            run_dir=run_dir,
            request=normalized_request,
            bundle=bundle,
        )
        state["candidate_patch_generated"] = True
        state["patch_metadata"] = metadata
        write_json_atomic(resolve_run_file(run_dir, PATCH_METADATA_FILE, for_write=True), metadata)
        return metadata
    finally:
        checkout_destroyed = destroy_generation_checkout(run_dir)
        state["checkout_destroyed"] = checkout_destroyed
        write_json_atomic(resolve_run_file(run_dir, STATE_FILE, for_write=True), state)


def _experiment_budgets(request: dict[str, Any]) -> dict[str, int]:
    return {
        "wall_clock_seconds": request["budgets"]["evaluation_timeout_seconds"],
        # Experiment Runner requires a positive infra retry budget; PR-2's one-attempt
        # generation invariant is enforced separately by the request contract.
        "retry_budget": 1,
        "max_changed_files": request["budgets"]["max_changed_files"],
        "network_budget": 0,
        "benchmark_budget": 1,
        "test_budget": min(3, max(1, len(request["oracle_commands"]))),
    }


def _creative_research_origin(bundle: dict[str, Any]) -> dict[str, str]:
    source = bundle["source_creative_research"]
    return {
        "bundle_id": source["bundle_id"],
        "candidate_id": source["candidate_id"],
        "promotion_decision": source["promotion_decision"],
    }


def _verified_patch_metadata(
    *,
    run_dir: Path,
    state: dict[str, Any],
    metadata: dict[str, Any],
) -> tuple[Path, list[str], str, int, int]:
    """Return patch metadata only when it matches the current candidate patch."""

    if state.get("candidate_patch_generated") is not True:
        raise CreativeCodePatchBuilderError("candidate patch must be generated before evaluate.")
    changed_paths = metadata.get("changed_paths")
    if not isinstance(changed_paths, list) or not all(
        isinstance(path, str) for path in changed_paths
    ):
        raise CreativeCodePatchBuilderError("patch metadata changed_paths must be a string list.")
    patch_file = resolve_run_file(run_dir, CANDIDATE_PATCH_FILE)
    try:
        patch_text = patch_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CreativeCodePatchBuilderError("candidate patch could not be read.") from exc
    current_fingerprint = fingerprint_payload({"candidate_patch": patch_text})
    current_bytes = len(patch_text.encode("utf-8"))
    current_lines = len(patch_text.splitlines())
    expected = {
        "patch_fingerprint": current_fingerprint,
        "patch_bytes": current_bytes,
        "diff_lines": current_lines,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise CreativeCodePatchBuilderError("candidate patch metadata does not match patch.")
    return patch_file, sorted(changed_paths), current_fingerprint, current_bytes, current_lines


def evaluate(*, run_id: str) -> dict[str, Any]:
    """Evaluate the generated candidate patch with Experiment Runner candidate mode."""

    run_dir, state, request, bundle = _load_run_state(run_id)
    normalized_request = validate_creative_code_patch_build_request(request, source_bundle=bundle)
    metadata = read_json(resolve_run_file(run_dir, PATCH_METADATA_FILE))
    if not isinstance(metadata, dict):
        raise CreativeCodePatchBuilderError("patch metadata must be a JSON object.")
    patch_file, changed_paths, patch_fingerprint, patch_bytes, diff_lines = (
        _verified_patch_metadata(
            run_dir=run_dir,
            state=state,
            metadata=metadata,
        )
    )
    selected_variant = _selected_variant(bundle)
    shared_status_before = shared_tree_status()
    packet = build_experiment_packet(
        decision_question=selected_variant["problem_statement"],
        task_class="Experimentation",
        mutable_paths=changed_paths,
        oracle_commands=normalized_request["oracle_commands"],
        metrics=normalized_request["metrics"],
        negative_controls=selected_variant["negative_controls"],
        promotion_target="audit_artifact",
        budgets=_experiment_budgets(normalized_request),
        creative_research_origin=_creative_research_origin(bundle),
    )
    write_json_atomic(resolve_run_file(run_dir, EXPERIMENT_PACKET_FILE, for_write=True), packet)
    failure_class: str | None = None
    try:
        runner_result = evaluate_candidate(packet, patch_file)
    except Exception as exc:
        failure_class = "infra_flake"
        runner_error = exc.__class__.__name__
        runner_result = {
            "experiment_id": packet["experiment_id"],
            "runner_mode": "candidate_patch",
            "candidate_patch": "sanitized",
            "status": "rejected",
            "failure_class": "infra_flake",
            "mutated_paths": [],
            "oracle_results": [],
            "budget_observations": {
                "configured_budgets": packet["budgets"],
                "oracle_commands_configured": len(packet["immutable_oracles"]),
                "oracle_commands_executed": 0,
                "candidate_changed_files": len(changed_paths),
                "attempts": 0,
                "retries_consumed": 0,
                "runner_error": runner_error,
            },
            "shared_tree_untouched": False,
        }
    shared_status_after = shared_tree_status()
    shared_untouched = shared_status_before == shared_status_after
    result = build_creative_code_patch_result(
        request=normalized_request,
        changed_paths=changed_paths,
        patch_fingerprint=patch_fingerprint,
        patch_bytes=patch_bytes,
        diff_lines=diff_lines,
        runner_result=runner_result,
        checkout_destroyed=bool(state.get("checkout_destroyed") is True),
        origin_removed=bool(state.get("workspace", {}).get("origin_removed") is True),
        shared_tree_untouched=shared_untouched,
        failure_class=failure_class,
    )
    state["candidate_patch_evaluated"] = True
    write_json_atomic(resolve_run_file(run_dir, RESULT_FILE, for_write=True), result)
    write_json_atomic(resolve_run_file(run_dir, STATE_FILE, for_write=True), state)
    return cast(dict[str, Any], result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare, generate, evaluate, and clean PR-2 creative-code patches."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--spec-bundle", required=True)
    prepare_parser.add_argument("--request", required=True)
    prepare_parser.add_argument("--run-dir", required=True)

    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--run-dir", required=True)

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--run-dir", required=True)

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--run-dir", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(
                spec_bundle_path=Path(args.spec_bundle),
                request_path=Path(args.request),
                run_id=args.run_dir,
            )
            print(PREPARE_SUCCESS_OUTPUT)
        elif args.command == "generate":
            generate(run_id=args.run_dir)
            print(GENERATE_SUCCESS_OUTPUT)
        elif args.command == "evaluate":
            evaluate(run_id=args.run_dir)
            print(EVALUATE_SUCCESS_OUTPUT)
        elif args.command == "cleanup":
            cleanup_run_dir(args.run_dir)
            print(CLEANUP_SUCCESS_OUTPUT)
        else:
            parser.error("unsupported command")
    except (
        CreativeCodePatchBuilderError,
        CreativeCodePatchContractError,
        CreativeCodePatchExecutorError,
        CreativeCodePatchWorkspaceError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
