"""Collect local creative-code telemetry for PR-4.

The collector reads only sanitized PR-1/PR-2/PR-3 artifacts and writes local
advisory telemetry under gitignored creative-code artifact roots.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
    read_creative_code_patch_result,
    validate_creative_code_patch_result,
)
from scripts.orchestration.creative_code_pr_promotion_contract import (
    CreativeCodePRPromotionContractError,
    read_json_object as read_promotion_json_object,
    validate_creative_code_pr_promotion_approval,
    validate_creative_code_pr_promotion_plan,
    validate_creative_code_pr_promotion_receipt,
    validate_creative_code_pr_promotion_validation,
)
from scripts.orchestration.creative_code_specification import (
    CreativeCodeSpecificationError,
    read_creative_code_specification_bundle,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.creative_code_telemetry_contract import (
    CreativeCodeTelemetryContractError,
    build_creative_code_rejection_taxonomy,
    build_creative_code_telemetry_rollup_v2,
    build_creative_code_terminal_telemetry_event,
    build_creative_code_telemetry_event,
    build_creative_code_telemetry_rollup,
    default_metrics,
    reject_unsafe_telemetry_value,
    validate_creative_code_rejection_taxonomy,
    validate_creative_code_telemetry_event_any,
    validate_creative_code_telemetry_rollup_any,
)
from scripts.orchestration.creative_code_terminal_outcome_contract import (
    CreativeCodeTerminalOutcomeError,
    read_json_object as read_terminal_json_object,
    validate_creative_code_terminal_outcome,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
SPEC_RUNS_DIR = CREATIVE_CODE_ROOT / "spec_runs"
PATCH_RUNS_DIR = CREATIVE_CODE_ROOT / "patch_runs"
PROMOTIONS_DIR = CREATIVE_CODE_ROOT / "promotions"
TERMINAL_OUTCOMES_DIR = CREATIVE_CODE_ROOT / "terminal_outcomes"
TELEMETRY_ROOT = CREATIVE_CODE_ROOT / "telemetry"

EVENTS_FILE = "creative_code_telemetry_events.jsonl"
ROLLUP_FILE = "creative_code_telemetry_rollup.json"
SUMMARY_FILE = "creative_code_telemetry_summary.md"
TAXONOMY_FILE = "creative_code_rejection_taxonomy.v1.json"
SUCCESS_OUTPUT = "PASS: creative-code telemetry collected"

PLAN_FILE = "promotion_plan.json"
VALIDATION_FILE = "preopen_validation.json"
APPROVAL_FILE = "promotion_approval.json"
RECEIPT_FILE = "promotion_receipt.json"


class CreativeCodeTelemetryError(ValueError):
    """Raised when local telemetry collection cannot stay contained."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _require_disjoint_mixed_input_roots(roots: tuple[Path, ...]) -> None:
    for index, left in enumerate(roots):
        for right in roots[index + 1 :]:
            if left == right or _is_relative_to(left, right) or _is_relative_to(right, left):
                raise CreativeCodeTelemetryError(
                    "mixed telemetry input roots must be path-disjoint."
                )


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
            raise CreativeCodeTelemetryError(f"{label} must not traverse symlinks.")


def _ensure_dir_root(root: Path) -> Path:
    _reject_symlink_components(root, label="artifact root")
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodeTelemetryError("artifact root could not be created.") from exc
    _reject_symlink_components(root, label="artifact root")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise CreativeCodeTelemetryError("artifact root must be a directory.")
    return resolved


def _resolve_requested_path(raw_path: Path, *, allowed_root: Path, resolved_root: Path) -> Path:
    if raw_path.is_absolute():
        return raw_path
    repo_relative = REPO_ROOT / raw_path
    if _is_relative_to(repo_relative.resolve(strict=False), resolved_root):
        return repo_relative
    return allowed_root / raw_path


