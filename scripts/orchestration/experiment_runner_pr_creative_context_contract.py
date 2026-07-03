"""Contracts for Experiment Runner PR creative-context artifacts.

The creative-context lane is a local, read-only orchestration layer. It may
build sanitized context maps, generate bounded hypotheses, route them to
registered role agents, and prepare human-approval summaries. It must not
generate patches, mutate branches, write GitHub state, call providers, or claim
merge readiness.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, cast

from core.evidence.fingerprints import build_asset_id, build_idempotency_key, fingerprint_payload
from scripts.orchestration.agent_consistency_loader import load_inventory_agents

SCHEMA_VERSION = "1.0"
POLICY_VERSION = "experiment-runner-pr-creative-context-v1"
OPERATOR_MODEL_INTAKE_POLICY_VERSION = "creative-hypothesis-operator-intake-v1"
COORDINATOR_DISPATCH_POLICY_VERSION = "creative-hypothesis-coordinator-dispatch-v1"

ORACLE_ATTACHMENT_TYPE = "experiment_runner_pr_oracle_attachment"
CONTEXT_MAP_TYPE = "creative_protocol_context_map"
HYPOTHESIS_PACKET_TYPE = "creative_hypothesis_packet"
AGENT_ROUTING_TYPE = "creative_hypothesis_agent_routing"
CONSUMPTION_SUMMARY_TYPE = "creative_hypothesis_agent_consumption_summary"
APPROVAL_TYPE = "creative_hypothesis_approval"
OPERATOR_MODEL_INTAKE_TYPE = "creative_hypothesis_operator_model_intake"
COORDINATOR_DISPATCH_TYPE = "creative_hypothesis_coordinator_dispatch"

CREATIVE_STATUSES = frozenset({"hypotheses_generated", "no_creative_action", "blocked"})
ORACLE_STATUSES = frozenset({"accepted", "rejected", "skipped", "failed"})
SUMMARY_NEXT_ACTIONS = frozenset({"agent_review", "approve_pr1_specification", "no_action", "hold"})
APPROVAL_DECISIONS = frozenset({"approve_for_pr1_specification", "reject", "defer"})
APPROVAL_NEXT_STEPS = frozenset({"create_pr1_specification", "no_action", "defer"})
HYPOTHESIS_GENERATION_MODES = frozenset(
    {"deterministic_templates_v1", "operator_validated_intake_v1"}
)
OPERATOR_TOOL_LABELS = frozenset({"codex", "comet", "ollama", "other_local", "unknown"})
SOURCE_DOMAINS = frozenset(
    {
        "philosophy",
        "nutrition",
        "security",
        "data",
        "UX",
        "testing",
        "economics",
        "biology",
        "CBT",
        "information_theory",
    }
)
ANALOGY_DOMAIN_AGENT_CANDIDATES = {
    "CBT": ("wellness-analyst-agent",),
    "UX": ("creative-designer", "frontend-engineer"),
    "biology": ("wellness-analyst-agent",),
    "data": ("data-scientist-agent",),
    "economics": ("business-strategist-agent",),
    "information_theory": ("data-scientist-agent", "logic-agent"),
    "nutrition": ("nutritionist-agent", "wellness-analyst-agent"),
    "philosophy": ("philosophy-agent", "epistemology-discovery-agent"),
    "security": ("security-auditor",),
    "testing": ("qa-engineer-agent", "bug-hunter"),
}
HYPOTHESIS_KINDS = frozenset(
    {
        "architecture",
        "security_authority",
        "testing_oracle",
        "creative_protocol",
        "scientific_stats",
    }
)
REASON_CODES = frozenset(
    {
        "eligible_orchestration_surface",
        "manual_activation",
        "label_activation",
        "marker_activation",
        "docs_only_no_runtime_action",
        "workflow_deferred_followup",
        "product_runtime_surface",
        "missing_changed_paths",
        "missing_required_capability",
        "unsupported_surface",
    }
)
ACTIVATION_SOURCES = frozenset({"path", "label", "marker", "manual", "none"})
REGISTERED_FALLBACK_AGENT = "agent-coordinator"
REQUIRED_CODE_TARGET_PREFIXES = (
    "scripts/",
    "tests/",
    "docs/orchestration/contracts/",
    "docs/orchestration/",
)
CONCRETE_HYPOTHESIS_TARGET_PREFIXES = (
    "scripts/",
    "tests/",
    "docs/orchestration/contracts/",
    "docs/prompts/",
    "tools/codex_skills/",
    ".agents/skills/",
)
APPROVABLE_PR1_TARGET_PREFIXES = (
    *CONCRETE_HYPOTHESIS_TARGET_PREFIXES,
    "docs/orchestration/",
)
ELIGIBLE_PREFIXES = (
    "scripts/orchestration/",
    "docs/orchestration/",
    "tools/codex_skills/",
    ".agents/skills/",
)
ELIGIBLE_EXACT_PATHS = frozenset(
    {
        "scripts/AGENTS.md",
        "docs/roadmap/BACKLOG_LEDGER.md",
        "RUNBOOK_AGENT.md",
    }
)
PRODUCT_RUNTIME_PREFIXES = ("app/", "core/", "frontend/", "ios/", "providers/", "alembic/")
PRODUCT_RUNTIME_ROOTS = frozenset(prefix.rstrip("/") for prefix in PRODUCT_RUNTIME_PREFIXES)
WORKFLOW_PREFIX = ".github/workflows/"
WORKFLOW_ROOT = WORKFLOW_PREFIX.rstrip("/")

AUTHORITY_TRUE_KEYS = frozenset(
    {
        "read_sanitized_context",
        "emit_local_artifacts",
        "generate_hypotheses",
        "route_to_agents",
        "prepare_human_approval_packet",
    }
)
AUTHORITY_FALSE_KEYS = frozenset(
    {
        "workflow_dispatch",
        "create_branch",
        "write_branch",
        "push",
        "open_pr",
        "open_draft_pr",
        "mark_pr_ready",
        "post_github_comment",
        "resolve_threads",
        "edit_fixed_mapping",
        "generate_patch",
        "execute_pr1_specification",
        "execute_pr2_patch_builder",
        "execute_pr3_promotion",
        "merge",
        "release",
        "claim_merge_readiness",
        "call_provider",
        "call_product_runtime",
        "read_secrets",
        "modify_github_app",
        "modify_slack",
        "modify_workflows",
        "use_semantic_cache",
        "change_openapi",
        "change_client_runtime",
    }
)
AUTHORITY_KEYS = AUTHORITY_TRUE_KEYS | AUTHORITY_FALSE_KEYS
INTAKE_AUTHORITY_TRUE_KEYS = frozenset({"operator_supplied_hypotheses"})
INTAKE_AUTHORITY_FALSE_KEYS = AUTHORITY_FALSE_KEYS | frozenset({"repo_provider_calls"})
INTAKE_AUTHORITY_KEYS = INTAKE_AUTHORITY_TRUE_KEYS | INTAKE_AUTHORITY_FALSE_KEYS
COORDINATOR_DISPATCH_AUTHORITY_TRUE_KEYS = frozenset({"dispatch_to_coordinator"})
COORDINATOR_DISPATCH_AUTHORITY_FALSE_KEYS = AUTHORITY_FALSE_KEYS | frozenset(
    {"execute_agent_tasks", "mutate_code"}
)
COORDINATOR_DISPATCH_AUTHORITY_KEYS = (
    COORDINATOR_DISPATCH_AUTHORITY_TRUE_KEYS | COORDINATOR_DISPATCH_AUTHORITY_FALSE_KEYS
)
CODEX_REVIEW_SINGLE_RUN_POLICY = "single_pass_per_material_diff"
CODEX_SECURITY_RERUN_ALLOWED_REASONS = (
    "security_relevant_diff_changed",
    "coordinator_evidence_backed_reroute",
    "operator_explicit_request",
    "scan_artifact_failed_or_incomplete",
)

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
AGENT_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
SAFE_GIT_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |candidate\.patch|candidate_patch|"
    r"candidate[_. -]?patch|raw[_. -]?(model[_. -]?payload|"
    r"body|prompt|response|context|patch|review|pr)|"
    r"review[_. -]?thread[_. -]?body|pull[_. -]?request[_. -]?body|"
    r"chain[_. -]?of[_. -]?thought|provider[_. -]?payload|"
    r"oracle[_. -]?(stdout|stderr|output)|file://|"
    r"/(?:Users|home|private/var|var/folders|tmp|etc|opt|usr|Volumes|mnt|root|"
    r"workspace|workspaces)(?:/|$)|~[/\\]|[A-Za-z]:[\\/]|\.venv/|\.git/|"
    r"worktrees([:/._-]|$)|merge[-_ ]?ready|ready to merge|mergeable)",
    re.IGNORECASE | re.MULTILINE,
)
UNSAFE_KEY_RE = re.compile(
    r"(?i)(^raw|raw_|_raw|body$|_body$|body_text|body_html|patch_text|raw_patch|"
    r"prompt_text|raw_prompt|provider_payload|oracle_stdout|oracle_stderr|"
    r"secret_value|token_value|access_token|api_key|workflow_log)"
)
SAFE_FALSE_METADATA_KEYS = frozenset({"raw_model_payload_stored"})
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

SOURCE_KEYS = frozenset(
    {
        "repository",
        "pr_number",
        "base_ref",
        "base_sha",
        "head_sha",
        "task_packet_id",
        "generated_at_utc",
    }
)
CLASSIFICATION_KEYS = frozenset(
    {"eligible", "creative_decision", "reason_code", "activation_source", "eligible_surface"}
)
CODEX_SECURITY_REVIEW_KEYS = frozenset(
    {
        "policy",
        "sealed_scan_ref",
        "sealed_scan_fingerprint",
        "security_relevant_diff_changed",
        "rerun_allowed_reasons",
    }
)
CONTEXT_MAP_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "context_id",
        "idempotency_key",
        "source",
        "classification",
        "changed_paths",
        "nearby_repo_refs",
        "test_refs",
        "contract_refs",
        "backlog_refs",
        "review_source_refs",
        "capability_state_ref",
        "philosophical_context_refs",
        "cross_domain_candidate_refs",
        "codex_security_review",
        "authority",
        "sanitized",
    }
)
ANALOGY_KEYS = frozenset(
    {
        "source_domain",
        "analogy",
        "target_repo_surface",
        "why_useful",
        "risk",
        "requires_specialist_agent",
    }
)
HYPOTHESIS_KEYS = frozenset(
    {
        "hypothesis_id",
        "hypothesis_kind",
        "title",
        "target_surfaces",
        "expected_behavior",
        "tests_or_oracles",
        "risk_notes",
        "cross_domain_analogies",
        "falsifier",
        "negative_controls",
        "requires_human_approval",
        "eligible_for_pr1_specification",
        "eligible_for_pr2_patch",
    }
)
OPERATOR_GENERATION_KEYS = frozenset(
    {
        "mode",
        "tool_label",
        "repo_provider_calls",
        "raw_model_payload_stored",
        "semantic_cache_used",
    }
)
OPERATOR_HYPOTHESIS_KEYS = HYPOTHESIS_KEYS - {"hypothesis_id"}
OPERATOR_MODEL_INTAKE_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "intake_id",
        "idempotency_key",
        "context_map_id",
        "context_map_fingerprint",
        "generation",
        "hypothesis_count",
        "hypotheses",
        "authority",
        "sanitized",
    }
)
OPERATOR_MODEL_INTAKE_REQUIRED_KEYS = OPERATOR_MODEL_INTAKE_KEYS - {
    "intake_id",
    "idempotency_key",
    "hypothesis_count",
}
HYPOTHESIS_PACKET_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "packet_id",
        "idempotency_key",
        "context_map_id",
        "context_map_fingerprint",
        "creative_status",
        "reason_code",
        "hypothesis_generation_mode",
        "source_model_intake_fingerprint",
        "repo_provider_calls",
        "raw_model_payload_stored",
        "semantic_cache_used",
        "hypothesis_count",
        "hypotheses",
        "authority",
        "sanitized",
    }
)
ROUTING_ENTRY_KEYS = frozenset(
    {
        "hypothesis_id",
        "primary_agent",
        "review_agents",
        "cross_domain_agents",
        "missing_agent_capabilities",
        "coordinator_decision_required",
        "mutation_authority",
    }
)
AGENT_ROUTING_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "routing_id",
        "idempotency_key",
        "source_hypothesis_packet_id",
        "source_hypothesis_packet_fingerprint",
        "routing",
        "agent_review_mode",
        "authority",
        "sanitized",
    }
)
COORDINATOR_DISPATCH_ENTRY_KEYS = frozenset(
    {
        "hypothesis_id",
        "task_packet_kind",
        "primary_agent",
        "review_agents",
        "cross_domain_agents",
        "missing_agent_capabilities",
        "task_mode",
        "mutation_authority",
        "coordinator_decision_required",
    }
)
COORDINATOR_DISPATCH_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "dispatch_id",
        "idempotency_key",
        "source_hypothesis_packet_id",
        "source_hypothesis_packet_fingerprint",
        "dispatch",
        "authority",
        "sanitized",
    }
)
ORACLE_ATTACHMENT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "attachment_id",
        "idempotency_key",
        "source",
        "runner_mode",
        "oracle_status",
        "result_ref",
        "result_fingerprint",
        "coauthor_required",
        "authority",
        "sanitized",
    }
)
CONSUMPTION_SUMMARY_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "summary_id",
        "idempotency_key",
        "source_hypothesis_packet_id",
        "source_agent_routing_id",
        "oracle_status",
        "hypothesis_count",
        "creative_status",
        "recommended_agents",
        "next_allowed_action",
        "requires_human_approval",
        "coauthor_required",
        "authority",
        "sanitized",
    }
)
APPROVAL_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "approval_id",
        "idempotency_key",
        "hypothesis_id",
        "decision",
        "approved_target_surfaces",
        "approved_agents",
        "approved_by",
        "generate_patch",
        "next_step",
        "authority",
        "sanitized",
    }
)


class ExperimentRunnerCreativeContextContractError(ValueError):
    """Raised when creative-context artifacts violate local authority."""


def _diagnostic_key(key: object) -> str:
    raw = str(key)
    if SECRET_RE.search(raw) or LEAK_TEXT_RE.search(raw) or UNSAFE_KEY_RE.search(raw):
        return "<redacted>"
    return raw


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ExperimentRunnerCreativeContextContractError(
                f"creative-context JSON has duplicate key: {_diagnostic_key(key)}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def read_json_object(path: str | Path) -> dict[str, Any]:
    """Read a JSON object while rejecting duplicate keys."""

    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except ExperimentRunnerCreativeContextContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentRunnerCreativeContextContractError(
            "Unable to read Experiment Runner creative-context JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ExperimentRunnerCreativeContextContractError(
            "Experiment Runner creative-context artifact must be a JSON object."
        )
    return payload


def reject_unsafe_creative_context_value(value: Any, *, label: str) -> None:
    """Reject text that could persist raw bodies, prompts, patches, secrets, or paths."""

    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise ExperimentRunnerCreativeContextContractError(
                f"{label} contains unsafe creative-context text."
            )
        if any(ord(character) < 32 and character not in "\t\n\r" for character in value):
            raise ExperimentRunnerCreativeContextContractError(
                f"{label} contains unsupported control characters."
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_unsafe_creative_context_value(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in SAFE_FALSE_METADATA_KEYS:
                if item is not False:
                    raise ExperimentRunnerCreativeContextContractError(
                        f"{label}.{_diagnostic_key(key)} must be false."
                    )
                continue
            if UNSAFE_KEY_RE.search(str(key)):
                raise ExperimentRunnerCreativeContextContractError(
                    f"{label}.{_diagnostic_key(key)} is an unsupported raw/private field."
                )
            reject_unsafe_creative_context_value(item, label=f"{label}.{_diagnostic_key(key)}")


def default_creative_context_authority() -> dict[str, bool]:
    """Return the only authority this local creative-context layer may claim."""

    authority = {key: False for key in sorted(AUTHORITY_FALSE_KEYS)}
    authority.update({key: True for key in sorted(AUTHORITY_TRUE_KEYS)})
    return dict(sorted(authority.items()))


def default_operator_model_intake_authority() -> dict[str, bool]:
    """Return the authority shape accepted from operator-supplied model JSON."""

    authority = {key: False for key in sorted(INTAKE_AUTHORITY_FALSE_KEYS)}
    authority.update({key: True for key in sorted(INTAKE_AUTHORITY_TRUE_KEYS)})
    return dict(sorted(authority.items()))


def default_coordinator_dispatch_authority() -> dict[str, bool]:
    """Return the authority shape for coordinator handoff artifacts."""

    authority = {key: False for key in sorted(COORDINATOR_DISPATCH_AUTHORITY_FALSE_KEYS)}
    authority.update({key: True for key in sorted(COORDINATOR_DISPATCH_AUTHORITY_TRUE_KEYS)})
    return dict(sorted(authority.items()))


def _require_exact_keys(
    payload: Mapping[str, Any],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.{key} must equal {expected!r}."
        )
    return value


def _require_bool(
    payload: Mapping[str, Any],
    key: str,
    *,
    expected: bool | None,
    label: str,
) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a boolean.")
    if expected is not None and value is not expected:
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be {expected}.")
    return value


def _require_int(
    payload: Mapping[str, Any],
    key: str,
    *,
    min_value: int,
    max_value: int,
    label: str,
) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be an integer.")
    if not min_value <= value <= max_value:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.{key} must be between {min_value} and {max_value}."
        )
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a safe id.")
    reject_unsafe_creative_context_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_token(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not SAFE_TOKEN_RE.fullmatch(normalized):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a safe token.")
    reject_unsafe_creative_context_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_agent_slug(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a string.")
    normalized = value.strip()
    if not AGENT_SLUG_RE.fullmatch(normalized):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be an agent slug.")
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def _require_safe_text(
    payload: Mapping[str, Any],
    key: str,
    *,
    label: str,
    max_chars: int = 360,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a string.")
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must not be empty.")
    if len(normalized) > max_chars:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.{key} must be at most {max_chars} characters."
        )
    reject_unsafe_creative_context_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_optional_safe_text(value: Any, *, label: str, max_chars: int = 360) -> str | None:
    if value is None:
        return None
    return _require_safe_text({"value": value}, "value", label=label, max_chars=max_chars)


def _require_sha(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a 40-char SHA.")
    return value


def _require_optional_sha(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _require_sha(value, label=label)


def _require_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a sha256 digest.")
    return value


def _require_optional_sha256(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _require_sha256(value, label=label)


def _require_timestamp(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a UTC timestamp.")
    return value


def _require_optional_timestamp(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _require_timestamp(value, label=label)


def _require_repository(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not REPOSITORY_RE.fullmatch(value):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be an owner/repo slug.")
    reject_unsafe_creative_context_value(value, label=label)
    return value


def _require_git_ref(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if (
        not normalized
        or not SAFE_GIT_REF_RE.fullmatch(normalized)
        or normalized.startswith(("/", "."))
        or normalized.endswith(("/", ".lock"))
        or ".." in normalized
        or "//" in normalized
        or "@{" in normalized
        or "\\" in normalized
    ):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.{key} must be a safe git ref.")
    reject_unsafe_creative_context_value(normalized, label=f"{label}.{key}")
    return normalized


def _normalize_repo_relative_path(
    raw_path: Any,
    *,
    label: str,
    allow_artifact_ref: bool = False,
) -> str:
    if not isinstance(raw_path, str):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a string.")
    value = raw_path.strip()
    if not value:
        raise ExperimentRunnerCreativeContextContractError(f"{label} must not be empty.")
    if value in {".", "*", "**"}:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} must reference a bounded repo-relative path."
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} must not contain control chars."
        )
    if "\\" in value:
        raise ExperimentRunnerCreativeContextContractError(f"{label} must use POSIX separators.")
    if value.startswith(("/", "~")) or Path(value).is_absolute():
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be repo-relative.")
    if SCHEME_RE.match(value):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must not be a URL.")
    path = PurePosixPath(value)
    if "." in path.parts or ".." in path.parts:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} must not contain traversal segments."
        )
    normalized = path.as_posix()
    if normalized in {".git", ".venv", "worktrees"} or normalized.startswith(
        (".git/", ".venv/", "worktrees/")
    ):
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} points to a forbidden surface."
        )
    if normalized == "artifacts" or normalized.startswith("artifacts/"):
        if not allow_artifact_ref:
            raise ExperimentRunnerCreativeContextContractError(
                f"{label} points to a local artifact path."
            )
        if not normalized.startswith(
            "artifacts/orchestration/experiments/"
        ) and not normalized.startswith("artifacts/orchestration/creative_code/"):
            raise ExperimentRunnerCreativeContextContractError(
                f"{label} must reference an approved local orchestration artifact."
            )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def _normalize_path_list(
    raw_paths: Any,
    *,
    label: str,
    allow_empty: bool,
    allow_artifact_ref: bool = False,
) -> list[str]:
    if not isinstance(raw_paths, list):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a list.")
    if not raw_paths and not allow_empty:
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be non-empty.")
    normalized = [
        _normalize_repo_relative_path(
            item,
            label=f"{label}[{index}]",
            allow_artifact_ref=allow_artifact_ref,
        )
        for index, item in enumerate(raw_paths)
    ]
    if len(normalized) != len(set(normalized)):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must not contain duplicates.")
    return sorted(normalized)


def _normalize_text_list(
    raw_values: Any,
    *,
    label: str,
    allow_empty: bool,
    max_chars: int = 360,
) -> list[str]:
    if not isinstance(raw_values, list):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a list.")
    if not raw_values and not allow_empty:
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be non-empty.")
    normalized = [
        _require_safe_text({"value": item}, "value", label=f"{label}[{index}]", max_chars=max_chars)
        for index, item in enumerate(raw_values)
    ]
    if len(normalized) != len(set(normalized)):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must not contain duplicates.")
    return normalized


def _normalize_agent_slug_list(
    raw_agents: Any,
    *,
    label: str,
    allow_empty: bool,
) -> list[str]:
    if not isinstance(raw_agents, list):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a list.")
    if not raw_agents and not allow_empty:
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be non-empty.")
    agents = [
        _require_agent_slug(agent, label=f"{label}[{index}]")
        for index, agent in enumerate(raw_agents)
    ]
    if len(agents) != len(set(agents)):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must not contain duplicates.")
    return agents


def _is_product_runtime_or_workflow_target(path: str) -> bool:
    return (
        path in PRODUCT_RUNTIME_ROOTS
        or path.startswith(PRODUCT_RUNTIME_PREFIXES)
        or path == WORKFLOW_ROOT
        or path.startswith(WORKFLOW_PREFIX)
    )


def _reject_product_runtime_or_workflow_targets(paths: Sequence[str], *, label: str) -> None:
    forbidden = [path for path in paths if _is_product_runtime_or_workflow_target(path)]
    if forbidden:
        joined = ", ".join(forbidden)
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} must not include product runtime or workflow targets: {joined}."
        )


def _normalize_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, Mapping):
        raise ExperimentRunnerCreativeContextContractError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, AUTHORITY_KEYS, label="authority")
    normalized: dict[str, bool] = {}
    for key in sorted(AUTHORITY_KEYS):
        expected = key in AUTHORITY_TRUE_KEYS
        normalized[key] = _require_bool(raw_authority, key, expected=expected, label="authority")
    return normalized


def _normalize_operator_model_intake_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, Mapping):
        raise ExperimentRunnerCreativeContextContractError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, INTAKE_AUTHORITY_KEYS, label="authority")
    normalized: dict[str, bool] = {}
    for key in sorted(INTAKE_AUTHORITY_KEYS):
        expected = key in INTAKE_AUTHORITY_TRUE_KEYS
        normalized[key] = _require_bool(raw_authority, key, expected=expected, label="authority")
    return normalized


def _normalize_coordinator_dispatch_authority(raw_authority: Any) -> dict[str, bool]:
    if not isinstance(raw_authority, Mapping):
        raise ExperimentRunnerCreativeContextContractError("authority must be a JSON object.")
    _require_exact_keys(
        raw_authority,
        COORDINATOR_DISPATCH_AUTHORITY_KEYS,
        label="authority",
    )
    normalized: dict[str, bool] = {}
    for key in sorted(COORDINATOR_DISPATCH_AUTHORITY_KEYS):
        expected = key in COORDINATOR_DISPATCH_AUTHORITY_TRUE_KEYS
        normalized[key] = _require_bool(raw_authority, key, expected=expected, label="authority")
    return normalized


def _normalize_source(raw_source: Any) -> dict[str, Any]:
    if not isinstance(raw_source, Mapping):
        raise ExperimentRunnerCreativeContextContractError("source must be a JSON object.")
    _require_exact_keys(raw_source, SOURCE_KEYS, label="source")
    return {
        "repository": _require_repository(raw_source["repository"], label="source.repository"),
        "pr_number": (
            None
            if raw_source["pr_number"] is None
            else _require_int(
                raw_source, "pr_number", min_value=1, max_value=1_000_000, label="source"
            )
        ),
        "base_ref": _require_git_ref(raw_source, "base_ref", label="source"),
        "base_sha": _require_optional_sha(raw_source["base_sha"], label="source.base_sha"),
        "head_sha": _require_optional_sha(raw_source["head_sha"], label="source.head_sha"),
        "task_packet_id": (
            None
            if raw_source["task_packet_id"] is None
            else _require_id(raw_source, "task_packet_id", label="source")
        ),
        "generated_at_utc": _require_optional_timestamp(
            raw_source["generated_at_utc"],
            label="source.generated_at_utc",
        ),
    }


def _artifact_identity(
    payload: Mapping[str, Any],
    *,
    artifact_type: str,
    upstream_ids: tuple[str, ...] = (),
    policy_version: str = POLICY_VERSION,
) -> tuple[str, str]:
    fingerprint = cast(str, fingerprint_payload(cast(dict[str, Any], dict(payload))))
    return (
        build_asset_id(
            asset_type=artifact_type,
            rail="orchestration",
            version=SCHEMA_VERSION,
            policy_version=policy_version,
            fingerprint=fingerprint,
            upstream_ids=upstream_ids,
        ),
        build_idempotency_key(
            asset_type=artifact_type,
            rail="orchestration",
            version=SCHEMA_VERSION,
            policy_version=policy_version,
            fingerprint=fingerprint,
            upstream_ids=upstream_ids,
        ),
    )


def classify_creative_context_eligibility(
    changed_paths: Sequence[str],
    *,
    label_enabled: bool = False,
    marker_enabled: bool = False,
    manual_enabled: bool = False,
) -> dict[str, Any]:
    """Classify whether a PR surface requires bounded creative hypotheses."""

    normalized = [
        _normalize_repo_relative_path(path, label=f"changed_paths[{index}]")
        for index, path in enumerate(changed_paths)
    ]
    if not normalized:
        return {
            "eligible": False,
            "creative_decision": "no_creative_action",
            "reason_code": "missing_changed_paths",
            "activation_source": "none",
            "eligible_surface": "",
        }
    if any(path == WORKFLOW_ROOT or path.startswith(WORKFLOW_PREFIX) for path in normalized):
        return {
            "eligible": False,
            "creative_decision": "no_creative_action",
            "reason_code": "workflow_deferred_followup",
            "activation_source": "none",
            "eligible_surface": "",
        }
    if any(
        path in PRODUCT_RUNTIME_ROOTS or path.startswith(PRODUCT_RUNTIME_PREFIXES)
        for path in normalized
    ):
        return {
            "eligible": False,
            "creative_decision": "no_creative_action",
            "reason_code": "product_runtime_surface",
            "activation_source": "none",
            "eligible_surface": "",
        }
    eligible_paths = [
        path
        for path in normalized
        if path in ELIGIBLE_EXACT_PATHS
        or any(path.startswith(prefix) for prefix in ELIGIBLE_PREFIXES)
    ]
    if eligible_paths:
        return {
            "eligible": True,
            "creative_decision": "hypotheses_required",
            "reason_code": "eligible_orchestration_surface",
            "activation_source": "path",
            "eligible_surface": eligible_paths[0],
        }
    if manual_enabled:
        return {
            "eligible": True,
            "creative_decision": "hypotheses_required",
            "reason_code": "manual_activation",
            "activation_source": "manual",
            "eligible_surface": normalized[0],
        }
    if label_enabled:
        return {
            "eligible": True,
            "creative_decision": "hypotheses_required",
            "reason_code": "label_activation",
            "activation_source": "label",
            "eligible_surface": normalized[0],
        }
    if marker_enabled:
        return {
            "eligible": True,
            "creative_decision": "hypotheses_required",
            "reason_code": "marker_activation",
            "activation_source": "marker",
            "eligible_surface": normalized[0],
        }
    if all(path.startswith("docs/") for path in normalized):
        return {
            "eligible": False,
            "creative_decision": "no_creative_action",
            "reason_code": "docs_only_no_runtime_action",
            "activation_source": "none",
            "eligible_surface": "",
        }
    return {
        "eligible": False,
        "creative_decision": "no_creative_action",
        "reason_code": "unsupported_surface",
        "activation_source": "none",
        "eligible_surface": "",
    }


def build_creative_protocol_context_map(
    *,
    changed_paths: Sequence[str],
    repository: str = "Katsiarynakavaleuskaya/PulsePlate",
    pr_number: int | None = None,
    base_ref: str = "main",
    base_sha: str | None = None,
    head_sha: str | None = None,
    task_packet_id: str | None = None,
    generated_at_utc: str | None = None,
    nearby_repo_refs: Sequence[str] = (),
    test_refs: Sequence[str] = (),
    contract_refs: Sequence[str] = (),
    backlog_refs: Sequence[str] = (),
    review_source_refs: Sequence[str] = (),
    capability_state_ref: str | None = None,
    philosophical_context_refs: Sequence[str] = (),
    cross_domain_candidate_refs: Sequence[str] = (),
    label_enabled: bool = False,
    marker_enabled: bool = False,
    manual_enabled: bool = False,
    sealed_codex_security_scan_ref: str | None = None,
    sealed_codex_security_scan_fingerprint: str | None = None,
    security_relevant_diff_changed: bool = False,
) -> dict[str, Any]:
    """Build and validate a sanitized PR creative-context map."""

    normalized_changed_paths = _normalize_path_list(
        list(changed_paths),
        label="changed_paths",
        allow_empty=True,
    )
    normalized_nearby_refs = _normalize_path_list(
        list(nearby_repo_refs),
        label="nearby_repo_refs",
        allow_empty=True,
    )
    normalized_test_refs = _normalize_path_list(
        list(test_refs), label="test_refs", allow_empty=True
    )
    normalized_contract_refs = _normalize_path_list(
        list(contract_refs),
        label="contract_refs",
        allow_empty=True,
    )
    normalized_backlog_refs = _normalize_path_list(
        list(backlog_refs),
        label="backlog_refs",
        allow_empty=True,
    )
    normalized_review_source_refs = _normalize_path_list(
        list(review_source_refs),
        label="review_source_refs",
        allow_empty=True,
        allow_artifact_ref=True,
    )
    normalized_philosophical_refs = _normalize_path_list(
        list(philosophical_context_refs),
        label="philosophical_context_refs",
        allow_empty=True,
    )
    normalized_cross_domain_refs = _normalize_path_list(
        list(cross_domain_candidate_refs),
        label="cross_domain_candidate_refs",
        allow_empty=True,
    )
    normalized_capability_ref = _normalize_optional_artifact_ref(
        capability_state_ref,
        label="capability_state_ref",
    )
    classification = classify_creative_context_eligibility(
        normalized_changed_paths,
        label_enabled=label_enabled,
        marker_enabled=marker_enabled,
        manual_enabled=manual_enabled,
    )
    source = {
        "repository": repository,
        "pr_number": pr_number,
        "base_ref": base_ref,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "task_packet_id": task_packet_id,
        "generated_at_utc": generated_at_utc,
    }
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": CONTEXT_MAP_TYPE,
        "policy_version": POLICY_VERSION,
        "source": source,
        "classification": classification,
        "changed_paths": normalized_changed_paths,
        "nearby_repo_refs": normalized_nearby_refs,
        "test_refs": normalized_test_refs,
        "contract_refs": normalized_contract_refs,
        "backlog_refs": normalized_backlog_refs,
        "review_source_refs": normalized_review_source_refs,
        "capability_state_ref": normalized_capability_ref,
        "philosophical_context_refs": normalized_philosophical_refs,
        "cross_domain_candidate_refs": normalized_cross_domain_refs,
        "codex_security_review": {
            "policy": CODEX_REVIEW_SINGLE_RUN_POLICY,
            "sealed_scan_ref": sealed_codex_security_scan_ref,
            "sealed_scan_fingerprint": sealed_codex_security_scan_fingerprint,
            "security_relevant_diff_changed": security_relevant_diff_changed,
            "rerun_allowed_reasons": list(CODEX_SECURITY_RERUN_ALLOWED_REASONS),
        },
        "authority": default_creative_context_authority(),
        "sanitized": True,
    }
    context_id, idempotency_key = _artifact_identity(body, artifact_type=CONTEXT_MAP_TYPE)
    return validate_creative_protocol_context_map(
        {
            **body,
            "context_id": context_id,
            "idempotency_key": idempotency_key,
        }
    )


def validate_creative_protocol_context_map(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeProtocolContextMap"
    _require_exact_keys(payload, CONTEXT_MAP_KEYS, label=label)
    classification = _normalize_classification(payload["classification"])
    changed_paths = _normalize_path_list(
        payload["changed_paths"],
        label="changed_paths",
        allow_empty=not classification["eligible"],
    )
    if classification["eligible"] and not changed_paths:
        raise ExperimentRunnerCreativeContextContractError(
            "eligible context maps require changed_paths."
        )
    if classification["eligible"] and not any(
        path.startswith(REQUIRED_CODE_TARGET_PREFIXES) for path in changed_paths
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "eligible context maps require a concrete code, test, workflow, or contract surface."
        )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", CONTEXT_MAP_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "context_id": _require_id(payload, "context_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source": _normalize_source(payload["source"]),
        "classification": classification,
        "changed_paths": changed_paths,
        "nearby_repo_refs": _normalize_path_list(
            payload["nearby_repo_refs"],
            label="nearby_repo_refs",
            allow_empty=True,
        ),
        "test_refs": _normalize_path_list(
            payload["test_refs"], label="test_refs", allow_empty=True
        ),
        "contract_refs": _normalize_path_list(
            payload["contract_refs"],
            label="contract_refs",
            allow_empty=True,
        ),
        "backlog_refs": _normalize_path_list(
            payload["backlog_refs"],
            label="backlog_refs",
            allow_empty=True,
        ),
        "review_source_refs": _normalize_path_list(
            payload["review_source_refs"],
            label="review_source_refs",
            allow_empty=True,
            allow_artifact_ref=True,
        ),
        "capability_state_ref": _normalize_optional_artifact_ref(
            payload["capability_state_ref"],
            label="capability_state_ref",
        ),
        "philosophical_context_refs": _normalize_path_list(
            payload["philosophical_context_refs"],
            label="philosophical_context_refs",
            allow_empty=True,
        ),
        "cross_domain_candidate_refs": _normalize_path_list(
            payload["cross_domain_candidate_refs"],
            label="cross_domain_candidate_refs",
            allow_empty=True,
        ),
        "codex_security_review": _normalize_codex_security_review(payload["codex_security_review"]),
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_identity(
        normalized,
        id_key="context_id",
        idempotency_key="idempotency_key",
        artifact_type=CONTEXT_MAP_TYPE,
    )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def _normalize_classification(raw_classification: Any) -> dict[str, Any]:
    if not isinstance(raw_classification, Mapping):
        raise ExperimentRunnerCreativeContextContractError("classification must be a JSON object.")
    _require_exact_keys(raw_classification, CLASSIFICATION_KEYS, label="classification")
    creative_decision = _require_token(
        raw_classification, "creative_decision", label="classification"
    )
    if creative_decision not in {"hypotheses_required", "no_creative_action", "blocked"}:
        raise ExperimentRunnerCreativeContextContractError(
            "classification.creative_decision is unsupported."
        )
    reason_code = _require_token(raw_classification, "reason_code", label="classification")
    if reason_code not in REASON_CODES:
        raise ExperimentRunnerCreativeContextContractError(
            "classification.reason_code is unsupported."
        )
    activation_source = _require_token(
        raw_classification,
        "activation_source",
        label="classification",
    )
    if activation_source not in ACTIVATION_SOURCES:
        raise ExperimentRunnerCreativeContextContractError(
            "classification.activation_source is unsupported."
        )
    eligible = _require_bool(raw_classification, "eligible", expected=None, label="classification")
    eligible_surface = str(raw_classification["eligible_surface"]).strip()
    if eligible:
        _normalize_repo_relative_path(eligible_surface, label="classification.eligible_surface")
        if creative_decision != "hypotheses_required":
            raise ExperimentRunnerCreativeContextContractError(
                "eligible classification requires hypotheses_required."
            )
    elif eligible_surface:
        raise ExperimentRunnerCreativeContextContractError(
            "ineligible classification must not set eligible_surface."
        )
    return {
        "eligible": eligible,
        "creative_decision": creative_decision,
        "reason_code": reason_code,
        "activation_source": activation_source,
        "eligible_surface": eligible_surface,
    }


def _normalize_codex_security_review(raw_review: Any) -> dict[str, Any]:
    if not isinstance(raw_review, Mapping):
        raise ExperimentRunnerCreativeContextContractError(
            "codex_security_review must be a JSON object."
        )
    _require_exact_keys(raw_review, CODEX_SECURITY_REVIEW_KEYS, label="codex_security_review")
    policy = _require_const(
        raw_review,
        "policy",
        CODEX_REVIEW_SINGLE_RUN_POLICY,
        label="codex_security_review",
    )
    raw_reasons = raw_review["rerun_allowed_reasons"]
    if (
        not isinstance(raw_reasons, list)
        or tuple(raw_reasons) != CODEX_SECURITY_RERUN_ALLOWED_REASONS
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "codex_security_review.rerun_allowed_reasons must match the single-pass policy."
        )
    return {
        "policy": policy,
        "sealed_scan_ref": _normalize_optional_artifact_ref(
            raw_review["sealed_scan_ref"],
            label="codex_security_review.sealed_scan_ref",
        ),
        "sealed_scan_fingerprint": _require_optional_sha256(
            raw_review["sealed_scan_fingerprint"],
            label="codex_security_review.sealed_scan_fingerprint",
        ),
        "security_relevant_diff_changed": _require_bool(
            raw_review,
            "security_relevant_diff_changed",
            expected=None,
            label="codex_security_review",
        ),
        "rerun_allowed_reasons": list(CODEX_SECURITY_RERUN_ALLOWED_REASONS),
    }


def _normalize_optional_artifact_ref(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    return _normalize_repo_relative_path(value, label=label, allow_artifact_ref=True)


def build_experiment_runner_pr_oracle_attachment(
    *,
    source: Mapping[str, Any],
    oracle_status: str = "skipped",
    result_ref: str | None = None,
    result_fingerprint: str | None = None,
    coauthor_required: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ORACLE_ATTACHMENT_TYPE,
        "policy_version": POLICY_VERSION,
        "source": dict(source),
        "runner_mode": "oracle_only_governance_reviewer",
        "oracle_status": oracle_status,
        "result_ref": result_ref,
        "result_fingerprint": result_fingerprint,
        "coauthor_required": coauthor_required,
        "authority": default_creative_context_authority(),
        "sanitized": True,
    }
    attachment_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=ORACLE_ATTACHMENT_TYPE,
    )
    return validate_experiment_runner_pr_oracle_attachment(
        {
            **body,
            "attachment_id": attachment_id,
            "idempotency_key": idempotency_key,
        }
    )


def validate_experiment_runner_pr_oracle_attachment(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "ExperimentRunnerPROracleAttachment"
    _require_exact_keys(payload, ORACLE_ATTACHMENT_KEYS, label=label)
    oracle_status = _require_token(payload, "oracle_status", label=label)
    if oracle_status not in ORACLE_STATUSES:
        raise ExperimentRunnerCreativeContextContractError(f"{label}.oracle_status is unsupported.")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            ORACLE_ATTACHMENT_TYPE,
            label=label,
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "attachment_id": _require_id(payload, "attachment_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source": _normalize_source(payload["source"]),
        "runner_mode": _require_const(
            payload,
            "runner_mode",
            "oracle_only_governance_reviewer",
            label=label,
        ),
        "oracle_status": oracle_status,
        "result_ref": _normalize_optional_artifact_ref(payload["result_ref"], label="result_ref"),
        "result_fingerprint": _require_optional_sha256(
            payload["result_fingerprint"],
            label="result_fingerprint",
        ),
        "coauthor_required": _require_bool(
            payload,
            "coauthor_required",
            expected=None,
            label=label,
        ),
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if normalized["oracle_status"] == "accepted" and not normalized["result_ref"]:
        raise ExperimentRunnerCreativeContextContractError(
            "accepted oracle attachments require result_ref."
        )
    if normalized["oracle_status"] == "accepted" and not normalized["result_fingerprint"]:
        raise ExperimentRunnerCreativeContextContractError(
            "accepted oracle attachments require result_fingerprint."
        )
    _validate_identity(
        normalized,
        id_key="attachment_id",
        idempotency_key="idempotency_key",
        artifact_type=ORACLE_ATTACHMENT_TYPE,
    )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def build_creative_hypothesis_packet(
    context_map: Mapping[str, Any],
    *,
    hypothesis_count: int = 4,
) -> dict[str, Any]:
    """Build bounded deterministic hypotheses for an eligible context map."""

    context = validate_creative_protocol_context_map(context_map)
    classification = context["classification"]
    if not classification["eligible"]:
        body: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": HYPOTHESIS_PACKET_TYPE,
            "policy_version": POLICY_VERSION,
            "context_map_id": context["context_id"],
            "context_map_fingerprint": cast(str, fingerprint_payload(context)),
            "creative_status": "no_creative_action",
            "reason_code": classification["reason_code"],
            "hypothesis_generation_mode": "deterministic_templates_v1",
            "source_model_intake_fingerprint": None,
            "repo_provider_calls": False,
            "raw_model_payload_stored": False,
            "semantic_cache_used": False,
            "hypothesis_count": 0,
            "hypotheses": [],
            "authority": default_creative_context_authority(),
            "sanitized": True,
        }
        packet_id, idempotency_key = _artifact_identity(
            body,
            artifact_type=HYPOTHESIS_PACKET_TYPE,
            upstream_ids=(context["context_id"],),
        )
        return validate_creative_hypothesis_packet(
            {
                **body,
                "packet_id": packet_id,
                "idempotency_key": idempotency_key,
            }
        )
    if hypothesis_count < 3 or hypothesis_count > 5:
        raise ExperimentRunnerCreativeContextContractError(
            "Eligible creative contexts require 3 to 5 hypotheses."
        )
    hypotheses = _generate_hypotheses(context, hypothesis_count=hypothesis_count)
    body = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": HYPOTHESIS_PACKET_TYPE,
        "policy_version": POLICY_VERSION,
        "context_map_id": context["context_id"],
        "context_map_fingerprint": cast(str, fingerprint_payload(context)),
        "creative_status": "hypotheses_generated",
        "reason_code": classification["reason_code"],
        "hypothesis_generation_mode": "deterministic_templates_v1",
        "source_model_intake_fingerprint": None,
        "repo_provider_calls": False,
        "raw_model_payload_stored": False,
        "semantic_cache_used": False,
        "hypothesis_count": len(hypotheses),
        "hypotheses": hypotheses,
        "authority": default_creative_context_authority(),
        "sanitized": True,
    }
    packet_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=HYPOTHESIS_PACKET_TYPE,
        upstream_ids=(context["context_id"],),
    )
    return validate_creative_hypothesis_packet(
        {
            **body,
            "packet_id": packet_id,
            "idempotency_key": idempotency_key,
        }
    )


def build_creative_hypothesis_packet_from_model_intake(
    context_map: Mapping[str, Any],
    model_intake: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize operator-supplied local model hypotheses into a governed packet."""

    context = validate_creative_protocol_context_map(context_map)
    if not context["classification"]["eligible"]:
        raise ExperimentRunnerCreativeContextContractError(
            "operator model intake requires an eligible creative context map."
        )
    intake = validate_creative_hypothesis_operator_model_intake(
        model_intake,
        context_map=context,
    )
    hypotheses = [
        _normalize_operator_hypothesis_as_packet_row(row, index=index)
        for index, row in enumerate(intake["hypotheses"], start=1)
    ]
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": HYPOTHESIS_PACKET_TYPE,
        "policy_version": POLICY_VERSION,
        "context_map_id": context["context_id"],
        "context_map_fingerprint": cast(str, fingerprint_payload(context)),
        "creative_status": "hypotheses_generated",
        "reason_code": context["classification"]["reason_code"],
        "hypothesis_generation_mode": "operator_validated_intake_v1",
        "source_model_intake_fingerprint": cast(str, fingerprint_payload(intake)),
        "repo_provider_calls": False,
        "raw_model_payload_stored": False,
        "semantic_cache_used": False,
        "hypothesis_count": len(hypotheses),
        "hypotheses": hypotheses,
        "authority": default_creative_context_authority(),
        "sanitized": True,
    }
    packet_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=HYPOTHESIS_PACKET_TYPE,
        upstream_ids=(context["context_id"],),
    )
    return validate_creative_hypothesis_packet(
        {
            **body,
            "packet_id": packet_id,
            "idempotency_key": idempotency_key,
        }
    )


