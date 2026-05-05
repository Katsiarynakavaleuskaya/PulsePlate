#!/usr/bin/env python3
"""Canonical eval validity contract for item-level invariance and mutation.

RU: Контракт для item-level validity: инвариантность, мутация, worst-case.
EN: Contract for item-level validity: invariance, mutation, worst-case reporting.

This module provides TypedDict schemas, validation helpers, and pure metric
functions for the evaluation-validity substrate.  It does NOT call any
network endpoints, LLM providers, or external services.  All computation
is deterministic and offline.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Literal, Sequence, TypedDict, get_args

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------
EVAL_VALIDITY_SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Literal types
# ---------------------------------------------------------------------------
VariantFamily = Literal["canonical", "invariance", "mutation"]
VARIANT_FAMILIES: tuple[str, ...] = get_args(VariantFamily)

ExpectedRelation = Literal[
    "same_decision",
    "same_grade_band",
    "controlled_drop",
]
EXPECTED_RELATIONS: tuple[str, ...] = get_args(ExpectedRelation)

# ---------------------------------------------------------------------------
# Record schemas (TypedDict)
# ---------------------------------------------------------------------------


class EvalVariantRecord(TypedDict):
    """Canonical eval item/variant record.

    RU: Описывает исходный eval-item и его вариант для проверки устойчивости.
    EN: Describes a canonical eval item and a variant for robustness checks.
    """

    canonical_id: str
    variant_id: str
    variant_family: VariantFamily
    transform_type: str
    expected_relation: ExpectedRelation
    slice_tags: list[str]
    input_payload: dict[str, Any]


class EvalOutcomeRecord(TypedDict):
    """Item-level eval outcome.

    RU: Результат одного eval-варианта.
    EN: Result for one eval variant.
    """

    canonical_id: str
    variant_id: str
    variant_family: VariantFamily
    transform_type: str
    passed: bool
    score: float
    decision: str
    slice_tags: list[str]


# ---------------------------------------------------------------------------
# Validation helpers (fail-closed)
# ---------------------------------------------------------------------------

_VARIANT_RECORD_REQUIRED_KEYS: frozenset[str] = frozenset(
    EvalVariantRecord.__annotations__,
)
_OUTCOME_RECORD_REQUIRED_KEYS: frozenset[str] = frozenset(
    EvalOutcomeRecord.__annotations__,
)


def _require_str(value: Any, *, field: str, record_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{record_name}.{field} must be str, got {type(value).__name__}")
    return value


def _require_list_of_str(value: Any, *, field: str, record_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{record_name}.{field} must be list[str], got {type(value).__name__}")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{record_name}.{field} must contain only str values")
    return list(value)


def _require_dict(value: Any, *, field: str, record_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{record_name}.{field} must be dict, got {type(value).__name__}")
    return dict(value)


def validate_eval_variant_record(
    raw: dict[str, Any],
) -> EvalVariantRecord:
    """Parse and validate a raw dict into an ``EvalVariantRecord``.

    Raises ``ValueError`` on missing keys or invalid literal values.
    """
    missing = _VARIANT_RECORD_REQUIRED_KEYS - raw.keys()
    if missing:
        raise ValueError(f"EvalVariantRecord missing keys: {sorted(missing)}")
    if raw["variant_family"] not in VARIANT_FAMILIES:
        raise ValueError(
            f"Invalid variant_family={raw['variant_family']!r}; "
            f"expected one of {VARIANT_FAMILIES}"
        )
    if raw["expected_relation"] not in EXPECTED_RELATIONS:
        raise ValueError(
            f"Invalid expected_relation={raw['expected_relation']!r}; "
            f"expected one of {EXPECTED_RELATIONS}"
        )
    return EvalVariantRecord(
        canonical_id=_require_str(
            raw["canonical_id"], field="canonical_id", record_name="EvalVariantRecord"
        ),
        variant_id=_require_str(
            raw["variant_id"], field="variant_id", record_name="EvalVariantRecord"
        ),
        variant_family=raw["variant_family"],
        transform_type=_require_str(
            raw["transform_type"], field="transform_type", record_name="EvalVariantRecord"
        ),
        expected_relation=raw["expected_relation"],
        slice_tags=_require_list_of_str(
            raw["slice_tags"], field="slice_tags", record_name="EvalVariantRecord"
        ),
        input_payload=_require_dict(
            raw["input_payload"], field="input_payload", record_name="EvalVariantRecord"
        ),
    )


def validate_eval_outcome_record(
    raw: dict[str, Any],
) -> EvalOutcomeRecord:
    """Parse and validate a raw dict into an ``EvalOutcomeRecord``.

    Raises ``ValueError`` on missing keys or invalid literal values.
    """
    missing = _OUTCOME_RECORD_REQUIRED_KEYS - raw.keys()
    if missing:
        raise ValueError(f"EvalOutcomeRecord missing keys: {sorted(missing)}")
    if raw["variant_family"] not in VARIANT_FAMILIES:
        raise ValueError(
            f"Invalid variant_family={raw['variant_family']!r}; "
            f"expected one of {VARIANT_FAMILIES}"
        )
    passed = raw["passed"]
    if not isinstance(passed, bool):
        raise ValueError(f"EvalOutcomeRecord.passed must be bool, got {type(passed).__name__}")
    score = raw["score"]
    if isinstance(score, bool):
        raise ValueError("EvalOutcomeRecord.score must be numeric, got bool")
    if not isinstance(score, (int, float)):
        raise ValueError(f"EvalOutcomeRecord.score must be numeric, got {type(score).__name__}")
    if not math.isfinite(score):
        raise ValueError(f"EvalOutcomeRecord.score must be finite, got {score!r}")
    return EvalOutcomeRecord(
        canonical_id=_require_str(
            raw["canonical_id"], field="canonical_id", record_name="EvalOutcomeRecord"
        ),
        variant_id=_require_str(
            raw["variant_id"], field="variant_id", record_name="EvalOutcomeRecord"
        ),
        variant_family=raw["variant_family"],
        transform_type=_require_str(
            raw["transform_type"], field="transform_type", record_name="EvalOutcomeRecord"
        ),
        passed=passed,
        score=float(score),
        decision=_require_str(raw["decision"], field="decision", record_name="EvalOutcomeRecord"),
        slice_tags=_require_list_of_str(
            raw["slice_tags"], field="slice_tags", record_name="EvalOutcomeRecord"
        ),
    )


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


def group_outcomes_by_canonical_id(
    outcomes: Sequence[EvalOutcomeRecord],
) -> dict[str, list[EvalOutcomeRecord]]:
    """Group outcome records by ``canonical_id`` with stable insertion order."""
    groups: dict[str, list[EvalOutcomeRecord]] = {}
    for rec in outcomes:
        groups.setdefault(rec["canonical_id"], []).append(rec)
    return groups


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def compute_invariance_score(
    outcomes: Sequence[EvalOutcomeRecord],
) -> float:
    """Fraction of invariance variants that agree with their canonical item.

    Only considers ``variant_family == "invariance"`` rows.  For each
    invariance row the canonical row must exist in *outcomes* with the same
    ``canonical_id`` and ``variant_family == "canonical"``.  Agreement is
    defined as having the same ``decision`` string.

    Returns 0.0 when there are no invariance rows.
    """
    canonical_decisions: dict[str, str] = {}
    for rec in outcomes:
        if rec["variant_family"] == "canonical":
            canonical_decisions[rec["canonical_id"]] = rec["decision"]

    invariance_rows = [r for r in outcomes if r["variant_family"] == "invariance"]
    if not invariance_rows:
        return 0.0

    agree = sum(
        1 for r in invariance_rows if canonical_decisions.get(r["canonical_id"]) == r["decision"]
    )
    return round(agree / len(invariance_rows), 6)


def compute_mutation_drop(
    outcomes: Sequence[EvalOutcomeRecord],
) -> dict[str, Any]:
    """Score drop from canonical to mutation variants.

    Returns ``{"overall": float, "by_transform": {transform: float}}``.
    Each drop value is ``canonical_avg - mutation_avg`` (positive = score
    decreased under mutation, which is the expected direction).
    Returns zeros when there are no mutation rows.
    """
    canonical_scores: dict[str, list[float]] = {}
    for rec in outcomes:
        if rec["variant_family"] == "canonical":
            canonical_scores.setdefault(rec["canonical_id"], []).append(rec["score"])

    mutation_rows = [r for r in outcomes if r["variant_family"] == "mutation"]
    if not mutation_rows:
        return {"overall": 0.0, "by_transform": {}}

    canonical_avg_map: dict[str, float] = {
        cid: statistics.mean(scores) for cid, scores in canonical_scores.items()
    }

    drops: list[float] = []
    by_transform: dict[str, list[float]] = {}
    for rec in mutation_rows:
        c_avg = canonical_avg_map.get(rec["canonical_id"])
        if c_avg is None:
            raise ValueError(
                f"Mutation row has no canonical baseline for "
                f"canonical_id={rec['canonical_id']!r}"
            )
        drop = c_avg - rec["score"]
        drops.append(drop)
        by_transform.setdefault(rec["transform_type"], []).append(drop)

    overall = round(statistics.mean(drops), 6) if drops else 0.0
    by_transform_avg = {t: round(statistics.mean(ds), 6) for t, ds in sorted(by_transform.items())}
    return {"overall": overall, "by_transform": by_transform_avg}


def compute_worst_case_error_rate(
    outcomes: Sequence[EvalOutcomeRecord],
) -> float:
    """Worst (maximum) failure rate across all canonical item groups.

    For each ``canonical_id`` group, the failure rate is the fraction of
    rows with ``passed is False``.  Returns the maximum across groups.
    Returns 0.0 when there are no outcomes.
    """
    groups = group_outcomes_by_canonical_id(outcomes)
    if not groups:
        return 0.0
    rates: list[float] = []
    for rows in groups.values():
        n_fail = sum(1 for r in rows if not r["passed"])
        rates.append(n_fail / len(rows))
    return round(max(rates), 6)


def compute_item_instability_index(
    outcomes: Sequence[EvalOutcomeRecord],
) -> float:
    """Fraction of canonical items that have at least one unstable variant.

    An item is *unstable* if any of its non-canonical variants has a
    different ``decision`` from the canonical row.

    Returns 0.0 when there are no multi-variant items.
    """
    groups = group_outcomes_by_canonical_id(outcomes)
    if not groups:
        return 0.0

    total = 0
    unstable = 0
    for cid, rows in groups.items():
        canonical_dec: str | None = None
        non_canonical: list[EvalOutcomeRecord] = []
        for r in rows:
            if r["variant_family"] == "canonical":
                canonical_dec = r["decision"]
            else:
                non_canonical.append(r)
        if canonical_dec is None or not non_canonical:
            continue
        total += 1
        if any(r["decision"] != canonical_dec for r in non_canonical):
            unstable += 1

    if total == 0:
        return 0.0
    return round(unstable / total, 6)


def _find_unstable_items(
    outcomes: Sequence[EvalOutcomeRecord],
) -> list[str]:
    """Return sorted list of canonical_ids that are unstable."""
    groups = group_outcomes_by_canonical_id(outcomes)
    unstable: list[str] = []
    for cid, rows in groups.items():
        canonical_dec: str | None = None
        non_canonical: list[EvalOutcomeRecord] = []
        for r in rows:
            if r["variant_family"] == "canonical":
                canonical_dec = r["decision"]
            else:
                non_canonical.append(r)
        if canonical_dec is None or not non_canonical:
            continue
        if any(r["decision"] != canonical_dec for r in non_canonical):
            unstable.append(cid)
    return sorted(unstable)


def _compute_slice_support(
    outcomes: Sequence[EvalOutcomeRecord],
) -> dict[str, int]:
    """Count of outcomes per slice tag (sorted deterministically)."""
    counts: dict[str, int] = {}
    for rec in outcomes:
        for tag in rec["slice_tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items()))


def _compute_slice_breakdown(
    outcomes: Sequence[EvalOutcomeRecord],
) -> list[dict[str, Any]]:
    """Per-slice pass rate and mean score (sorted by tag)."""
    by_tag: dict[str, list[EvalOutcomeRecord]] = {}
    for rec in outcomes:
        for tag in rec["slice_tags"]:
            by_tag.setdefault(tag, []).append(rec)

    breakdown: list[dict[str, Any]] = []
    for tag in sorted(by_tag):
        rows = by_tag[tag]
        n_pass = sum(1 for r in rows if r["passed"])
        mean_score = statistics.mean(r["score"] for r in rows)
        breakdown.append(
            {
                "slice_tag": tag,
                "count": len(rows),
                "pass_rate": round(n_pass / len(rows), 6),
                "mean_score": round(mean_score, 6),
            }
        )
    return breakdown


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_validity_report(
    outcomes: Sequence[EvalOutcomeRecord],
) -> dict[str, Any]:
    """Build the full validity report dict from a sequence of outcomes.

    The report is deterministic: identical input always produces identical
    output (sorted keys, stable ordering).
    """
    return {
        "schema_version": EVAL_VALIDITY_SCHEMA_VERSION,
        "invariance_score": compute_invariance_score(outcomes),
        "mutation_drop": compute_mutation_drop(outcomes),
        "worst_case_error_rate": compute_worst_case_error_rate(outcomes),
        "item_instability_index": compute_item_instability_index(outcomes),
        "slice_support": _compute_slice_support(outcomes),
        "unstable_items": _find_unstable_items(outcomes),
        "slice_breakdown": _compute_slice_breakdown(outcomes),
    }