def _resolve_dir(raw_path: Path, *, allowed_root: Path, create: bool, label: str) -> Path:
    root = _ensure_dir_root(allowed_root)
    path = _resolve_requested_path(raw_path, allowed_root=allowed_root, resolved_root=root)
    if path.is_absolute() and not _is_relative_to(path, root):
        raise CreativeCodeTelemetryError(f"{label} must stay under creative-code artifacts.")
    _reject_symlink_components(path, label=label)
    candidate = path.resolve(strict=False)
    if not _is_relative_to(candidate, root):
        raise CreativeCodeTelemetryError(f"{label} must stay under creative-code artifacts.")
    if create:
        path.mkdir(parents=True, exist_ok=True)
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CreativeCodeTelemetryError(f"{label} must exist.") from exc
    if not _is_relative_to(resolved, root):
        raise CreativeCodeTelemetryError(f"{label} must stay under creative-code artifacts.")
    if not resolved.is_dir():
        raise CreativeCodeTelemetryError(f"{label} must be a directory.")
    return resolved


def _resolve_optional_dir(raw_path: Path, *, allowed_root: Path, label: str) -> Path:
    root = _ensure_dir_root(allowed_root)
    path = _resolve_requested_path(raw_path, allowed_root=allowed_root, resolved_root=root)
    if path.is_absolute() and not _is_relative_to(path, root):
        raise CreativeCodeTelemetryError(f"{label} must stay under creative-code artifacts.")
    _reject_symlink_components(path, label=label)
    candidate = path.resolve(strict=False)
    if not _is_relative_to(candidate, root):
        raise CreativeCodeTelemetryError(f"{label} must stay under creative-code artifacts.")
    if path.exists():
        return _resolve_dir(path, allowed_root=allowed_root, create=False, label=label)
    return candidate


def _resolve_output_dir(raw_path: Path) -> Path:
    return _resolve_dir(
        raw_path, allowed_root=TELEMETRY_ROOT, create=True, label="output directory"
    )


def _safe_root_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix().replace("/", ".")
    except ValueError:
        return path.name


def _iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    json_files: list[Path] = []
    for path in sorted(root.rglob("*.json")):
        _reject_symlink_components(path, label="artifact JSON")
        if path.is_file():
            json_files.append(path)
    return json_files


def _source_fingerprint(payload: dict[str, Any]) -> str:
    fingerprint = fingerprint_payload(payload)
    if not isinstance(fingerprint, str):
        raise CreativeCodeTelemetryError("source fingerprint must be a string.")
    return fingerprint


def _artifact_locator_fingerprint(path: Path) -> str:
    _reject_symlink_components(path, label="artifact read error source")
    root = CREATIVE_CODE_ROOT.resolve(strict=False)
    resolved = path.resolve(strict=False)
    if not _is_relative_to(resolved, root):
        raise CreativeCodeTelemetryError(
            "artifact read error source must stay under creative-code artifacts."
        )
    locator = resolved.relative_to(root).as_posix()
    locator_fingerprint = _source_fingerprint({"artifact_locator": locator})
    return _source_fingerprint({"artifact_locator_fingerprint": locator_fingerprint})


def _taxonomy_from_failure(failure_class: str | None) -> list[str]:
    if failure_class is None:
        return []
    if failure_class == "duplicate_spec_fingerprint":
        return ["duplicate_variant"]
    if failure_class == "review_blocker":
        return ["review_blocker"]
    if failure_class == "unsafe_authority":
        return ["unsafe_authority"]
    if failure_class in {
        "timeout",
        "oom",
        "metric_regression",
        "guard_failure",
        "policy_violation",
        "unchanged_result",
        "capability_mismatch",
        "infra_flake",
    }:
        return [failure_class]
    if failure_class == "invalid_input":
        return ["invalid_input"]
    return ["unknown"]