def validate_creative_hypothesis_operator_model_intake(
    payload: Mapping[str, Any],
    *,
    context_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    label = "CreativeHypothesisOperatorModelIntake"
    actual = set(payload)
    missing = sorted(OPERATOR_MODEL_INTAKE_REQUIRED_KEYS - actual)
    extra = sorted(actual - OPERATOR_MODEL_INTAKE_KEYS)
    if missing:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} has unsupported fields: {', '.join(extra)}"
        )
    for optional_identity_key in ("intake_id", "idempotency_key"):
        if optional_identity_key in payload:
            _require_id(payload, optional_identity_key, label=label)
    raw_hypotheses = payload["hypotheses"]
    if not isinstance(raw_hypotheses, list):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.hypotheses must be a list.")
    hypotheses = [
        _normalize_operator_hypothesis(row, label=f"hypotheses[{index}]")
        for index, row in enumerate(raw_hypotheses)
    ]
    if "hypothesis_count" in payload:
        hypothesis_count = _require_int(
            payload,
            "hypothesis_count",
            min_value=3,
            max_value=5,
            label=label,
        )
    else:
        hypothesis_count = len(hypotheses)
        if not 3 <= hypothesis_count <= 5:
            raise ExperimentRunnerCreativeContextContractError(
                "operator model intake hypotheses must contain 3 to 5 rows."
            )
    if hypothesis_count != len(hypotheses):
        raise ExperimentRunnerCreativeContextContractError(
            "operator model intake hypothesis_count must match hypotheses."
        )
    normalized_body = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            OPERATOR_MODEL_INTAKE_TYPE,
            label=label,
        ),
        "policy_version": _require_const(
            payload,
            "policy_version",
            OPERATOR_MODEL_INTAKE_POLICY_VERSION,
            label=label,
        ),
        "context_map_id": _require_id(payload, "context_map_id", label=label),
        "context_map_fingerprint": _require_sha256(
            payload["context_map_fingerprint"],
            label="context_map_fingerprint",
        ),
        "generation": _normalize_operator_generation(payload["generation"]),
        "hypothesis_count": hypothesis_count,
        "hypotheses": hypotheses,
        "authority": _normalize_operator_model_intake_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    intake_id, idempotency_key = _artifact_identity(
        normalized_body,
        artifact_type=OPERATOR_MODEL_INTAKE_TYPE,
        upstream_ids=(normalized_body["context_map_id"],),
        policy_version=OPERATOR_MODEL_INTAKE_POLICY_VERSION,
    )
    normalized = {
        **normalized_body,
        "intake_id": intake_id,
        "idempotency_key": idempotency_key,
    }
    if context_map is not None:
        context = validate_creative_protocol_context_map(context_map)
        if normalized["context_map_id"] != context["context_id"]:
            raise ExperimentRunnerCreativeContextContractError(
                "operator model intake context_map_id must match context map."
            )
        if normalized["context_map_fingerprint"] != fingerprint_payload(context):
            raise ExperimentRunnerCreativeContextContractError(
                "operator model intake context_map_fingerprint must match context map."
            )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def _normalize_operator_generation(raw_generation: Any) -> dict[str, Any]:
    if not isinstance(raw_generation, Mapping):
        raise ExperimentRunnerCreativeContextContractError("generation must be a JSON object.")
    _require_exact_keys(raw_generation, OPERATOR_GENERATION_KEYS, label="generation")
    mode = _require_const(
        raw_generation,
        "mode",
        "operator_supplied_model_json",
        label="generation",
    )
    tool_label = _require_token(raw_generation, "tool_label", label="generation")
    if tool_label not in OPERATOR_TOOL_LABELS:
        raise ExperimentRunnerCreativeContextContractError("generation.tool_label is unsupported.")
    return {
        "mode": mode,
        "tool_label": tool_label,
        "repo_provider_calls": _require_bool(
            raw_generation,
            "repo_provider_calls",
            expected=False,
            label="generation",
        ),
        "raw_model_payload_stored": _require_bool(
            raw_generation,
            "raw_model_payload_stored",
            expected=False,
            label="generation",
        ),
        "semantic_cache_used": _require_bool(
            raw_generation,
            "semantic_cache_used",
            expected=False,
            label="generation",
        ),
    }


