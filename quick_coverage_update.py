#!/usr/bin/env python3
"""Quick coverage check for our progress."""

# nosec B404 - subprocess is safe: args are static (hardcoded test file paths),
# shell=False (default), sys.executable (not user-controlled), no user input,
# args passed as list
import json
import subprocess  # nosec B404
import sys
import tempfile
import time
import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path


def run_coverage_check() -> bool:
    """Run coverage on our new test files specifically."""
    print("🔍 Checking coverage progress...")
    start_time = time.time()

    # Create temporary files for structured reports
    with (
        tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as junit_file,
        tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as cov_json_file,
    ):

        junit_path = junit_file.name
        cov_json_path = cov_json_file.name

    try:
        # Run only our new tests with overall coverage
        # Use structured machine-readable reports instead of parsing text output
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_product_varieties.py",
            "tests/test_product_finder_simple.py",
            "tests/test_bmi_core_validation_edges.py",
            "--cov=.",
            "--cov-fail-under=97",
            f"--junitxml={junit_path}",  # JUnit XML for test results
            f"--cov-report=json:{cov_json_path}",  # JSON for coverage data
            "--cov-report=term-missing",  # Keep terminal output for fallback
            "--tb=no",  # No traceback for faster execution
            "-q",  # Quiet mode
        ]

        # Timeout aligned with analyze_coverage_gaps.py (600s) for consistency
        # Note: This script runs a subset of tests, so typically completes faster
        # nosec B603: Safe subprocess invocation - cmd is a static list built from
        # sys.executable and hardcoded pytest arguments only; no user input or
        # external data is used. Timeout (600s) prevents hangs.
        result = subprocess.run(  # nosec B603
            cmd, capture_output=True, text=True, timeout=600, cwd=Path(__file__).parent
        )
        elapsed = time.time() - start_time

        print(f"⏱️  Execution time: {elapsed:.1f}s")

        # Parse JUnit XML for test results
        try:
            tree = ET.parse(junit_path)  # nosec B314
            root = tree.getroot()

            # Extract test counts from testsuite element
            testsuite = root.find(".//testsuite")
            if testsuite is not None:
                tests = int(testsuite.get("tests", 0))
                failures = int(testsuite.get("failures", 0))
                errors = int(testsuite.get("errors", 0))
                skipped = int(testsuite.get("skipped", 0))
                passed = tests - failures - errors - skipped

                print(f"✅ Tests passed: {passed}")
                if failures > 0:
                    print(f"❌ Tests failed: {failures}")
                if errors > 0:
                    print(f"⚠️  Tests errors: {errors}")
                if skipped > 0:
                    print(f"⏭️  Tests skipped: {skipped}")
            else:
                print("⚠️  Could not parse test results from JUnit XML")
        except ET.ParseError as xml_error:
            print(f"⚠️  Error parsing JUnit XML (malformed XML): {xml_error}")
            # Fallback to stdout parsing
            print(f"✅ Tests passed: {result.stdout.count(' PASSED')} (fallback)")
        except (FileNotFoundError, PermissionError) as file_error:
            print(f"⚠️  Error accessing JUnit XML file: {file_error}")
            # Fallback to stdout parsing
            print(f"✅ Tests passed: {result.stdout.count(' PASSED')} (fallback)")
        except Exception as e:
            print(f"⚠️  Unexpected error parsing JUnit XML: {e}")
            # Fallback to stdout parsing
            print(f"✅ Tests passed: {result.stdout.count(' PASSED')} (fallback)")

        # Parse JSON coverage report
        try:
            with open(cov_json_path, "r", encoding="utf-8") as f:
                cov_data = json.load(f)

            # Extract overall coverage percentage from totals
            totals = cov_data.get("totals", {})
            percent_covered = totals.get("percent_covered")

            if percent_covered is not None:
                print(f"🎯 Overall coverage: {percent_covered:.2f}%")
                print(
                    f"📊 Coverage details: {totals.get('num_statements', 0)} statements, "
                    f"{totals.get('covered_lines', 0)} covered, "
                    f"{totals.get('missing_lines', 0)} missing"
                )
            else:
                print("❌ Could not extract coverage percentage from JSON")
        except Exception as json_error:
            print(f"⚠️  Error parsing coverage JSON: {json_error}")
            # Fallback to stdout parsing
            for line in result.stdout.split("\n"):
                if "TOTAL" in line and "%" in line:
                    print(f"📊 Coverage result: {line} (fallback)")
                    break

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⏰ Coverage check timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Clean up temporary files
        for path_str in [junit_path, cov_json_path]:
            try:
                Path(path_str).unlink(missing_ok=True)
            except Exception:  # nosec B110
                pass  # Ignore cleanup errors


if __name__ == "__main__":
    success = run_coverage_check()
    print(f"🏁 Coverage check {'completed' if success else 'failed'}")
