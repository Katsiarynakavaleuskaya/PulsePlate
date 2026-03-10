#!/usr/bin/env python3
"""Deterministic experiment bootstrap entrypoint.

RU: Генерирует детерминированный experiment packet для governed experimentation lane.
EN: Generates a deterministic experiment packet for the governed experimentation lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

EXPERIMENT_BOOTSTRAP_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(EXPERIMENT_BOOTSTRAP_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_BOOTSTRAP_REPO_ROOT))

from scripts.orchestration.context_pack import REPO_ROOT, repo_relative_paths, resolve_domain
from scripts.orchestration.route_with_telemetry import TELEMETRY_PATH, route
from scripts.orchestration.routing_graph_loader import load_routing_graph
from scripts.orchestration.skill_router import route_skills

SCHEMA_VERSION = "1.0"
EXPERIMENT_PACKET_DIR: Path = REPO_ROOT / "artifacts" / "orchestration" / "experiments"

PRIMARY_AGENT = "agent-coordinator"
REVIEWER = "architecture-specialist"

PROMOTION_TARGETS: tuple[str, ...] = (
    "pr_packet",
    "audit_artifact",
    "guard_test_proposal",
    "backlog_entry",
    "memory_capsule",
)

DEFAULT_STOP_CONDITION = (
    "Stop on timeout, OOM, metric regression, guard failure, policy violation, or unchanged result."
)
DEFAULT_BUDGETS: dict[str, int] = {
    "wall_clock_seconds": 300,
    "retry_budget": 1,
    "max_changed_files": 3,
    "network_budget": 0,
    "benchmark_budget": 1,
    "test_budget": 2,
}

ALLOWED_MUTABLE_PREFIXES: tuple[str, ...] = (
    "core/insight/",
    "core/rag/",
)
ALLOWED_DOC_SUFFIXES: tuple[str, ...] = ("program.md",)
ALLOWED_DOC_SEGMENTS: tuple[str, ...] = ("/prompts/", "/programs/")

ML_TEXT_HINTS: tuple[str, ...] = (
    "benchmark",
    "eval",
    "evaluation",
    "experiment",
    "llm",
    "optimization",
    "rag",
    "reliability",
)
CV_TEXT_HINTS: tuple[str, ...] = (
    "cv",
    "image",
    "multimodal",
    "photo",
    "vision",
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_text(*parts: str) -> str:
    """Normalize free text for deterministic lexical checks."""

    raw = " ".join(part.strip().lower() for part in parts if part.strip())
    for token in ("/", "_", "-", ".", ":", "(", ")", ","):
        raw = raw.replace(token, " ")
    return " ".join(raw.split())


def _is_allowed_prompt_or_program_doc(path: str) -> bool:
    if not path.startswith("docs/"):
        return False
    if any(path.endswith(suffix) for suffix in ALLOWED_DOC_SUFFIXES):
        return True
    return any(segment in f"/{path}" for segment in ALLOWED_DOC_SEGMENTS)


def validate_mutable_candidate_surface(paths: list[str] | tuple[str, ...]) -> list[str]:
    """Validate mutable surfaces against the PR1 experimentation allowlist."""

    normalized_paths = repo_relative_paths(paths)
    if not normalized_paths:
        raise ValueError("At least one --mutable-path is required.")

    invalid_paths: list[str] = []
    for path in normalized_paths:
        if Path(path).is_absolute():
            invalid_paths.append(path)
            continue
        if any(path.startswith(prefix) for prefix in ALLOWED_MUTABLE_PREFIXES):
            continue
        if _is_allowed_prompt_or_program_doc(path):
            continue
        invalid_paths.append(path)

    if invalid_paths:
        joined = ", ".join(invalid_paths)
        raise ValueError(
            "Mutable candidate surface must stay within core/insight/*, core/rag/*, "
            f"or approved prompt/program docs. Invalid paths: {joined}"
        )
    return normalized_paths


def validate_immutable_oracles(commands: list[str] | tuple[str, ...]) -> list[dict[str, str]]:
    """Validate oracle commands and normalize them into the packet shape."""

    cleaned = [command.strip() for command in commands if command.strip()]
    if not cleaned:
        raise ValueError("At least one --oracle-command is required.")
    return [{"command": command, "expected_signal": "must pass"} for command in cleaned]


def validate_metrics(metrics: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Require a primary metric and preserve stable ordering for secondary metrics."""

    cleaned = [metric.strip() for metric in metrics if metric.strip()]
    if not cleaned:
        raise ValueError("At least one --metric is required.")
    return {
        "primary": cleaned[0],
        "secondary": cleaned[1:],
    }


