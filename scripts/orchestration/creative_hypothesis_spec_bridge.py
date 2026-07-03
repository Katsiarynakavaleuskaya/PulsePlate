#!/usr/bin/env python3
"""Local bridge from approved creative hypotheses to PR-1 specification inputs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_spec_pipeline
from scripts.orchestration.creative_code_contract import (
    CreativeCodeContractError,
    read_creative_code_candidate_packet,
    validate_creative_code_candidate_packet,
)
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    BLOCKED_STATUS,
    BRIDGE_SUCCESS_STATUS,
    PREPARED_STATUS,
    PREPARE_FILENAMES,
    CreativeHypothesisSpecBridgeError,
    build_creative_hypothesis_spec_bridge_bundle,
    mark_bridge_prepared,
    update_bridge_metrics_for_prepare,
    validate_bridge_metrics,
    validate_creative_hypothesis_specification_bridge,
)
from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    ExperimentRunnerCreativeContextContractError,
    read_json_object,
    reject_unsafe_creative_context_value,
)

SPEC_BRIDGE_ROOT = creative_code_spec_pipeline.ARTIFACT_ROOT / "spec_bridge"
CREATIVE_CONTEXT_ROOT = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "creative_context"
)
BRIDGE_FILENAME = "creative_hypothesis_specification_bridge.json"
CANDIDATE_FILENAME = "creative_code_candidate_packet.json"
METRICS_FILENAME = "bridge_metrics.json"
SUCCESS_BUILD_OUTPUT = "PASS: creative-hypothesis specification bridge candidate built"
SUCCESS_PREPARE_OUTPUT = "PASS: creative-hypothesis specification bridge prepare complete"
SUCCESS_BUILD_PREPARE_OUTPUT = (
    "PASS: creative-hypothesis specification bridge candidate built and prepared"
)
SUCCESS_VALIDATE_OUTPUT = "PASS: creative-hypothesis specification bridge artifacts valid"


class CreativeHypothesisSpecBridgeCliError(ValueError):
    """Raised when bridge CLI file I/O cannot safely complete."""


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
            raise CreativeHypothesisSpecBridgeCliError(f"{label} must not traverse symlinks.")


def _ensure_spec_bridge_root() -> Path:
    _reject_symlink_components(SPEC_BRIDGE_ROOT, label="spec bridge root")
    SPEC_BRIDGE_ROOT.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(SPEC_BRIDGE_ROOT, label="spec bridge root")
    root = Path(SPEC_BRIDGE_ROOT.resolve(strict=True))
    if not root.is_dir():
        raise CreativeHypothesisSpecBridgeCliError("spec bridge root must be a directory.")
    return root


def _resolve_output_dir(
    raw_output_dir: Path | None,
    *,
    bridge_id: str,
    create: bool,
) -> Path:
    root = _ensure_spec_bridge_root()
    if raw_output_dir is None:
        candidate = root / bridge_id
    elif raw_output_dir.is_absolute():
        candidate = raw_output_dir
    elif raw_output_dir.parts[:4] == (
        "artifacts",
        "orchestration",
        "creative_code",
        "spec_bridge",
    ):
        candidate = REPO_ROOT / raw_output_dir
    else:
        candidate = root / raw_output_dir
    _reject_symlink_components(candidate, label="spec bridge output directory")
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_candidate, root):
        raise CreativeHypothesisSpecBridgeCliError(
            "output directory must stay under creative-code spec_bridge artifacts."
        )
    if candidate.name != bridge_id:
        raise CreativeHypothesisSpecBridgeCliError(
            "output directory leaf must equal the derived bridge id."
        )
    if create:
        candidate.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(candidate, label="spec bridge output directory")
    resolved = candidate.resolve(strict=True)
    if not _is_relative_to(resolved, root) or not resolved.is_dir():
        raise CreativeHypothesisSpecBridgeCliError(
            "output directory must stay under creative-code spec_bridge artifacts."
        )
    return resolved


def _resolve_bridge_file(path: Path) -> Path:
    candidate = path if path.is_absolute() else REPO_ROOT / path
    _reject_symlink_components(candidate, label="bridge input")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeHypothesisSpecBridgeCliError("bridge input must exist.") from exc
    if not _is_relative_to(resolved, REPO_ROOT.resolve()):
        raise CreativeHypothesisSpecBridgeCliError("bridge input must stay inside the repository.")
    if not resolved.is_file() or resolved.suffix != ".json":
        raise CreativeHypothesisSpecBridgeCliError("bridge input must be a JSON file.")
    return resolved


def _resolve_creative_context_input(raw_path: Path, *, expected_filename: str) -> Path:
    candidate = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
    _reject_symlink_components(candidate, label="creative context bridge input")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeHypothesisSpecBridgeCliError(
            "creative context bridge input must exist."
        ) from exc
    repo_root = REPO_ROOT.resolve()
    if not _is_relative_to(resolved, repo_root):
        raise CreativeHypothesisSpecBridgeCliError(
            "creative context bridge input must stay inside the repository."
        )
    creative_context_root = CREATIVE_CONTEXT_ROOT.resolve(strict=False)
    if not _is_relative_to(resolved, creative_context_root):
        raise CreativeHypothesisSpecBridgeCliError(
            "creative context bridge input must stay under creative_context artifacts."
        )
    if resolved.name != expected_filename:
        raise CreativeHypothesisSpecBridgeCliError(
            f"creative context bridge input filename must be {expected_filename}."
        )
    if not resolved.is_file() or resolved.suffix != ".json":
        raise CreativeHypothesisSpecBridgeCliError(
            "creative context bridge input must be a JSON file."
        )
    return resolved


def _repo_ref_to_file(ref: str) -> Path:
    candidate = REPO_ROOT / ref
    _reject_symlink_components(candidate, label="bridge artifact ref")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise CreativeHypothesisSpecBridgeCliError("bridge artifact ref must exist.") from exc
    if not _is_relative_to(resolved, REPO_ROOT.resolve()):
        raise CreativeHypothesisSpecBridgeCliError(
            "bridge artifact ref must stay inside the repository."
        )
    if not resolved.is_file():
        raise CreativeHypothesisSpecBridgeCliError("bridge artifact ref must be a file.")
    return resolved


def _repo_ref_to_dir(ref: str) -> Path:
    candidate = REPO_ROOT / ref
    _reject_symlink_components(candidate, label="bridge artifact directory ref")
    resolved = candidate.resolve(strict=False)
    if not _is_relative_to(resolved, REPO_ROOT.resolve()):
        raise CreativeHypothesisSpecBridgeCliError(
            "bridge artifact directory ref must stay inside the repository."
        )
    return candidate


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    reject_unsafe_creative_context_value(dict(payload), label="spec_bridge_output")
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(payload, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
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


def _write_bridge_outputs(
    output_dir: Path,
    *,
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> None:
    _write_json_atomic(output_dir / CANDIDATE_FILENAME, candidate)
    _write_json_atomic(output_dir / BRIDGE_FILENAME, bridge)
    _write_json_atomic(output_dir / METRICS_FILENAME, metrics)


def _read_bridge_with_dir(path: Path) -> tuple[dict[str, Any], Path]:
    bridge_path = _resolve_bridge_file(path)
    bridge = validate_creative_hypothesis_specification_bridge(read_json_object(bridge_path))
    output_dir = bridge_path.parent
    derived_dir = _resolve_output_dir(output_dir, bridge_id=str(bridge["bridge_id"]), create=False)
    if derived_dir != output_dir.resolve(strict=True):
        raise CreativeHypothesisSpecBridgeCliError("bridge path does not match derived output dir.")
    return bridge, derived_dir


def _count_prepare_files(run_dir: Path) -> int:
    return sum(1 for name in PREPARE_FILENAMES if (run_dir / name).is_file())


def _pending_skeptic_review_count(run_dir: Path) -> int:
    reviews_path = run_dir / "skeptic_reviews.json"
    if not reviews_path.is_file():
        return 0
    payload = json.loads(reviews_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise CreativeHypothesisSpecBridgeCliError("skeptic_reviews.json must be an array.")
    return sum(
        1
        for row in payload
        if isinstance(row, dict)
        and row.get("decision") != "pass"
        and "skeptic_review_required" in row.get("blockers", [])
    )


def _prepare_from_bridge(
    *,
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
    metrics: Mapping[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    candidate_ref = str(cast_mapping(bridge["candidate_packet"])["candidate_packet_ref"])
    run_dir_ref = str(cast_mapping(bridge["spec_prepare"])["run_dir_ref"])
    candidate_path = _repo_ref_to_file(candidate_ref)
    run_dir = _repo_ref_to_dir(run_dir_ref)
    try:
        _assert_candidate_matches_bridge(bridge=bridge, candidate=candidate)
    except CreativeHypothesisSpecBridgeCliError as exc:
        blocked_metrics = update_bridge_metrics_for_prepare(
            metrics=metrics,
            bridge=bridge,
            candidate=candidate,
            status=BLOCKED_STATUS,
            blocked_reason="fingerprint_mismatch",
            prepare_files_written=_count_prepare_files(run_dir),
            pending_skeptic_review_count=_pending_skeptic_review_count(run_dir),
        )
        _write_json_atomic(output_dir / METRICS_FILENAME, blocked_metrics)
        raise exc
    try:
        creative_code_spec_pipeline.prepare(candidate_path, run_dir)
    except creative_code_spec_pipeline.CreativeCodeSpecPipelineError as exc:
        blocked_metrics = update_bridge_metrics_for_prepare(
            metrics=metrics,
            bridge=bridge,
            candidate=candidate,
            status=BLOCKED_STATUS,
            blocked_reason="spec_prepare_failed",
            prepare_files_written=_count_prepare_files(run_dir),
            pending_skeptic_review_count=_pending_skeptic_review_count(run_dir),
        )
        _write_json_atomic(output_dir / METRICS_FILENAME, blocked_metrics)
        raise CreativeHypothesisSpecBridgeCliError(f"spec_prepare_failed: {exc}") from exc
    prepared_bridge = mark_bridge_prepared(bridge)
    prepared_metrics = update_bridge_metrics_for_prepare(
        metrics=metrics,
        bridge=prepared_bridge,
        candidate=candidate,
        status=PREPARED_STATUS,
        blocked_reason=None,
        prepare_files_written=_count_prepare_files(run_dir),
        pending_skeptic_review_count=_pending_skeptic_review_count(run_dir),
    )
    _write_json_atomic(output_dir / BRIDGE_FILENAME, prepared_bridge)
    _write_json_atomic(output_dir / METRICS_FILENAME, prepared_metrics)
    return {"bridge": prepared_bridge, "metrics": prepared_metrics}


def _assert_candidate_matches_bridge(
    *,
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> None:
    candidate_ref = cast_mapping(bridge["candidate_packet"])
    normalized_candidate = validate_creative_code_candidate_packet(dict(candidate))
    if normalized_candidate["candidate_id"] != candidate_ref["candidate_id"]:
        raise CreativeHypothesisSpecBridgeCliError(
            "fingerprint_mismatch: candidate packet id does not match bridge."
        )
    observed_fingerprint = fingerprint_payload(dict(normalized_candidate))
    if observed_fingerprint != candidate_ref["candidate_fingerprint"]:
        raise CreativeHypothesisSpecBridgeCliError(
            "fingerprint_mismatch: candidate packet fingerprint does not match bridge."
        )


def _assert_metrics_matches_bridge_and_candidate(
    *,
    metrics: Mapping[str, Any],
    bridge: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> None:
    normalized_metrics = validate_bridge_metrics(metrics)
    normalized_candidate = validate_creative_code_candidate_packet(dict(candidate))
    source = cast_mapping(normalized_metrics["source"])
    if normalized_metrics["bridge_id"] != bridge["bridge_id"]:
        raise CreativeHypothesisSpecBridgeCliError(
            "fingerprint_mismatch: metrics bridge id does not match bridge."
        )
    if normalized_metrics["candidate_id"] != normalized_candidate["candidate_id"]:
        raise CreativeHypothesisSpecBridgeCliError(
            "fingerprint_mismatch: metrics candidate id does not match candidate."
        )
    selected_hypothesis = cast_mapping(bridge["selected_hypothesis"])
    if normalized_metrics["selected_hypothesis_id"] != selected_hypothesis["hypothesis_id"]:
        raise CreativeHypothesisSpecBridgeCliError(
            "fingerprint_mismatch: metrics selected hypothesis id does not match bridge."
        )
    if source["candidate_fingerprint"] != fingerprint_payload(dict(normalized_candidate)):
        raise CreativeHypothesisSpecBridgeCliError(
            "fingerprint_mismatch: metrics candidate fingerprint does not match candidate."
        )
    bridge_source = cast_mapping(bridge["source"])
    for key in (
        "context_map_id",
        "context_map_fingerprint",
        "hypothesis_packet_id",
        "hypothesis_packet_fingerprint",
        "coordinator_dispatch_id",
        "coordinator_dispatch_fingerprint",
        "approval_id",
        "approval_fingerprint",
    ):
        if source[key] != bridge_source[key]:
            raise CreativeHypothesisSpecBridgeCliError(
                f"fingerprint_mismatch: metrics {key} does not match bridge."
            )
    counts = cast_mapping(normalized_metrics["counts"])
    expected_counts = {
        "approved_target_count": len(selected_hypothesis["approved_target_surfaces"]),
        "candidate_target_count": len(normalized_candidate["target_surface"]),
        "immutable_oracle_count": len(normalized_candidate["immutable_oracles"]),
        "variant_count": normalized_candidate["variant_count"],
    }
    for key, expected in expected_counts.items():
        if counts[key] != expected:
            raise CreativeHypothesisSpecBridgeCliError(
                f"fingerprint_mismatch: metrics {key} does not match bridge/candidate."
            )


def cast_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CreativeHypothesisSpecBridgeCliError("expected JSON object.")
    return value


def _build_bundle_from_args(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    context_map = _resolve_creative_context_input(
        args.context_map,
        expected_filename="context_map.json",
    )
    hypothesis_packet = _resolve_creative_context_input(
        args.hypothesis_packet,
        expected_filename="hypothesis_packet.json",
    )
    coordinator_dispatch = _resolve_creative_context_input(
        args.coordinator_dispatch,
        expected_filename="coordinator_dispatch.json",
    )
    approval = _resolve_creative_context_input(args.approval, expected_filename="approval.json")
    return cast(
        dict[str, dict[str, Any]],
        build_creative_hypothesis_spec_bridge_bundle(
            context_map=read_json_object(context_map),
            hypothesis_packet=read_json_object(hypothesis_packet),
            coordinator_dispatch=read_json_object(coordinator_dispatch),
            approval=read_json_object(approval),
            variant_count=args.variant_count,
        ),
    )


def _cmd_build_candidate(args: argparse.Namespace) -> int:
    bundle = _build_bundle_from_args(args)
    bridge = bundle["bridge"]
    output_dir = _resolve_output_dir(
        args.output_dir, bridge_id=str(bridge["bridge_id"]), create=True
    )
    _write_bridge_outputs(
        output_dir,
        bridge=bridge,
        candidate=bundle["candidate"],
        metrics=bundle["metrics"],
    )
    print(SUCCESS_BUILD_OUTPUT)
    return 0


def _cmd_prepare_specification(args: argparse.Namespace) -> int:
    bridge, output_dir = _read_bridge_with_dir(args.bridge)
    candidate_path = _resolve_bridge_file(output_dir / CANDIDATE_FILENAME)
    candidate = read_creative_code_candidate_packet(candidate_path)
    metrics_path = _resolve_bridge_file(output_dir / METRICS_FILENAME)
    metrics = validate_bridge_metrics(read_json_object(metrics_path))
    _prepare_from_bridge(
        bridge=bridge,
        candidate=candidate,
        metrics=metrics,
        output_dir=output_dir,
    )
    print(SUCCESS_PREPARE_OUTPUT)
    return 0


def _cmd_build_and_prepare(args: argparse.Namespace) -> int:
    bundle = _build_bundle_from_args(args)
    bridge = bundle["bridge"]
    output_dir = _resolve_output_dir(
        args.output_dir, bridge_id=str(bridge["bridge_id"]), create=True
    )
    _write_bridge_outputs(
        output_dir,
        bridge=bridge,
        candidate=bundle["candidate"],
        metrics=bundle["metrics"],
    )
    _prepare_from_bridge(
        bridge=bridge,
        candidate=bundle["candidate"],
        metrics=bundle["metrics"],
        output_dir=output_dir,
    )
    print(SUCCESS_BUILD_PREPARE_OUTPUT)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    bridge, output_dir = _read_bridge_with_dir(args.bridge)
    if args.candidate:
        candidate_path = _resolve_bridge_file(args.candidate)
        candidate = validate_creative_code_candidate_packet(
            read_creative_code_candidate_packet(candidate_path)
        )
    else:
        candidate_path = _repo_ref_to_file(
            str(cast_mapping(bridge["candidate_packet"])["candidate_packet_ref"])
        )
        candidate = validate_creative_code_candidate_packet(
            read_creative_code_candidate_packet(candidate_path)
        )
    _assert_candidate_matches_bridge(bridge=bridge, candidate=candidate)
    if args.metrics:
        metrics_path = _resolve_bridge_file(args.metrics)
        metrics = validate_bridge_metrics(read_json_object(metrics_path))
    else:
        metrics_path = _resolve_bridge_file(output_dir / METRICS_FILENAME)
        metrics = validate_bridge_metrics(read_json_object(metrics_path))
    _assert_metrics_matches_bridge_and_candidate(
        metrics=metrics,
        bridge=bridge,
        candidate=candidate,
    )
    print(SUCCESS_VALIDATE_OUTPUT)
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_build_inputs(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--context-map", type=Path, required=True)
        subparser.add_argument("--hypothesis-packet", type=Path, required=True)
        subparser.add_argument("--coordinator-dispatch", type=Path, required=True)
        subparser.add_argument("--approval", type=Path, required=True)
        subparser.add_argument(
            "--variant-count",
            type=int,
            choices=sorted({3, 4, 5}),
            required=True,
        )
        subparser.add_argument("--output-dir", type=Path)

    build_parser = subparsers.add_parser("build-candidate")
    add_build_inputs(build_parser)
    build_parser.set_defaults(func=_cmd_build_candidate)

    prepare_parser = subparsers.add_parser("prepare-specification")
    prepare_parser.add_argument("--bridge", type=Path, required=True)
    prepare_parser.set_defaults(func=_cmd_prepare_specification)

    build_prepare_parser = subparsers.add_parser("build-and-prepare")
    add_build_inputs(build_prepare_parser)
    build_prepare_parser.set_defaults(func=_cmd_build_and_prepare)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--bridge", type=Path, required=True)
    validate_parser.add_argument("--candidate", type=Path)
    validate_parser.add_argument("--metrics", type=Path)
    validate_parser.set_defaults(func=_cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (
        CreativeCodeContractError,
        CreativeHypothesisSpecBridgeCliError,
        CreativeHypothesisSpecBridgeError,
        ExperimentRunnerCreativeContextContractError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
