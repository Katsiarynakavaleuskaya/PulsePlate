#!/usr/bin/env python3
import json
import subprocess  # nosec B404
import sys
from pathlib import Path

VERS = Path("cache/food_db/database_versions.json")

CANDIDATES = [
    "20250924_180009",  # YYYYMMDD_HHMMSS
    "20250924-180009",  # YYYYMMDD-HHMMSS
    "20250924180009",  # YYYYMMDDHHMMSS
    "2025-09-24T18:00:09Z",  # ISO-like in version (некоторые валидаторы так любят)
    "v20250924-180009",  # v + YYYYMMDD-HHMMSS
    "2025.09.24+180009",  # dotted date + HHMMSS
]


def set_version(v: str) -> None:
    """Set or normalize the version string in the database versions file.

    Sets the OpenFoodFacts version in the database_versions.json file to the
    provided version string. If the file does not exist, creates it with default
    metadata before updating the version.

    Args:
        v: Version string to set as the OpenFoodFacts database version.

    Side Effects:
        Creates cache/food_db/database_versions.json if it doesn't exist.
        Updates or creates the openfoodfacts.version field in the JSON file.
    """
    if not VERS.exists():
        print(f"WARNING: {VERS} missing, creating default", file=sys.stderr)
        # Create default database_versions.json if it doesn't exist
        VERS.parent.mkdir(parents=True, exist_ok=True)
        default_meta = {
            "openfoodfacts": {
                "source": "openfoodfacts",
                "version": "0.0.1",
                "last_updated": "1970-01-01T00:00:00.000000+00:00",
                "record_count": 0,
                "checksum": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
                "metadata": {
                    "update_type": "default",
                    "api_source": "Open Food Facts",
                    "sample_size": 0,
                },
            }
        }
        VERS.write_text(json.dumps(default_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        meta = default_meta
    else:
        meta = json.loads(VERS.read_text(encoding="utf-8"))

    off = dict(meta.get("openfoodfacts") or {})
    off["version"] = v
    meta["openfoodfacts"] = off
    VERS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def validate() -> int:
    """Run data validation by executing the validation script.

    Executes scripts/validate_data.py as a subprocess and checks the output
    for successful validation. Success is indicated by the presence of "DATA:OK"
    in either stdout or stderr output.

    Returns:
        0 on success (DATA:OK found in output), 1 on failure.

    Side Effects:
        Writes validation script output to stdout and stderr.
    """
    try:
        process_result = subprocess.run(  # nosec B603
            [sys.executable, "scripts/validate_data.py"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        sys.stdout.write(process_result.stdout)
        sys.stderr.write(process_result.stderr)

        if process_result.returncode != 0:
            error_msg = (
                f"Validation script exited with code {process_result.returncode}. "
                f"stdout: {process_result.stdout[:500]}, "
                f"stderr: {process_result.stderr[:500]}"
            )
            print(f"ERROR: {error_msg}", file=sys.stderr)
            return 1

        # Return 0 if validation passed, otherwise 1
        return 0 if "DATA:OK" in (process_result.stdout + process_result.stderr) else 1
    except subprocess.TimeoutExpired as e:
        error_msg = f"Validation script timed out after 30 seconds: {e}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        # Try to kill the process if it's still running (process attribute available in Python 3.3+)
        if hasattr(e, "process") and e.process:
            try:
                e.process.kill()
                e.process.wait(timeout=5)
            except Exception as cleanup_err:
                # Process may have already terminated; ignore cleanup errors
                print(f"Warning: Could not clean up process: {cleanup_err}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        error_msg = "Validation script not found: scripts/validate_data.py"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        return 1
    except OSError as e:
        error_msg = f"OS error while running validation script: {e}"
        print(f"ERROR: {error_msg}", file=sys.stderr)
        return 1


def main() -> int:
    """Program entrypoint that normalizes and validates database version.

    Iterates through candidate version string formats, sets each version using
    set_version(), and validates it using validate(). Returns successfully on
    the first candidate that passes validation, otherwise returns error code
    after trying all candidates.

    Expected Arguments:
        None (uses module-level CANDIDATES list).

    Returns:
        0 if a valid version format is found and accepted.
        2 if none of the candidate versions pass validation.

    Side Effects:
        Calls set_version() and validate() for each candidate.
        Prints validation results to stdout.
        Modifies cache/food_db/database_versions.json file.
    """
    for v in CANDIDATES:
        set_version(v)
        code = validate()
        if code == 0:
            print(f"✅ version accepted: {v}")
            return 0
        else:
            print(f"… version rejected: {v}")
    print("❌ none of the candidates passed; keep last tried value")
    return 2


if __name__ == "__main__":
    sys.exit(main())
