#!/usr/bin/env python3
"""Deterministic coordinator bootstrap entrypoint.

RU: Генерирует task packet для coordinator-first workflow.
EN: Generates a task packet artifact for coordinator-first routing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.orchestration.context_pack import (
    REPO_ROOT,
    collect_context_pack,
    compute_task_packet_id,
    repo_relative_paths,
    resolve_domain,
)
from scripts.orchestration.route_with_telemetry import TELEMETRY_PATH, route
from scripts.orchestration.routing_graph_loader import load_routing_graph

SCHEMA_VERSION = "2.0"
TASK_PACKET_DIR = REPO_ROOT / "artifacts" / "orchestration" / "task_packets"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def build_task_packet(
    *,
    goal: str,
    task_class: str,
    candidate_paths: list[str],
    telemetry_path: Path = TELEMETRY_PATH,
) -> dict[str, Any]:
    """Build a deterministic task packet for orchestration tooling."""

    normalized_paths = repo_relative_paths(candidate_paths)
    domain = resolve_domain(task_class=task_class, candidate_paths=normalized_paths)
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
        domain=domain,
        candidate_paths=normalized_paths,
    )
    context_pack = collect_context_pack(
        normalized_paths,
        include_orchestration=decision.cluster == "ops" or len(normalized_paths) != 1,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "task_packet_id": packet_id,
        "goal": goal.strip(),
        "task_class": task_class.strip(),
        "domain": decision.domain,
        "cluster": decision.cluster,
        "candidate_paths": normalized_paths,
        "primary_agent": decision.primary,
        "secondary_agents": [agent for agent in [decision.secondary] if agent],
        "reviewer": decision.reviewer,
        "required_context": context_pack,
        "routing_rationale": decision.rationale,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="task_bootstrap",
        description="Build deterministic coordinator task packet artifact.",
    )
    parser.add_argument("--goal", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--path", action="append", default=[])
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
        telemetry_path=Path(args.telemetry),
    )
    out_path = (
        Path(args.output) if args.output else TASK_PACKET_DIR / f"{packet['task_packet_id']}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "task_packet_id": packet["task_packet_id"],
                "domain": packet["domain"],
                "cluster": packet["cluster"],
                "primary_agent": packet["primary_agent"],
                "reviewer": packet["reviewer"],
                "output": str(out_path.relative_to(REPO_ROOT)),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
