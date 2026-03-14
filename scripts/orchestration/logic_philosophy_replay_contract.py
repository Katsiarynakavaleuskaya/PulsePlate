"""Offline replay contract for the logic + philosophy reliability lane.

RU: Fail-closed contract helpers for the offline replay + ablation lane.
EN: Fail-closed contract helpers for the offline replay + ablation lane.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPLAY_SCHEMA_VERSION = "1.0"
REPLAY_MODE = "offline_replay_ablation"
REPLAY_ARMS: tuple[str, ...] = (
    "A0_control",
    "A1_logic",
    "A2_philosophy",
    "A3_combined",
)
PRIMARY_METRICS: tuple[str, ...] = (
    "correctness_pass_rate",
    "unsupported_claim_rate",
    "contradiction_rate",
    "first_pass_readiness_proxy",
)
DEFAULT_NETWORK_BUDGET = 0


def load_json_document(path: Path, *, label: str) -> dict[str, Any]:
    """RU: Загружает JSON object. EN: Load a JSON object from disk."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} file does not exist: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _require_non_empty_string(value: Any, *, label: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{label} must be non-empty.")
    return normalized


def _normalize_snippet_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    normalized: list[str] = []
    for item in value:
        snippet = _require_non_empty_string(item, label=label)
        if snippet not in normalized:
            normalized.append(snippet)
    if not normalized:
        raise ValueError(f"{label} must contain at least one non-empty item.")
    return normalized


def _validate_arm_outputs(value: Any, *, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    missing_arms = [arm for arm in REPLAY_ARMS if arm not in value]
    if missing_arms:
        joined = ", ".join(missing_arms)
        raise ValueError(f"{label} is missing required arms: {joined}")
    extra_arms = sorted(set(value) - set(REPLAY_ARMS))
    if extra_arms:
        joined = ", ".join(extra_arms)
        raise ValueError(f"{label} contains unsupported arms: {joined}")
    return {
        arm: _require_non_empty_string(value[arm], label=f"{label}.{arm}") for arm in REPLAY_ARMS
    }


def _validate_network_budget(value: Any, *, label: str) -> int:
    try:
        budget = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer.") from exc
    if budget != DEFAULT_NETWORK_BUDGET:
        raise ValueError(f"{label} must equal {DEFAULT_NETWORK_BUDGET} for wave 1 offline replay.")
    return budget


def validate_replay_cases_document(payload: Any) -> dict[str, Any]:
    """Validate the immutable replay corpus document."""

    if not isinstance(payload, dict):
        raise ValueError("Replay cases document must be a JSON object.")
    schema_version = _require_non_empty_string(
        payload.get("schema_version", ""),
        label="Replay cases document schema_version",
    )
    if schema_version != REPLAY_SCHEMA_VERSION:
        raise ValueError(
            "Replay cases document schema_version must equal " f"{REPLAY_SCHEMA_VERSION!r}."
        )
    mode = _require_non_empty_string(payload.get("mode", ""), label="Replay cases document mode")
    if mode != REPLAY_MODE:
        raise ValueError(f"Replay cases document mode must equal {REPLAY_MODE!r}.")
    network_budget = _validate_network_budget(
        payload.get("network_budget", DEFAULT_NETWORK_BUDGET),
        label="Replay cases document network_budget",
    )
    primary_metrics = _normalize_snippet_list(
        payload.get("primary_metrics", []),
        label="Replay cases document primary_metrics",
    )
    if tuple(primary_metrics) != PRIMARY_METRICS:
        raise ValueError(
            "Replay cases document primary_metrics must equal the canonical list: "
            f"{', '.join(PRIMARY_METRICS)}"
        )
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Replay cases document cases must be a non-empty list.")
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_case in enumerate(raw_cases):
        label = f"Replay case #{index + 1}"
        if not isinstance(raw_case, dict):
            raise ValueError(f"{label} must be an object.")
        case_id = _require_non_empty_string(raw_case.get("case_id", ""), label=f"{label} case_id")
        if case_id in seen_ids:
            raise ValueError(f"Replay case ids must be unique; duplicate: {case_id}")
        seen_ids.add(case_id)
        required_facts = _normalize_snippet_list(
            raw_case.get("required_facts", []),
            label=f"{label} required_facts",
        )
        supported_claims = _normalize_snippet_list(
            raw_case.get("supported_claims", []),
            label=f"{label} supported_claims",
        )
        for fact in required_facts:
            if fact not in supported_claims:
                supported_claims.append(fact)
        cases.append(
            {
                "case_id": case_id,
                "prompt": _require_non_empty_string(
                    raw_case.get("prompt", ""), label=f"{label} prompt"
                ),
                "required_facts": required_facts,
                "supported_claims": supported_claims,
                "usefulness_markers": _normalize_snippet_list(
                    raw_case.get("usefulness_markers", []),
                    label=f"{label} usefulness_markers",
                ),
                "arm_outputs": _validate_arm_outputs(
                    raw_case.get("arm_outputs", {}),
                    label=f"{label} arm_outputs",
                ),
            }
        )
    return {
        "schema_version": schema_version,
        "mode": mode,
        "network_budget": network_budget,
        "primary_metrics": list(PRIMARY_METRICS),
        "cases": cases,
    }


def validate_negative_controls_document(payload: Any) -> dict[str, Any]:
    """Validate the immutable known-good negative-control document."""

    if not isinstance(payload, dict):
        raise ValueError("Replay negative controls document must be a JSON object.")
    schema_version = _require_non_empty_string(
        payload.get("schema_version", ""),
        label="Replay negative controls document schema_version",
    )
    if schema_version != REPLAY_SCHEMA_VERSION:
        raise ValueError(
            "Replay negative controls document schema_version must equal "
            f"{REPLAY_SCHEMA_VERSION!r}."
        )
    mode = _require_non_empty_string(
        payload.get("mode", ""),
        label="Replay negative controls document mode",
    )
    if mode != REPLAY_MODE:
        raise ValueError(f"Replay negative controls document mode must equal {REPLAY_MODE!r}.")
    network_budget = _validate_network_budget(
        payload.get("network_budget", DEFAULT_NETWORK_BUDGET),
        label="Replay negative controls document network_budget",
    )
    raw_controls = payload.get("known_good_controls")
    if not isinstance(raw_controls, list) or not raw_controls:
        raise ValueError("Replay negative controls document must include known_good_controls.")
    controls: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_control in enumerate(raw_controls):
        label = f"Replay negative control #{index + 1}"
        if not isinstance(raw_control, dict):
            raise ValueError(f"{label} must be an object.")
        control_id = _require_non_empty_string(
            raw_control.get("control_id", ""),
            label=f"{label} control_id",
        )
        if control_id in seen_ids:
            raise ValueError(f"Replay negative control ids must be unique; duplicate: {control_id}")
        seen_ids.add(control_id)
        controls.append(
            {
                "control_id": control_id,
                "answer": _require_non_empty_string(
                    raw_control.get("answer", ""), label=f"{label} answer"
                ),
                "supported_claims": _normalize_snippet_list(
                    raw_control.get("supported_claims", []),
                    label=f"{label} supported_claims",
                ),
                "usefulness_markers": _normalize_snippet_list(
                    raw_control.get("usefulness_markers", []),
                    label=f"{label} usefulness_markers",
                ),
            }
        )
    return {
        "schema_version": schema_version,
        "mode": mode,
        "network_budget": network_budget,
        "known_good_controls": controls,
    }
