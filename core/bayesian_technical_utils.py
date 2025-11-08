#!/usr/bin/env python3
"""
Shared utility functions for technical aspects analysis in Bayesian analyzers.
"""

import ast
import re
from typing import List


def analyze_technical_aspects_common(code: str, test_name: str) -> List[str]:
    """Shared logic for analyzing technical aspects of a test.

    This function contains the common technical analysis logic used by
    both BayesianTestAnalyzer and IntegratedBayesianAnalyzer.

    Args:
        code: The test code to analyze
        test_name: Name of the test being analyzed
            TODO: Reserved for future use (logging/telemetry and per-test heuristics);
            intentionally unused for now.

    Returns:
        List of identified technical issues
    """
    issues: List[str] = []

    # Prefer AST-based analysis; fall back to regex with word boundaries if parsing fails
    try:
        tree = ast.parse(code)

        has_async_def = any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(tree))
        has_await = any(isinstance(node, ast.Await) for node in ast.walk(tree))
        has_raise = any(isinstance(node, ast.Raise) for node in ast.walk(tree))
        has_try = any(isinstance(node, ast.Try) for node in ast.walk(tree))
        missing_return_annotation = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.returns is None
            and not getattr(node, "name", "").startswith("test_")
            for node in ast.walk(tree)
        )
        has_mock_call = any(
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "Mock")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "Mock")
            )
            for node in ast.walk(tree)
        )
        has_asyncmock_call = any(
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "AsyncMock")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "AsyncMock")
            )
            for node in ast.walk(tree)
        )

        # Async checks
        if has_async_def and not has_await:
            issues.append("Async function without await usage")

        # Mocking checks
        if has_async_def and has_mock_call and not has_asyncmock_call:
            issues.append("Using Mock instead of AsyncMock for async methods")

        # Exception handling checks
        if has_raise and not has_try:
            issues.append("Exception raised without handling")

        # Return type hint checks
        if missing_return_annotation:
            issues.append("Missing return type annotations")

    except SyntaxError:
        # Regex fallback with word boundaries to avoid matches inside other words/identifiers
        async_present = re.search(r"\basync\b", code) is not None
        await_present = re.search(r"\bawait\b", code) is not None
        mock_present = re.search(r"\bMock\s*\(", code) is not None
        asyncmock_present = re.search(r"\bAsyncMock\s*\(", code) is not None
        raise_present = re.search(r"\braise\b", code) is not None
        try_present = re.search(r"\btry\b", code) is not None
        def_present = re.search(r"\bdef\b", code) is not None
        arrow_present = re.search(r"->", code) is not None

        if async_present and not await_present:
            issues.append("Async function without await usage")
        if async_present and mock_present and not asyncmock_present:
            issues.append("Using Mock instead of AsyncMock for async methods")
        if raise_present and not try_present:
            issues.append("Exception raised without handling")
        if def_present and not arrow_present:
            issues.append("Missing return type annotations")

    return issues
