#!/usr/bin/env python3
"""RAG release-gate validity sidecar adapter.

RU: Адаптер для преобразования RAG release-gate trace-ов в validity-совместимые
    EvalOutcomeRecord и генерации validity sidecar артефактов.
EN: Adapter to convert RAG release-gate traces into validity-compatible
    EvalOutcomeRecord rows and generate validity sidecar artifacts.

This module is a bridge between the RAG release-gate runner
(``scripts/evals/run_rag_release_gates.py``) and the evaluation-validity
substrate (``scripts/evals/eval_validity_contract.py``).

Hard rules:
- No network calls.
- No model invocations.
- No changes to PASS/NO-GO logic.
- No changes to gate thresholds.
- Sidecar artifacts are informational sibling artifacts.
- Canonical-only rows must not be misrepresented as invariance/mutation coverage.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any, Sequence

from scripts.evals.eval_validity_contract import (
    EvalOutcomeRecord,
    build_validity_report,
    validate_eval_outcome_record,
)

# ---------------------------------------------------------------------------
# Constants (aligned with RAG release-gate GATE_THRESHOLDS)
# ---------------------------------------------------------------------------

# These thresholds mirror the per-item faithfulness criteria used by the
# RAG release-gate runner for gate checks B1, B2, B3.  They are used here
# to derive per-item pass/fail in the validity sidecar.
#
# IMPORTANT: These must stay aligned with GATE_THRESHOLDS in
# run_rag_release_gates.py.  Any threshold drift is a bug.
_ITEM_SUPPORT_PRECISION_THRESHOLD: float = 0.80
_ITEM_NLI_ENTAILMENT_THRESHOLD: float = 0.85

VALIDITY_ITEMS_FILENAME = "validity_items.jsonl"
VALIDITY_REPORT_FILENAME = "validity_report.json"


# ---------------------------------------------------------------------------
# Trace -> EvalOutcomeRecord mapping
# ---------------------------------------------------------------------------


def trace_to_eval_outcome(trace: dict[str, Any]) -> EvalOutcomeRecord:
    """Convert a single RAG release-gate trace dict to an ``EvalOutcomeRecord``.

    Per-item pass/fail is derived from the same faithfulness thresholds
    used by the RAG release-gate runner (gates B1, B2, B3):

    - ``evidence_exact_match`` must be True (gate B1)
    - ``mean_nli_entailment`` must be >= 0.85 (gate B2)
    - ``support_precision`` must be >= 0.80 (gate B3)

    The composite score is the mean of the three faithfulness sub-metrics
    (treating ``evidence_exact_match`` as 1.0/0.0).

    Since current RAG eval datasets contain only canonical items (no
    invariance or mutation variants), all rows are mapped as
    ``variant_family="canonical"`` and ``transform_type="none"``.
    """
    query_id = str(trace.get("query_id", "unknown"))
    fm = trace.get("faithfulness_metrics") or {}

    evidence_exact_match: bool = bool(fm.get("evidence_exact_match", False))
    mean_nli_entailment: float = float(fm.get("mean_nli_entailment", 0.0))
    support_precision: float = float(fm.get("support_precision", 0.0))

    # Per-item pass/fail aligned with gate B1, B2, B3 thresholds.
    passed = (
        evidence_exact_match
        and mean_nli_entailment >= _ITEM_NLI_ENTAILMENT_THRESHOLD
        and support_precision >= _ITEM_SUPPORT_PRECISION_THRESHOLD
    )

    # Composite score: mean of the three faithfulness sub-metrics.
    evidence_score = 1.0 if evidence_exact_match else 0.0
    score = round(
        statistics.mean([evidence_score, mean_nli_entailment, support_precision]),
        6,
    )

    decision = "pass" if passed else "fail"

    raw: dict[str, Any] = {
        "canonical_id": query_id,
        "variant_id": query_id,
        "variant_family": "canonical",
        "transform_type": "none",
        "passed": passed,
        "score": score,
        "decision": decision,
        "slice_tags": ["rag", "release_gate"],
    }
    return validate_eval_outcome_record(raw)


def traces_to_eval_outcomes(
    traces: Sequence[dict[str, Any]],
) -> list[EvalOutcomeRecord]:
    """Convert a sequence of RAG release-gate traces to ``EvalOutcomeRecord`` rows.

    Deterministic: insertion order is preserved.
    """
    return [trace_to_eval_outcome(t) for t in traces]


# ---------------------------------------------------------------------------
# Sidecar artifact writing
# ---------------------------------------------------------------------------


def write_validity_sidecar(
    run_dir: Path,
    traces: Sequence[dict[str, Any]],
) -> dict[str, str]:
    """Write validity sidecar artifacts into the RAG release-gate run directory.

    Emits two files:

    - ``validity_items.jsonl`` -- one ``EvalOutcomeRecord`` per trace row.
    - ``validity_report.json`` -- the validity report built from those outcomes.

    Returns a dict mapping artifact kind to file path (string).

    The sidecar files are informational measurement artifacts.  They do NOT
    override ``threshold_results`` or the canonical RAG release-gate
    PASS/NO-GO decision.
    """
    outcomes = traces_to_eval_outcomes(traces)
    report = build_validity_report(outcomes)

    run_dir.mkdir(parents=True, exist_ok=True)

    # Write item-level outcomes.
    items_path = run_dir / VALIDITY_ITEMS_FILENAME
    with open(items_path, "w", encoding="utf-8") as fh:
        for rec in outcomes:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    # Write validity report.
    report_path = run_dir / VALIDITY_REPORT_FILENAME
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")

    return {
        "validity_items": str(items_path),
        "validity_report": str(report_path),
    }
