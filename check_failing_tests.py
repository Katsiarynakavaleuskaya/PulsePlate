#!/usr/bin/env python3
"""
Script to find and fix failing tests systematically
"""

import glob
import subprocess  # nosec B404
import sys


def run_test_file(test_file):
    """Run a single test file and return result"""
    try:
        result = subprocess.run(  # nosec B603
            [sys.executable, "-m", "pytest", test_file, "--tb=short", "-x", "--maxfail=1"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return "PASS", result.stdout
        else:
            return "FAIL", result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT", f"Test {test_file} timed out"
    except Exception as e:
        return "ERROR", str(e)


def main():
    # Get all test files
    test_files = glob.glob("tests/test_*.py")
    failing_tests = []
    timeout_tests = []

    print(f"🔍 Checking {len(test_files)} test files...")

    for i, test_file in enumerate(test_files, 1):
        print(f"[{i:03d}/{len(test_files)}] Testing {test_file}... ", end="")

        status, output = run_test_file(test_file)

        if status == "PASS":
            print("✅ PASS")
        elif status == "FAIL":
            print("❌ FAIL")
            failing_tests.append((test_file, output))
        elif status == "TIMEOUT":
            print("⏰ TIMEOUT")
            timeout_tests.append(test_file)
        else:
            print("💥 ERROR")
            failing_tests.append((test_file, output))

    print("\n📊 Summary:")
    print(f"✅ Passing: {len(test_files) - len(failing_tests) - len(timeout_tests)}")
    print(f"❌ Failing: {len(failing_tests)}")
    print(f"⏰ Timeout: {len(timeout_tests)}")

    if failing_tests:
        print("\n❌ Failing tests:")
        for test_file, output in failing_tests:
            print(f"  - {test_file}")
            # Show first error line
            lines = output.split("\n")
            for line in lines:
                if "assert" in line and "==" in line:
                    print(f"    Error: {line.strip()}")
                    break

    if timeout_tests:
        print("\n⏰ Timeout tests:")
        for test_file in timeout_tests:
            print(f"  - {test_file}")

    return len(failing_tests) + len(timeout_tests)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
