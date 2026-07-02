#!/usr/bin/env python3
"""Local Experiment Runner PR creative-context CLI.

The CLI emits sanitized local artifacts only. It does not call providers, read
raw PR/review bodies, dispatch workflows, create branches, open PRs, edit fixed
mapping, resolve threads, or claim merge readiness.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.experiment_runner_pr_creative_context_contract import (
    AGENT_ROUTING_TYPE,
    APPROVAL_TYPE,
    COORDINATOR_DISPATCH_TYPE,
    CONTEXT_MAP_TYPE,
    CONSUMPTION_SUMMARY_TYPE,
    HYPOTHESIS_PACKET_TYPE,
    ORACLE_ATTACHMENT_TYPE,
    OPERATOR_MODEL_INTAKE_TYPE,
    ExperimentRunnerCreativeContextContractError,
    build_agent_consumption_summary,
    build_creative_hypothesis_coordinator_dispatch,
    build_creative_hypothesis_agent_routing,
    build_creative_hypothesis_packet,
    build_creative_hypothesis_packet_from_model_intake,
    build_creative_protocol_context_map,
    build_experiment_runner_pr_oracle_attachment,
    read_json_object,
    reject_unsafe_creative_context_value,
    validate_artifact_by_type,
    validate_creative_hypothesis_agent_routing,
    validate_creative_hypothesis_packet,
    validate_creative_protocol_context_map,
    validate_experiment_runner_pr_oracle_attachment,
)

CREATIVE_CONTEXT_ROOT = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "creative_context"
)
ALLOWED_OUTPUT_FILENAMES = frozenset(
    {
        "context_map.json",
        "hypothesis_packet.json",
        "agent_routing.json",
        "agent_consumption_summary.json",
        "coordinator_dispatch.json",
        "oracle_attachment.json",
        "approval.json",
        "creative_context.json",
    }
)
SUCCESS_PREPARE_OUTPUT = "PASS: experiment-runner creative-context artifacts prepared"


class ExperimentRunnerCreativeContextCliError(ValueError):
    """Raised when the CLI cannot safely complete."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
            raise ExperimentRunnerCreativeContextCliError(f"{label} must not traverse symlinks.")


def _ensure_creative_context_root() -> Path:
    _reject_symlink_components(CREATIVE_CONTEXT_ROOT, label="creative context root")
    CREATIVE_CONTEXT_ROOT.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(CREATIVE_CONTEXT_ROOT, label="creative context root")
    root = CREATIVE_CONTEXT_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise ExperimentRunnerCreativeContextCliError("creative context root must be a directory.")
    return root


def _resolve_output_dir(raw_output_dir: Path | None, *, create: bool) -> Path:
    root = _ensure_creative_context_root()
    if raw_output_dir is None:
        return root
    if raw_output_dir.is_absolute():
        candidate = raw_output_dir
    elif raw_output_dir.parts[:4] == (
        "artifacts",
        "orchestration",
        "experiments",
        "creative_context",
    ):
        candidate = REPO_ROOT / raw_output_dir
    else:
        candidate = root / raw_output_dir
    _reject_symlink_components(candidate, label="creative context output directory")
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_candidate, root):
        raise ExperimentRunnerCreativeContextCliError(
            "output directory must stay under creative context artifacts."
        )
    if create:
        candidate.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(candidate, label="creative context output directory")
    resolved = candidate.resolve(strict=True)
    if not _is_relative_to(resolved, root) or not resolved.is_dir():
        raise ExperimentRunnerCreativeContextCliError(
            "output directory must stay under creative context artifacts."
        )
    return resolved