def _candidate_ids(
    *,
    source_packet_id: str | None = None,
    source_bundle_id: str | None = None,
    selected_variant_id: str | None = None,
    request_id: str | None = None,
    result_id: str | None = None,
    promotion_id: str | None = None,
) -> dict[str, str | None]:
    return {
        "promotion_id": promotion_id,
        "request_id": request_id,
        "result_id": result_id,
        "selected_variant_id": selected_variant_id,
        "source_bundle_id": source_bundle_id,
        "source_packet_id": source_packet_id,
    }


def event_from_specification_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_creative_code_specification_bundle(bundle)
    selected_variant_id = normalized["synthesis"]["selected_variant_id"]
    failure_class = normalized["failure_class"]
    status = "accepted" if selected_variant_id and failure_class is None else "rejected"
    taxonomy_codes = _taxonomy_from_failure(failure_class)
    rejection_class = taxonomy_codes[0] if taxonomy_codes else None
    event: dict[str, Any] = build_creative_code_telemetry_event(
        lane_stage="specification",
        source_artifact_type="creative_code_specification",
        source_artifact_id=normalized["bundle_id"],
        source_fingerprint=_source_fingerprint(normalized),
        candidate_ids=_candidate_ids(
            source_packet_id=normalized["source_packet_id"],
            source_bundle_id=normalized["bundle_id"],
            selected_variant_id=selected_variant_id,
        ),
        status=status,
        rejection_class=rejection_class,
        failure_class=rejection_class,
        taxonomy_codes=taxonomy_codes,
        metrics=default_metrics(
            selected_variant_count=1 if selected_variant_id else 0,
            variant_count=len(normalized["variants"]),
        ),
    )
    return event