def _normalize_operator_hypothesis(raw_hypothesis: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_hypothesis, Mapping):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_hypothesis, OPERATOR_HYPOTHESIS_KEYS, label=label)
    normalized = _normalize_hypothesis(
        {
            **raw_hypothesis,
            "hypothesis_id": "hyp-operator-normalization-placeholder",
        },
        label=label,
    )
    if not all(
        target.startswith(CONCRETE_HYPOTHESIS_TARGET_PREFIXES)
        for target in normalized["target_surfaces"]
    ):
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.target_surfaces must all be concrete code, test, contract, "
            "agent, or prompt/program target."
        )
    return {key: value for key, value in normalized.items() if key != "hypothesis_id"}


def _normalize_operator_hypothesis_as_packet_row(
    raw_hypothesis: Mapping[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    hypothesis = dict(raw_hypothesis)
    hypothesis["hypothesis_id"] = f"hyp-{index:03d}"
    return _normalize_hypothesis(hypothesis, label=f"hypotheses[{index - 1}]")


def _generate_hypotheses(
    context: Mapping[str, Any], *, hypothesis_count: int
) -> list[dict[str, Any]]:
    changed_paths = list(context["changed_paths"])
    tests_or_oracles = list(context["test_refs"]) or [
        "tests/test_experiment_runner_pr_creative_context.py"
    ]
    primary_target = _first_concrete_target(changed_paths)
    templates = [
        (
            "architecture",
            "Bounded context expansion before creative generation",
            "Context maps reduce uncertainty before any hypothesis is routed to role agents.",
            "information_theory",
            "Context maps act like compression with provenance, reducing irrelevant entropy before generation.",
            "The analogy fails if compression hides required repo evidence or source ownership.",
        ),
        (
            "security_authority",
            "Least-privilege creative authority boundary",
            "Generated hypotheses remain advisory until a human approves a later specification handoff.",
            "security",
            "A least-privilege capability gate grants read and planning authority without write authority.",
            "The analogy fails if advisory output is later treated as patch or PR mutation permission.",
        ),
        (
            "testing_oracle",
            "Oracle-backed falsifiability for generated hypotheses",
            "Every hypothesis names deterministic tests or oracle commands that could falsify it.",
            "testing",
            "A falsifier works like a regression test: useful only when it can fail the proposal.",
            "The analogy fails if tests are merely documentation links without executable checks.",
        ),
        (
            "creative_protocol",
            "Skeptic critique before specification handoff",
            "Coordinator routes each hypothesis to specialist critique before PR-1 specification.",
            "philosophy",
            "Hegelian opposition maps to skeptic review before synthesis and promotion.",
            "The analogy fails if critique becomes decorative and cannot block promotion.",
        ),
        (
            "scientific_stats",
            "Feedback-loop measurement for creative routing",
            "Routing artifacts record missing capability and review outcomes for later calibration.",
            "biology",
            "Homeostatic feedback maps to lifecycle repair loops that adapt without overcorrecting.",
            "The analogy fails if feedback is mistaken for product runtime truth.",
        ),
    ]
    hypotheses: list[dict[str, Any]] = []
    for index, template in enumerate(templates[:hypothesis_count], start=1):
        kind, title, expected, domain, analogy, analogy_risk = template
        target = (
            primary_target if index <= 2 else _target_for_kind(kind, changed_paths, primary_target)
        )
        hypothesis_id = f"hyp-{index:03d}"
        hypotheses.append(
            {
                "hypothesis_id": hypothesis_id,
                "hypothesis_kind": kind,
                "title": title,
                "target_surfaces": [target],
                "expected_behavior": expected,
                "tests_or_oracles": tests_or_oracles,
                "risk_notes": [
                    "Must stay local-only and sanitized.",
                    "Must not be treated as code mutation approval.",
                ],
                "cross_domain_analogies": [
                    {
                        "source_domain": domain,
                        "analogy": analogy,
                        "target_repo_surface": target,
                        "why_useful": "It produces a concrete implementation hypothesis for PR governance.",
                        "risk": analogy_risk,
                        "requires_specialist_agent": True,
                    }
                ],
                "falsifier": "Fails if the validator cannot reject unsafe authority or missing evidence.",
                "negative_controls": [
                    "Unsanitized PR or review text must be rejected.",
                    "Patch generation authority must remain false.",
                ],
                "requires_human_approval": True,
                "eligible_for_pr1_specification": True,
                "eligible_for_pr2_patch": False,
            }
        )
    return hypotheses


def _first_concrete_target(paths: Sequence[str]) -> str:
    for prefix in REQUIRED_CODE_TARGET_PREFIXES:
        for path in paths:
            if path.startswith(prefix):
                return path
    return paths[0]


def _target_for_kind(kind: str, paths: Sequence[str], fallback: str) -> str:
    if kind == "testing_oracle":
        for path in paths:
            if path.startswith("tests/"):
                return path
        return "tests/test_experiment_runner_pr_creative_context.py"
    if kind == "creative_protocol":
        for path in paths:
            if path.startswith("docs/orchestration/"):
                return path
    if kind == "scientific_stats":
        return "docs/roadmap/BACKLOG_LEDGER.md"
    return fallback


def validate_creative_hypothesis_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeHypothesisPacket"
    _require_exact_keys(payload, HYPOTHESIS_PACKET_KEYS, label=label)
    creative_status = _require_token(payload, "creative_status", label=label)
    if creative_status not in CREATIVE_STATUSES:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.creative_status is unsupported."
        )
    reason_code = _require_token(payload, "reason_code", label=label)
    if reason_code not in REASON_CODES:
        raise ExperimentRunnerCreativeContextContractError(f"{label}.reason_code is unsupported.")
    generation_mode = _require_token(payload, "hypothesis_generation_mode", label=label)
    if generation_mode not in HYPOTHESIS_GENERATION_MODES:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.hypothesis_generation_mode is unsupported."
        )
    raw_hypotheses = payload["hypotheses"]
    if not isinstance(raw_hypotheses, list):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.hypotheses must be a list.")
    hypotheses = [
        _normalize_hypothesis(row, label=f"hypotheses[{index}]")
        for index, row in enumerate(raw_hypotheses)
    ]
    hypothesis_ids = [row["hypothesis_id"] for row in hypotheses]
    if len(hypothesis_ids) != len(set(hypothesis_ids)):
        raise ExperimentRunnerCreativeContextContractError("hypothesis_id values must be unique.")
    hypothesis_count = _require_int(
        payload,
        "hypothesis_count",
        min_value=0,
        max_value=5,
        label=label,
    )
    if hypothesis_count != len(hypotheses):
        raise ExperimentRunnerCreativeContextContractError(
            "hypothesis_count must match hypotheses."
        )
    if creative_status == "hypotheses_generated" and not 3 <= hypothesis_count <= 5:
        raise ExperimentRunnerCreativeContextContractError(
            "generated hypothesis packets require 3 to 5 hypotheses."
        )
    if creative_status == "hypotheses_generated" and not any(
        target.startswith(CONCRETE_HYPOTHESIS_TARGET_PREFIXES)
        for hypothesis in hypotheses
        for target in hypothesis["target_surfaces"]
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "generated hypothesis packets require at least one concrete code, "
            "test, contract, agent, or prompt/program target."
        )
    if creative_status == "no_creative_action" and hypothesis_count != 0:
        raise ExperimentRunnerCreativeContextContractError(
            "no_creative_action packets must not contain hypotheses."
        )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            HYPOTHESIS_PACKET_TYPE,
            label=label,
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "packet_id": _require_id(payload, "packet_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "context_map_id": _require_id(payload, "context_map_id", label=label),
        "context_map_fingerprint": _require_sha256(
            payload["context_map_fingerprint"],
            label="context_map_fingerprint",
        ),
        "creative_status": creative_status,
        "reason_code": reason_code,
        "hypothesis_generation_mode": generation_mode,
        "source_model_intake_fingerprint": _require_optional_sha256(
            payload["source_model_intake_fingerprint"],
            label="source_model_intake_fingerprint",
        ),
        "repo_provider_calls": _require_bool(
            payload,
            "repo_provider_calls",
            expected=False,
            label=label,
        ),
        "raw_model_payload_stored": _require_bool(
            payload,
            "raw_model_payload_stored",
            expected=False,
            label=label,
        ),
        "semantic_cache_used": _require_bool(
            payload,
            "semantic_cache_used",
            expected=False,
            label=label,
        ),
        "hypothesis_count": hypothesis_count,
        "hypotheses": hypotheses,
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if (
        normalized["hypothesis_generation_mode"] == "operator_validated_intake_v1"
        and not normalized["source_model_intake_fingerprint"]
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "operator_validated_intake_v1 packets require source_model_intake_fingerprint."
        )
    if (
        normalized["hypothesis_generation_mode"] == "operator_validated_intake_v1"
        and normalized["creative_status"] != "hypotheses_generated"
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "operator_validated_intake_v1 packets require hypotheses_generated."
        )
    if (
        normalized["hypothesis_generation_mode"] == "deterministic_templates_v1"
        and normalized["source_model_intake_fingerprint"]
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "deterministic template packets must not carry source_model_intake_fingerprint."
        )
    _validate_identity(
        normalized,
        id_key="packet_id",
        idempotency_key="idempotency_key",
        artifact_type=HYPOTHESIS_PACKET_TYPE,
        upstream_ids=(normalized["context_map_id"],),
    )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def _normalize_hypothesis(raw_hypothesis: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(raw_hypothesis, Mapping):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_hypothesis, HYPOTHESIS_KEYS, label=label)
    hypothesis_kind = _require_token(raw_hypothesis, "hypothesis_kind", label=label)
    if hypothesis_kind not in HYPOTHESIS_KINDS:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.hypothesis_kind is unsupported."
        )
    target_surfaces = _normalize_path_list(
        raw_hypothesis["target_surfaces"],
        label=f"{label}.target_surfaces",
        allow_empty=False,
    )
    _reject_product_runtime_or_workflow_targets(
        target_surfaces,
        label=f"{label}.target_surfaces",
    )
    tests_or_oracles = _normalize_path_list(
        raw_hypothesis["tests_or_oracles"],
        label=f"{label}.tests_or_oracles",
        allow_empty=False,
    )
    _reject_product_runtime_or_workflow_targets(
        tests_or_oracles,
        label=f"{label}.tests_or_oracles",
    )
    return {
        "hypothesis_id": _require_id(raw_hypothesis, "hypothesis_id", label=label),
        "hypothesis_kind": hypothesis_kind,
        "title": _require_safe_text(raw_hypothesis, "title", label=label),
        "target_surfaces": target_surfaces,
        "expected_behavior": _require_safe_text(
            raw_hypothesis,
            "expected_behavior",
            label=label,
            max_chars=360,
        ),
        "tests_or_oracles": tests_or_oracles,
        "risk_notes": _normalize_text_list(
            raw_hypothesis["risk_notes"],
            label=f"{label}.risk_notes",
            allow_empty=False,
        ),
        "cross_domain_analogies": _normalize_analogies(
            raw_hypothesis["cross_domain_analogies"], label=label
        ),
        "falsifier": _require_safe_text(
            raw_hypothesis,
            "falsifier",
            label=label,
            max_chars=360,
        ),
        "negative_controls": _normalize_text_list(
            raw_hypothesis["negative_controls"],
            label=f"{label}.negative_controls",
            allow_empty=False,
        ),
        "requires_human_approval": _require_bool(
            raw_hypothesis,
            "requires_human_approval",
            expected=True,
            label=label,
        ),
        "eligible_for_pr1_specification": _require_bool(
            raw_hypothesis,
            "eligible_for_pr1_specification",
            expected=True,
            label=label,
        ),
        "eligible_for_pr2_patch": _require_bool(
            raw_hypothesis,
            "eligible_for_pr2_patch",
            expected=False,
            label=label,
        ),
    }


