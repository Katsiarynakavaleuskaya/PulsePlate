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
from scripts.orchestration.route_with_telemetry import TELEMETRY_PATH, route
from scripts.orchestration.routing_graph_loader import load_routing_graph
from scripts.orchestration.skill_router import route_skills

SCHEMA_VERSION = "2.0"
TASK_PACKET_DIR: Path = REPO_ROOT / "artifacts" / "orchestration" / "task_packets"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_requested_agents(requested_agents: list[str] | tuple[str, ...]) -> list[str]:
    """Normalize requested agent slugs while preserving order and uniqueness."""

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_agent in requested_agents:
        agent = raw_agent.strip().lower()
        if not agent or agent in seen:
            continue
        seen.add(agent)
        normalized.append(agent)
    return normalized


def _select_independent_reviewer(
    *,
    primary_agent: str,
    canonical_reviewer: str,
    canonical_secondary: str | None,
    previous_primary: str,
) -> str:
    """Keep reviewer independent after requested-agent promotion."""

    for candidate in (
        canonical_reviewer,
        canonical_secondary,
        previous_primary,
        "agent-coordinator",
    ):
        if candidate and candidate != primary_agent:
            return candidate
    return "qa-engineer-agent"


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

    for agent in requested_agents:
        if agent not in inventory:
            dispositions.append(
                {
                    "agent": agent,
                    "status": "rejected_unknown_agent",
                    "reason": "Agent is not registered in the canonical inventory.",
                }
            )
            continue

        if agent == resolved_primary:
            dispositions.append(
                {
                    "agent": agent,
                    "status": "honored_primary",
                    "reason": "Requested agent already matches the routed primary.",
                }
            )
            continue

        if agent in non_routable:
            if agent not in advisory_agents:
                advisory_agents.append(agent)
            dispositions.append(
                {
                    "agent": agent,
                    "status": "advisory_non_routable",
                    "reason": "Agent is canonical but non-routable; kept as an advisory collaborator.",
                }
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
            dispositions.append(
                {
                    "agent": agent,
                    "status": "promoted_requested_agent",
                    "reason": "Requested agent is compatible with the routed domain and was promoted.",
                }
            )
            continue

        if agent not in advisory_agents:
            advisory_agents.append(agent)
        dispositions.append(
            {
                "agent": agent,
                "status": "advisory_domain_mismatch",
                "reason": "Requested agent stays advisory because it is outside the routed domain slot set.",
            }
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
    normalized_requested_agents = _normalize_requested_agents(requested_agents)
    domain = resolve_domain(
        task_class=task_class,
        candidate_paths=normalized_paths,
        goal=goal,
    )
    routing = load_routing_graph()
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
    skill_routing = route_skills(
        goal=goal,
        task_class=task_class,
        candidate_paths=normalized_paths,
        domain=decision.domain,
        requested_agents=normalized_requested_agents,
    )

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
