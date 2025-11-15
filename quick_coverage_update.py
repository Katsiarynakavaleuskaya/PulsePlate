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
from pathlib import Path

from defusedxml import ElementTree as ET


def fallback_tests_from_stdout(result: subprocess.CompletedProcess[str]) -> None:
    """Print test results fallback from stdout when JUnit XML parsing fails."""
    passed = result.stdout.count(" PASSED")
    failed = result.stdout.count(" FAILED")
    errors = result.stdout.count(" ERROR")
    skipped = result.stdout.count(" SKIPPED")
    print(
        f"✅ Tests: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped (fallback)"
    )


def fallback_coverage_from_stdout(result: subprocess.CompletedProcess[str]) -> None:
    """Print coverage results fallback from stdout when JSON parsing fails."""
    for line in result.stdout.split("\n"):
        if "TOTAL" in line and "%" in line:
            print(f"📊 Coverage result: {line} (fallback)")
            break


def run_coverage_check() -> bool:
    """Run coverage on our new test files specifically."""
    print("🔍 Checking coverage progress...")
    start_time = time.perf_counter()

    # Initialize paths before with block to avoid NameError in finally
    junit_path: str | None = None
    cov_json_path: str | None = None

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
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=Path(__file__).resolve().parent,
        )
        elapsed = time.perf_counter() - start_time

        print(f"⏱️  Execution time: {elapsed:.1f}s")

        # Parse JUnit XML for test results
        try:
            tree = ET.parse(junit_path)
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
                # Fallback to stdout parsing
                fallback_tests_from_stdout(result)
        except ET.ParseError as xml_error:
            print(f"⚠️  Error parsing JUnit XML (malformed XML): {xml_error}")
            # Fallback to stdout parsing
            fallback_tests_from_stdout(result)
        except (FileNotFoundError, PermissionError) as file_error:
            print(f"⚠️  Error accessing JUnit XML file: {file_error}")
            # Fallback to stdout parsing
            fallback_tests_from_stdout(result)
        except Exception as e:
            print(f"⚠️  Unexpected error parsing JUnit XML: {e}")
            # Fallback to stdout parsing
            fallback_tests_from_stdout(result)

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
        except FileNotFoundError:
            print(f"⚠️  Coverage JSON file not found: {cov_json_path}")
            # Fallback to stdout parsing
            fallback_coverage_from_stdout(result)
        except PermissionError as perm_error:
            print(f"⚠️  Permission denied accessing coverage JSON file: {perm_error}")
            # Fallback to stdout parsing
            fallback_coverage_from_stdout(result)
        except json.JSONDecodeError as json_decode_error:
            print(
                f"⚠️  Invalid JSON in coverage report "
                f"(line {json_decode_error.lineno}, col {json_decode_error.colno}): "
                f"{json_decode_error.msg}"
            )
            # Fallback to stdout parsing
            fallback_coverage_from_stdout(result)
        except UnicodeDecodeError as unicode_error:
            print(f"⚠️  Unicode decode error in coverage JSON file: {unicode_error}")
            # Fallback to stdout parsing
            fallback_coverage_from_stdout(result)
        except (KeyError, TypeError) as data_error:
            print(f"⚠️  Unexpected JSON structure in coverage report: {data_error}")
            # Fallback to stdout parsing
            fallback_coverage_from_stdout(result)
        except Exception as json_error:
            print(
                f"⚠️  Unexpected error parsing coverage JSON: "
                f"{type(json_error).__name__}: {json_error}"
            )
            # Fallback to stdout parsing
            fallback_coverage_from_stdout(result)

        if result.returncode != 0:
            print("🔎 pytest stdout (failure):")
            print(result.stdout)
            if result.stderr:
                print("⚠️  pytest stderr (failure):")
                print(result.stderr)
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
            if path_str is not None:
                try:
                    Path(path_str).unlink(missing_ok=True)
                except Exception:  # nosec B110
                    pass  # Ignore cleanup errors


if __name__ == "__main__":
    success = run_coverage_check()
    print(f"🏁 Coverage check {'completed' if success else 'failed'}")