def _normalize_analogies(raw_analogies: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_analogies, list) or not raw_analogies:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.cross_domain_analogies must be a non-empty list."
        )
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(raw_analogies):
        row_label = f"{label}.cross_domain_analogies[{index}]"
        if not isinstance(row, Mapping):
            raise ExperimentRunnerCreativeContextContractError(
                f"{row_label} must be a JSON object."
            )
        _require_exact_keys(row, ANALOGY_KEYS, label=row_label)
        source_domain = str(row["source_domain"])
        if source_domain not in SOURCE_DOMAINS:
            raise ExperimentRunnerCreativeContextContractError(
                f"{row_label}.source_domain is unsupported."
            )
        target_repo_surface = _normalize_repo_relative_path(
            row["target_repo_surface"],
            label=f"{row_label}.target_repo_surface",
        )
        _reject_product_runtime_or_workflow_targets(
            [target_repo_surface],
            label=f"{row_label}.target_repo_surface",
        )
        normalized.append(
            {
                "source_domain": source_domain,
                "analogy": _require_safe_text(row, "analogy", label=row_label, max_chars=360),
                "target_repo_surface": target_repo_surface,
                "why_useful": _require_safe_text(row, "why_useful", label=row_label),
                "risk": _require_safe_text(row, "risk", label=row_label, max_chars=360),
                "requires_specialist_agent": _require_bool(
                    row,
                    "requires_specialist_agent",
                    expected=None,
                    label=row_label,
                ),
            }
        )
    return normalized