def _resolve_json_output(raw_path: Path) -> Path:
    root = _ensure_creative_context_root()
    if raw_path.name not in ALLOWED_OUTPUT_FILENAMES:
        allowed = ", ".join(sorted(ALLOWED_OUTPUT_FILENAMES))
        raise ExperimentRunnerCreativeContextCliError(f"output filename must be one of: {allowed}.")
    if raw_path.is_absolute():
        candidate = raw_path
    elif raw_path.parts[:4] == ("artifacts", "orchestration", "experiments", "creative_context"):
        candidate = REPO_ROOT / raw_path
    else:
        candidate = root / raw_path
    _reject_symlink_components(candidate.parent, label="creative context output parent")
    parent = candidate.parent.resolve(strict=False)
    if not _is_relative_to(parent, root):
        raise ExperimentRunnerCreativeContextCliError(
            "output path must stay under creative context artifacts."
        )
    candidate.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(candidate.parent, label="creative context output parent")
    resolved_parent = candidate.parent.resolve(strict=True)
    if not _is_relative_to(resolved_parent, root):
        raise ExperimentRunnerCreativeContextCliError(
            "output path must stay under creative context artifacts."
        )
    if candidate.exists() or candidate.is_symlink():
        if candidate.is_symlink():
            raise ExperimentRunnerCreativeContextCliError("output file must not be a symlink.")
        if not candidate.is_file():
            raise ExperimentRunnerCreativeContextCliError("output path must be a regular file.")
    return resolved_parent / candidate.name


def _write_json(path: Path | None, payload: Mapping[str, Any]) -> None:
    reject_unsafe_creative_context_value(dict(payload), label="output")
    if path is None:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    output = _resolve_json_output(path)
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


def _artifact_subdir(context_map: Mapping[str, Any]) -> Path:
    context_id = str(context_map["context_id"])
    leaf = context_id.rsplit(":", maxsplit=1)[-1]
    return _resolve_output_dir(Path(leaf), create=True)


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _common_context_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "changed_paths": args.changed_path,
        "repository": args.repository,
        "pr_number": args.pr_number,
        "base_ref": args.base_ref,
        "base_sha": args.base_sha,
        "head_sha": args.head_sha,
        "task_packet_id": args.task_packet_id,
        "generated_at_utc": args.generated_at_utc or _utc_now(),
        "nearby_repo_refs": args.nearby_repo_ref,
        "test_refs": args.test_ref,
        "contract_refs": args.contract_ref,
        "backlog_refs": args.backlog_ref,
        "review_source_refs": args.review_source_ref,
        "capability_state_ref": args.capability_state_ref,
        "philosophical_context_refs": args.philosophical_context_ref,
        "cross_domain_candidate_refs": args.cross_domain_candidate_ref,
        "label_enabled": args.label_enabled,
        "marker_enabled": args.marker_enabled,
        "manual_enabled": args.manual_enabled,
        "sealed_codex_security_scan_ref": args.sealed_codex_security_scan_ref,
        "sealed_codex_security_scan_fingerprint": args.sealed_codex_security_scan_fingerprint,
        "security_relevant_diff_changed": args.security_relevant_diff_changed,
    }


def _cmd_collect_context(args: argparse.Namespace) -> int:
    context_map = build_creative_protocol_context_map(**_common_context_kwargs(args))
    _write_json(Path(args.output) if args.output else None, context_map)
    return 0


def _cmd_generate_hypotheses(args: argparse.Namespace) -> int:
    context_map = validate_creative_protocol_context_map(read_json_object(args.context_map))
    packet = build_creative_hypothesis_packet(
        context_map,
        hypothesis_count=args.hypothesis_count,
    )
    _write_json(Path(args.output) if args.output else None, packet)
    return 0


def _cmd_route_agents(args: argparse.Namespace) -> int:
    packet = validate_creative_hypothesis_packet(read_json_object(args.hypothesis_packet))
    routing = build_creative_hypothesis_agent_routing(packet)
    _write_json(Path(args.output) if args.output else None, routing)
    return 0


