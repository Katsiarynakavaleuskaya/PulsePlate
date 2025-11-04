#!/usr/bin/env python3
import copy
import json
import logging
import subprocess  # nosec B404
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict, cast

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)

VERS = Path("cache/food_db/database_versions.json")

# Console preview limit for stdout/stderr (increased from 500)
CONSOLE_PREVIEW_LIMIT = 1000

CANDIDATES = [
    "20250924_180009",  # YYYYMMDD_HHMMSS
    "20250924-180009",  # YYYYMMDD-HHMMSS
    "20250924180009",  # YYYYMMDDHHMMSS
    "2025-09-24T18:00:09Z",  # ISO-like in version (some validators prefer this)
    "v20250924-180009",  # v + YYYYMMDD-HHMMSS
    "2025.09.24+180009",  # dotted date + HHMMSS
]


class DatabaseMetadataDict(TypedDict):
    """Metadata dictionary for a single database source."""

    source: str
    version: str
    last_updated: str
    record_count: int
    checksum: Optional[str]  # None indicates no checksum available
    metadata: Dict[str, Any]


class DatabaseVersionsDict(TypedDict):
    """Top-level dictionary structure for database_versions.json."""

    openfoodfacts: DatabaseMetadataDict


DEFAULT_DATABASE_METADATA: DatabaseVersionsDict = {
    "openfoodfacts": {
        "source": "openfoodfacts",
        "version": "0.0.1",
        "last_updated": "1970-01-01T00:00:00.000000+00:00",
        "record_count": 0,
        "checksum": None,  # Sentinel value indicating no checksum available
        "metadata": {
            "update_type": "default",
            "api_source": "Open Food Facts",
            "sample_size": 0,
        },
    }
}


