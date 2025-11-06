#!/usr/bin/env python3
import copy
import json
import logging
import os
import subprocess  # nosec B404
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)

VERS: Path = Path("cache/food_db/database_versions.json")

# Console preview limit for stdout/stderr (increased from 500)
CONSOLE_PREVIEW_LIMIT: int = 1000

# ASCII-safe status labels for CI/terminal compatibility
STATUS_OK: str = "[OK]"
STATUS_REJECTED: str = "[REJECTED]"
STATUS_ERROR: str = "[ERROR]"

CANDIDATES: list[str] = [
    "20250924_180009",  # YYYYMMDD_HHMMSS
    "20250924-180009",  # YYYYMMDD-HHMMSS
    "20250924180009",  # YYYYMMDDHHMMSS
    "v20250924-180009",  # v + YYYYMMDD-HHMMSS
    "2025.09.24+180009",  # dotted date + HHMMSS
]


class DatabaseMetadataDict(TypedDict):
    """Metadata dictionary for a single database source."""

    source: str
    version: str
    last_updated: str
    record_count: int
    checksum: str
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
        # Default SHA-256 to align with validate_data.py
        "checksum": ("44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"),
        "metadata": {
            "update_type": "default",
            "api_source": "Open Food Facts",
            "sample_size": 0,
        },
    }
}


def _log_validation_error(
    error_type: str,
    error_details: str,
    stdout: str,
    stderr: str,
    *,
    prefix: str,
) -> None:
    """Compose, persist, and log a standardized validation error message.

    Builds a full output blob, writes it to a timestamped log file using the provided
    prefix, creates truncated previews for console readability, and logs a consolidated
    error message including truncation indicators and the path to the saved log file.
    """
    full_output = (
        f"=== {error_type} ===\n\n"
        f"{error_details}\n\n"
        f"=== STDOUT ===\n{stdout}\n\n"
        f"=== STDERR ===\n{stderr}\n"
    )
    log_file = write_log_file(full_output, prefix=prefix)

    stdout_preview = (
        stdout[:CONSOLE_PREVIEW_LIMIT] if len(stdout) > CONSOLE_PREVIEW_LIMIT else stdout
    )
    stderr_preview = (
        stderr[:CONSOLE_PREVIEW_LIMIT] if len(stderr) > CONSOLE_PREVIEW_LIMIT else stderr
    )

    msg = f"{error_type}. {error_details} " f"stdout ({len(stdout)} chars): {stdout_preview}"
    if len(stdout) > CONSOLE_PREVIEW_LIMIT:
        msg += "... (truncated, see full log)"
    if stderr:
        msg += f", stderr ({len(stderr)} chars): {stderr_preview}"
        if len(stderr) > CONSOLE_PREVIEW_LIMIT:
            msg += "... (truncated, see full log)"

    if log_file:
        msg += f"\nFull output saved to: {log_file}"
    else:
        msg += "\n(Note: Failed to save full output to log file)"

    logger.error(msg)


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
    temp_fd = None
    temp_path = None
    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename: normalize_off_version_YYYYMMDD_HHMMSS.log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"{prefix}_{timestamp}.log"

        # Atomic write pattern: write to temp file, then atomically replace
        # Create a temporary file in the same directory as the target
        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(logs_dir), prefix=f".{prefix}_", suffix=".tmp"
        )

        # Write content to temporary file with UTF-8 encoding
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        temp_fd = None  # File descriptor is closed by fdopen

        # Atomically replace the target file
        os.replace(temp_path, log_file)
        temp_path = None  # Successfully moved, no need to clean up

        return log_file
    except Exception as e:
        logger.warning(f"Failed to write log file: {e}")
        # Clean up temporary file if it exists
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except Exception as close_err:
                logger.debug("Failed to close temporary file descriptor: %s", close_err)
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as unlink_err:
                logger.debug("Failed to unlink temporary file %s: %s", temp_path, unlink_err)
        return None


def _atomic_write_json(target_path: Path, data: Dict[str, Any]) -> None:
    """Atomically write JSON to target_path.

    RU: Атомарная запись JSON в файл: во временный файл в той же директории,
    затем os.replace(). Гарантирует целостность при сбоях.
    EN: Atomic JSON write using temp file in same directory followed by os.replace().
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = None
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        with tempfile.NamedTemporaryFile(dir=str(target_path.parent), delete=False) as tf:
            tmp_file = Path(tf.name)
            tf.write(json_bytes)
            tf.flush()
            os.fsync(tf.fileno())
        # Replace atomically
        os.replace(tmp_file, target_path)
    except Exception:
        # Best-effort cleanup
        if tmp_file and tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception as cleanup_err:
                logger.debug("Failed to remove temporary JSON file %s: %s", tmp_file, cleanup_err)
        raise


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
        meta = copy.deepcopy(DEFAULT_DATABASE_METADATA)
        _atomic_write_json(VERS, meta)
    else:
        meta = json.loads(VERS.read_text(encoding="utf-8"))
        # Defensively validate meta: ensure it's a dict
        if not isinstance(meta, dict):
            logger.warning(f"{VERS} contains non-dict data, replacing with default structure")
            meta = copy.deepcopy(DEFAULT_DATABASE_METADATA)

    # Defensively validate openfoodfacts: ensure it's a dict
    if not isinstance(meta.get("openfoodfacts"), dict):
        logger.warning(
            f"{VERS} openfoodfacts is not a dict (type: {type(meta.get('openfoodfacts'))}), "
            "overwriting with new dict"
        )
        meta["openfoodfacts"] = copy.deepcopy(DEFAULT_DATABASE_METADATA["openfoodfacts"])

    # Set the version key on the validated dict
    meta["openfoodfacts"]["version"] = v
    _atomic_write_json(VERS, meta)


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
            _log_validation_error(
                error_type=f"Validation Error (exit code: {process_result.returncode})",
                error_details="Subprocess returned non-zero exit status",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                prefix="normalize_off_version_validation_error",
            )
            return 1

        # Parse JSON output (canonical success detection method)
        # The validation script uses --json flag, so output should be structured JSON
        try:
            result_data = json.loads(process_result.stdout.strip())
            if isinstance(result_data, dict) and result_data.get("success") is True:
                return 0
            # JSON parsed but success field is not True
            _log_validation_error(
                error_type="Validation JSON Parsed But Success Not True",
                error_details=f"result_data: {result_data}",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                prefix="normalize_off_version_success_not_true",
            )
            return 1
        except json.JSONDecodeError as e:
            _log_validation_error(
                error_type="Validation JSON Parse Error",
                error_details=f"JSONDecodeError: {e}",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                prefix="normalize_off_version_json_error",
            )
            return 1
        except AttributeError as e:
            _log_validation_error(
                error_type="Validation JSON Structure Error",
                error_details=f"AttributeError: {e}",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                prefix="normalize_off_version_structure_error",
            )
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
    if not CANDIDATES:
        logger.error(
            "no candidates provided: CANDIDATES list is empty, "
            "cannot normalize database version. "
            "Context: expected non-empty list of version string candidates to test."
        )
        return 2
    for v in CANDIDATES:
        set_version(v)
        code = validate()
        if code == 0:
            logger.info(f"{STATUS_OK} version accepted: {v}")
            return 0
        else:
            logger.info(f"{STATUS_REJECTED} version rejected: {v}")
    logger.error(f"{STATUS_ERROR} none of the candidates passed; keep last tried value")
    return 2


if __name__ == "__main__":
    sys.exit(main())