def _cmd_ingest_model_hypotheses(args: argparse.Namespace) -> int:
    context_map = validate_creative_protocol_context_map(read_json_object(args.context_map))
    packet = build_creative_hypothesis_packet_from_model_intake(
        context_map,
        read_json_object(args.model_intake),
    )
    _write_json(Path(args.output) if args.output else None, packet)
    return 0


def _cmd_dispatch_coordinator(args: argparse.Namespace) -> int:
    packet = validate_creative_hypothesis_packet(read_json_object(args.hypothesis_packet))
    routing = validate_creative_hypothesis_agent_routing(read_json_object(args.routing))
    dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=packet,
        routing=routing,
    )
    _write_json(Path(args.output) if args.output else None, dispatch)
    return 0


def _cmd_summarize(args: argparse.Namespace) -> int:
    oracle = None
    if args.oracle:
        oracle = validate_experiment_runner_pr_oracle_attachment(read_json_object(args.oracle))
    packet = validate_creative_hypothesis_packet(read_json_object(args.hypotheses))
    routing = validate_creative_hypothesis_agent_routing(read_json_object(args.routing))
    summary = build_agent_consumption_summary(
        oracle_attachment=oracle,
        hypothesis_packet=packet,
        routing=routing,
    )
    _write_json(Path(args.output) if args.output else None, summary)
    return 0


