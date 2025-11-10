#!/usr/bin/env python3
"""Quick coverage check for our progress."""

# nosec B404 - subprocess is safe: args are static (hardcoded test file paths),
# shell=False (default), sys.executable (not user-controlled), no user input,
# args passed as list
import subprocess  # nosec B404
import sys
import time


def run_coverage_check() -> bool:
    """Run coverage on our new test files specifically."""
    print("🔍 Checking coverage progress...")
    start_time = time.time()

    # Run only our new tests with overall coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_product_varieties.py",
        "tests/test_product_finder_simple.py",
        "tests/test_bmi_core_validation_edges.py",
        "--cov=.",
        "--cov-report=term-missing",
        "--tb=no",  # No traceback for faster execution
        "-q",  # Quiet mode
    ]

    try:
        # Timeout aligned with analyze_coverage_gaps.py (600s) for consistency
        # Note: This script runs a subset of tests, so typically completes faster
        # nosec B603: Safe subprocess invocation - cmd (defined lines 15-26) is a static
        # list built from sys.executable and hardcoded pytest arguments only; no user
        # input or external data is used. Timeout (600s) prevents hangs, and
        # capture_output/text are used intentionally to safely capture stdout/stderr
        # without shell injection risks.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # nosec B603
        elapsed = time.time() - start_time

        lines = result.stdout.split("\n")

        # Find coverage percentage
        coverage_line = None
        for line in lines:
            if "TOTAL" in line and "%" in line:
                coverage_line = line
                break

        print(f"⏱️  Execution time: {elapsed:.1f}s")

        if coverage_line:
            print(f"📊 Coverage result: {coverage_line}")

            # Extract percentage
            parts = coverage_line.split()
            for part in parts:
                if "%" in part:
                    percentage = part.replace("%", "")
                    print(f"🎯 Overall coverage: {percentage}%")
                    break
        else:
            print("❌ Could not find coverage percentage")

        # Show any test failures
        if "FAILED" in result.stdout:
            print("⚠️  Some tests failed")

        print(f"✅ Tests passed: {result.stdout.count(' PASSED')}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⏰ Coverage check timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = run_coverage_check()
    print(f"🏁 Coverage check {'completed' if success else 'failed'}")
