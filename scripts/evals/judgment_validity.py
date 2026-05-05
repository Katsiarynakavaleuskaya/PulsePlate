#!/usr/bin/env python3
"""Judgment replay validity sidecar adapter.

RU: Адаптер для преобразования FitChef judgment replay результатов в
    validity-совместимые EvalOutcomeRecord и генерации validity sidecar
    артефактов.
EN: Adapter to convert FitChef judgment replay results into validity-compatible
    EvalOutcomeRecord rows and generate validity sidecar artifacts.

This module is a bridge between the FitChef judgment replay eval runner
(``scripts/orchestration/judgment_eval.py``) and the evaluation-validity
substrate (``scripts/evals/eval_validity_contract.py``).

Hard rules:
- No network calls.
- No model invocations.
- No changes to promote/defer/discard logic.
- No changes to claim taxonomy.
- No changes to claim-to-evidence semantics.
- Sidecar artifacts are informational sibling artifacts.
- Canonical-only rows must not be misrepresented as invariance/mutation coverage.

Judgment validity sidecar artifacts are informational measurement artifacts.
They do not override claim taxonomy, claim-to-evidence records, uncertainty
split, or canonical promote/defer/discard decisions.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Sequence

from scripts.evals.eval_validity_contract import (
    EvalOutcomeRecord,
    build_validity_report,
    validate_eval_outcome_record,
)

# ---------------------------------------------------------------------------
# Constants (judgment decision -> validity score mapping)
# ---------------------------------------------------------------------------

# Deterministic mapping from judgment decisions to validity scores.
#
# - promote (1.0): fully supported, safe to surface.
# - defer (0.5): safe but under-supported; not a failure, but not fully promoted.
#   passed=True because defer means content is safe (per judgment protocol).
# - discard (0.0): failed safety or evidence checks.
JUDGMENT_DECISION_SCORES: dict[str, float] = {
    "promote": 1.0,
    "defer": 0.5,
    "discard": 0.0,
}

# Decisions that map to passed=True in validity sidecar.
# Defer is treated as passed because the judgment protocol defines defer as
# "safe but still under-supported" -- content is not harmful, just incomplete.
_PASSED_DECISIONS: frozenset[str] = frozenset({"promote", "defer"})

JUDGMENT_VALIDITY_ITEMS_FILENAME = "judgment_validity_items.jsonl"
JUDGMENT_VALIDITY_REPORT_FILENAME = "judgment_validity_report.json"


def _safe_write_text(path: Path, content: str) -> None:
    """Write text without following symlinks."""
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise OSError("Symlink-safe writes are not supported on this platform")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    flags |= no_follow
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# Result -> EvalOutcomeRecord mapping
# ---------------------------------------------------------------------------


def result_to_eval_outcome(
    result: dict[str, Any],
    pack_meta: dict[str, Any] | None = None,
) -> EvalOutcomeRecord:
    """Convert a single FitChef judgment replay result to an ``EvalOutcomeRecord``.

    The mapping preserves existing promote/defer/discard semantics:

    - ``promote`` -> passed=True, score=1.0
    - ``defer``   -> passed=True, score=0.5
    - ``discard`` -> passed=False, score=0.0

    Since current judgment replay datasets contain only canonical items (no
    invariance or mutation variants), all rows are mapped as
    ``variant_family="canonical"`` and ``transform_type="none"``.

    The ``decision`` field carries the original judgment decision string
    (``"promote"`` / ``"defer"`` / ``"discard"``), not a pass/fail label.

    Parameters
    ----------
    result:
        A FitChef replay result dict (``FitChefReplayResultRecord``-shaped).
    pack_meta:
        Optional pack-level metadata (unused in current implementation but
        reserved for future variant-family support).
    """
    del pack_meta  # reserved for future variant-family support
    case_id = str(result.get("case_id", "unknown"))
    decision = str(result.get("decision", "")).strip().lower()
    boundary_class = str(result.get("boundary_class", "unknown"))
    _raw_hfr = result.get("hard_fail_reasons")
    hard_fail_reasons: list[str] = _raw_hfr if isinstance(_raw_hfr, list) else []

    score = JUDGMENT_DECISION_SCORES.get(decision, 0.0)
    passed = decision in _PASSED_DECISIONS

    slice_tags: list[str] = ["judgment", boundary_class]
    if hard_fail_reasons:
        slice_tags.append("hard_fail")

    raw: dict[str, Any] = {
        "canonical_id": case_id,
        "variant_id": case_id,
        "variant_family": "canonical",
        "transform_type": "none",
        "passed": passed,
        "score": score,
        "decision": decision,
        "slice_tags": slice_tags,
    }
    return validate_eval_outcome_record(raw)


def results_to_eval_outcomes(
    results: Sequence[dict[str, Any]],
    pack_meta: dict[str, Any] | None = None,
) -> list[EvalOutcomeRecord]:
    """Convert a sequence of FitChef judgment replay results to ``EvalOutcomeRecord`` rows.

    Deterministic: insertion order is preserved.
    """
    return [result_to_eval_outcome(r, pack_meta) for r in results]


# ---------------------------------------------------------------------------
# Sidecar artifact writing
# ---------------------------------------------------------------------------


def write_judgment_validity_sidecar(
    run_dir: Path,
    results: Sequence[dict[str, Any]],
    pack_meta: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Write judgment validity sidecar artifacts into the run directory.

    Emits two files:

    - ``judgment_validity_items.jsonl`` -- one ``EvalOutcomeRecord`` per result.
    - ``judgment_validity_report.json`` -- the validity report built from those
      outcomes.

    Returns a dict mapping artifact kind to file path (string).

    The sidecar files are informational measurement artifacts.  They do NOT
    override the claim taxonomy, claim-to-evidence records, uncertainty split,
    or the canonical promote/defer/discard decisions.
    """
    outcomes = results_to_eval_outcomes(results, pack_meta)
    report = build_validity_report(outcomes)

    run_dir.mkdir(parents=True, exist_ok=True)

    # Write item-level outcomes.
    items_path = run_dir / JUDGMENT_VALIDITY_ITEMS_FILENAME
    items_content = "".join(
        json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n" for rec in outcomes
    )
    _safe_write_text(items_path, items_content)

    # Write validity report.
    report_path = run_dir / JUDGMENT_VALIDITY_REPORT_FILENAME
    report_content = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    _safe_write_text(report_path, report_content)

    return {
        "validity_items": str(items_path),
        "validity_report": str(report_path),
    }
