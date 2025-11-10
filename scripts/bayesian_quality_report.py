#!/usr/bin/env python3
"""
Generates a nightly quality report for the Bayesian analyzer based on test history.

Outputs bayesian_quality_report.json with:
- prior_probabilities (normalized)
- error_type_counts (weighted)
- history_size
- avg_confidence_estimate (approx via entropy of priors)

Usage:
    PYTHONPATH="$PWD:$PWD/core:$PWD/app" python scripts/bayesian_quality_report.py

Note: This script requires PYTHONPATH to be set so imports resolve correctly.
      Do not modify sys.path at runtime - use environment configuration instead.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Dict

from core.bayesian_test_analyzer import BayesianTestAnalyzer, ErrorType, TestStatus


def calculate_confidence_from_priors(priors: Dict[str, float]) -> float:
    """Calculate confidence estimate from normalized prior probabilities using entropy.

    Args:
        priors: Dictionary mapping error type strings to normalized probabilities.

    Returns:
        Confidence estimate between 0.0 and 1.0, where:
        - 0.0 indicates no confidence (uniform or all-zero distribution)
        - 1.0 indicates full confidence (single outcome has all probability mass)
    """
    probs = list(priors.values())
    if not probs:
        # Empty distribution: no confidence estimate
        return 0.0
    elif len(probs) == 1:
        # Single-probability distribution: full confidence (all mass on one outcome)
        return 1.0
    else:
        # Check for all-zero priors case
        if all(abs(p) < 1e-10 for p in probs) or sum(probs) < 1e-10:
            # All-zero priors: no confidence
            return 0.0
        else:
            # Multiple probabilities: compute entropy-based confidence
            entropy = -sum(p * math.log2(p) if p > 0 else 0.0 for p in probs)
            max_entropy = math.log2(len(probs))
            # Guard against division by zero
            if max_entropy == 0:  # pragma: no cover - defensive guard for float precision
                return 0.0
            else:
                return 1.0 - (entropy / max_entropy)


def normalize(d: Dict[ErrorType, float]) -> Dict[str, float]:
    """Normalize a dictionary of ErrorType counts to probabilities.

    Args:
        d: Dictionary mapping ErrorType to numeric weights.

    Returns:
        Dictionary mapping ErrorType string values to normalized probabilities.
        If all values are zero, returns zeros (avoids division by zero).
    """
    prior_sum = sum(d.values())
    # Explicit check for zero sum to avoid division by zero
    if prior_sum == 0.0:
        denominator = 1.0
    else:
        denominator = float(prior_sum)
    return {k.value: float(v) / denominator for k, v in d.items()}


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
        avg_confidence_estimate = calculate_confidence_from_priors(priors_norm)

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
