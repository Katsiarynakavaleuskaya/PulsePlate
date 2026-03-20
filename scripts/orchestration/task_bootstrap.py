#!/usr/bin/env python3
"""Deterministic coordinator bootstrap entrypoint.

RU: Генерирует task packet для coordinator-first workflow.
EN: Generates a task packet artifact for coordinator-first routing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BOOTSTRAP_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(BOOTSTRAP_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_REPO_ROOT))

from core.judgment import (
    CLAIM_EVIDENCE_FIELDS,
    CLAIM_TYPES,
    EVIDENCE_MODES,
    JUDGMENT_FLOW,
    PROMOTION_LABELS,
    SUPPORT_STATUSES,
    UNCERTAINTY_FIELDS,
)
from scripts.orchestration.context_pack import (
    REPO_ROOT,
    collect_context_pack,
    compute_task_packet_id,
    repo_relative_paths,
    resolve_domain,
)
from scripts.orchestration.agent_consistency_loader import (
    load_inventory_agents,
    load_non_routable_agents,
)
from scripts.orchestration.native_subagent_bridge import build_native_subagent_bridge
from scripts.orchestration.route_with_telemetry import TELEMETRY_PATH, route
from scripts.orchestration.routing_graph_loader import (
    BootstrapLaneActivation,
    load_bootstrap_lane_activations,
    load_routing_graph,
)
from scripts.orchestration.requested_agents import normalize_requested_agents
from scripts.orchestration.skill_router import route_skills

SCHEMA_VERSION = "2.0"
TASK_PACKET_DIR: Path = REPO_ROOT / "artifacts" / "orchestration" / "task_packets"
REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN = "rejected_unknown_agent"
REQUESTED_AGENT_STATUS_HONORED_PRIMARY = "honored_primary"
REQUESTED_AGENT_STATUS_HONORED_SECONDARY = "honored_secondary"
REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE = "advisory_non_routable"
REQUESTED_AGENT_STATUS_PROMOTED = "promoted_requested_agent"
REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH = "advisory_domain_mismatch"
PRIVILEGED_REVIEW_PREFIXES: tuple[str, ...] = (
    ".github/workflows/",
    "ios/fastlane/",
    "scripts/orchestration/",
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _select_independent_reviewer(
    *,
    primary_agent: str,
    canonical_reviewer: str,
    canonical_secondary: str | None,
    previous_primary: str,
) -> str:
    """Keep reviewer independent after requested-agent promotion."""

    reviewer_candidate = next(
        (
            candidate
            for candidate in (
                canonical_reviewer,
                canonical_secondary,
                previous_primary,
                "agent-coordinator",
            )
            if candidate and candidate != primary_agent
        ),
        None,
    )
    if reviewer_candidate is not None:
        return reviewer_candidate
    return "qa-engineer-agent"


def _requires_security_review(candidate_paths: list[str] | tuple[str, ...]) -> bool:
    """Return True when the task touches privileged surfaces that require security review."""

    return any(
        any(
            path == prefix.rstrip("/") or path.startswith(prefix)
            for prefix in PRIVILEGED_REVIEW_PREFIXES
        )
        for path in candidate_paths
    )


def _judgment_lane_enabled(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str] | tuple[str, ...],
    activation: BootstrapLaneActivation | None,
) -> bool:
    """Return True when the task clearly targets the judgment/adjudication lane."""

    if activation is None:
        return False

    normalized_haystack = " ".join(
        [
            goal.strip().lower(),
            task_class.strip().lower(),
            *(path.lower() for path in candidate_paths),
        ]
    )
    return any(term in normalized_haystack for term in activation.signal_terms)


def _partition_native_secondaries(
    *,
    secondary_agents: list[str],
    requested_agent_disposition: list[dict[str, str]],
    forced_executable_agents: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Split executable secondaries from advisory-only collaborators.

    RU: advisory specialists stay in the task packet but must not be promoted to
    runnable native subagents.
    EN: advisory specialists remain in the task packet but must not be promoted
    into runnable native subagents.
    """

    advisory_statuses = {
        REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
        REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
    }
    normalized_forced_executable_agents = forced_executable_agents or set()
    advisory_agents = {
        disposition["agent"]
        for disposition in requested_agent_disposition
        if disposition["status"] in advisory_statuses
    }
    executable_secondaries: list[str] = []
    advisory_collaborators: list[str] = []
    for agent_slug in secondary_agents:
        if agent_slug in advisory_agents and agent_slug not in normalized_forced_executable_agents:
            advisory_collaborators.append(agent_slug)
        else:
            executable_secondaries.append(agent_slug)
    return executable_secondaries, advisory_collaborators


