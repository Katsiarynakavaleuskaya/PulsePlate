#!/usr/bin/env python3
"""Local CLI for adaptive production-adjacent creative pilots."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.creative_pilot_workspace_contract import (
    CreativePilotContractError,
    build_approval_v2,
    add_rebuttal_assignments,
    apply_synthesis_transition,
    build_context_map_v2,
    build_evidence_events,
    build_hypothesis_packet_v2,
    build_role_result,
    build_synthesis,
    build_target_manifest,
    build_workspace,
    complete_handoff,
    detect_conflicts,
    ingest_role_result,
    load_json_strict,
    terminate_workspace,
    validate_synthesis,
    validate_workspace,
)
from scripts.orchestration.creative_code_spec_pipeline import prepare as prepare_specification
from scripts.orchestration.creative_hypothesis_spec_bridge_contract import (
    build_creative_pilot_spec_bridge_bundle,
)

PILOT_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "adaptive_pilots"
FIXED_FILENAMES = {
    "context": "context_map.v2.json",
    "packet": "hypothesis_packet.v2.json",
    "workspace": "workspace.json",
    "synthesis": "synthesis.json",
    "approval": "approval.v2.json",
    "evidence": "evidence_events.json",
    "bridge": "spec_bridge.v2.json",
    "candidate": "creative_code_candidate.v1.json",
}


def _read(path: Path) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], load_json_strict(path.read_text(encoding="utf-8")))
    except OSError as exc:
        raise CreativePilotContractError(f"unable to read {path}") from exc


def _atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def _run_dir(pilot_id: str) -> Path:
    if not pilot_id or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        for char in pilot_id
    ):
        raise CreativePilotContractError("pilot-id must be a safe token")
    root = PILOT_ROOT.resolve()
    candidate = (root / pilot_id).resolve()
    if candidate.parent != root:
        raise CreativePilotContractError("pilot directory escaped the adaptive-pilot root")
    current = candidate
    while current != root:
        if current.is_symlink():
            raise CreativePilotContractError("pilot directory must not traverse symlinks")
        current = current.parent
    return candidate


def _workspace_path(args: argparse.Namespace) -> Path:
    return _run_dir(args.pilot_id) / FIXED_FILENAMES["workspace"]


def _cmd_prepare(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    manifest = build_target_manifest(
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        paths=args.target,
        symbols=args.symbol,
        immutable_oracles=args.oracle,
    )
    context = build_context_map_v2(target_manifest=manifest, context_refs=args.context_ref)
    hypotheses = _read(Path(args.hypotheses)).get("hypotheses")
    if not isinstance(hypotheses, list):
        raise CreativePilotContractError("hypotheses file must contain a hypotheses array")
    packet = build_hypothesis_packet_v2(context_map=context, hypotheses=hypotheses)
    workspace = build_workspace(
        context_map=context,
        hypothesis_packet=packet,
        selected_hypothesis_id=args.selected_hypothesis,
    )
    _atomic_write(run_dir / FIXED_FILENAMES["context"], context)
    _atomic_write(run_dir / FIXED_FILENAMES["packet"], packet)
    _atomic_write(run_dir / FIXED_FILENAMES["workspace"], workspace)
    print(
        f"PASS phase={workspace['state']['phase']} next=emit-dispatch workspace={run_dir.relative_to(REPO_ROOT)}/{FIXED_FILENAMES['workspace']}"
    )


def _cmd_emit_dispatch(args: argparse.Namespace) -> None:
    workspace = validate_workspace(_read(_workspace_path(args)))
    phase = args.phase
    assignments = [row for row in workspace["assignments"] if row["phase"] == phase]
    if not assignments:
        raise CreativePilotContractError(f"workspace has no {phase} assignments")
    payload = {
        "workspace_id": workspace["workspace_id"],
        "workspace_intent_fingerprint": workspace["intent_fingerprint"],
        "workspace_revision_fingerprint": workspace["revision_fingerprint"],
        "phase": phase,
        "assignments": assignments,
        "authority": {
            "execute_role_passes": True,
            "generate_patch": False,
            "write_repository": False,
        },
    }
    output = _run_dir(args.pilot_id) / f"dispatch.{phase}.json"
    _atomic_write(output, payload)
    print(
        f"PASS phase={workspace['state']['phase']} next=task-bootstrap dispatch={output.relative_to(REPO_ROOT)}"
    )


def _cmd_ingest(args: argparse.Namespace) -> None:
    path = _workspace_path(args)
    workspace = validate_workspace(_read(path))
    updated = ingest_role_result(workspace, _read(Path(args.role_result)))
    _atomic_write(path, updated)
    print(
        f"PASS phase={updated['state']['phase']} next={'detect-conflicts' if updated['state']['phase'] == 'independent_complete' else 'ingest-role-result'}"
    )


def _cmd_record_role_result(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    path = run_dir / FIXED_FILENAMES["workspace"]
    workspace = validate_workspace(_read(path))
    result = build_role_result(
        workspace=workspace,
        assignment_id=args.assignment_id,
        stance=args.stance,
        claim_ids=args.claim_id,
        evidence_refs=args.evidence_ref,
        blocker_codes=args.blocker_code,
        oracle_gap_codes=args.oracle_gap_code,
        peer_result_refs=args.peer_result_ref,
    )
    result_path = run_dir / "role_results" / f"{result['result_id'].split(':')[-1]}.json"
    if result_path.exists() and _read(result_path) != result:
        raise CreativePilotContractError("divergent role-result overwrite is forbidden")
    _atomic_write(result_path, result)
    updated = ingest_role_result(workspace, result)
    _atomic_write(path, updated)
    print(
        f"PASS result_id={result['result_id']} phase={updated['state']['phase']} "
        f"next={'detect-conflicts' if updated['state']['phase'] in {'independent_complete', 'rebuttal_complete'} else 'record-role-result'}"
    )


def _cmd_detect(args: argparse.Namespace) -> None:
    path = _workspace_path(args)
    updated = detect_conflicts(validate_workspace(_read(path)))
    _atomic_write(path, updated)
    print(
        f"PASS phase={updated['state']['phase']} next={'emit-rebuttal' if updated['state']['phase'] == 'rebuttal_required' else 'synthesize'}"
    )


def _cmd_emit_rebuttal(args: argparse.Namespace) -> None:
    path = _workspace_path(args)
    updated = add_rebuttal_assignments(validate_workspace(_read(path)))
    _atomic_write(path, updated)
    output = _run_dir(args.pilot_id) / "dispatch.rebuttal.json"
    _atomic_write(
        output,
        {
            "workspace_id": updated["workspace_id"],
            "workspace_intent_fingerprint": updated["intent_fingerprint"],
            "workspace_revision_fingerprint": updated["revision_fingerprint"],
            "phase": "rebuttal",
            "assignments": [row for row in updated["assignments"] if row["phase"] == "rebuttal"],
            "authority": {
                "execute_role_passes": True,
                "generate_patch": False,
                "write_repository": False,
            },
        },
    )
    print(
        f"PASS phase={updated['state']['phase']} next=task-bootstrap dispatch={output.relative_to(REPO_ROOT)}"
    )


def _cmd_synthesize(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis = build_synthesis(workspace)
    transitioned = apply_synthesis_transition(workspace, synthesis)
    _atomic_write(run_dir / FIXED_FILENAMES["workspace"], transitioned)
    _atomic_write(run_dir / FIXED_FILENAMES["synthesis"], synthesis)
    events = [
        event.to_dict()
        for event in build_evidence_events(
            workspace=transitioned,
            synthesis=synthesis,
            produced_at=datetime.now(timezone.utc).isoformat(),
        )
    ]
    _atomic_write(run_dir / FIXED_FILENAMES["evidence"], events)
    print(
        f"PASS decision={synthesis['decision']} evidence={synthesis['evidence_sufficiency']} next={synthesis['next_allowed_action']}"
    )


def _cmd_approve(args: argparse.Namespace) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise CreativePilotContractError("approve-handoff requires an interactive TTY")
    run_dir = _run_dir(args.pilot_id)
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis = validate_synthesis(_read(run_dir / FIXED_FILENAMES["synthesis"]))
    expected = f"APPROVE {args.pilot_id} {synthesis['synthesis_id']} {workspace['target_manifest']['head_sha']}"
    print(f"Type exactly: {expected}")
    if input("approval> ") != expected:
        raise CreativePilotContractError("approval phrase did not match")
    approval = build_approval_v2(
        workspace=workspace,
        synthesis=synthesis,
        approved_by=args.approved_by,
    )
    approval_path = run_dir / FIXED_FILENAMES["approval"]
    if approval_path.exists() and _read(approval_path) != approval:
        raise CreativePilotContractError("divergent approval overwrite is forbidden")
    _atomic_write(approval_path, approval)
    print(f"PASS approval_id={approval['approval_id']} next=creative-hypothesis-spec-bridge-v2")


def _cmd_build_handoff(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    context = _read(run_dir / FIXED_FILENAMES["context"])
    packet = _read(run_dir / FIXED_FILENAMES["packet"])
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis = validate_synthesis(_read(run_dir / FIXED_FILENAMES["synthesis"]))
    approval = _read(run_dir / FIXED_FILENAMES["approval"])
    bundle = build_creative_pilot_spec_bridge_bundle(
        context_map=context,
        hypothesis_packet=packet,
        workspace=workspace,
        synthesis=synthesis,
        approval=approval,
        variant_count=args.variant_count,
    )
    bridge_path = run_dir / FIXED_FILENAMES["bridge"]
    candidate_path = run_dir / FIXED_FILENAMES["candidate"]
    _atomic_write(bridge_path, bundle["bridge"])
    _atomic_write(candidate_path, bundle["candidate"])
    prepare_dir = run_dir / "pr1_prepare"
    prepare_specification(candidate_path, prepare_dir)
    completed = complete_handoff(
        workspace=workspace,
        approval=approval,
        bridge=bundle["bridge"],
        candidate=bundle["candidate"],
    )
    _atomic_write(run_dir / FIXED_FILENAMES["workspace"], completed)
    print(
        "PASS candidate_schema=1.0 patch_generated=false "
        f"phase={completed['state']['phase']} next=agent-skeptic-review "
        f"prepare={prepare_dir.relative_to(REPO_ROOT)}"
    )


def _cmd_status(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    workspace = validate_workspace(_read(run_dir / FIXED_FILENAMES["workspace"]))
    synthesis_path = run_dir / FIXED_FILENAMES["synthesis"]
    approval_path = run_dir / FIXED_FILENAMES["approval"]
    payload = {
        "pilot_id": args.pilot_id,
        "workspace_id": workspace["workspace_id"],
        "phase": workspace["state"]["phase"],
        "terminal": workspace["state"]["terminal"],
        "role_results": len(workspace["role_results"]),
        "synthesis_exists": synthesis_path.is_file(),
        "approval_exists": approval_path.is_file(),
        "patch_generated": False,
    }
    print(json.dumps(payload, sort_keys=True))


def _cmd_stop(args: argparse.Namespace) -> None:
    run_dir = _run_dir(args.pilot_id)
    workspace_path = run_dir / FIXED_FILENAMES["workspace"]
    workspace, disposition = terminate_workspace(
        validate_workspace(_read(workspace_path)),
        phase=args.phase,
        reason_code=args.reason_code,
    )
    _atomic_write(workspace_path, workspace)
    _atomic_write(run_dir / "disposition.json", disposition)
    print(f"PASS phase={workspace['state']['phase']} terminal=true next=none")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creative_pilot_workspace")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--pilot-id", required=True)
    prepare.add_argument("--base-sha", required=True)
    prepare.add_argument("--head-sha", required=True)
    prepare.add_argument("--target", action="append", required=True)
    prepare.add_argument("--symbol", action="append", required=True)
    prepare.add_argument("--oracle", action="append", required=True)
    prepare.add_argument("--context-ref", action="append", required=True)
    prepare.add_argument("--hypotheses", required=True)
    prepare.add_argument("--selected-hypothesis", required=True)
    prepare.set_defaults(func=_cmd_prepare)
    dispatch = sub.add_parser("emit-dispatch")
    dispatch.add_argument("--pilot-id", required=True)
    dispatch.add_argument("--phase", choices=("independent", "rebuttal"), required=True)
    dispatch.set_defaults(func=_cmd_emit_dispatch)
    ingest = sub.add_parser("ingest-role-result")
    ingest.add_argument("--pilot-id", required=True)
    ingest.add_argument("--role-result", required=True)
    ingest.set_defaults(func=_cmd_ingest)
    record = sub.add_parser("record-role-result")
    record.add_argument("--pilot-id", required=True)
    record.add_argument("--assignment-id", required=True)
    record.add_argument("--stance", choices=("pass", "revise", "reject", "abstain"), required=True)
    record.add_argument("--claim-id", action="append", required=True)
    record.add_argument("--evidence-ref", action="append", required=True)
    record.add_argument("--blocker-code", action="append", default=[])
    record.add_argument("--oracle-gap-code", action="append", default=[])
    record.add_argument("--peer-result-ref", action="append", default=[])
    record.set_defaults(func=_cmd_record_role_result)
    detect = sub.add_parser("detect-conflicts")
    detect.add_argument("--pilot-id", required=True)
    detect.set_defaults(func=_cmd_detect)
    rebuttal = sub.add_parser("emit-rebuttal")
    rebuttal.add_argument("--pilot-id", required=True)
    rebuttal.set_defaults(func=_cmd_emit_rebuttal)
    synthesize = sub.add_parser("synthesize")
    synthesize.add_argument("--pilot-id", required=True)
    synthesize.set_defaults(func=_cmd_synthesize)
    approve = sub.add_parser("approve-handoff")
    approve.add_argument("--pilot-id", required=True)
    approve.add_argument("--approved-by", required=True)
    approve.set_defaults(func=_cmd_approve)
    handoff = sub.add_parser("build-handoff")
    handoff.add_argument("--pilot-id", required=True)
    handoff.add_argument("--variant-count", type=int, default=3, choices=(3, 4, 5))
    handoff.set_defaults(func=_cmd_build_handoff)
    status = sub.add_parser("status")
    status.add_argument("--pilot-id", required=True)
    status.set_defaults(func=_cmd_status)
    stop = sub.add_parser("stop")
    stop.add_argument("--pilot-id", required=True)
    stop.add_argument("--phase", choices=("revise", "reject", "blocked"), required=True)
    stop.add_argument("--reason-code", required=True)
    stop.set_defaults(func=_cmd_stop)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        args.func(args)
    except CreativePilotContractError as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
