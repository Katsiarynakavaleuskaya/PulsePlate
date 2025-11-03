#!/usr/bin/env python3
"""Find and summarize failing tests quickly."""

import glob
import re
from pathlib import Path
import subprocess
import sys
from typing import Optional, Tuple


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
            "AssertionError" in line
            or "FAILED" in line
            or line.startswith("ERROR")
            or "Traceback" in line
            or assert_pattern.search(line)  # Match assert with word boundary, space, or paren
            or line.startswith("E ")  # pytest error marker
            or line.startswith("F ")  # pytest failure marker
        ):
            return stripped

    # Fallback: return first non-empty line if no pattern matched
    for line in lines:
        if line.strip():
            return line.strip()

    return None


def run_test_file(test_file: str) -> Tuple[bool, str]:
    """Run a single test file and return (status_ok, output)."""
    try:
        # Use the running interpreter for safety and portability (Bandit: B607)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "--tb=short", "--maxfail=1"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT: Test {test_file} timed out"
    except Exception as e:
        return False, f"ERROR: {e}"


def main() -> int:
    """Execute quick pass over tests/test_*.py and print a compact summary."""
    # Get all test files (restrict to repo tests dir, avoid traversal)
    test_files = [
        str(p)
        for p in map(Path, sorted(glob.glob("tests/test_*.py")))
        if p.is_file() and p.resolve().is_relative_to(Path("tests").resolve())
    ]
    failing_tests = []
    timeout_tests = []

    print(f"🔍 Checking {len(test_files)} test files...")

    for i, test_file in enumerate(test_files, 1):
        print(f"[{i:03d}/{len(test_files)}] Testing {test_file}... ", end="")

        status_ok, output = run_test_file(test_file)

        if status_ok:
            print("✅ PASS")
        elif output.startswith("TIMEOUT"):
            print("⏰ TIMEOUT")
            timeout_tests.append(test_file)
        else:
            print("❌ FAIL")
            failing_tests.append((test_file, output))

    print("\n📊 Summary:")
    print(f"✅ Passing: {len(test_files) - len(failing_tests) - len(timeout_tests)}")
    print(f"❌ Failing: {len(failing_tests)}")
    print(f"⏰ Timeout: {len(timeout_tests)}")

    if failing_tests:
        print("\n❌ Failing tests:")
        for test_file, output in failing_tests:
            print(f"  - {test_file}")
            error_line = extract_error_line(output)
            if error_line:
                print(f"    Error: {error_line}")

    if timeout_tests:
        print("\n⏰ Timeout tests:")
        for test_file in timeout_tests:
            print(f"  - {test_file}")

    return len(failing_tests) + len(timeout_tests)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
