#!/usr/bin/env python3
"""Deterministic experiment bootstrap entrypoint.

RU: Генерирует детерминированный experiment packet для governed experimentation lane.
EN: Generates a deterministic experiment packet for the governed experimentation lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

EXPERIMENT_BOOTSTRAP_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(EXPERIMENT_BOOTSTRAP_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_BOOTSTRAP_REPO_ROOT))

from scripts.orchestration.context_pack import (
    REPO_ROOT,
    normalize_text,
    resolve_domain,
)
from scripts.orchestration.experiment_contract import (
    ALLOWED_MUTABLE_PREFIXES,
    DEFAULT_BUDGETS,
    DEFAULT_METRIC_ACCEPTANCE_THRESHOLD,
    DEFAULT_METRIC_BASELINE_REF,
    DEFAULT_STOP_CONDITION,
    PRIMARY_AGENT,
    REVIEWER,
    SCHEMA_VERSION,
    validate_budget_payload,
    validate_immutable_oracles,
    validate_metrics,
    validate_mutable_candidate_surface,
    validate_negative_controls,
    validate_promotion_target,
)
from scripts.orchestration.route_with_telemetry import TELEMETRY_PATH, route
from scripts.orchestration.routing_graph_loader import load_routing_graph
from scripts.orchestration.skill_router import route_skills

EXPERIMENT_PACKET_DIR: Path = REPO_ROOT / "artifacts" / "orchestration" / "experiments"

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


def _contains_hint(normalized_text: str, hints: tuple[str, ...]) -> bool:
    """Match hints on token boundaries to avoid accidental substring hits."""

    return any(
        re.search(rf"(?<!\w){re.escape(normalize_text(hint))}(?!\w)", normalized_text)
        for hint in hints
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_experiment_domain(
    *,
    decision_question: str,
    task_class: str,
    mutable_paths: list[str],
) -> str:
    """Resolve the dominant experiment domain without mutating shared routing helpers."""

    normalized_text = normalize_text(decision_question, task_class, *mutable_paths)
    if _contains_hint(normalized_text, CV_TEXT_HINTS):
        return "ml"
    if any(
        path.startswith(prefix) for path in mutable_paths for prefix in ALLOWED_MUTABLE_PREFIXES
    ):
        return "ml"
    if _contains_hint(normalized_text, ML_TEXT_HINTS):
        return "ml"
    resolved_domain = resolve_domain(task_class=task_class, candidate_paths=mutable_paths)
    if not isinstance(resolved_domain, str):
        raise TypeError("resolve_domain() must return str")
    return resolved_domain


def _recommend_advisory_agents(
    *,
    decision_question: str,
    mutable_paths: list[str],
) -> list[str]:
    """Return deterministic advisory agents for the experimentation lane."""

    normalized_text = normalize_text(decision_question, *mutable_paths)
    advisory_agents = ["data-scientist-agent"]
    if _contains_hint(normalized_text, CV_TEXT_HINTS):
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
    budgets: dict[str, int],
    stop_condition: str,
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
            "budgets": budgets,
            "stop_condition": stop_condition.strip() or DEFAULT_STOP_CONDITION,
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
    metric_baseline_reference: str = DEFAULT_METRIC_BASELINE_REF,
    metric_acceptance_threshold: str = DEFAULT_METRIC_ACCEPTANCE_THRESHOLD,
) -> dict[str, Any]:
    """Build a deterministic experiment packet for PR2 bootstrap tooling."""

    validated_paths = validate_mutable_candidate_surface(mutable_paths)
    immutable_oracles = validate_immutable_oracles(oracle_commands)
    metric_payload = validate_metrics(
        metrics,
        baseline_reference=metric_baseline_reference,
        acceptance_threshold=metric_acceptance_threshold,
    )
    validated_negative_controls = validate_negative_controls(negative_controls)
    validated_promotion_target = validate_promotion_target(promotion_target)
    budget_payload = validate_budget_payload(budgets)

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
        budgets=budget_payload,
        stop_condition=stop_condition,
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
    """Resolve output path under the local experiment artifact directory only."""

    if not raw_output:
        return (EXPERIMENT_PACKET_DIR / f"{experiment_id}.json").resolve()

    candidate = Path(raw_output)
    if not candidate.is_absolute():
        candidate = (EXPERIMENT_PACKET_DIR / candidate).resolve()
    else:
        candidate = candidate.resolve()

    try:
        candidate.relative_to(EXPERIMENT_PACKET_DIR.resolve())
    except ValueError as exc:
        raise ValueError("--output must stay within artifacts/orchestration/experiments") from exc
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
    parser.add_argument("--metric-baseline-ref", default=DEFAULT_METRIC_BASELINE_REF)
    parser.add_argument(
        "--metric-acceptance-threshold",
        default=DEFAULT_METRIC_ACCEPTANCE_THRESHOLD,
    )
    parser.add_argument(
        "--wall-clock-seconds", type=int, default=DEFAULT_BUDGETS["wall_clock_seconds"]
    )
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
        help=(
            "Optional JSON output path under artifacts/orchestration/experiments/. "
            "Defaults to artifacts/orchestration/experiments/<id>.json"
        ),
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
            metric_baseline_reference=args.metric_baseline_ref,
            metric_acceptance_threshold=args.metric_acceptance_threshold,
        )
        out_path = _resolve_output_path(args.output, packet["experiment_id"])
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"FAIL: unable to write experiment packet: {exc}")
        return 1
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
