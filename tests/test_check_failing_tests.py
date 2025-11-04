"""Unit tests for check_failing_tests helper functions."""

import pytest

from check_failing_tests import extract_error_line


def test_extract_error_line_assertion_error() -> None:
    """Test extraction when AssertionError is present."""
    output = "Some text\nAssertionError: expected 1 but got 2\nMore text"
    result = extract_error_line(output)
    assert result == "AssertionError: expected 1 but got 2"


def test_extract_error_line_failed_marker() -> None:
    """Test extraction when FAILED marker is present."""
    output = "Test output\nFAILED tests/test_example.py::test_case\nMore output"
    result = extract_error_line(output)
    assert result == "FAILED tests/test_example.py::test_case"


def test_extract_error_line_error_prefix() -> None:
    """Test extraction when line starts with ERROR."""
    output = "Normal output\nERROR: Something went wrong\nMore output"
    result = extract_error_line(output)
    assert result == "ERROR: Something went wrong"


def test_extract_error_line_traceback() -> None:
    """Test extraction when Traceback is present."""
    output = "Output\nTraceback (most recent call last):\n  File test.py"
    result = extract_error_line(output)
    assert result is not None, "Expected result to be a string, not None"
    assert "Traceback" in result


def test_extract_error_line_assert_with_space() -> None:
    """Test extraction when assert statement has trailing space."""
    output = "Some code\n    assert value == expected\nMore code"
    result = extract_error_line(output)
    assert result == "assert value == expected"


def test_extract_error_line_assert_with_paren() -> None:
    """Test extraction when assert statement uses parentheses."""
    output = "Code here\n    assert(value == expected)\nMore code"
    result = extract_error_line(output)
    assert result is not None, "Expected result to be a string, not None"
    assert "assert" in result.lower()


def test_extract_error_line_assert_with_tab() -> None:
    """Test extraction when assert statement has tab separator."""
    output = "Code\n    assert\tvalue\nMore"
    result = extract_error_line(output)
    assert result == "assert\tvalue"


def test_extract_error_line_pytest_error_marker() -> None:
    """Test extraction when pytest E marker is present."""
    output = "Test output\nE   AssertionError: failed\nMore"
    result = extract_error_line(output)
    assert result == "E   AssertionError: failed"


def test_extract_error_line_pytest_failure_marker() -> None:
    """Test extraction when pytest F marker is present."""
    output = "Test output\nF   tests/test_example.py::test_case\nMore"
    result = extract_error_line(output)
    assert result == "F   tests/test_example.py::test_case"


def test_extract_error_line_fallback_to_first_line() -> None:
    """Test fallback to first non-empty line when no pattern matches."""
    output = "First non-empty line\nSecond line\nThird line"
    result = extract_error_line(output)
    assert result == "First non-empty line"


def test_extract_error_line_empty_output() -> None:
    """Test extraction with empty output returns None."""
    output = ""
    result = extract_error_line(output)
    assert result is None


def test_extract_error_line_only_whitespace() -> None:
    """Test extraction with only whitespace returns None."""
    output = "   \n\t\n   \n"
    result = extract_error_line(output)
    assert result is None


def test_extract_error_line_assertionerror_takes_priority() -> None:
    """Test that AssertionError is found before fallback."""
    output = "First line\nAssertionError: failed\nassert value"
    result = extract_error_line(output)
    assert result is not None, "Expected result to be a string, not None"
    assert "AssertionError" in result
    assert result != "First line"
