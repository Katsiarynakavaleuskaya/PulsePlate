#!/usr/bin/env python3
"""
Generates a nightly quality report for the Bayesian analyzer based on test history.

Outputs bayesian_quality_report.json with:
- prior_probabilities (normalized)
- error_type_counts (weighted)
- history_size
- avg_confidence_estimate (approx via entropy of priors)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    TestStatus,
    ErrorType,
)


def normalize(d: Dict[ErrorType, float]) -> Dict[str, float]:
    s = float(sum(d.values()) or 1.0)
    return {k.value: float(v) / s for k, v in d.items()}


def main() -> int:
    analyzer = BayesianTestAnalyzer()
    history = analyzer.execution_history

    # Weighted error counts (simple counts as proxy)
    counts: Dict[ErrorType, float] = {et: 0.0 for et in ErrorType}
    for rec in history:
        if rec.result == TestStatus.FAILED and rec.error_type is not None:
            counts[rec.error_type] += 1.0

    priors_norm = normalize(analyzer.prior_probabilities)

    # Estimate avg confidence from priors entropy proxy
    probs = list(priors_norm.values())
    entropy = -sum(p * math.log2(p) if p > 0 else 0.0 for p in probs)
    max_entropy = math.log2(len(probs)) if probs else 1.0
    avg_confidence_estimate = 1.0 - (entropy / max_entropy if max_entropy > 0 else 0.0)

    report = {
        "history_size": len(history),
        "prior_probabilities": priors_norm,
        "error_type_counts": {k.value: v for k, v in counts.items()},
        "avg_confidence_estimate": avg_confidence_estimate,
    }

    out = Path("bayesian_quality_report.json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Wrote {out} with {len(history)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