def build_creative_hypothesis_agent_routing(
    hypothesis_packet: Mapping[str, Any],
    *,
    registered_agents: set[str] | None = None,
) -> dict[str, Any]:
    packet = validate_creative_hypothesis_packet(hypothesis_packet)
    agents = registered_agents if registered_agents is not None else load_inventory_agents()
    routing = [
        _route_hypothesis(hypothesis, registered_agents=agents)
        for hypothesis in packet["hypotheses"]
    ]
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": AGENT_ROUTING_TYPE,
        "policy_version": POLICY_VERSION,
        "source_hypothesis_packet_id": packet["packet_id"],
        "source_hypothesis_packet_fingerprint": cast(str, fingerprint_payload(packet)),
        "routing": routing,
        "agent_review_mode": "critique_refine_only",
        "authority": default_creative_context_authority(),
        "sanitized": True,
    }
    routing_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=AGENT_ROUTING_TYPE,
        upstream_ids=(packet["packet_id"],),
    )
    return validate_creative_hypothesis_agent_routing(
        {
            **body,
            "routing_id": routing_id,
            "idempotency_key": idempotency_key,
        },
        registered_agents=agents,
    )


def _route_hypothesis(
    hypothesis: Mapping[str, Any],
    *,
    registered_agents: set[str],
) -> dict[str, Any]:
    route_map: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
        "architecture": (
            "architecture-specialist",
            ("security-auditor", "qa-engineer-agent"),
            (),
            (),
        ),
        "security_authority": (
            "security-auditor",
            ("bug-hunter", "architecture-specialist"),
            (),
            (),
        ),
        "testing_oracle": (
            "qa-engineer-agent",
            ("bug-hunter", "logic-agent"),
            (),
            (),
        ),
        "creative_protocol": (
            "philosophy-agent",
            ("logic-agent",),
            ("epistemology-discovery-agent",),
            (),
        ),
        "scientific_stats": (
            "data-scientist-agent",
            ("epistemology-discovery-agent",),
            (),
            ("experiment-design-stats-agent",),
        ),
    }
    primary, review_agents, cross_agents, missing_candidates = route_map[
        cast(str, hypothesis["hypothesis_kind"])
    ]
    missing = [agent for agent in missing_candidates if agent not in registered_agents]
    primary_agent = primary if primary in registered_agents else REGISTERED_FALLBACK_AGENT
    review = [agent for agent in review_agents if agent in registered_agents]
    cross = [agent for agent in cross_agents if agent in registered_agents]
    if primary not in registered_agents:
        missing.append(primary)
    already_routed = {primary_agent, *review}
    for analogy in hypothesis["cross_domain_analogies"]:
        if not analogy["requires_specialist_agent"]:
            continue
        candidates = ANALOGY_DOMAIN_AGENT_CANDIDATES[cast(str, analogy["source_domain"])]
        routed_for_analogy = False
        for candidate in candidates:
            if candidate in registered_agents:
                if candidate not in already_routed:
                    cross.append(candidate)
                    already_routed.add(candidate)
                routed_for_analogy = True
        if not routed_for_analogy:
            missing.extend(candidates)
    return {
        "hypothesis_id": hypothesis["hypothesis_id"],
        "primary_agent": primary_agent,
        "review_agents": sorted(set(review)),
        "cross_domain_agents": sorted(set(cross)),
        "missing_agent_capabilities": sorted(set(missing)),
        "coordinator_decision_required": True,
        "mutation_authority": False,
    }


