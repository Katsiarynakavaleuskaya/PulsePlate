#!/usr/bin/env python3
"""Find and summarize failing tests quickly."""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, Union

# Directory name for test files
TESTS_DIR_NAME = "tests"


def extract_error_line(output: str) -> Optional[str]:
    """Extract the first error line from test output.

    Scans for various failure indicators including assertion errors,
    test failures, and error markers. Uses regex pattern to match
    assertions more robustly (handles assert(value), assert\tvalue, etc.).

    Args:
        output: Complete test output string (stdout + stderr).

    Returns:
        First matched error line (stripped) or None if no error pattern found.
    """
    lines = output.split("\n")
    # Regex pattern to match "assert" with word boundary, followed by whitespace, paren, or tab
    assert_pattern = re.compile(r"\bassert\s|\bassert\(")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Prioritize specific error indicators (case-sensitive)
        if (
            "AssertionError" in stripped
            or "FAILED" in stripped
            or stripped.startswith("ERROR")
            or "Traceback" in stripped
            or assert_pattern.search(stripped)  # Match assert with word boundary, space, or paren
            or stripped.startswith("E ")  # pytest error marker
            or stripped.startswith("F ")  # pytest failure marker
        ):
            return stripped

    # Fallback: return first non-empty line if no pattern matched
    for line in lines:
        if line.strip():
            return line.strip()

    return None


def run_test_file(test_file: Union[Path, str]) -> Tuple[bool, str]:
    """Run a single test file using pytest via subprocess and return status and output.

    Executes pytest on the specified test file using subprocess.run() with the current
    Python interpreter (sys.executable) for safety and portability. Captures both stdout
    and stderr, and applies a 60-second timeout to prevent hanging tests.

    Args:
        test_file: Path to the test file (Path or str). Converted to string for subprocess.

    Returns:
        Tuple containing:
            - bool: True if test passed (returncode == 0), False otherwise
            - str: Combined stdout and stderr on success/failure, or error message string
                  on exception. On timeout, returns "TIMEOUT: Test {file} timed out".
                  On other exceptions, returns "ERROR: {exception_message}".

    Exceptions:
        Handles subprocess.TimeoutExpired by returning (False, "TIMEOUT: ...").
        Handles other exceptions by returning (False, "ERROR: ...").

    Note:
        Uses subprocess.run() with:
        - sys.executable: Current Python interpreter (for security and portability)
        - pytest command: "-m pytest {test_file} --tb=short --maxfail=1"
        - capture_output=True: Captures both stdout and stderr
        - text=True: Returns output as string (not bytes)
        - timeout=60: 60-second timeout per test file
    """
    test_file_str = str(test_file)
    try:
        # Use the running interpreter for safety and portability (Bandit: B607)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file_str, "--tb=short", "--maxfail=1"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT: Test {test_file_str} timed out"
    except Exception as e:
        return False, f"ERROR: {e}"


def main() -> int:
    """Execute quick pass over tests/test_*.py and print a compact summary."""
    # Get all test files (restrict to repo tests dir, avoid traversal)
    tests_dir = Path(TESTS_DIR_NAME).resolve()
    if not tests_dir.exists() or not tests_dir.is_dir():
        print(f"❌ Error: Tests directory not found: {tests_dir}", file=sys.stderr)
        return 1
    test_files = sorted(
        [
            p
            for p in tests_dir.glob("test_*.py")
            if p.is_file() and p.resolve().is_relative_to(tests_dir)
        ]
    )
    failing_tests: list[tuple[str, str]] = []
    timeout_tests: list[str] = []

    print(f"🔍 Checking {len(test_files)} test files...")

    for i, test_file in enumerate(test_files, 1):
        print(f"[{i:03d}/{len(test_files)}] Testing {test_file}... ", end="")

        status_ok, output = run_test_file(test_file)

        if status_ok:
            print("✅ PASS")
        elif output.startswith("TIMEOUT"):
            print("⏰ TIMEOUT")
            timeout_tests.append(str(test_file))
        else:
            print("❌ FAIL")
            failing_tests.append((str(test_file), output))

    print("\n📊 Summary:")
    print(f"✅ Passing: {len(test_files) - len(failing_tests) - len(timeout_tests)}")
    print(f"❌ Failing: {len(failing_tests)}")
    print(f"⏰ Timeout: {len(timeout_tests)}")

    if failing_tests:
        print("\n❌ Failing tests:")
        for test_name, test_output in failing_tests:
            print(f"  - {test_name}")
            error_line = extract_error_line(test_output)
            if error_line:
                print(f"    Error: {error_line}")

    if timeout_tests:
        print("\n⏰ Timeout tests:")
        for test_name in timeout_tests:
            print(f"  - {str(test_name)}")

    return len(failing_tests) + len(timeout_tests)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
