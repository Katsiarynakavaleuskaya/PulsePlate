#!/usr/bin/env python3
"""
Shared utility functions for technical aspects analysis in Bayesian analyzers.
"""

import ast
import re
from typing import List, Union


def _has_explicit_return_or_yield(node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> bool:
    """
    Check if function body contains return with value or yield statement.

    This function returns True only when the function body contains:
    - A Return node with a non-None value (i.e., "return value", not just "return")
    - Any Yield or YieldFrom node

    A bare "return" statement (without a value) does not count, as it implicitly
    returns None and does not require a return type annotation.

    This distinction is important for return type annotation validation because:
    - Functions that return values or yield require explicit return type annotations
    - Functions that only have bare "return" statements implicitly return None
      and the absence of a return type annotation is acceptable

    AST node checks performed:
    - ast.Return with child.value is not None: indicates return with value
    - ast.Yield: indicates generator function
    - ast.YieldFrom: indicates generator delegation

    Args:
        node: AST node representing a function definition (FunctionDef or AsyncFunctionDef)

    Returns:
        True if function contains return with value or yield/yield from,
        False otherwise (including bare "return" statements)
    """

    root_node = node

    def _check_node(n: ast.AST) -> bool:
        """Recursively check node and its children, skipping nested function definitions."""
        # Check for return with value (not just "return" alone)
        if isinstance(n, ast.Return) and n.value is not None:
            return True
        # Check for yield or yield from
        if isinstance(n, (ast.Yield, ast.YieldFrom)):
            return True

        # Skip nested function definitions - don't recurse into their bodies
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not root_node:
            return False

        # Recursively check child nodes
        # For nodes with body attributes (like FunctionDef, Module, ClassDef, If, For, While, etc.)
        if hasattr(n, "body") and isinstance(n.body, list):
            for stmt in n.body:
                if _check_node(stmt):
                    return True
        # Also check other statement lists like orelse, finalbody, etc.
        # Note: orelse and finalbody contain statements (ast.stmt), while handlers
        # contains exception handlers (ast.excepthandler), not expressions
        for attr_name in ["orelse", "finalbody", "handlers"]:
            if hasattr(n, attr_name):
                attr_value = getattr(n, attr_name)
                if isinstance(attr_value, list):
                    for stmt in attr_value:
                        if _check_node(stmt):
                            return True
                # These attributes contain statements or handlers, not expressions
                # The ast.expr branch was incorrect and is removed

        # For other nodes, check all children (but nested functions are already skipped above)
        for child in ast.iter_child_nodes(n):
            if _check_node(child):
                return True
        return False

    # Start checking from the function node
    return _check_node(node)


def analyze_technical_aspects_common(code: str, _test_name: str = "") -> List[str]:
    """Shared logic for analyzing technical aspects of a test.

    This function contains the common technical analysis logic used by
    both BayesianTestAnalyzer and IntegratedBayesianAnalyzer.

    Args:
        code: The test code to analyze
        _test_name: Reserved for future logging/telemetry.
            TODO: Use for test-specific context in issue messages (issue #TBD)

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
        # Check only top-level function nodes, not nested functions
        missing_return_annotation = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.returns is None
            and not getattr(node, "name", "").startswith("test_")
            and _has_explicit_return_or_yield(node)
            for node in ast.iter_child_nodes(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
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
        # Check for return with value (not just "return" alone) or yield
        # Pattern: "return" followed by whitespace and a non-whitespace, non-comment character
        # Negative lookahead (?![#\n]) excludes "return # comment" and "return\n"
        # \S ensures at least one non-whitespace token follows (excludes "return   ")
        return_with_value = re.search(r"return\s+(?![#\n])\S", code) is not None
        yield_present = re.search(r"\byield\b", code) is not None
        has_explicit_return_or_yield = return_with_value or yield_present

        if async_present and not await_present:
            issues.append("Async function without await usage")
        if async_present and mock_present and not asyncmock_present:
            issues.append("Using Mock instead of AsyncMock for async methods")
        if raise_present and not try_present:
            issues.append("Exception raised without handling")
        if def_present and not arrow_present and has_explicit_return_or_yield:
            issues.append("Missing return type annotations")

    return issues