def validate_creative_hypothesis_agent_routing(
    payload: Mapping[str, Any],
    *,
    registered_agents: set[str] | None = None,
) -> dict[str, Any]:
    label = "CreativeHypothesisAgentRouting"
    _require_exact_keys(payload, AGENT_ROUTING_KEYS, label=label)
    agents = registered_agents if registered_agents is not None else load_inventory_agents()
    raw_routing = payload["routing"]
    if not isinstance(raw_routing, list):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.routing must be a list.")
    routing = [
        _normalize_routing_entry(row, label=f"routing[{index}]", registered_agents=agents)
        for index, row in enumerate(raw_routing)
    ]
    if len([row["hypothesis_id"] for row in routing]) != len(
        {row["hypothesis_id"] for row in routing}
    ):
        raise ExperimentRunnerCreativeContextContractError("routing hypothesis ids must be unique.")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", AGENT_ROUTING_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "routing_id": _require_id(payload, "routing_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source_hypothesis_packet_id": _require_id(
            payload,
            "source_hypothesis_packet_id",
            label=label,
        ),
        "source_hypothesis_packet_fingerprint": _require_sha256(
            payload["source_hypothesis_packet_fingerprint"],
            label="source_hypothesis_packet_fingerprint",
        ),
        "routing": routing,
        "agent_review_mode": _require_const(
            payload,
            "agent_review_mode",
            "critique_refine_only",
            label=label,
        ),
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_identity(
        normalized,
        id_key="routing_id",
        idempotency_key="idempotency_key",
        artifact_type=AGENT_ROUTING_TYPE,
        upstream_ids=(normalized["source_hypothesis_packet_id"],),
    )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def build_creative_hypothesis_coordinator_dispatch(
    *,
    hypothesis_packet: Mapping[str, Any],
    routing: Mapping[str, Any],
    registered_agents: set[str] | None = None,
) -> dict[str, Any]:
    """Build a coordinator-owned critique/refine handoff without execution authority."""

    packet = validate_creative_hypothesis_packet(hypothesis_packet)
    agents = registered_agents if registered_agents is not None else load_inventory_agents()
    routing_payload = validate_creative_hypothesis_agent_routing(
        routing,
        registered_agents=agents,
    )
    if routing_payload["source_hypothesis_packet_id"] != packet["packet_id"]:
        raise ExperimentRunnerCreativeContextContractError(
            "coordinator dispatch routing must reference the supplied hypothesis packet."
        )
    if routing_payload["source_hypothesis_packet_fingerprint"] != fingerprint_payload(packet):
        raise ExperimentRunnerCreativeContextContractError(
            "coordinator dispatch routing fingerprint must match the supplied packet."
        )
    packet_hypothesis_ids = {row["hypothesis_id"] for row in packet["hypotheses"]}
    routing_hypothesis_ids = {row["hypothesis_id"] for row in routing_payload["routing"]}
    if routing_hypothesis_ids != packet_hypothesis_ids:
        raise ExperimentRunnerCreativeContextContractError(
            "coordinator dispatch rows must match hypothesis packet rows."
        )
    dispatch = [
        {
            "hypothesis_id": row["hypothesis_id"],
            "task_packet_kind": "TASK_PACKET_V1",
            "primary_agent": row["primary_agent"],
            "review_agents": row["review_agents"],
            "cross_domain_agents": row["cross_domain_agents"],
            "missing_agent_capabilities": row["missing_agent_capabilities"],
            "task_mode": "critique_refine_only",
            "mutation_authority": False,
            "coordinator_decision_required": True,
        }
        for row in routing_payload["routing"]
    ]
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": COORDINATOR_DISPATCH_TYPE,
        "policy_version": COORDINATOR_DISPATCH_POLICY_VERSION,
        "source_hypothesis_packet_id": packet["packet_id"],
        "source_hypothesis_packet_fingerprint": cast(str, fingerprint_payload(packet)),
        "dispatch": dispatch,
        "authority": default_coordinator_dispatch_authority(),
        "sanitized": True,
    }
    dispatch_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=COORDINATOR_DISPATCH_TYPE,
        upstream_ids=(packet["packet_id"],),
        policy_version=COORDINATOR_DISPATCH_POLICY_VERSION,
    )
    return validate_creative_hypothesis_coordinator_dispatch(
        {
            **body,
            "dispatch_id": dispatch_id,
            "idempotency_key": idempotency_key,
        },
        registered_agents=agents,
    )