def _promote_forced_secondary_dispositions(
    *,
    requested_agent_disposition: list[dict[str, str]],
    forced_executable_agents: set[str],
) -> None:
    """Keep dispositions aligned with forced executable secondaries.

    RU: Если привилегированный review-path требует агента, он не должен
    оставаться advisory only в packet-disposition metadata.
    EN: If the privileged review path requires an agent, it must not remain
    advisory-only in packet disposition metadata.
    """

    advisory_statuses = {
        REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
        REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
    }
    for disposition in requested_agent_disposition:
        if disposition["agent"] not in forced_executable_agents:
            continue
        if disposition["status"] not in advisory_statuses:
            continue
        disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_SECONDARY
        disposition["reason"] = (
            "Requested agent is required for the privileged review path and stays "
            "executable in secondary."
        )


def _apply_requested_agent_overrides(
    *,
    domain: str,
    primary_agent: str,
    secondary_agent: str | None,
    reviewer: str,
    requested_agents: list[str],
    routing: dict[str, Any],
) -> dict[str, Any]:
    """Apply explicit requested-agent overrides in a deterministic, bounded way."""

    inventory = load_inventory_agents()
    non_routable = load_non_routable_agents()
    canonical_route = routing.get(domain)

    resolved_primary = primary_agent
    resolved_secondary_agents = [agent for agent in [secondary_agent] if agent]
    dispositions: list[dict[str, str]] = []
    advisory_agents: list[str] = []

    def _disposition(agent: str, status: str, reason: str) -> dict[str, str]:
        """Build a deterministic disposition payload for requested-agent handling."""

        return {"agent": agent, "status": status, "reason": reason}

    for agent in requested_agents:
        if agent not in inventory:
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_REJECTED_UNKNOWN,
                    "Agent is not registered in the canonical inventory.",
                )
            )
            continue

        if agent == resolved_primary:
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_HONORED_PRIMARY,
                    "Requested agent already matches the routed primary.",
                )
            )
            continue

        if agent in non_routable:
            if agent not in advisory_agents:
                advisory_agents.append(agent)
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_ADVISORY_NON_ROUTABLE,
                    "Agent is canonical but non-routable; kept as an advisory collaborator.",
                )
            )
            continue

        allowed_promotions = {candidate for candidate in [secondary_agent, reviewer] if candidate}
        if canonical_route is not None:
            allowed_promotions.add(canonical_route.primary)
            if canonical_route.secondary:
                allowed_promotions.add(canonical_route.secondary)
            allowed_promotions.add(canonical_route.reviewer)

        if agent in allowed_promotions:
            previous_primary = resolved_primary
            resolved_primary = agent
            resolved_secondary_agents = [
                candidate
                for candidate in [previous_primary, *resolved_secondary_agents]
                if candidate and candidate != resolved_primary
            ]
            reviewer = _select_independent_reviewer(
                primary_agent=resolved_primary,
                canonical_reviewer=canonical_route.reviewer if canonical_route else reviewer,
                canonical_secondary=(
                    canonical_route.secondary if canonical_route else secondary_agent
                ),
                previous_primary=previous_primary,
            )
            for disposition in dispositions:
                if (
                    disposition["agent"] == previous_primary
                    and disposition["status"] == REQUESTED_AGENT_STATUS_HONORED_PRIMARY
                ):
                    disposition["status"] = REQUESTED_AGENT_STATUS_HONORED_SECONDARY
                    disposition["reason"] = (
                        "Requested agent stayed honored but moved to secondary after a later promotion."
                    )
            dispositions.append(
                _disposition(
                    agent,
                    REQUESTED_AGENT_STATUS_PROMOTED,
                    "Requested agent is compatible with the routed domain and was promoted.",
                )
            )
            continue

        if agent not in advisory_agents:
            advisory_agents.append(agent)
        dispositions.append(
            _disposition(
                agent,
                REQUESTED_AGENT_STATUS_ADVISORY_DOMAIN_MISMATCH,
                "Requested agent stays advisory because it is outside the routed domain slot set.",
            )
        )

    ordered_secondary_agents: list[str] = []
    for candidate in [*resolved_secondary_agents, *advisory_agents]:
        if (
            candidate
            and candidate != resolved_primary
            and candidate not in ordered_secondary_agents
        ):
            ordered_secondary_agents.append(candidate)

    return {
        "primary_agent": resolved_primary,
        "secondary_agents": ordered_secondary_agents,
        "reviewer": reviewer,
        "requested_agent_disposition": dispositions,
    }


