"""Shared experiment contract helpers.

RU: Общие константы и fail-closed валидация для experiment packet.
EN: Shared constants and fail-closed validation helpers for experiment packets.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess  # nosec B404: bounded git ls-files validation only (remove-by: 2026-07-31, ref: ledger-p1-experiment-runner-oracle-only-governance-reviewer)
from typing import Any

from scripts.orchestration.context_pack import REPO_ROOT, normalize_text, repo_relative_paths

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
RESULT_STATUSES: tuple[str, ...] = ("accepted", "rejected")
DEFAULT_RUNNER_MODE = "candidate_patch"
ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE = "oracle_only_governance_reviewer"
RUNNER_MODES: tuple[str, ...] = (
    DEFAULT_RUNNER_MODE,
    ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE,
)
CONTRIBUTION_KINDS: tuple[str, ...] = (
    "none",
    "oracle_review",
    "experiment_design",
    "admission_review",
    "fixed_mapping_review",
    "review_disposition",
    "commit_decision",
)
FAILURE_CLASSES: tuple[str, ...] = (
    "timeout",
    "oom",
    "metric_regression",
    "guard_failure",
    "policy_violation",
    "unchanged_result",
    "infra_flake",
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
ORACLE_BINARY_ALLOWLIST: tuple[str, ...] = (
    "coverage",
    "diff-cover",
    "git",
    "make",
    "mypy",
    "pytest",
    "python",
    "python3",
    "ruff",
)
FORBIDDEN_AUTONOMOUS_MUTATION_PREFIXES: tuple[str, ...] = (
    ".github/workflows/",
    "docs/orchestration/",
    "docs/review/",
    "scripts/ci/",
    "tests/",
)
FORBIDDEN_AUTONOMOUS_MUTATION_EXACT_PATHS: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "scripts/orchestration/check_merge_ready.py",
        "scripts/orchestration/check_review_threads_disposition.py",
    }
)
FORBIDDEN_AUTONOMOUS_MUTATION_FILENAMES: frozenset[str] = frozenset({"AGENTS.md"})
EXPERIMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
CV_EXPERIMENT_HINTS: tuple[str, ...] = (
    "cv",
    "image",
    "multimodal",
    "photo",
    "vision",
)
CV_UNCERTAINTY_BANDS: tuple[str, ...] = ("high", "medium", "low", "unknown")
CV_DEGRADE_STATES: tuple[str, ...] = (
    "show_ranked_candidates",
    "confirm_top_candidate",
    "manual_entry_required",
    "reject_unusable_image",
    "privacy_blocked",
)


def _is_allowed_prompt_or_program_doc(path: str) -> bool:
    if not path.startswith("docs/"):
        return False
    if any(path.endswith(suffix) for suffix in ALLOWED_DOC_SUFFIXES):
        return True
    return any(segment in f"/{path}" for segment in ALLOWED_DOC_SEGMENTS)


def _contains_hint(normalized_text: str, hints: tuple[str, ...]) -> bool:
    """RU: Проверяет hint на границах токенов. EN: Match hints on token boundaries."""

    return any(
        re.search(rf"(?<!\w){re.escape(normalize_text(hint))}(?!\w)", normalized_text)
        for hint in hints
    )


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


def _is_forbidden_autonomous_mutation_surface(path: str) -> bool:
    return (
        path in FORBIDDEN_AUTONOMOUS_MUTATION_EXACT_PATHS
        or Path(path).name in FORBIDDEN_AUTONOMOUS_MUTATION_FILENAMES
        or any(path.startswith(prefix) for prefix in FORBIDDEN_AUTONOMOUS_MUTATION_PREFIXES)
    )


def _git_env_without_parent_state() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


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


def validate_oracle_context_surface(paths: list[str] | tuple[str, ...]) -> list[str]:
    """Validate PR-owned context paths for oracle-only reviewer evidence."""

    normalized_paths = sorted(
        {_normalize_mutable_surface_path(path) for path in repo_relative_paths(paths)}
    )
    if not normalized_paths:
        raise ValueError("At least one oracle-only context path is required.")

    invalid_paths = [
        path
        for path in normalized_paths
        if Path(path).is_absolute()
        or path == "artifacts"
        or path.startswith("artifacts/")
        or path == "worktrees"
        or path.startswith("worktrees/")
        or path == ".venv"
        or path.startswith(".venv/")
    ]
    if invalid_paths:
        joined = ", ".join(invalid_paths)
        raise ValueError(
            "Oracle-only context paths must be repo-relative tracked surfaces. "
            f"Invalid paths: {joined}"
        )

    git_binary = shutil.which("git")
    if not git_binary:
        raise ValueError("git binary is required to validate oracle-only context paths.")
    tracked_process = subprocess.run(  # nosec B603: absolute git binary checks tracked context paths without shell (remove-by: 2026-07-31, ref: ledger-p1-experiment-runner-oracle-only-governance-reviewer)
        [git_binary, "--literal-pathspecs", "ls-files", "--error-unmatch", "--", *normalized_paths],
        cwd=str(REPO_ROOT),
        env=_git_env_without_parent_state(),
        capture_output=True,
        text=True,
        check=False,
    )
    if tracked_process.returncode != 0:
        diagnostic = tracked_process.stderr.strip() or tracked_process.stdout.strip()
        raise ValueError(
            "Oracle-only context paths must already be tracked by git: "
            f"{diagnostic or ', '.join(normalized_paths)}"
        )
    return normalized_paths


def validate_runner_mode(value: Any) -> str:
    """Normalize the runner mode while preserving backward compatibility."""

    if value is None:
        normalized = DEFAULT_RUNNER_MODE
    elif not isinstance(value, str):
        allowed = ", ".join(RUNNER_MODES)
        raise ValueError(f"Experiment packet runner_mode must be one of: {allowed}")
    else:
        normalized = value.strip().lower()
    if normalized not in RUNNER_MODES:
        allowed = ", ".join(RUNNER_MODES)
        raise ValueError(f"Experiment packet runner_mode must be one of: {allowed}")
    return normalized


def validate_contribution_attribution(
    *,
    contribution_kind: Any = "none",
    coauthor_required: Any = False,
    coauthor_reason: Any = "",
    status: str | None = None,
) -> tuple[str, bool, str]:
    """Validate Experiment Runner contribution/co-author attribution metadata."""

    normalized_kind = str(contribution_kind).strip()
    if normalized_kind not in CONTRIBUTION_KINDS:
        allowed_kinds = ", ".join(CONTRIBUTION_KINDS)
        raise ValueError(f"Experiment result contribution_kind must be one of: {allowed_kinds}")

    if not isinstance(coauthor_required, bool):
        raise ValueError("Experiment result coauthor_required must be a boolean.")

    if not isinstance(coauthor_reason, str):
        raise ValueError("Experiment result coauthor_reason must be a string.")
    normalized_reason = coauthor_reason.strip()

    if coauthor_required and normalized_kind == "none":
        raise ValueError(
            "Experiment result coauthor_required requires a material contribution_kind."
        )
    if normalized_kind != "none" and not coauthor_required:
        raise ValueError("Experiment result material contribution_kind requires coauthor_required.")
    if coauthor_required and not normalized_reason:
        raise ValueError(
            "Experiment result coauthor_reason must be non-empty when coauthor_required."
        )
    if not coauthor_required and normalized_reason:
        raise ValueError(
            "Experiment result coauthor_reason must be empty unless coauthor_required."
        )
    if status == "rejected" and coauthor_required:
        raise ValueError("Rejected Experiment Runner artifacts must not require co-authoring.")

    return normalized_kind, coauthor_required, normalized_reason


def validate_immutable_oracles(commands: list[str] | tuple[str, ...]) -> list[dict[str, str]]:
    """Validate oracle commands and normalize them into the packet shape."""

    cleaned_commands = [command.strip() for command in commands if command.strip()]
    if not cleaned_commands:
        raise ValueError("At least one --oracle-command is required.")

    normalized_oracles: list[dict[str, str]] = []
    allowed_binaries = ", ".join(ORACLE_BINARY_ALLOWLIST)
    for command in cleaned_commands:
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise ValueError(f"Unable to parse oracle command: {command}") from exc
        if not argv:
            raise ValueError("Oracle command must not be empty.")
        if argv[0] not in ORACLE_BINARY_ALLOWLIST:
            raise ValueError(
                f"Oracle binary {argv[0]!r} is not allowlisted. " f"Allowed: {allowed_binaries}"
            )
        normalized_oracles.append(
            {
                "command": command,
                "expected_signal": "must pass",
            }
        )
    return normalized_oracles


def validate_metrics(
    metrics: list[str] | tuple[str, ...],
    *,
    baseline_reference: str = DEFAULT_METRIC_BASELINE_REF,
    acceptance_threshold: str = DEFAULT_METRIC_ACCEPTANCE_THRESHOLD,
) -> dict[str, Any]:
    """Require a primary metric and preserve stable ordering for secondary metrics."""

    if not metrics or not str(metrics[0]).strip():
        raise ValueError("A primary --metric is required.")
    cleaned = [metric.strip() for metric in metrics if metric.strip()]
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


def validate_experiment_id(value: Any, *, label: str) -> str:
    """Require a deterministic, path-safe experiment identifier."""

    experiment_id = str(value).strip()
    if not experiment_id:
        raise ValueError(f"{label} must include a non-empty experiment_id.")
    if not EXPERIMENT_ID_RE.fullmatch(experiment_id):
        raise ValueError(
            f"{label} experiment_id must contain only ASCII letters, digits, hyphens, "
            "and underscores, and must not contain path separators."
        )
    return experiment_id


def is_cv_experiment(*parts: Any) -> bool:
    """Return whether the experiment intent is CV-oriented and needs cv_context."""

    normalized = normalize_text(*[str(part) for part in parts if str(part).strip()])
    return bool(normalized) and _contains_hint(normalized, CV_EXPERIMENT_HINTS)


def _require_non_empty_string(
    payload: dict[str, Any],
    *,
    key: str,
    label: str,
) -> str:
    """RU: Требует непустую строку. EN: Require a non-empty string field."""

    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"{label} must include a non-empty {key}.")
    return value


def validate_cv_context(payload: Any) -> dict[str, Any]:
    """RU: Нормализует CV packet fields. EN: Normalize fail-closed CV packet fields."""

    if not isinstance(payload, dict):
        raise ValueError("Experiment packet cv_context must be an object.")
    dataset_raw = payload.get("dataset")
    if not isinstance(dataset_raw, dict):
        raise ValueError("Experiment packet cv_context.dataset must be an object.")
    dataset = {
        "id": _require_non_empty_string(
            dataset_raw,
            key="id",
            label="Experiment packet cv_context.dataset",
        ),
        "version": _require_non_empty_string(
            dataset_raw,
            key="version",
            label="Experiment packet cv_context.dataset",
        ),
        "source": _require_non_empty_string(
            dataset_raw,
            key="source",
            label="Experiment packet cv_context.dataset",
        ),
        "license": _require_non_empty_string(
            dataset_raw,
            key="license",
            label="Experiment packet cv_context.dataset",
        ),
        "split_strategy": _require_non_empty_string(
            dataset_raw,
            key="split_strategy",
            label="Experiment packet cv_context.dataset",
        ),
        "label_provenance": _require_non_empty_string(
            dataset_raw,
            key="label_provenance",
            label="Experiment packet cv_context.dataset",
        ),
    }

    sensor_conditions_raw = payload.get("sensor_conditions")
    if not isinstance(sensor_conditions_raw, list):
        raise ValueError("Experiment packet cv_context.sensor_conditions must be a list.")
    sensor_conditions = sorted(
        {str(condition).strip() for condition in sensor_conditions_raw if str(condition).strip()}
    )
    if not sensor_conditions:
        raise ValueError(
            "Experiment packet cv_context.sensor_conditions must include at least one item."
        )

    uncertainty_raw = payload.get("uncertainty_band_policy")
    if not isinstance(uncertainty_raw, dict):
        raise ValueError("Experiment packet cv_context.uncertainty_band_policy must be an object.")
    bands_raw = uncertainty_raw.get("bands")
    if not isinstance(bands_raw, list):
        raise ValueError(
            "Experiment packet cv_context.uncertainty_band_policy.bands must be a list."
        )
    mode = _require_non_empty_string(
        uncertainty_raw,
        key="mode",
        label="Experiment packet cv_context.uncertainty_band_policy",
    )
    bands = [str(band).strip().lower() for band in bands_raw if str(band).strip()]
    if tuple(bands) != CV_UNCERTAINTY_BANDS:
        allowed_bands = ", ".join(CV_UNCERTAINTY_BANDS)
        raise ValueError(
            "Experiment packet cv_context.uncertainty_band_policy.bands must equal: "
            f"{allowed_bands}"
        )

    degrade_raw = payload.get("degrade_state_matrix")
    if not isinstance(degrade_raw, dict):
        raise ValueError("Experiment packet cv_context.degrade_state_matrix must be an object.")
    degrade_state_matrix: dict[str, str] = {}
    for band in CV_UNCERTAINTY_BANDS:
        degrade_state = str(degrade_raw.get(band, "")).strip()
        if degrade_state not in CV_DEGRADE_STATES:
            allowed_states = ", ".join(CV_DEGRADE_STATES)
            raise ValueError(
                "Experiment packet cv_context.degrade_state_matrix entries must be one of: "
                f"{allowed_states}"
            )
        degrade_state_matrix[band] = degrade_state

    privacy_raw = payload.get("privacy_packet")
    if not isinstance(privacy_raw, dict):
        raise ValueError("Experiment packet cv_context.privacy_packet must be an object.")
    privacy_packet = {
        "raw_image_retention": _require_non_empty_string(
            privacy_raw,
            key="raw_image_retention",
            label="Experiment packet cv_context.privacy_packet",
        ),
        "logging_policy": _require_non_empty_string(
            privacy_raw,
            key="logging_policy",
            label="Experiment packet cv_context.privacy_packet",
        ),
        "consent_policy": _require_non_empty_string(
            privacy_raw,
            key="consent_policy",
            label="Experiment packet cv_context.privacy_packet",
        ),
        "deletion_policy": _require_non_empty_string(
            privacy_raw,
            key="deletion_policy",
            label="Experiment packet cv_context.privacy_packet",
        ),
    }
    return {
        "dataset": dataset,
        "sensor_conditions": sensor_conditions,
        "uncertainty_band_policy": {
            "mode": mode,
            "bands": list(CV_UNCERTAINTY_BANDS),
        },
        "degrade_state_matrix": degrade_state_matrix,
        "privacy_packet": privacy_packet,
    }


def validate_experiment_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate a PR2 experiment packet for deterministic PR3 consumption."""

    if not isinstance(packet, dict):
        raise ValueError("Experiment packet must be a JSON object.")

    schema_version = str(packet.get("schema_version", "")).strip()
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Experiment packet schema_version must equal {SCHEMA_VERSION!r}, "
            f"got {schema_version!r}."
        )

    experiment_id = validate_experiment_id(
        packet.get("experiment_id", ""),
        label="Experiment packet",
    )

    decision_question = str(packet.get("decision_question", "")).strip()
    if not decision_question:
        raise ValueError("Experiment packet must include a non-empty decision_question.")

    task_class = str(packet.get("task_class", "")).strip()
    if not task_class:
        raise ValueError("Experiment packet must include a non-empty task_class.")

    runner_mode = validate_runner_mode(packet.get("runner_mode", DEFAULT_RUNNER_MODE))

    mutable_surface_raw = packet.get("mutable_candidate_surface")
    if not isinstance(mutable_surface_raw, list):
        raise ValueError("Experiment packet mutable_candidate_surface must be a list.")
    if runner_mode == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
        mutable_surface = validate_oracle_context_surface(
            [str(path) for path in mutable_surface_raw]
        )
    else:
        mutable_surface = validate_mutable_candidate_surface(
            [str(path) for path in mutable_surface_raw]
        )
        if any(_is_forbidden_autonomous_mutation_surface(path) for path in mutable_surface):
            raise ValueError(
                "Experiment packet mutable_candidate_surface must not include governance, "
                "review, CI validator, merge-gate, test, fixture, or AGENTS surfaces. "
                "Use immutable_oracles for governance reviewer evidence instead."
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
    normalized_budget_overrides = {
        key: int(value) for key, value in budgets_raw.items() if key != "stop_condition"
    }
    validated_budgets = validate_budget_payload(normalized_budget_overrides)

    metrics_raw = packet.get("metrics")
    if not isinstance(metrics_raw, dict):
        raise ValueError("Experiment packet metrics must be an object.")
    primary_metric = str(metrics_raw.get("primary", "")).strip()
    secondary_metrics_raw = metrics_raw.get("secondary", [])
    if not isinstance(secondary_metrics_raw, list):
        raise ValueError("Experiment packet metrics.secondary must be a list.")
    metric_payload = validate_metrics(
        [primary_metric, *[str(item) for item in secondary_metrics_raw]],
        baseline_reference=str(metrics_raw.get("baseline_reference", DEFAULT_METRIC_BASELINE_REF)),
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
    negative_controls = validate_negative_controls([str(item) for item in negative_controls_raw])

    promotion_target = validate_promotion_target(str(packet.get("promotion_target", "")))
    cv_context_raw = packet.get("cv_context")
    requires_cv_context = is_cv_experiment(decision_question, task_class, *mutable_surface)
    if cv_context_raw is None:
        if requires_cv_context:
            raise ValueError(
                "CV-oriented experiment packets must include cv_context "
                "(dataset provenance, uncertainty bands, privacy packet, and degrade states)."
            )
        cv_context = None
    else:
        cv_context = validate_cv_context(cv_context_raw)

    normalized = dict(packet)
    normalized["schema_version"] = schema_version
    normalized["experiment_id"] = experiment_id
    normalized["decision_question"] = decision_question
    normalized["task_class"] = task_class
    normalized["runner_mode"] = runner_mode
    normalized["mutable_candidate_surface"] = mutable_surface
    normalized["immutable_oracles"] = immutable_oracles
    normalized["budgets"] = {
        **validated_budgets,
        "stop_condition": stop_condition or DEFAULT_STOP_CONDITION,
    }
    normalized["metrics"] = metric_payload
    normalized["negative_controls"] = negative_controls
    normalized["promotion_target"] = promotion_target
    if cv_context is not None:
        normalized["cv_context"] = cv_context
    return normalized


def validate_experiment_result(result: dict[str, Any]) -> dict[str, Any]:
    """Validate a PR3 experiment result artifact for PR4 promotion/telemetry."""

    if not isinstance(result, dict):
        raise ValueError("Experiment result must be a JSON object.")

    schema_version = str(result.get("schema_version", "")).strip()
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Experiment result schema_version must equal {SCHEMA_VERSION!r}, "
            f"got {schema_version!r}."
        )

    experiment_id = validate_experiment_id(
        result.get("experiment_id", ""),
        label="Experiment result",
    )

    runner_mode = validate_runner_mode(result.get("runner_mode", DEFAULT_RUNNER_MODE))

    status = str(result.get("status", "")).strip()
    if status not in RESULT_STATUSES:
        allowed_statuses = ", ".join(RESULT_STATUSES)
        raise ValueError(f"Experiment result status must be one of: {allowed_statuses}")

    failure_class_raw = result.get("failure_class")
    if failure_class_raw is not None:
        failure_class = str(failure_class_raw).strip()
        if failure_class not in FAILURE_CLASSES:
            allowed_failures = ", ".join(FAILURE_CLASSES)
            raise ValueError(
                f"Experiment result failure_class must be null or one of: {allowed_failures}"
            )
    else:
        failure_class = None
    if status == "rejected" and failure_class is None:
        allowed_failures = ", ".join(FAILURE_CLASSES)
        raise ValueError(
            "Experiment result failure_class must be one of: "
            f"{allowed_failures} when status is 'rejected'."
        )

    mutated_paths_raw = result.get("mutated_paths")
    if not isinstance(mutated_paths_raw, list):
        raise ValueError("Experiment result mutated_paths must be a list.")
    mutated_paths = repo_relative_paths([str(path) for path in mutated_paths_raw])

    oracle_results_raw = result.get("oracle_results")
    if not isinstance(oracle_results_raw, list):
        raise ValueError("Experiment result oracle_results must be a list.")
    oracle_results: list[dict[str, Any]] = []
    for oracle_result in oracle_results_raw:
        if not isinstance(oracle_result, dict):
            raise ValueError("Each oracle result must be an object.")
        command = str(oracle_result.get("command", "")).strip()
        if not command:
            raise ValueError("Each oracle result must include a non-empty command.")
        oracle_results.append(
            {
                "command": command,
                "returncode": int(oracle_result.get("returncode", 0) or 0),
                "timed_out": bool(oracle_result.get("timed_out", False)),
                "truncated": bool(oracle_result.get("truncated", False)),
                "stdout": str(oracle_result.get("stdout", "")),
                "stderr": str(oracle_result.get("stderr", "")),
                "cwd": str(oracle_result.get("cwd", "")),
            }
        )

    budget_observations = result.get("budget_observations")
    if not isinstance(budget_observations, dict):
        raise ValueError("Experiment result budget_observations must be an object.")

    shared_tree_untouched = result.get("shared_tree_untouched")
    if not isinstance(shared_tree_untouched, bool):
        raise ValueError("Experiment result shared_tree_untouched must be a boolean.")

    promotion_ready = result.get("promotion_ready")
    if not isinstance(promotion_ready, bool):
        raise ValueError("Experiment result promotion_ready must be a boolean.")

    contribution_kind, coauthor_required, coauthor_reason = validate_contribution_attribution(
        contribution_kind=result.get("contribution_kind", "none"),
        coauthor_required=result.get("coauthor_required", False),
        coauthor_reason=result.get("coauthor_reason", ""),
        status=status,
    )

    candidate_patch = str(result.get("candidate_patch", "")).strip()
    if not candidate_patch:
        raise ValueError("Experiment result must include a non-empty candidate_patch.")
    if runner_mode == ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
        if mutated_paths:
            raise ValueError(
                "Oracle-only governance reviewer results must not record mutated_paths."
            )
        if promotion_ready:
            raise ValueError("Oracle-only governance reviewer results must not be promotion_ready.")
        if candidate_patch != ORACLE_ONLY_GOVERNANCE_REVIEWER_MODE:
            raise ValueError(
                "Oracle-only governance reviewer results must use the stable "
                "candidate_patch marker."
            )

    normalized = dict(result)
    normalized["schema_version"] = schema_version
    normalized["experiment_id"] = experiment_id
    normalized["runner_mode"] = runner_mode
    normalized["status"] = status
    normalized["failure_class"] = failure_class
    normalized["mutated_paths"] = mutated_paths
    normalized["oracle_results"] = oracle_results
    normalized["budget_observations"] = dict(budget_observations)
    normalized["shared_tree_untouched"] = shared_tree_untouched
    normalized["promotion_ready"] = promotion_ready
    normalized["contribution_kind"] = contribution_kind
    normalized["coauthor_required"] = coauthor_required
    normalized["coauthor_reason"] = coauthor_reason
    normalized["candidate_patch"] = candidate_patch
    return normalized
