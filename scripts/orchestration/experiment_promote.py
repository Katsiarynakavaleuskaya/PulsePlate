#!/usr/bin/env python3
"""Deterministic promotion tooling for governed experiment results.

RU: Продвигает result packet ровно в один долговечный repo-artifact и пишет
локальный promotion decision artifact.
EN: Promotes a result packet into exactly one durable repo artifact and writes
the local promotion decision artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
    from scripts.orchestration.experiment_contract import (
        ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
        SCHEMA_VERSION,
        validate_creative_research_origin,
        validate_experiment_id,
        validate_experiment_packet,
        validate_experiment_result,
    )
except ImportError:  # pragma: no cover - CLI fallback for direct script execution.
    import sys

    experiment_promote_repo_root = Path(__file__).resolve().parents[2]
    if str(experiment_promote_repo_root) not in sys.path:
        sys.path.insert(0, str(experiment_promote_repo_root))
    from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
    from scripts.orchestration.experiment_contract import (
        ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
        SCHEMA_VERSION,
        validate_creative_research_origin,
        validate_experiment_id,
        validate_experiment_packet,
        validate_experiment_result,
    )

PROMOTION_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "promotions"
PR_PACKET_DIR = REPO_ROOT / "docs" / "orchestration" / "experiment_pr_packets"
GUARD_PROPOSAL_DIR = REPO_ROOT / "docs" / "orchestration" / "experiment_guard_proposals"
AUDIT_PREFIX = "EXPERIMENT_"
MEMORY_INDEX_PATH = REPO_ROOT / "docs" / "memory" / "index.md"
BACKLOG_LEDGER_PATH = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
MEMORY_INDEX_MARKER = "<!-- EXPERIMENT_MEMORY_CAPSULES:INSERT BELOW -->"
BACKLOG_MARKER = "<!-- EXPERIMENT_BACKLOG_ENTRIES:INSERT BELOW -->"

DEFAULT_BACKLOG_OWNER = "@katsiaryna_kavaleuskaya"
DEFAULT_BACKLOG_PRIORITY = "P1"
DEFAULT_BACKLOG_TARGET_PR_PREFIX = "PR_TBD_"
DEFAULT_BACKLOG_AREA = "orchestration / experimentation"
RESULT_PROMOTION_STATUSES: tuple[str, ...] = ("promoted", "deferred")
TERMINAL_REJECTION_FAILURE_CLASSES: frozenset[str] = frozenset(
    {"capability_mismatch", "infra_flake", "policy_violation"}
)


class ExperimentPromotionError(RuntimeError):
    """Base error for promotion contract violations."""


def _promotion_packet(packet: dict[str, Any]) -> dict[str, Any]:
    try:
        validated_packet: dict[str, Any] = validate_experiment_packet(packet)
        return validated_packet
    except ValueError as exc:
        raise ExperimentPromotionError(str(exc)) from exc


def _creative_research_origin_for_promotion(packet: dict[str, Any]) -> dict[str, str] | None:
    try:
        validated_origin: dict[str, str] | None = validate_creative_research_origin(
            packet.get("creative_research_origin")
        )
        return validated_origin
    except ValueError as exc:
        raise ExperimentPromotionError(str(exc)) from exc


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return payload


def _resolve_output_path(raw_output: str | None, experiment_id: str) -> Path:
    if raw_output:
        candidate = Path(raw_output)
        if not candidate.is_absolute():
            candidate = PROMOTION_ARTIFACT_DIR / candidate
    else:
        candidate = PROMOTION_ARTIFACT_DIR / f"{experiment_id}.json"
    candidate = candidate.resolve()
    try:
        candidate.relative_to(PROMOTION_ARTIFACT_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "--output must stay within artifacts/orchestration/experiments/promotions"
        ) from exc
    return candidate


def _require_matching_experiment(packet: dict[str, Any], result: dict[str, Any]) -> None:
    if packet["experiment_id"] != result["experiment_id"]:
        raise ExperimentPromotionError(
            "Experiment packet and result must reference the same experiment_id."
        )
    if packet.get("runner_mode") != result.get("runner_mode"):
        raise ExperimentPromotionError(
            "Experiment packet and result must reference the same runner_mode."
        )
    if packet.get("candidate_patch_fingerprint") != result.get("candidate_patch_fingerprint"):
        raise ExperimentPromotionError(
            "Experiment packet and result must reference the same candidate_patch_fingerprint."
        )


def _result_policy(packet: dict[str, Any], result: dict[str, Any]) -> str:
    target = packet["promotion_target"]
    status = result["status"]
    if (
        packet.get("runner_mode") == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
        or result.get("runner_mode") == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE
    ):
        raise ExperimentPromotionError(
            "Oracle-only governance reviewer results are advisory local evidence "
            "and must not be promoted."
        )
    if status == "accepted":
        if not result["shared_tree_untouched"]:
            raise ExperimentPromotionError(
                "Accepted result is not promotable when shared_tree_untouched is false."
            )
        return "promoted"
    if status == "rejected":
        failure_class = result.get("failure_class")
        if failure_class in TERMINAL_REJECTION_FAILURE_CLASSES:
            raise ExperimentPromotionError(
                f"Rejected {failure_class} results must stop before promotion."
            )
        if target != "backlog_entry":
            raise ExperimentPromotionError("Rejected results may promote only to backlog_entry.")
        return "deferred"
    raise ExperimentPromotionError(f"Unsupported result status: {status}")


def _artifact_paths_for_target(experiment_id: str, target: str) -> list[Path]:
    experiment_id = validate_experiment_id(experiment_id, label="Promotion target")
    upper_id = experiment_id.upper().replace("-", "_")
    if target == "pr_packet":
        return [PR_PACKET_DIR / f"{experiment_id}.md"]
    if target == "audit_artifact":
        return [REPO_ROOT / "docs" / "audit" / f"{AUDIT_PREFIX}{upper_id}.md"]
    if target == "guard_test_proposal":
        return [GUARD_PROPOSAL_DIR / f"{experiment_id}.md"]
    if target == "backlog_entry":
        return [BACKLOG_LEDGER_PATH]
    if target == "memory_capsule":
        return [
            REPO_ROOT / "docs" / "memory" / f"{experiment_id}_capsule.md",
            MEMORY_INDEX_PATH,
        ]
    raise ExperimentPromotionError(f"Unsupported promotion_target: {target}")


def _evidence_lines(result: dict[str, Any]) -> list[str]:
    oracle_lines = []
    for oracle_result in result["oracle_results"]:
        oracle_lines.append(
            "- `"
            + oracle_result["command"]
            + "` -> rc="
            + str(oracle_result["returncode"])
            + ", timed_out="
            + str(oracle_result["timed_out"]).lower()
            + ", truncated="
            + str(oracle_result["truncated"]).lower()
        )
    if not oracle_lines:
        oracle_lines.append("- No oracle commands executed.")
    return oracle_lines


def _creative_research_origin_markdown(origin: dict[str, str] | None) -> str:
    if origin is None:
        return ""
    return (
        "\n## Creative Research Origin\n\n"
        f"- Bundle ID: `{origin['bundle_id']}`\n"
        f"- Candidate ID: `{origin['candidate_id']}`\n"
        f"- Promotion decision: `{origin['promotion_decision']}`\n"
    )


def _base_markdown(packet: dict[str, Any], result: dict[str, Any], disposition: str) -> str:
    origin = _creative_research_origin_for_promotion(packet)
    mutated = (
        "\n".join(f"- `{path}`" for path in result["mutated_paths"])
        if result["mutated_paths"]
        else "- No mutated paths recorded."
    )
    oracles = "\n".join(
        f"- `{oracle['command']}` ({oracle['expected_signal']})"
        for oracle in packet["immutable_oracles"]
    )
    evidence = "\n".join(_evidence_lines(result))
    failure_class = result["failure_class"] if result["failure_class"] is not None else "none"
    return (
        f"# Experiment Promotion: {packet['experiment_id']}\n\n"
        f"- Decision question: {packet['decision_question']}\n"
        f"- Promotion target: `{packet['promotion_target']}`\n"
        f"- Disposition: `{disposition}`\n"
        f"- Result status: `{result['status']}`\n"
        f"- Failure class: `{failure_class}`\n\n"
        f"{_creative_research_origin_markdown(origin)}"
        "## Mutable Surface\n\n"
        f"{mutated}\n\n"
        "## Immutable Oracles\n\n"
        f"{oracles}\n\n"
        "## Evidence\n\n"
        f"{evidence}\n\n"
        "## Deferred Follow-up Block\n\n"
        f"- Owner: `{DEFAULT_BACKLOG_OWNER}`\n"
        f"- Priority: `{DEFAULT_BACKLOG_PRIORITY}`\n"
        f"- Target PR: `{DEFAULT_BACKLOG_TARGET_PR_PREFIX}{packet['experiment_id'].upper().replace('-', '_')}`\n"
        f"- Reason: `failure_class={failure_class}`\n"
    )


def _render_pr_packet(packet: dict[str, Any], result: dict[str, Any], disposition: str) -> str:
    return _base_markdown(packet, result, disposition).replace(
        "# Experiment Promotion:", "# Experiment PR Packet:"
    )


def _render_audit_artifact(packet: dict[str, Any], result: dict[str, Any], disposition: str) -> str:
    return _base_markdown(packet, result, disposition).replace(
        "# Experiment Promotion:", "# Experiment Audit Artifact:"
    )


def _render_guard_proposal(packet: dict[str, Any], result: dict[str, Any], disposition: str) -> str:
    return _base_markdown(packet, result, disposition).replace(
        "# Experiment Promotion:", "# Experiment Guard Proposal:"
    )


def _render_memory_capsule(packet: dict[str, Any], result: dict[str, Any], disposition: str) -> str:
    return _base_markdown(packet, result, disposition).replace(
        "# Experiment Promotion:", "# Memory Capsule:"
    )


def _stable_write(path: Path, content: str) -> None:
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise ExperimentPromotionError(
                f"Target artifact already exists with different content: {normalize_repo_path(path)}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _insert_once(path: Path, marker: str, block: str) -> None:
    content = path.read_text(encoding="utf-8")
    if block in content:
        return
    if marker not in content:
        raise ExperimentPromotionError(
            f"Missing deterministic marker in {normalize_repo_path(path)}"
        )
    updated = content.replace(marker, f"{marker}\n{block.rstrip()}\n", 1)
    path.write_text(updated, encoding="utf-8")


def _render_backlog_entry(packet: dict[str, Any], result: dict[str, Any], disposition: str) -> str:
    experiment_slug = packet["experiment_id"].replace("_", "-")
    failure_class = result["failure_class"] if result["failure_class"] is not None else "none"
    origin = _creative_research_origin_for_promotion(packet)
    origin_lines = ""
    if origin is not None:
        origin_lines = (
            "  - Creative research origin:\n"
            f"    - Bundle ID: `{origin['bundle_id']}`\n"
            f"    - Candidate ID: `{origin['candidate_id']}`\n"
            f"    - Promotion decision: `{origin['promotion_decision']}`\n"
        )
    return (
        f'<a id="ledger-{experiment_slug}"></a>\n'
        f"- [ ] P1: Experiment follow-up for {packet['experiment_id']}\n"
        f"  - Owner: {DEFAULT_BACKLOG_OWNER}\n"
        f"  - Priority: {DEFAULT_BACKLOG_PRIORITY}\n"
        f"  - Target PR: {DEFAULT_BACKLOG_TARGET_PR_PREFIX}{packet['experiment_id'].upper().replace('-', '_')}\n"
        f"  - Area: {DEFAULT_BACKLOG_AREA}\n"
        f"  - Status: {'Deferred' if disposition == 'deferred' else 'Planned'}\n"
        f"  - Reason (EN): Experiment `{packet['experiment_id']}` ended with status `{result['status']}` "
        f"and failure class `{failure_class}`; follow-up is tracked via KPP-only promotion.\n"
        f"{origin_lines}"
        "  - Links:\n"
        f"    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`\n"
        f"    - `docs/memory/kpp_knowledge_promotion_pipeline.md`\n"
        "  - DoD:\n"
        "    - Follow-up scope is promoted through exactly one durable artifact\n"
        "    - Evidence references the immutable oracles used by the experiment\n"
    )


def _render_memory_index_line(experiment_id: str) -> str:
    return (
        f"- `docs/memory/{experiment_id}_capsule.md`"
        f" - Experiment capsule for `{experiment_id}` promotion outcome"
    )


def _write_durable_artifacts(
    packet: dict[str, Any],
    result: dict[str, Any],
    disposition: str,
) -> str:
    target = packet["promotion_target"]
    artifact_paths = _artifact_paths_for_target(packet["experiment_id"], target)

    if target == "pr_packet":
        durable_path = artifact_paths[0]
        _stable_write(durable_path, _render_pr_packet(packet, result, disposition))
        repo_ref: str = normalize_repo_path(durable_path)
        return repo_ref
    if target == "audit_artifact":
        durable_path = artifact_paths[0]
        _stable_write(durable_path, _render_audit_artifact(packet, result, disposition))
        repo_ref = normalize_repo_path(durable_path)
        return repo_ref
    if target == "guard_test_proposal":
        durable_path = artifact_paths[0]
        _stable_write(durable_path, _render_guard_proposal(packet, result, disposition))
        repo_ref = normalize_repo_path(durable_path)
        return repo_ref
    if target == "backlog_entry":
        durable_path = artifact_paths[0]
        _insert_once(
            durable_path, BACKLOG_MARKER, _render_backlog_entry(packet, result, disposition)
        )
        repo_ref = normalize_repo_path(durable_path)
        return repo_ref
    if target == "memory_capsule":
        capsule_path, index_path = artifact_paths
        _stable_write(capsule_path, _render_memory_capsule(packet, result, disposition))
        _insert_once(
            index_path, MEMORY_INDEX_MARKER, _render_memory_index_line(packet["experiment_id"])
        )
        repo_ref = normalize_repo_path(capsule_path)
        return repo_ref
    raise ExperimentPromotionError(f"Unsupported promotion target: {target}")


def build_promotion_decision(packet: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    packet = _promotion_packet(packet)
    _require_matching_experiment(packet, result)
    creative_research_origin = _creative_research_origin_for_promotion(packet)
    disposition = _result_policy(packet, result)
    if disposition not in RESULT_PROMOTION_STATUSES:
        raise ExperimentPromotionError(f"Unsupported disposition: {disposition}")
    durable_artifact_path = _write_durable_artifacts(packet, result, disposition)
    decision = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": packet["experiment_id"],
        "result_status": result["status"],
        "failure_class": result["failure_class"],
        "promotion_target": packet["promotion_target"],
        "disposition": disposition,
        "durable_artifact_path": durable_artifact_path,
        "shared_tree_untouched": result["shared_tree_untouched"],
        "domain": packet.get("domain", ""),
        "evidence": {
            "oracle_commands": [oracle["command"] for oracle in packet["immutable_oracles"]],
            "mutated_paths": list(result["mutated_paths"]),
            "oracle_count": len(result["oracle_results"]),
        },
    }
    if creative_research_origin is not None:
        decision["creative_research_origin"] = creative_research_origin
    return decision


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="experiment_promote",
        description="Promote governed experiment results into exactly one durable repo artifact.",
    )
    parser.add_argument("--packet", required=True, help="Experiment packet JSON path.")
    parser.add_argument("--result", required=True, help="Experiment result JSON path.")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional promotion decision JSON path under "
            "artifacts/orchestration/experiments/promotions/. "
            "Defaults to artifacts/orchestration/experiments/promotions/<id>.json"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    packet_path = Path(args.packet).expanduser().resolve()
    result_path = Path(args.result).expanduser().resolve()

    try:
        packet = _promotion_packet(_read_json_object(packet_path, label="experiment packet"))
        result = validate_experiment_result(
            _read_json_object(result_path, label="experiment result")
        )
        output_path = _resolve_output_path(args.output, packet["experiment_id"])
        decision = build_promotion_decision(packet, result)
    except (ValueError, ExperimentPromotionError) as exc:
        print(f"FAIL: {exc}")
        return 1

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"FAIL: unable to write promotion decision: {exc}")
        return 1

    print(
        json.dumps(
            {
                "experiment_id": decision["experiment_id"],
                "promotion_target": decision["promotion_target"],
                "disposition": decision["disposition"],
                "output": normalize_repo_path(output_path),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