def event_from_patch_result(result: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_creative_code_patch_result(result)
    taxonomy_codes = _taxonomy_from_failure(normalized["failure_class"])
    rejection_class = taxonomy_codes[0] if taxonomy_codes else None
    patch_summary = normalized["patch_summary"]
    runner_summary = normalized["runner_summary"]
    event: dict[str, Any] = build_creative_code_telemetry_event(
        lane_stage="patch_evaluation",
        source_artifact_type="creative_code_patch_result",
        source_artifact_id=normalized["result_id"],
        source_fingerprint=_source_fingerprint(normalized),
        candidate_ids=_candidate_ids(
            source_bundle_id=normalized["source_bundle_id"],
            selected_variant_id=normalized["selected_variant_id"],
            request_id=normalized["request_id"],
            result_id=normalized["result_id"],
        ),
        status=normalized["status"],
        rejection_class=rejection_class,
        failure_class=rejection_class,
        taxonomy_codes=taxonomy_codes,
        metrics=default_metrics(
            changed_files=len(normalized["changed_paths"]),
            diff_lines=patch_summary["diff_lines"],
            generation_attempts=runner_summary["attempts"],
            oracle_commands_configured=runner_summary["oracle_commands_configured"],
            oracle_commands_executed=runner_summary["oracle_commands_executed"],
            patch_bytes=patch_summary["patch_bytes"],
        ),
    )
    return event


def event_from_promotion_plan(plan: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_creative_code_pr_promotion_plan(plan)
    event: dict[str, Any] = build_creative_code_telemetry_event(
        lane_stage="promotion_plan",
        source_artifact_type="creative_code_pr_promotion_plan",
        source_artifact_id=normalized["promotion_id"],
        source_fingerprint=_source_fingerprint(normalized),
        candidate_ids=_candidate_ids(
            source_bundle_id=normalized["source_bundle_id"],
            selected_variant_id=normalized["selected_variant_id"],
            request_id=normalized["source_request_id"],
            result_id=normalized["source_result_id"],
            promotion_id=normalized["promotion_id"],
        ),
        status="accepted",
        metrics=default_metrics(
            changed_files=len(normalized["changed_paths"]),
            promotion_plan_count=1,
        ),
    )
    return event


def event_from_promotion_validation(validation: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_creative_code_pr_promotion_validation(validation)
    oracle_evidence = normalized["oracle_evidence"]
    event: dict[str, Any] = build_creative_code_telemetry_event(
        lane_stage="promotion_validation",
        source_artifact_type="creative_code_pr_promotion_validation",
        source_artifact_id=normalized["promotion_id"],
        source_fingerprint=_source_fingerprint(normalized),
        candidate_ids=_candidate_ids(promotion_id=normalized["promotion_id"]),
        status="accepted",
        metrics=default_metrics(
            oracle_commands_configured=oracle_evidence["oracle_commands_configured"],
            oracle_commands_executed=oracle_evidence["oracle_commands_executed"],
            promotion_validation_passed=1,
        ),
    )
    return event


def event_from_promotion_approval(approval: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_creative_code_pr_promotion_approval(approval)
    event: dict[str, Any] = build_creative_code_telemetry_event(
        lane_stage="promotion_approval",
        source_artifact_type="creative_code_pr_promotion_approval",
        source_artifact_id=normalized["approval_id"],
        source_fingerprint=_source_fingerprint(normalized),
        candidate_ids=_candidate_ids(promotion_id=normalized["promotion_id"]),
        status="accepted",
        metrics=default_metrics(promotion_approval_count=1),
    )
    return event


def _promotion_receipt_failure_code(receipt: dict[str, Any]) -> str | None:
    if receipt["pull_request_state"] == "open":
        return None
    partial_failure = str(receipt["partial_failure"] or "").lower()
    if receipt["pull_request_url"] and (
        "readback" in partial_failure or "verification" in partial_failure
    ):
        return "pr_readback_failed"
    return "github_transport_failed"


def event_from_promotion_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_creative_code_pr_promotion_receipt(receipt)
    failure_code = _promotion_receipt_failure_code(normalized)
    status = "opened" if failure_code is None else "blocked"
    taxonomy_codes = [] if failure_code is None else [failure_code]
    event: dict[str, Any] = build_creative_code_telemetry_event(
        lane_stage="pr_open",
        source_artifact_type="creative_code_pr_promotion_receipt",
        source_artifact_id=normalized["receipt_id"],
        source_fingerprint=_source_fingerprint(normalized),
        candidate_ids=_candidate_ids(
            result_id=normalized["source_result_id"],
            promotion_id=normalized["promotion_id"],
        ),
        status=status,
        rejection_class=taxonomy_codes[0] if taxonomy_codes else None,
        failure_class=taxonomy_codes[0] if taxonomy_codes else None,
        taxonomy_codes=taxonomy_codes,
        metrics=default_metrics(pull_requests_opened=1 if status == "opened" else 0),
    )
    return event


def safe_read_error_event(path: Path) -> dict[str, Any]:
    path_fingerprint = _artifact_locator_fingerprint(path)
    source_id = path_fingerprint.removeprefix("sha256:")[:24]
    event: dict[str, Any] = build_creative_code_telemetry_event(
        lane_stage="artifact_read_error",
        source_artifact_type="creative_code_artifact_read_error",
        source_artifact_id=f"read-error:{source_id}",
        source_fingerprint=path_fingerprint,
        candidate_ids=_candidate_ids(),
        status="blocked",
        rejection_class="malformed_artifact",
        failure_class="malformed_artifact",
        taxonomy_codes=["malformed_artifact"],
        metrics=default_metrics(),
    )
    return event


def _load_spec_event(path: Path) -> dict[str, Any] | None:
    try:
        payload = read_creative_code_specification_bundle(path)
        return event_from_specification_bundle(payload)
    except CreativeCodeSpecificationError:
        return safe_read_error_event(path)
    except CreativeCodeTelemetryContractError:
        raise


def _load_patch_event(path: Path) -> dict[str, Any] | None:
    if path.name != "result.json":
        return None
    try:
        return event_from_patch_result(read_creative_code_patch_result(str(path)))
    except CreativeCodePatchContractError:
        return safe_read_error_event(path)


def _load_promotion_event(path: Path) -> dict[str, Any] | None:
    loaders = {
        PLAN_FILE: (read_promotion_json_object, event_from_promotion_plan),
        VALIDATION_FILE: (read_promotion_json_object, event_from_promotion_validation),
        APPROVAL_FILE: (read_promotion_json_object, event_from_promotion_approval),
        RECEIPT_FILE: (read_promotion_json_object, event_from_promotion_receipt),
    }
    loader = loaders.get(path.name)
    if loader is None:
        return None
    reader, builder = loader
    try:
        return builder(reader(path))
    except CreativeCodePRPromotionContractError:
        return safe_read_error_event(path)


def _load_terminal_event(
    path: Path,
    *,
    terminal_root: Path,
) -> dict[str, Any] | None:
    if path.name != "terminal_outcome.json":
        return None
    try:
        outcome = validate_creative_code_terminal_outcome(read_terminal_json_object(path))
        canonical_path = terminal_root / outcome["outcome_id"] / "terminal_outcome.json"
        if path != canonical_path:
            raise CreativeCodeTelemetryError(
                "terminal outcome must use its canonical outcome directory."
            )
        event: dict[str, Any] = build_creative_code_terminal_telemetry_event(outcome)
        return event
    except CreativeCodeTerminalOutcomeError as exc:
        raise CreativeCodeTelemetryError("terminal outcome validation failed.") from exc


def collect_events(
    *,
    spec_runs_dir: Path = SPEC_RUNS_DIR,
    patch_runs_dir: Path = PATCH_RUNS_DIR,
    promotions_dir: Path = PROMOTIONS_DIR,
    terminal_outcomes_dir: Path | None = None,
    strict: bool = False,
) -> list[dict[str, Any]]:
    roots = _resolve_optional_dir(
        spec_runs_dir,
        allowed_root=CREATIVE_CODE_ROOT,
        label="spec runs directory",
    )
    patch_root = _resolve_optional_dir(
        patch_runs_dir,
        allowed_root=CREATIVE_CODE_ROOT,
        label="patch runs directory",
    )
    promotion_root = _resolve_optional_dir(
        promotions_dir,
        allowed_root=CREATIVE_CODE_ROOT,
        label="promotions directory",
    )
    terminal_root = (
        _resolve_optional_dir(
            terminal_outcomes_dir,
            allowed_root=CREATIVE_CODE_ROOT,
            label="terminal outcomes directory",
        )
        if terminal_outcomes_dir is not None
        else None
    )
    if terminal_root is not None:
        _require_disjoint_mixed_input_roots((roots, patch_root, promotion_root, terminal_root))
    events: list[dict[str, Any]] = []

    for path in _iter_json_files(roots):
        event = _load_spec_event(path)
        if event is not None:
            events.append(event)
        elif strict:
            events.append(safe_read_error_event(path))

    for path in _iter_json_files(patch_root):
        event = _load_patch_event(path)
        if event is not None:
            events.append(event)

    for path in _iter_json_files(promotion_root):
        event = _load_promotion_event(path)
        if event is not None:
            events.append(event)

    if terminal_root is not None:
        for path in _iter_json_files(terminal_root):
            event = _load_terminal_event(path, terminal_root=terminal_root)
            if event is not None:
                events.append(event)

    normalized = [validate_creative_code_telemetry_event_any(event) for event in events]
    return sorted(normalized, key=lambda row: row["event_id"])


def _write_text_atomic(path: Path, content: str) -> None:
    reject_unsafe_telemetry_value(content, label=path.name)
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


def _write_json_atomic(path: Path, payload: Any) -> None:
    _write_text_atomic(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def write_events_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    lines = [
        json.dumps(event, ensure_ascii=False, sort_keys=True)
        for event in sorted(events, key=lambda row: row["event_id"])
    ]
    _write_text_atomic(path, "\n".join(lines) + ("\n" if lines else ""))


def render_summary(rollup: dict[str, Any]) -> str:
    validated = validate_creative_code_telemetry_rollup_any(rollup)
    funnel = validated["funnel"]
    lines = [
        "# Creative-Code Telemetry Summary",
        "",
        "Local-only advisory telemetry. Not merge-readiness evidence.",
        "",
        f"- Events: {validated['event_count']}",
        f"- Specification bundles: {funnel['specification_bundles']}",
        f"- Patch results accepted: {funnel['patch_results_accepted']}",
        f"- Patch results rejected: {funnel['patch_results_rejected']}",
        f"- Pull requests opened: {funnel['pull_requests_opened']}",
    ]
    if validated["schema_version"] == "2.0":
        terminal = validated["terminal"]
        lines.extend(
            [
                f"- Terminal outcomes: {terminal['outcome_count']}",
                f"- Merged observations: {terminal['merged']}",
                f"- Closed-unmerged observations: {terminal['closed_unmerged']}",
            ]
        )
    lines.extend(["", "Caveats:"])
    lines.extend(f"- {caveat}" for caveat in validated["caveats"])
    return "\n".join(lines) + "\n"


def collect_and_write(
    *,
    spec_runs_dir: Path = SPEC_RUNS_DIR,
    patch_runs_dir: Path = PATCH_RUNS_DIR,
    promotions_dir: Path = PROMOTIONS_DIR,
    terminal_outcomes_dir: Path | None = None,
    output_dir: Path = TELEMETRY_ROOT,
    strict: bool = False,
) -> dict[str, Any]:
    events = collect_events(
        spec_runs_dir=spec_runs_dir,
        patch_runs_dir=patch_runs_dir,
        promotions_dir=promotions_dir,
        terminal_outcomes_dir=terminal_outcomes_dir,
        strict=strict,
    )
    input_roots = [
        _safe_root_label(spec_runs_dir),
        _safe_root_label(patch_runs_dir),
        _safe_root_label(promotions_dir),
    ]
    rollup: dict[str, Any]
    if terminal_outcomes_dir is None:
        rollup = build_creative_code_telemetry_rollup(
            events,
            input_roots=input_roots,
        )
    else:
        input_roots.append(_safe_root_label(terminal_outcomes_dir))
        rollup = build_creative_code_telemetry_rollup_v2(
            events,
            input_roots=input_roots,
        )
    taxonomy = build_creative_code_rejection_taxonomy()
    output = _resolve_output_dir(output_dir)
    write_events_jsonl(output / EVENTS_FILE, events)
    _write_json_atomic(output / ROLLUP_FILE, rollup)
    _write_json_atomic(output / TAXONOMY_FILE, validate_creative_code_rejection_taxonomy(taxonomy))
    _write_text_atomic(output / SUMMARY_FILE, render_summary(rollup))
    return rollup


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect local PR-4 creative-code telemetry sidecars."
    )
    parser.add_argument("--spec-runs-dir", default=str(SPEC_RUNS_DIR))
    parser.add_argument("--patch-runs-dir", default=str(PATCH_RUNS_DIR))
    parser.add_argument("--promotions-dir", default=str(PROMOTIONS_DIR))
    parser.add_argument("--terminal-outcomes-dir")
    parser.add_argument("--output-dir", default=str(TELEMETRY_ROOT))
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        collect_and_write(
            spec_runs_dir=Path(args.spec_runs_dir),
            patch_runs_dir=Path(args.patch_runs_dir),
            promotions_dir=Path(args.promotions_dir),
            terminal_outcomes_dir=(
                Path(args.terminal_outcomes_dir) if args.terminal_outcomes_dir else None
            ),
            output_dir=Path(args.output_dir),
            strict=args.strict,
        )
    except (CreativeCodeTelemetryError, CreativeCodeTelemetryContractError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(SUCCESS_OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
