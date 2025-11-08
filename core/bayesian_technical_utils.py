#!/usr/bin/env python3
"""
Shared utility functions for technical aspects analysis in Bayesian analyzers.
"""

from typing import List


def analyze_technical_aspects_common(code: str, test_name: str) -> List[str]:
    """Shared logic for analyzing technical aspects of a test.

    This function contains the common technical analysis logic used by
    both BayesianTestAnalyzer and IntegratedBayesianAnalyzer.

    Args:
        code: The test code to analyze
        test_name: Name of the test being analyzed

    Returns:
        List of identified technical issues
    """
    issues: List[str] = []

    # Async checks
    if "async" in code and "await" not in code:
        issues.append("Async function without await usage")

    # Mocking checks
    if "Mock()" in code and "AsyncMock" not in code and "async" in code:
        issues.append("Using Mock instead of AsyncMock for async methods")

    # Exception handling checks
    if "raise" in code and "try" not in code:
        issues.append("Exception raised without handling")

    # Return type hint checks
    if "def " in code and "->" not in code:
        issues.append("Missing return type annotations")

    return issues
