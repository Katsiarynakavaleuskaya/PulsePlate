"""Shared experiment contract helpers.

RU: Общие константы и fail-closed валидация для experiment packet.
EN: Shared constants and fail-closed validation helpers for experiment packets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.orchestration.context_pack import REPO_ROOT, repo_relative_paths

SCHEMA_VERSION = "1.0"

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
MAX_BUDGETS: dict[str, int] = {
    "wall_clock_seconds": 600,
    "retry_budget": 2,
    "max_changed_files": 5,
    "network_budget": 20,
    "benchmark_budget": 2,
    "test_budget": 3,
}

DEFAULT_METRIC_BASELINE_REF = "current-main"
DEFAULT_METRIC_ACCEPTANCE_THRESHOLD = "strict_improvement"

ALLOWED_MUTABLE_PREFIXES: tuple[str, ...] = (
    "core/insight/",
    "core/rag/",
)
ALLOWED_DOC_SUFFIXES: tuple[str, ...] = ("program.md",)
ALLOWED_DOC_SEGMENTS: tuple[str, ...] = ("/prompts/", "/programs/")


def _is_allowed_prompt_or_program_doc(path: str) -> bool:
    if not path.startswith("docs/"):
        return False
    if any(path.endswith(suffix) for suffix in ALLOWED_DOC_SUFFIXES):
        return True
    return any(segment in f"/{path}" for segment in ALLOWED_DOC_SEGMENTS)


def _normalize_mutable_surface_path(raw_path: str) -> str:
    """Collapse traversal segments before mutable-surface allowlist checks."""

    candidate = Path(raw_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (REPO_ROOT / candidate).resolve()

    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def validate_mutable_candidate_surface(paths: list[str] | tuple[str, ...]) -> list[str]:
    """Validate mutable surfaces against the PR1 experimentation allowlist."""

    normalized_paths = sorted(
        {_normalize_mutable_surface_path(path) for path in repo_relative_paths(paths)}
    )
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


def validate_metrics(
    metrics: list[str] | tuple[str, ...],
    *,
    baseline_reference: str = DEFAULT_METRIC_BASELINE_REF,
    acceptance_threshold: str = DEFAULT_METRIC_ACCEPTANCE_THRESHOLD,
) -> dict[str, Any]:
    """Require a primary metric and preserve stable ordering for secondary metrics."""

    cleaned = [metric.strip() for metric in metrics if metric.strip()]
    if not cleaned:
        raise ValueError("At least one --metric is required.")
    normalized_baseline_reference = baseline_reference.strip()
    normalized_acceptance_threshold = acceptance_threshold.strip()
    if not normalized_baseline_reference:
        raise ValueError("--metric-baseline-ref must be non-empty.")
    if not normalized_acceptance_threshold:
        raise ValueError("--metric-acceptance-threshold must be non-empty.")
    return {
        "primary": cleaned[0],
        "secondary": cleaned[1:],
        "baseline_reference": normalized_baseline_reference,
        "acceptance_threshold": normalized_acceptance_threshold,
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


def validate_budget_payload(budgets: dict[str, int] | None = None) -> dict[str, int]:
    """Reject invalid budget overrides and enforce protocol hard caps."""

    budget_payload = dict(DEFAULT_BUDGETS)
    if budgets:
        unknown_keys = sorted(set(budgets) - set(DEFAULT_BUDGETS))
        if unknown_keys:
            joined = ", ".join(unknown_keys)
            raise ValueError(f"Unsupported budget keys: {joined}.")
        budget_payload.update(budgets)

    for key, cap in MAX_BUDGETS.items():
        value = budget_payload[key]
        if value < 0:
            raise ValueError(f"{key} must be >= 0.")
        if key != "network_budget" and value == 0:
            raise ValueError(f"{key} must be > 0.")
        if value > cap:
            raise ValueError(f"{key} must be <= {cap}.")
    return budget_payload


def validate_experiment_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate a PR2 experiment packet for deterministic PR3 consumption."""

    if not isinstance(packet, dict):
        raise ValueError("Experiment packet must be a JSON object.")

    experiment_id = str(packet.get("experiment_id", "")).strip()
    if not experiment_id:
        raise ValueError("Experiment packet must include a non-empty experiment_id.")

    decision_question = str(packet.get("decision_question", "")).strip()
    if not decision_question:
        raise ValueError("Experiment packet must include a non-empty decision_question.")

    task_class = str(packet.get("task_class", "")).strip()
    if not task_class:
        raise ValueError("Experiment packet must include a non-empty task_class.")

    mutable_surface_raw = packet.get("mutable_candidate_surface")
    if not isinstance(mutable_surface_raw, list):
        raise ValueError("Experiment packet mutable_candidate_surface must be a list.")
    mutable_surface = validate_mutable_candidate_surface(
        [str(path) for path in mutable_surface_raw]
    )

    immutable_oracles_raw = packet.get("immutable_oracles")
    if not isinstance(immutable_oracles_raw, list):
        raise ValueError("Experiment packet immutable_oracles must be a list.")
    oracle_commands: list[str] = []
    for oracle in immutable_oracles_raw:
        if not isinstance(oracle, dict):
            raise ValueError("Each immutable oracle must be an object.")
        oracle_command = str(oracle.get("command", "")).strip()
        if not oracle_command:
            raise ValueError("Each immutable oracle must include a non-empty command.")
        oracle_commands.append(oracle_command)
    immutable_oracles = validate_immutable_oracles(oracle_commands)

    budgets_raw = packet.get("budgets")
    if not isinstance(budgets_raw, dict):
        raise ValueError("Experiment packet budgets must be an object.")
    stop_condition = str(budgets_raw.get("stop_condition", DEFAULT_STOP_CONDITION)).strip()
    validated_budgets = validate_budget_payload(
        {
            key: int(budgets_raw[key])
            for key in DEFAULT_BUDGETS
            if key in budgets_raw
        }
    )

    metrics_raw = packet.get("metrics")
    if not isinstance(metrics_raw, dict):
        raise ValueError("Experiment packet metrics must be an object.")
    primary_metric = str(metrics_raw.get("primary", "")).strip()
    secondary_metrics_raw = metrics_raw.get("secondary", [])
    if not isinstance(secondary_metrics_raw, list):
        raise ValueError("Experiment packet metrics.secondary must be a list.")
    metric_payload = validate_metrics(
        [primary_metric, *[str(item) for item in secondary_metrics_raw]],
        baseline_reference=str(
            metrics_raw.get("baseline_reference", DEFAULT_METRIC_BASELINE_REF)
        ),
        acceptance_threshold=str(
            metrics_raw.get(
                "acceptance_threshold",
                DEFAULT_METRIC_ACCEPTANCE_THRESHOLD,
            )
        ),
    )

    negative_controls_raw = packet.get("negative_controls")
    if not isinstance(negative_controls_raw, list):
        raise ValueError("Experiment packet negative_controls must be a list.")
    negative_controls = validate_negative_controls(
        [str(item) for item in negative_controls_raw]
    )

    promotion_target = validate_promotion_target(str(packet.get("promotion_target", "")))

    normalized = dict(packet)
    normalized["schema_version"] = str(packet.get("schema_version", SCHEMA_VERSION))
    normalized["experiment_id"] = experiment_id
    normalized["decision_question"] = decision_question
    normalized["task_class"] = task_class
    normalized["mutable_candidate_surface"] = mutable_surface
    normalized["immutable_oracles"] = immutable_oracles
    normalized["budgets"] = {
        **validated_budgets,
        "stop_condition": stop_condition or DEFAULT_STOP_CONDITION,
    }
    normalized["metrics"] = metric_payload
    normalized["negative_controls"] = negative_controls
    normalized["promotion_target"] = promotion_target
    return normalized
