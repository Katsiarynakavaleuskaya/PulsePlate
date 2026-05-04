#!/usr/bin/env python3
"""Evaluation item statistics baseline.

RU: Описательная статистика eval-элементов для психометрической готовности.
EN: Descriptive item-level statistics layer over curated fixture outcomes
    and the item metadata registry.  Combines registry metadata with
    fixture outcomes to produce per-item descriptive statistics.

This module is a **descriptive measurement layer**, not IRT, not
psychometric calibration, not an adaptive item selector, and not a
release-gate decision source.

Hard rules:
- No IRT, Rasch, 2PL, 3PL.
- No scientific computing libraries (stdlib-only).
- No network calls, no provider metadata.
- No mutation of EvalOutcomeRecord or EvalItemMetadataRecord schemas.
- No mutation of RAG PASS/NO-GO or judgment promote/defer/discard logic.
- Stdlib-only.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Sequence, TypedDict

from scripts.evals.eval_item_registry import (
    EvalItemMetadataRecord,
)
from scripts.evals.eval_validity_contract import (
    EvalOutcomeRecord,
    validate_eval_outcome_record,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DECIMAL_PLACES = 6
"""Rounding precision for all computed rates and means."""

# ---------------------------------------------------------------------------
# Item statistics record schema
# ---------------------------------------------------------------------------


class EvalItemStatisticsRecord(TypedDict):
    """Descriptive statistics for one canonical eval item.

    RU: Описательная статистика для одного канонического eval-элемента.
    EN: Combines registry metadata with fixture outcome data to produce
        per-item descriptive statistics.  These are NOT IRT estimates,
        NOT calibrated difficulty parameters, and NOT psychometric scores.
    """

    canonical_id: str
    lane: str
    domain: str
    skill_dimension: str
    difficulty_band: str
    expected_decision: str
    expected_score_band: str
    variant_count: int
    canonical_score: float
    canonical_passed: bool
    invariance_count: int
    invariance_agreement_count: int
    invariance_agreement_rate: float
    mutation_count: int
    mutation_mean_drop: float
    worst_variant_score: float
    pass_rate: float
    decision_set: list[str]
    instability_flag: bool
    anchor_item: bool


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def load_fixture_outcomes(path: Path) -> list[EvalOutcomeRecord]:
    """Load and validate EvalOutcomeRecord rows from a JSONL file.

    Raises ``ValueError`` on first malformed line.
    """
    outcomes: list[EvalOutcomeRecord] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            outcomes.append(validate_eval_outcome_record(raw))
    return outcomes


# ---------------------------------------------------------------------------
# Statistics computation
# ---------------------------------------------------------------------------


def _compute_item_stats(
    canonical_id: str,
    outcomes: list[EvalOutcomeRecord],
    registry_record: EvalItemMetadataRecord,
) -> EvalItemStatisticsRecord:
    """Compute descriptive statistics for one canonical item group."""
    # Find the canonical row
    canonical_row: EvalOutcomeRecord | None = None
    for rec in outcomes:
        if rec["variant_family"] == "canonical":
            canonical_row = rec
            break

    if canonical_row is None:
        raise ValueError(f"No canonical row found for canonical_id={canonical_id!r}")

    canonical_score = canonical_row["score"]
    canonical_passed = canonical_row["passed"]
    canonical_decision = canonical_row["decision"]

    # Invariance stats
    invariance_rows = [r for r in outcomes if r["variant_family"] == "invariance"]
    invariance_count = len(invariance_rows)
    invariance_agreement_count = sum(
        1 for r in invariance_rows if r["decision"] == canonical_decision
    )
    invariance_agreement_rate = (
        round(invariance_agreement_count / invariance_count, _DECIMAL_PLACES)
        if invariance_count > 0
        else 0.0
    )

    # Mutation stats
    mutation_rows = [r for r in outcomes if r["variant_family"] == "mutation"]
    mutation_count = len(mutation_rows)
    if mutation_count > 0:
        drops = [canonical_score - r["score"] for r in mutation_rows]
        mutation_mean_drop = round(statistics.mean(drops), _DECIMAL_PLACES)
    else:
        mutation_mean_drop = 0.0

    # Aggregate stats
    variant_count = len(outcomes)
    all_scores = [r["score"] for r in outcomes]
    worst_variant_score = min(all_scores)
    pass_count = sum(1 for r in outcomes if r["passed"])
    pass_rate = round(pass_count / variant_count, _DECIMAL_PLACES)
    decision_set = sorted(set(r["decision"] for r in outcomes))
    instability_flag = len(decision_set) > 1

    return EvalItemStatisticsRecord(
        canonical_id=canonical_id,
        lane=registry_record["lane"],
        domain=registry_record["domain"],
        skill_dimension=registry_record["skill_dimension"],
        difficulty_band=registry_record["difficulty_band"],
        expected_decision=registry_record["expected_decision"],
        expected_score_band=registry_record["expected_score_band"],
        variant_count=variant_count,
        canonical_score=canonical_score,
        canonical_passed=canonical_passed,
        invariance_count=invariance_count,
        invariance_agreement_count=invariance_agreement_count,
        invariance_agreement_rate=invariance_agreement_rate,
        mutation_count=mutation_count,
        mutation_mean_drop=mutation_mean_drop,
        worst_variant_score=worst_variant_score,
        pass_rate=pass_rate,
        decision_set=decision_set,
        instability_flag=instability_flag,
        anchor_item=registry_record["anchor_item"],
    )


def build_item_statistics(
    outcomes: Sequence[EvalOutcomeRecord],
    registry_records: Sequence[EvalItemMetadataRecord],
) -> list[EvalItemStatisticsRecord]:
    """Build per-item statistics from outcomes and registry records.

    Raises ``ValueError`` on coverage mismatch (orphan stats or missing
    registry items).  Results are sorted by ``(lane, canonical_id)``
    for deterministic output.
    """
    # Group outcomes by canonical_id
    by_cid: dict[str, list[EvalOutcomeRecord]] = {}
    for rec in outcomes:
        by_cid.setdefault(rec["canonical_id"], []).append(rec)

    # Index registry
    registry_index: dict[str, EvalItemMetadataRecord] = {}
    for reg in registry_records:
        registry_index[reg["canonical_id"]] = reg

    # Validate coverage
    outcome_cids = set(by_cid.keys())
    registry_cids = set(registry_index.keys())

    missing_from_registry = outcome_cids - registry_cids
    if missing_from_registry:
        raise ValueError(
            f"Outcome canonical_ids missing from registry: {sorted(missing_from_registry)}"
        )

    orphan_registry = registry_cids - outcome_cids
    if orphan_registry:
        raise ValueError(
            f"Orphan registry canonical_ids not in outcomes: {sorted(orphan_registry)}"
        )

    # Compute stats per item, then sort by (lane, canonical_id) for determinism
    items: list[EvalItemStatisticsRecord] = []
    for cid in registry_cids:
        item_stats = _compute_item_stats(cid, by_cid[cid], registry_index[cid])
        items.append(item_stats)

    items.sort(key=lambda x: (x["lane"], x["canonical_id"]))
    return items


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------


def build_item_statistics_report(
    items: Sequence[EvalItemStatisticsRecord],
) -> dict[str, Any]:
    """Build the item statistics report envelope.

    The report is deterministic: identical input always produces identical
    output (sorted keys, stable ordering, no timestamps).
    """
    lane_counts: dict[str, int] = {}
    anchor_count = 0
    unstable_count = 0

    for item in items:
        lane = item["lane"]
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        if item["anchor_item"]:
            anchor_count += 1
        if item["instability_flag"]:
            unstable_count += 1

    return {
        "schema_version": "1.0",
        "item_count": len(items),
        "lane_counts": dict(sorted(lane_counts.items())),
        "anchor_item_count": anchor_count,
        "unstable_item_count": unstable_count,
        "items": list(items),
    }


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def write_item_statistics_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """Write item statistics report as deterministic JSON.

    Creates parent directories if needed.  No timestamps in output.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
