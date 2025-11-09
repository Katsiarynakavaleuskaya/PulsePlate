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
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bayesian_test_analyzer import (
    BayesianTestAnalyzer,
    TestStatus,
    ErrorType,
)


def normalize(d: Dict[ErrorType, float]) -> Dict[str, float]:
    """Normalize a dictionary of ErrorType counts to probabilities.

    Args:
        d: Dictionary mapping ErrorType to numeric weights.

    Returns:
        Dictionary mapping ErrorType string values to normalized probabilities.
        If all values are zero, returns zeros (avoids division by zero).
    """
    s = float(sum(d.values()) or 1.0)
    return {k.value: float(v) / s for k, v in d.items()}


def main() -> int:
    try:
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
        if not probs:
            # Empty distribution: no confidence estimate
            avg_confidence_estimate = 0.0
        elif len(probs) == 1:
            # Single-probability distribution: full confidence (all mass on one outcome)
            avg_confidence_estimate = 1.0
        else:
            # Multiple probabilities: compute entropy-based confidence
            entropy = -sum(p * math.log2(p) if p > 0 else 0.0 for p in probs)
            max_entropy = math.log2(len(probs))
            avg_confidence_estimate = 1.0 - (entropy / max_entropy)

        report = {
            "history_size": len(history),
            "prior_probabilities": priors_norm,
            "error_type_counts": {k.value: v for k, v in counts.items()},
            "avg_confidence_estimate": avg_confidence_estimate,
        }

        try:
            out = Path("bayesian_quality_report.json")
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
            print(f"Wrote {out} with {len(history)} records")
            return 0
        except Exception as e:
            print(f"Error writing report: {e}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error initializing BayesianTestAnalyzer: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