def validate_creative_hypothesis_coordinator_dispatch(
    payload: Mapping[str, Any],
    *,
    registered_agents: set[str] | None = None,
) -> dict[str, Any]:
    label = "CreativeHypothesisCoordinatorDispatch"
    _require_exact_keys(payload, COORDINATOR_DISPATCH_KEYS, label=label)
    agents = registered_agents if registered_agents is not None else load_inventory_agents()
    raw_dispatch = payload["dispatch"]
    if not isinstance(raw_dispatch, list):
        raise ExperimentRunnerCreativeContextContractError(f"{label}.dispatch must be a list.")
    if not raw_dispatch:
        raise ExperimentRunnerCreativeContextContractError(
            "coordinator dispatch must contain at least one dispatch entry."
        )
    dispatch = [
        _normalize_coordinator_dispatch_entry(
            row,
            label=f"dispatch[{index}]",
            registered_agents=agents,
        )
        for index, row in enumerate(raw_dispatch)
    ]
    if len([row["hypothesis_id"] for row in dispatch]) != len(
        {row["hypothesis_id"] for row in dispatch}
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "coordinator dispatch hypothesis ids must be unique."
        )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            COORDINATOR_DISPATCH_TYPE,
            label=label,
        ),
        "policy_version": _require_const(
            payload,
            "policy_version",
            COORDINATOR_DISPATCH_POLICY_VERSION,
            label=label,
        ),
        "dispatch_id": _require_id(payload, "dispatch_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source_hypothesis_packet_id": _require_id(
            payload,
            "source_hypothesis_packet_id",
            label=label,
        ),
        "source_hypothesis_packet_fingerprint": _require_sha256(
            payload["source_hypothesis_packet_fingerprint"],
            label="source_hypothesis_packet_fingerprint",
        ),
        "dispatch": dispatch,
        "authority": _normalize_coordinator_dispatch_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_identity(
        normalized,
        id_key="dispatch_id",
        idempotency_key="idempotency_key",
        artifact_type=COORDINATOR_DISPATCH_TYPE,
        upstream_ids=(normalized["source_hypothesis_packet_id"],),
        policy_version=COORDINATOR_DISPATCH_POLICY_VERSION,
    )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def _normalize_coordinator_dispatch_entry(
    raw_entry: Any,
    *,
    label: str,
    registered_agents: set[str],
) -> dict[str, Any]:
    if not isinstance(raw_entry, Mapping):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_entry, COORDINATOR_DISPATCH_ENTRY_KEYS, label=label)
    primary_agent = _require_token(raw_entry, "primary_agent", label=label)
    if primary_agent not in registered_agents:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.primary_agent is not registered."
        )
    return {
        "hypothesis_id": _require_id(raw_entry, "hypothesis_id", label=label),
        "task_packet_kind": _require_const(
            raw_entry,
            "task_packet_kind",
            "TASK_PACKET_V1",
            label=label,
        ),
        "primary_agent": primary_agent,
        "review_agents": _normalize_agent_list(
            raw_entry["review_agents"],
            label=f"{label}.review_agents",
            registered_agents=registered_agents,
        ),
        "cross_domain_agents": _normalize_agent_list(
            raw_entry["cross_domain_agents"],
            label=f"{label}.cross_domain_agents",
            registered_agents=registered_agents,
        ),
        "missing_agent_capabilities": _normalize_agent_slug_list(
            raw_entry["missing_agent_capabilities"],
            label=f"{label}.missing_agent_capabilities",
            allow_empty=True,
        ),
        "task_mode": _require_const(
            raw_entry,
            "task_mode",
            "critique_refine_only",
            label=label,
        ),
        "mutation_authority": _require_bool(
            raw_entry,
            "mutation_authority",
            expected=False,
            label=label,
        ),
        "coordinator_decision_required": _require_bool(
            raw_entry,
            "coordinator_decision_required",
            expected=True,
            label=label,
        ),
    }


def _normalize_routing_entry(
    raw_entry: Any,
    *,
    label: str,
    registered_agents: set[str],
) -> dict[str, Any]:
    if not isinstance(raw_entry, Mapping):
        raise ExperimentRunnerCreativeContextContractError(f"{label} must be a JSON object.")
    _require_exact_keys(raw_entry, ROUTING_ENTRY_KEYS, label=label)
    primary_agent = _require_token(raw_entry, "primary_agent", label=label)
    if primary_agent not in registered_agents:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.primary_agent is not registered."
        )
    review_agents = _normalize_agent_list(
        raw_entry["review_agents"],
        label=f"{label}.review_agents",
        registered_agents=registered_agents,
    )
    cross_domain_agents = _normalize_agent_list(
        raw_entry["cross_domain_agents"],
        label=f"{label}.cross_domain_agents",
        registered_agents=registered_agents,
    )
    missing = _normalize_agent_slug_list(
        raw_entry["missing_agent_capabilities"],
        label=f"{label}.missing_agent_capabilities",
        allow_empty=True,
    )
    return {
        "hypothesis_id": _require_id(raw_entry, "hypothesis_id", label=label),
        "primary_agent": primary_agent,
        "review_agents": review_agents,
        "cross_domain_agents": cross_domain_agents,
        "missing_agent_capabilities": missing,
        "coordinator_decision_required": _require_bool(
            raw_entry,
            "coordinator_decision_required",
            expected=True,
            label=label,
        ),
        "mutation_authority": _require_bool(
            raw_entry,
            "mutation_authority",
            expected=False,
            label=label,
        ),
    }


def _normalize_agent_list(
    raw_agents: Any,
    *,
    label: str,
    registered_agents: set[str],
) -> list[str]:
    agents = _normalize_agent_slug_list(raw_agents, label=label, allow_empty=True)
    unknown = [agent for agent in agents if agent not in registered_agents]
    if unknown:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label} contains unregistered agents: {', '.join(unknown)}"
        )
    return agents