def validate_negative_controls(items: list[str] | tuple[str, ...]) -> list[str]:
    """Require at least two negative controls, as mandated by the protocol."""

    cleaned = [item.strip() for item in items if item.strip()]
    if len(cleaned) < 2:
        raise ValueError("At least two --negative-control values are required.")
    return cleaned


def validate_promotion_target(target: str) -> str:
    """Accept only protocol-approved promotion targets."""

    normalized = target.strip().lower()
    if normalized not in PROMOTION_TARGETS:
        allowed = ", ".join(PROMOTION_TARGETS)
        raise ValueError(f"--promotion-target must be one of: {allowed}")
    return normalized


def _resolve_experiment_domain(
    *,
    decision_question: str,
    task_class: str,
    mutable_paths: list[str],
) -> str:
    """Resolve the dominant experiment domain without mutating shared routing helpers."""

    normalized_text = _normalize_text(decision_question, task_class, *mutable_paths)
    if any(hint in normalized_text for hint in CV_TEXT_HINTS):
        return "ml"
    if any(
        path.startswith(prefix)
        for path in mutable_paths
        for prefix in ALLOWED_MUTABLE_PREFIXES
    ):
        return "ml"
    if any(hint in normalized_text for hint in ML_TEXT_HINTS):
        return "ml"
    return resolve_domain(task_class=task_class, candidate_paths=mutable_paths)


def _recommend_advisory_agents(
    *,
    decision_question: str,
    mutable_paths: list[str],
) -> list[str]:
    """Return deterministic advisory agents for the experimentation lane."""

    normalized_text = _normalize_text(decision_question, *mutable_paths)
    advisory_agents = ["data-scientist-agent"]
    if any(hint in normalized_text for hint in CV_TEXT_HINTS):
        advisory_agents.extend(["cv-agent", "ml-engineer-agent"])
    else:
        advisory_agents.append("ml-engineer-agent")
    return advisory_agents