def write_log_file(content: str, prefix: str = "normalize_off_version") -> Optional[Path]:
    """Write content to a timestamped log file in the logs directory.

    RU: Записывает содержимое в файл лога с временной меткой в директории logs.
    EN: Writes content to a timestamped log file in the logs directory.

    Args:
        content: The text content to write to the log file.
        prefix: Prefix for the log file name (default: "normalize_off_version").

    Returns:
        Path to the created log file, or None if writing failed.

    Side Effects:
        Creates logs directory if it doesn't exist.
        Writes content to a timestamped log file.
    """
    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename: normalize_off_version_YYYYMMDD_HHMMSS.log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"{prefix}_{timestamp}.log"

        # Write content using text mode with UTF-8 encoding
        # Handle large content by writing directly without loading into memory
        log_file.write_text(content, encoding="utf-8")

        return log_file
    except Exception as e:
        logger.warning(f"Failed to write log file: {e}")
        return None


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
        logger.warning(f"{VERS} missing, creating default")
        # Create default database_versions.json if it doesn't exist
        VERS.parent.mkdir(parents=True, exist_ok=True)
        meta: Dict[str, Any] = cast(Dict[str, Any], copy.deepcopy(DEFAULT_DATABASE_METADATA))
        VERS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        meta = json.loads(VERS.read_text(encoding="utf-8"))
        # Defensively validate meta: ensure it's a dict
        if not isinstance(meta, dict):
            logger.warning(f"{VERS} contains non-dict data, replacing with empty dict")
            meta = {}

    # Defensively validate openfoodfacts: ensure it's a dict
    if not isinstance(meta.get("openfoodfacts"), dict):
        logger.warning(
            f"{VERS} openfoodfacts is not a dict (type: {type(meta.get('openfoodfacts'))}), "
            "overwriting with new dict"
        )
        meta["openfoodfacts"] = {}

    # Set the version key on the validated dict
    meta["openfoodfacts"]["version"] = v
    VERS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def validate() -> int:
    """Run data validation by executing the validation script.

    Executes scripts/validate_data.py with --json flag as a subprocess and checks
    the output for successful validation. Success requires both a zero returncode
    and a JSON response with "success": true in stdout.

    Returns:
        0 on success (zero returncode and JSON success field is True), 1 on failure.

    Side Effects:
        Writes validation script output to stdout and stderr.
        Logs detailed errors if JSON parsing fails or success field is not True.
    """
    try:
        process_result = subprocess.run(  # nosec B603
            [sys.executable, "scripts/validate_data.py", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        sys.stdout.write(process_result.stdout)
        sys.stderr.write(process_result.stderr)

        # First verify returncode is zero
        if process_result.returncode != 0:
            # Write full output to timestamped log file
            full_output = (
                f"=== Validation Error (exit code: {process_result.returncode}) ===\n\n"
                f"=== STDOUT ===\n{process_result.stdout}\n\n"
                f"=== STDERR ===\n{process_result.stderr}\n"
            )
            log_file = write_log_file(full_output, prefix="normalize_off_version_validation_error")

            # Create console message with truncated preview and log file path
            stdout_preview = (
                process_result.stdout[:CONSOLE_PREVIEW_LIMIT]
                if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT
                else process_result.stdout
            )
            stderr_preview = (
                process_result.stderr[:CONSOLE_PREVIEW_LIMIT]
                if len(process_result.stderr) > CONSOLE_PREVIEW_LIMIT
                else process_result.stderr
            )

            error_msg = (
                f"Validation script exited with code {process_result.returncode}. "
                f"stdout ({len(process_result.stdout)} chars): {stdout_preview}"
                + (
                    "... (truncated, see full log)"
                    if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT
                    else ""
                )
                + ", "
                + f"stderr ({len(process_result.stderr)} chars): {stderr_preview}"
                + (
                    "... (truncated, see full log)"
                    if len(process_result.stderr) > CONSOLE_PREVIEW_LIMIT
                    else ""
                )
            )

            if log_file:
                error_msg += f"\nFull output saved to: {log_file}"
            else:
                error_msg += "\n(Note: Failed to save full output to log file)"

            logger.error(error_msg)
            return 1

        # Parse JSON output (canonical success detection method)
        # The validation script uses --json flag, so output should be structured JSON
        try:
            result_data = json.loads(process_result.stdout.strip())
            if isinstance(result_data, dict) and result_data.get("success") is True:
                return 0
            # JSON parsed but success field is not True
            # Write full output to timestamped log file
            full_output = (
                "=== Validation JSON Parsed But Success Not True ===\n\n"
                f"result_data: {result_data}\n\n"
                f"=== STDOUT ===\n{process_result.stdout}\n\n"
                f"=== STDERR ===\n{process_result.stderr}\n"
            )
            log_file = write_log_file(full_output, prefix="normalize_off_version_success_not_true")

            # Create console message with truncated preview and log file path
            stdout_preview = (
                process_result.stdout[:CONSOLE_PREVIEW_LIMIT]
                if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT
                else process_result.stdout
            )

            error_msg = (
                f"Validation JSON parsed but success is not True. "
                f"result_data: {result_data}, "
                f"stdout ({len(process_result.stdout)} chars): {stdout_preview}"
            )
            if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT:
                error_msg += "... (truncated, see full log)"

            if log_file:
                error_msg += f"\nFull output saved to: {log_file}"
            else:
                error_msg += "\n(Note: Failed to save full output to log file)"

            logger.error(error_msg)
            return 1
        except json.JSONDecodeError as e:
            # JSON parsing failed - log detailed error for debugging
            # Write full output to timestamped log file
            full_output = (
                f"=== Validation JSON Parse Error ===\n\n"
                f"JSONDecodeError: {e}\n\n"
                f"=== STDOUT ===\n{process_result.stdout}\n\n"
                f"=== STDERR ===\n{process_result.stderr}\n"
            )
            log_file = write_log_file(full_output, prefix="normalize_off_version_json_error")

            # Create console message with truncated preview and log file path
            stdout_preview = (
                process_result.stdout[:CONSOLE_PREVIEW_LIMIT]
                if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT
                else process_result.stdout
            )
            stderr_preview = (
                process_result.stderr[:CONSOLE_PREVIEW_LIMIT]
                if len(process_result.stderr) > CONSOLE_PREVIEW_LIMIT
                else process_result.stderr
            )

            error_msg = (
                f"Failed to parse validation JSON output. "
                f"JSONDecodeError: {e}, "
                f"stdout ({len(process_result.stdout)} chars): {stdout_preview}"
            )
            if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT:
                error_msg += "... (truncated, see full log)"
            error_msg += f", stderr ({len(process_result.stderr)} chars): {stderr_preview}"
            if len(process_result.stderr) > CONSOLE_PREVIEW_LIMIT:
                error_msg += "... (truncated, see full log)"

            if log_file:
                error_msg += f"\nFull output saved to: {log_file}"
            else:
                error_msg += "\n(Note: Failed to save full output to log file)"

            logger.error(error_msg)
            return 1
        except AttributeError as e:
            # Unexpected structure in parsed JSON
            # Write full output to timestamped log file
            full_output = (
                f"=== Validation JSON Structure Error ===\n\n"
                f"AttributeError: {e}\n\n"
                f"=== STDOUT ===\n{process_result.stdout}\n\n"
                f"=== STDERR ===\n{process_result.stderr}\n"
            )
            log_file = write_log_file(full_output, prefix="normalize_off_version_structure_error")

            # Create console message with truncated preview and log file path
            stdout_preview = (
                process_result.stdout[:CONSOLE_PREVIEW_LIMIT]
                if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT
                else process_result.stdout
            )

            error_msg = (
                f"Unexpected JSON structure from validation script. "
                f"Error: {e}, "
                f"stdout ({len(process_result.stdout)} chars): {stdout_preview}"
            )
            if len(process_result.stdout) > CONSOLE_PREVIEW_LIMIT:
                error_msg += "... (truncated, see full log)"

            if log_file:
                error_msg += f"\nFull output saved to: {log_file}"
            else:
                error_msg += "\n(Note: Failed to save full output to log file)"

            logger.error(error_msg)
            return 1
    except subprocess.TimeoutExpired as e:
        error_msg = f"Validation script timed out after 30 seconds: {e}"
        logger.error(error_msg)
        # Try to kill the process if it's still running (Python 3.3+ provides e.process)
        try:
            e.process.kill()  # type: ignore[attr-defined]
            e.process.wait(timeout=5)  # type: ignore[attr-defined]
        except Exception as cleanup_err:
            # Process may have already terminated; ignore cleanup errors
            logger.warning(f"Could not clean up process: {cleanup_err}")
        return 1
    except FileNotFoundError:
        error_msg = "Validation script not found: scripts/validate_data.py"
        logger.error(error_msg)
        return 1
    except OSError as e:
        error_msg = f"OS error while running validation script: {e}"
        logger.error(error_msg)
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
            logger.info(f"✅ version accepted: {v}")
            return 0
        else:
            logger.info(f"… version rejected: {v}")
    logger.error("❌ none of the candidates passed; keep last tried value")
    return 2


if __name__ == "__main__":
    sys.exit(main())