def build_agent_consumption_summary(
    *,
    hypothesis_packet: Mapping[str, Any],
    routing: Mapping[str, Any],
    oracle_attachment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = validate_creative_hypothesis_packet(hypothesis_packet)
    routing_payload = validate_creative_hypothesis_agent_routing(routing)
    if routing_payload["source_hypothesis_packet_id"] != packet["packet_id"]:
        raise ExperimentRunnerCreativeContextContractError(
            "agent routing must reference the supplied hypothesis packet."
        )
    packet_fingerprint = cast(str, fingerprint_payload(packet))
    if routing_payload["source_hypothesis_packet_fingerprint"] != packet_fingerprint:
        raise ExperimentRunnerCreativeContextContractError(
            "agent routing fingerprint must match the supplied hypothesis packet."
        )
    packet_hypothesis_ids = {row["hypothesis_id"] for row in packet["hypotheses"]}
    routing_hypothesis_ids = {row["hypothesis_id"] for row in routing_payload["routing"]}
    if routing_hypothesis_ids != packet_hypothesis_ids:
        raise ExperimentRunnerCreativeContextContractError(
            "agent routing rows must match hypothesis packet rows."
        )
    oracle_status = "skipped"
    coauthor_required = False
    if oracle_attachment is not None:
        oracle = validate_experiment_runner_pr_oracle_attachment(oracle_attachment)
        oracle_status = oracle["oracle_status"]
        coauthor_required = bool(oracle["coauthor_required"])
    recommended_agents = sorted(
        {row["primary_agent"] for row in routing_payload["routing"]}
        | {
            agent
            for row in routing_payload["routing"]
            for agent in [*row["review_agents"], *row["cross_domain_agents"]]
        }
    )
    if packet["creative_status"] == "hypotheses_generated":
        next_action = "agent_review"
        requires_human_approval = True
    elif packet["creative_status"] == "blocked":
        next_action = "hold"
        requires_human_approval = True
    else:
        next_action = "no_action"
        requires_human_approval = False
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": CONSUMPTION_SUMMARY_TYPE,
        "policy_version": POLICY_VERSION,
        "source_hypothesis_packet_id": packet["packet_id"],
        "source_agent_routing_id": routing_payload["routing_id"],
        "oracle_status": oracle_status,
        "hypothesis_count": packet["hypothesis_count"],
        "creative_status": packet["creative_status"],
        "recommended_agents": recommended_agents,
        "next_allowed_action": next_action,
        "requires_human_approval": requires_human_approval,
        "coauthor_required": coauthor_required,
        "authority": default_creative_context_authority(),
        "sanitized": True,
    }
    summary_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=CONSUMPTION_SUMMARY_TYPE,
        upstream_ids=(packet["packet_id"], routing_payload["routing_id"]),
    )
    return validate_agent_consumption_summary(
        {
            **body,
            "summary_id": summary_id,
            "idempotency_key": idempotency_key,
        }
    )


def validate_agent_consumption_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeHypothesisAgentConsumptionSummary"
    _require_exact_keys(payload, CONSUMPTION_SUMMARY_KEYS, label=label)
    oracle_status = _require_token(payload, "oracle_status", label=label)
    if oracle_status not in ORACLE_STATUSES:
        raise ExperimentRunnerCreativeContextContractError(f"{label}.oracle_status is unsupported.")
    creative_status = _require_token(payload, "creative_status", label=label)
    if creative_status not in CREATIVE_STATUSES:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.creative_status is unsupported."
        )
    next_action = _require_token(payload, "next_allowed_action", label=label)
    if next_action not in SUMMARY_NEXT_ACTIONS:
        raise ExperimentRunnerCreativeContextContractError(
            f"{label}.next_allowed_action is unsupported."
        )
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(
            payload,
            "artifact_type",
            CONSUMPTION_SUMMARY_TYPE,
            label=label,
        ),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "summary_id": _require_id(payload, "summary_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "source_hypothesis_packet_id": _require_id(
            payload,
            "source_hypothesis_packet_id",
            label=label,
        ),
        "source_agent_routing_id": _require_id(
            payload,
            "source_agent_routing_id",
            label=label,
        ),
        "oracle_status": oracle_status,
        "hypothesis_count": _require_int(
            payload,
            "hypothesis_count",
            min_value=0,
            max_value=5,
            label=label,
        ),
        "creative_status": creative_status,
        "recommended_agents": _normalize_text_list(
            payload["recommended_agents"],
            label="recommended_agents",
            allow_empty=True,
        ),
        "next_allowed_action": next_action,
        "requires_human_approval": _require_bool(
            payload,
            "requires_human_approval",
            expected=None,
            label=label,
        ),
        "coauthor_required": _require_bool(
            payload,
            "coauthor_required",
            expected=None,
            label=label,
        ),
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    _validate_identity(
        normalized,
        id_key="summary_id",
        idempotency_key="idempotency_key",
        artifact_type=CONSUMPTION_SUMMARY_TYPE,
        upstream_ids=(
            normalized["source_hypothesis_packet_id"],
            normalized["source_agent_routing_id"],
        ),
    )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def build_creative_hypothesis_approval(
    *,
    hypothesis_id: str,
    decision: str,
    approved_target_surfaces: Sequence[str] = (),
    approved_agents: Sequence[str] = (),
    approved_by: str = "human_operator",
    next_step: str = "no_action",
) -> dict[str, Any]:
    normalized_targets = _normalize_path_list(
        list(approved_target_surfaces),
        label="approved_target_surfaces",
        allow_empty=True,
    )
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": APPROVAL_TYPE,
        "policy_version": POLICY_VERSION,
        "hypothesis_id": hypothesis_id,
        "decision": decision,
        "approved_target_surfaces": normalized_targets,
        "approved_agents": _normalize_text_list(
            list(approved_agents),
            label="approved_agents",
            allow_empty=True,
        ),
        "approved_by": approved_by,
        "generate_patch": False,
        "next_step": next_step,
        "authority": default_creative_context_authority(),
        "sanitized": True,
    }
    approval_id, idempotency_key = _artifact_identity(
        body,
        artifact_type=APPROVAL_TYPE,
        upstream_ids=(hypothesis_id,),
    )
    return validate_creative_hypothesis_approval(
        {
            **body,
            "approval_id": approval_id,
            "idempotency_key": idempotency_key,
        }
    )


def validate_creative_hypothesis_approval(payload: Mapping[str, Any]) -> dict[str, Any]:
    label = "CreativeHypothesisApproval"
    _require_exact_keys(payload, APPROVAL_KEYS, label=label)
    decision = _require_token(payload, "decision", label=label)
    if decision not in APPROVAL_DECISIONS:
        raise ExperimentRunnerCreativeContextContractError(f"{label}.decision is unsupported.")
    next_step = _require_token(payload, "next_step", label=label)
    if next_step not in APPROVAL_NEXT_STEPS:
        raise ExperimentRunnerCreativeContextContractError(f"{label}.next_step is unsupported.")
    normalized = {
        "schema_version": _require_const(payload, "schema_version", SCHEMA_VERSION, label=label),
        "artifact_type": _require_const(payload, "artifact_type", APPROVAL_TYPE, label=label),
        "policy_version": _require_const(payload, "policy_version", POLICY_VERSION, label=label),
        "approval_id": _require_id(payload, "approval_id", label=label),
        "idempotency_key": _require_id(payload, "idempotency_key", label=label),
        "hypothesis_id": _require_id(payload, "hypothesis_id", label=label),
        "decision": decision,
        "approved_target_surfaces": _normalize_path_list(
            payload["approved_target_surfaces"],
            label="approved_target_surfaces",
            allow_empty=True,
        ),
        "approved_agents": _normalize_text_list(
            payload["approved_agents"],
            label="approved_agents",
            allow_empty=True,
        ),
        "approved_by": _require_const(payload, "approved_by", "human_operator", label=label),
        "generate_patch": _require_bool(payload, "generate_patch", expected=False, label=label),
        "next_step": next_step,
        "authority": _normalize_authority(payload["authority"]),
        "sanitized": _require_bool(payload, "sanitized", expected=True, label=label),
    }
    if normalized["decision"] == "approve_for_pr1_specification" and (
        normalized["next_step"] != "create_pr1_specification"
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "approval for PR-1 specification must set next_step=create_pr1_specification."
        )
    if normalized["decision"] != "approve_for_pr1_specification" and (
        normalized["next_step"] == "create_pr1_specification"
    ):
        raise ExperimentRunnerCreativeContextContractError(
            "only approve_for_pr1_specification may create PR-1 specification."
        )
    if normalized["decision"] == "reject" and normalized["next_step"] != "no_action":
        raise ExperimentRunnerCreativeContextContractError("rejected approvals must set no_action.")
    if normalized["decision"] == "defer" and normalized["next_step"] != "defer":
        raise ExperimentRunnerCreativeContextContractError("deferred approvals must set defer.")
    if normalized["decision"] == "approve_for_pr1_specification":
        if not normalized["approved_target_surfaces"]:
            raise ExperimentRunnerCreativeContextContractError(
                "PR-1 approval requires at least one approved target surface."
            )
        invalid_targets = [
            target
            for target in normalized["approved_target_surfaces"]
            if not target.startswith(APPROVABLE_PR1_TARGET_PREFIXES)
            or target.startswith(PRODUCT_RUNTIME_PREFIXES)
            or target.startswith(WORKFLOW_PREFIX)
        ]
        if invalid_targets:
            raise ExperimentRunnerCreativeContextContractError(
                "PR-1 approval targets must stay on creative-context orchestration surfaces."
            )
    elif normalized["approved_target_surfaces"] or normalized["approved_agents"]:
        raise ExperimentRunnerCreativeContextContractError(
            "reject/defer approvals must not carry approved targets or agents."
        )
    _validate_identity(
        normalized,
        id_key="approval_id",
        idempotency_key="idempotency_key",
        artifact_type=APPROVAL_TYPE,
        upstream_ids=(normalized["hypothesis_id"],),
    )
    reject_unsafe_creative_context_value(normalized, label=label)
    return normalized


def _validate_identity(
    normalized: Mapping[str, Any],
    *,
    id_key: str,
    idempotency_key: str,
    artifact_type: str,
    upstream_ids: tuple[str, ...] = (),
    policy_version: str = POLICY_VERSION,
) -> None:
    body = dict(normalized)
    observed_id = str(body.pop(id_key))
    observed_idempotency_key = str(body.pop(idempotency_key))
    expected_id, expected_idempotency_key = _artifact_identity(
        body,
        artifact_type=artifact_type,
        upstream_ids=upstream_ids,
        policy_version=policy_version,
    )
    if observed_id != expected_id:
        raise ExperimentRunnerCreativeContextContractError(f"{id_key} does not match content.")
    if observed_idempotency_key != expected_idempotency_key:
        raise ExperimentRunnerCreativeContextContractError(
            f"{idempotency_key} does not match content."
        )


def validate_artifact_by_type(artifact_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    validators: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
        ORACLE_ATTACHMENT_TYPE: validate_experiment_runner_pr_oracle_attachment,
        CONTEXT_MAP_TYPE: validate_creative_protocol_context_map,
        HYPOTHESIS_PACKET_TYPE: validate_creative_hypothesis_packet,
        AGENT_ROUTING_TYPE: validate_creative_hypothesis_agent_routing,
        CONSUMPTION_SUMMARY_TYPE: validate_agent_consumption_summary,
        APPROVAL_TYPE: validate_creative_hypothesis_approval,
        OPERATOR_MODEL_INTAKE_TYPE: validate_creative_hypothesis_operator_model_intake,
        COORDINATOR_DISPATCH_TYPE: validate_creative_hypothesis_coordinator_dispatch,
    }
    if artifact_type not in validators:
        supported = ", ".join(sorted(validators))
        raise ExperimentRunnerCreativeContextContractError(
            f"Unsupported artifact type: {artifact_type}. Supported: {supported}"
        )
    return validators[artifact_type](payload)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Experiment Runner PR creative-context artifacts."
    )
    parser.add_argument("--artifact-type", required=True)
    parser.add_argument("--path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        validate_artifact_by_type(args.artifact_type, read_json_object(args.path))
    except ExperimentRunnerCreativeContextContractError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: experiment-runner creative-context contract valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