def compute_experiment_id(
    *,
    decision_question: str,
    task_class: str,
    mutable_paths: list[str],
    immutable_oracles: list[dict[str, str]],
    metrics: dict[str, Any],
    negative_controls: list[str],
    promotion_target: str,
) -> str:
    """Return deterministic short experiment id."""

    payload = json.dumps(
        {
            "decision_question": decision_question.strip(),
            "task_class": task_class.strip(),
            "mutable_paths": mutable_paths,
            "immutable_oracles": immutable_oracles,
            "metrics": metrics,
            "negative_controls": negative_controls,
            "promotion_target": promotion_target,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return f"exp-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:12]}"


def build_experiment_packet(
    *,
    decision_question: str,
    task_class: str,
    mutable_paths: list[str],
    oracle_commands: list[str],
    metrics: list[str],
    negative_controls: list[str],
    promotion_target: str,
    telemetry_path: Path = TELEMETRY_PATH,
    budgets: dict[str, int] | None = None,
    stop_condition: str = DEFAULT_STOP_CONDITION,
) -> dict[str, Any]:
    """Build a deterministic experiment packet for PR2 bootstrap tooling."""

    validated_paths = validate_mutable_candidate_surface(mutable_paths)
    immutable_oracles = validate_immutable_oracles(oracle_commands)
    metric_payload = validate_metrics(metrics)
    validated_negative_controls = validate_negative_controls(negative_controls)
    validated_promotion_target = validate_promotion_target(promotion_target)
    budget_payload = dict(DEFAULT_BUDGETS)
    if budgets:
        budget_payload.update(budgets)

    domain = _resolve_experiment_domain(
        decision_question=decision_question,
        task_class=task_class,
        mutable_paths=validated_paths,
    )
    routing = load_routing_graph()
    routing_decision = route(
        domain,
        task_class,
        telemetry=_read_json(telemetry_path),
        routing=routing,
    )
    skill_routing = route_skills(
        goal=decision_question,
        task_class=task_class,
        candidate_paths=validated_paths,
        domain=domain,
    )
    experiment_id = compute_experiment_id(
        decision_question=decision_question,
        task_class=task_class,
        mutable_paths=validated_paths,
        immutable_oracles=immutable_oracles,
        metrics=metric_payload,
        negative_controls=validated_negative_controls,
        promotion_target=validated_promotion_target,
    )

    recommended_agents = [PRIMARY_AGENT, routing_decision.primary]
    if routing_decision.secondary:
        recommended_agents.append(routing_decision.secondary)
    recommended_agents.extend(
        _recommend_advisory_agents(
            decision_question=decision_question,
            mutable_paths=validated_paths,
        )
    )
    recommended_agents.append(REVIEWER)

    deduped_agents = list(dict.fromkeys(recommended_agents))

    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "decision_question": decision_question.strip(),
        "task_class": task_class.strip(),
        "domain": domain,
        "mutable_candidate_surface": validated_paths,
        "immutable_oracles": immutable_oracles,
        "budgets": {
            **budget_payload,
            "stop_condition": stop_condition.strip() or DEFAULT_STOP_CONDITION,
        },
        "metrics": metric_payload,
        "negative_controls": validated_negative_controls,
        "promotion_target": validated_promotion_target,
        "primary_agent": PRIMARY_AGENT,
        "reviewer": REVIEWER,
        "recommended_agents": deduped_agents,
        "recommended_skills": [item["skill"] for item in skill_routing["recommended"]],
        "skill_routing": skill_routing,
        "routing_context": {
            "cluster": routing_decision.cluster,
            "domain": routing_decision.domain,
            "task_type": routing_decision.task_type,
            "primary": routing_decision.primary,
            "secondary": routing_decision.secondary,
            "reviewer": routing_decision.reviewer,
        },
    }


def _resolve_output_path(raw_output: str | None, experiment_id: str) -> Path:
    """Resolve output path relative to repo root and reject out-of-repo writes."""

    if not raw_output:
        return (EXPERIMENT_PACKET_DIR / f"{experiment_id}.json").resolve()

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
        prog="experiment_bootstrap",
        description="Build deterministic experiment packet artifact.",
    )
    parser.add_argument("--decision-question", required=True)
    parser.add_argument("--task-class", default="Experimentation")
    parser.add_argument("--mutable-path", action="append", default=[])
    parser.add_argument("--oracle-command", action="append", default=[])
    parser.add_argument("--metric", action="append", default=[])
    parser.add_argument("--negative-control", action="append", default=[])
    parser.add_argument("--promotion-target", required=True)
    parser.add_argument("--wall-clock-seconds", type=int, default=DEFAULT_BUDGETS["wall_clock_seconds"])
    parser.add_argument("--retry-budget", type=int, default=DEFAULT_BUDGETS["retry_budget"])
    parser.add_argument(
        "--max-changed-files",
        type=int,
        default=DEFAULT_BUDGETS["max_changed_files"],
    )
    parser.add_argument("--network-budget", type=int, default=DEFAULT_BUDGETS["network_budget"])
    parser.add_argument(
        "--benchmark-budget",
        type=int,
        default=DEFAULT_BUDGETS["benchmark_budget"],
    )
    parser.add_argument("--test-budget", type=int, default=DEFAULT_BUDGETS["test_budget"])
    parser.add_argument("--stop-condition", default=DEFAULT_STOP_CONDITION)
    parser.add_argument("--telemetry", default=str(TELEMETRY_PATH))
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Defaults to artifacts/orchestration/experiments/<id>.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        packet = build_experiment_packet(
            decision_question=args.decision_question,
            task_class=args.task_class,
            mutable_paths=args.mutable_path,
            oracle_commands=args.oracle_command,
            metrics=args.metric,
            negative_controls=args.negative_control,
            promotion_target=args.promotion_target,
            telemetry_path=Path(args.telemetry),
            budgets={
                "wall_clock_seconds": args.wall_clock_seconds,
                "retry_budget": args.retry_budget,
                "max_changed_files": args.max_changed_files,
                "network_budget": args.network_budget,
                "benchmark_budget": args.benchmark_budget,
                "test_budget": args.test_budget,
            },
            stop_condition=args.stop_condition,
        )
        out_path = _resolve_output_path(args.output, packet["experiment_id"])
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
                "experiment_id": packet["experiment_id"],
                "domain": packet["domain"],
                "primary_agent": packet["primary_agent"],
                "reviewer": packet["reviewer"],
                "recommended_agents": packet["recommended_agents"],
                "recommended_skills": packet["recommended_skills"],
                "promotion_target": packet["promotion_target"],
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