def build_task_packet(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str],
    requested_agents: list[str] | tuple[str, ...] = (),
    telemetry_path: Path = TELEMETRY_PATH,
) -> dict[str, Any]:
    """Build a deterministic task packet for orchestration tooling."""

    normalized_paths = repo_relative_paths(candidate_paths)
    normalized_requested_agents = normalize_requested_agents(requested_agents)
    domain = resolve_domain(
        task_class=task_class,
        candidate_paths=normalized_paths,
        goal=goal,
    )
    routing = load_routing_graph()
    bootstrap_lane_activations = load_bootstrap_lane_activations()
    decision = route(
        domain,
        task_class,
        telemetry=_read_json(telemetry_path),
        routing=routing,
    )
    packet_id = compute_task_packet_id(
        goal=goal,
        task_class=task_class,
        domain=decision.domain,
        candidate_paths=normalized_paths,
        requested_agents=normalized_requested_agents,
    )
    context_pack = collect_context_pack(
        normalized_paths,
        include_orchestration=decision.cluster == "ops" or len(normalized_paths) != 1,
    )
    requested_agent_resolution = _apply_requested_agent_overrides(
        domain=decision.domain,
        primary_agent=decision.primary,
        secondary_agent=decision.secondary,
        reviewer=decision.reviewer,
        requested_agents=normalized_requested_agents,
        routing=routing,
    )
    security_review_required = _requires_security_review(normalized_paths)
    if security_review_required:
        secondary_agents = list(requested_agent_resolution["secondary_agents"])
        security_in_review_path = "security-auditor" in {
            requested_agent_resolution["primary_agent"],
            requested_agent_resolution["reviewer"],
            *secondary_agents,
        }
        if not security_in_review_path:
            secondary_agents.append("security-auditor")
        requested_agent_resolution["secondary_agents"] = secondary_agents
    skill_routing = route_skills(
        goal=goal,
        task_class=task_class,
        candidate_paths=normalized_paths,
        domain=decision.domain,
        requested_agents=normalized_requested_agents,
    )
    forced_executable_agents = {"security-auditor"} if security_review_required else set()
    if forced_executable_agents:
        _promote_forced_secondary_dispositions(
            requested_agent_disposition=requested_agent_resolution["requested_agent_disposition"],
            forced_executable_agents=forced_executable_agents,
        )
    executable_secondaries, advisory_agents = _partition_native_secondaries(
        secondary_agents=requested_agent_resolution["secondary_agents"],
        requested_agent_disposition=requested_agent_resolution["requested_agent_disposition"],
        forced_executable_agents=forced_executable_agents,
    )
    native_subagent_bridge = build_native_subagent_bridge(
        primary_agent=requested_agent_resolution["primary_agent"],
        secondary_agents=executable_secondaries,
        reviewer=requested_agent_resolution["reviewer"],
        advisory_agents=advisory_agents,
    )
    judgment_activation = bootstrap_lane_activations.get("judgment")
    if judgment_activation is None:
        raise ValueError("Required bootstrap lane activation missing: judgment")
    judgment_enabled = _judgment_lane_enabled(
        goal=goal,
        task_class=task_class,
        candidate_paths=normalized_paths,
        activation=judgment_activation,
    )
    if judgment_enabled:
        decision_contract = {
            "mode": judgment_activation.decision_mode,
            "judgment_enabled": True,
            "claim_taxonomy": list(CLAIM_TYPES),
            "flow": list(JUDGMENT_FLOW),
        }
        judgment_budget = {
            "skeptic_pass_required": True,
            "verifier_pass_required": True,
            "max_provider_calls": 0,
            "uncertainty_split_required": True,
        }
        result_adjudication = {
            "claim_evidence_fields": list(CLAIM_EVIDENCE_FIELDS),
            "support_statuses": list(SUPPORT_STATUSES),
            "evidence_modes": list(EVIDENCE_MODES),
            "uncertainty_fields": list(UNCERTAINTY_FIELDS),
            "promotion_labels": list(PROMOTION_LABELS),
        }
    else:
        decision_contract = {
            "mode": "standard",
            "judgment_enabled": False,
            "claim_taxonomy": [],
            "flow": [],
        }
        judgment_budget = {
            "skeptic_pass_required": False,
            "verifier_pass_required": False,
            "max_provider_calls": 0,
            "uncertainty_split_required": False,
        }
        result_adjudication = {
            "claim_evidence_fields": [],
            "support_statuses": [],
            "evidence_modes": [],
            "uncertainty_fields": [],
            "promotion_labels": [],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "task_packet_id": packet_id,
        "goal": goal.strip(),
        "task_class": task_class.strip(),
        "domain": decision.domain,
        "cluster": decision.cluster,
        "candidate_paths": normalized_paths,
        "primary_agent": requested_agent_resolution["primary_agent"],
        "secondary_agents": requested_agent_resolution["secondary_agents"],
        "reviewer": requested_agent_resolution["reviewer"],
        "requested_agents": normalized_requested_agents,
        "requested_agent_disposition": requested_agent_resolution["requested_agent_disposition"],
        "required_context": context_pack,
        "recommended_skills": [item["skill"] for item in skill_routing["recommended"]],
        "skill_routing": skill_routing,
        "decision_contract": decision_contract,
        "judgment_budget": judgment_budget,
        "result_adjudication": result_adjudication,
        "native_subagent_bridge": native_subagent_bridge,
        "routing_rationale": decision.rationale,
    }