def _cmd_prepare(args: argparse.Namespace) -> int:
    context_map = (
        validate_creative_protocol_context_map(read_json_object(args.context_map))
        if args.context_map
        else build_creative_protocol_context_map(**_common_context_kwargs(args))
    )
    output_dir = (
        _resolve_output_dir(Path(args.output_dir), create=True)
        if args.output_dir
        else _artifact_subdir(context_map)
    )
    if args.model_intake:
        hypothesis_packet = build_creative_hypothesis_packet_from_model_intake(
            context_map,
            read_json_object(args.model_intake),
        )
    else:
        hypothesis_packet = build_creative_hypothesis_packet(
            context_map,
            hypothesis_count=args.hypothesis_count,
        )
    agent_routing = build_creative_hypothesis_agent_routing(hypothesis_packet)
    coordinator_dispatch = build_creative_hypothesis_coordinator_dispatch(
        hypothesis_packet=hypothesis_packet,
        routing=agent_routing,
    )
    oracle_attachment = build_experiment_runner_pr_oracle_attachment(
        source=context_map["source"],
        oracle_status=args.oracle_status,
        result_ref=args.oracle_result_ref,
        result_fingerprint=args.oracle_result_fingerprint,
        coauthor_required=args.oracle_coauthor_required,
    )
    summary = build_agent_consumption_summary(
        oracle_attachment=oracle_attachment,
        hypothesis_packet=hypothesis_packet,
        routing=agent_routing,
    )
    _write_json(output_dir / "context_map.json", context_map)
    _write_json(output_dir / "hypothesis_packet.json", hypothesis_packet)
    _write_json(output_dir / "agent_routing.json", agent_routing)
    _write_json(output_dir / "coordinator_dispatch.json", coordinator_dispatch)
    _write_json(output_dir / "oracle_attachment.json", oracle_attachment)
    _write_json(output_dir / "agent_consumption_summary.json", summary)
    print(SUCCESS_PREPARE_OUTPUT)
    print(f"Artifact directory: {_display_path(output_dir)}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    payload = validate_artifact_by_type(args.artifact_type, read_json_object(args.path))
    if args.output:
        _write_json(Path(args.output), payload)
    else:
        print("PASS: experiment-runner creative-context artifact valid")
    return 0


def _add_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--repository", default="Katsiarynakavaleuskaya/PulsePlate")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--task-packet-id")
    parser.add_argument("--generated-at-utc")
    parser.add_argument("--nearby-repo-ref", action="append", default=[])
    parser.add_argument("--test-ref", action="append", default=[])
    parser.add_argument("--contract-ref", action="append", default=[])
    parser.add_argument("--backlog-ref", action="append", default=[])
    parser.add_argument("--review-source-ref", action="append", default=[])
    parser.add_argument("--capability-state-ref")
    parser.add_argument("--philosophical-context-ref", action="append", default=[])
    parser.add_argument("--cross-domain-candidate-ref", action="append", default=[])
    parser.add_argument("--label-enabled", action="store_true")
    parser.add_argument("--marker-enabled", action="store_true")
    parser.add_argument("--manual-enabled", action="store_true")
    parser.add_argument("--sealed-codex-security-scan-ref")
    parser.add_argument("--sealed-codex-security-scan-fingerprint")
    parser.add_argument("--security-relevant-diff-changed", action="store_true")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare local Experiment Runner PR creative-context artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect-context")
    _add_context_args(collect_parser)
    collect_parser.add_argument("--output")
    collect_parser.set_defaults(func=_cmd_collect_context)

    hypothesis_parser = subparsers.add_parser("generate-hypotheses")
    hypothesis_parser.add_argument("--context-map", required=True)
    hypothesis_parser.add_argument("--hypothesis-count", type=int, default=4)
    hypothesis_parser.add_argument("--output")
    hypothesis_parser.set_defaults(func=_cmd_generate_hypotheses)

    routing_parser = subparsers.add_parser("route-agents")
    routing_parser.add_argument("--hypothesis-packet", required=True)
    routing_parser.add_argument("--output")
    routing_parser.set_defaults(func=_cmd_route_agents)

    ingest_parser = subparsers.add_parser("ingest-model-hypotheses")
    ingest_parser.add_argument("--context-map", required=True)
    ingest_parser.add_argument("--model-intake", required=True)
    ingest_parser.add_argument("--output")
    ingest_parser.set_defaults(func=_cmd_ingest_model_hypotheses)

    dispatch_parser = subparsers.add_parser("dispatch-coordinator")
    dispatch_parser.add_argument("--hypothesis-packet", required=True)
    dispatch_parser.add_argument("--routing", required=True)
    dispatch_parser.add_argument("--output")
    dispatch_parser.set_defaults(func=_cmd_dispatch_coordinator)

    summary_parser = subparsers.add_parser("summarize")
    summary_parser.add_argument("--oracle")
    summary_parser.add_argument("--hypotheses", required=True)
    summary_parser.add_argument("--routing", required=True)
    summary_parser.add_argument("--output")
    summary_parser.set_defaults(func=_cmd_summarize)

    prepare_parser = subparsers.add_parser("prepare")
    _add_context_args(prepare_parser)
    prepare_parser.add_argument("--context-map")
    prepare_parser.add_argument("--hypothesis-count", type=int, default=4)
    prepare_parser.add_argument("--model-intake")
    prepare_parser.add_argument("--oracle-status", default="skipped")
    prepare_parser.add_argument("--oracle-result-ref")
    prepare_parser.add_argument("--oracle-result-fingerprint")
    prepare_parser.add_argument("--oracle-coauthor-required", action="store_true")
    prepare_parser.add_argument("--output-dir")
    prepare_parser.set_defaults(func=_cmd_prepare)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument(
        "--artifact-type",
        required=True,
        choices=sorted(
            {
                ORACLE_ATTACHMENT_TYPE,
                CONTEXT_MAP_TYPE,
                HYPOTHESIS_PACKET_TYPE,
                AGENT_ROUTING_TYPE,
                OPERATOR_MODEL_INTAKE_TYPE,
                COORDINATOR_DISPATCH_TYPE,
                CONSUMPTION_SUMMARY_TYPE,
                APPROVAL_TYPE,
            }
        ),
    )
    validate_parser.add_argument("--path", required=True)
    validate_parser.add_argument("--output")
    validate_parser.set_defaults(func=_cmd_validate)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return int(args.func(args))
    except (
        ExperimentRunnerCreativeContextCliError,
        ExperimentRunnerCreativeContextContractError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