def _resolve_output_path(raw_output: str | None, packet_id: str) -> Path:
    """Resolve output path relative to repo root and reject out-of-repo writes."""

    if not raw_output:
        return (TASK_PACKET_DIR / f"{packet_id}.json").resolve()

    candidate = Path(raw_output)
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError("--output must stay within the repository root") from exc
    return candidate


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="task_bootstrap",
        description="Build deterministic coordinator task packet artifact.",
    )
    parser.add_argument("--goal", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument(
        "--requested-agent",
        action="append",
        default=[],
        help="Optional requested agent slug. May be repeated.",
    )
    parser.add_argument("--telemetry", default=str(TELEMETRY_PATH))
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Defaults to artifacts/orchestration/task_packets/<id>.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    packet = build_task_packet(
        goal=args.goal,
        task_class=args.task_class,
        candidate_paths=args.path,
        requested_agents=args.requested_agent,
        telemetry_path=Path(args.telemetry),
    )
    try:
        out_path = _resolve_output_path(args.output, packet["task_packet_id"])
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        output_ref = str(out_path.relative_to(REPO_ROOT))
    except ValueError:
        output_ref = str(out_path)
    print(
        json.dumps(
            {
                "task_packet_id": packet["task_packet_id"],
                "domain": packet["domain"],
                "cluster": packet["cluster"],
                "primary_agent": packet["primary_agent"],
                "reviewer": packet["reviewer"],
                "requested_agents": packet["requested_agents"],
                "recommended_skills": packet["recommended_skills"],
                "primary_native_agent_type": packet["native_subagent_bridge"]["primary"][
                    "native_agent_type"
                ],
                "reviewer_native_agent_type": packet["native_subagent_bridge"]["reviewer"][
                    "native_agent_type"
                ],
                "output": output_ref,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
