#!/usr/bin/env python3
"""Food Database Update Scheduler.

RU: Планировщик обновления базы данных продуктов.
EN: Food database update scheduler.
"""

import argparse
import logging
import math
import os
import random
import subprocess  # nosec B404 - controlled execution of internal script
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

# Convert project_root to Path for pathlib operations
project_root_path = Path(project_root)

# Configure logging
# Ensure logs directory exists before configuring file handler
logs_dir = project_root_path / "logs"
logs_dir_created = False

try:
    logs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir_created = True
except Exception as e:
    print(
        f"Warning: Failed to create logs directory '{logs_dir}': {e}\n"
        "Continuing without file logging.",
        file=sys.stderr,
    )

# Configure handlers - only add FileHandler if logs directory was created
handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
if logs_dir_created:
    try:
        log_file_path = logs_dir / "food_db_update.log"
        handlers.append(logging.FileHandler(str(log_file_path)))
    except Exception as e:
        print(
            f"Warning: Failed to create file handler for '{log_file_path}': {e}\n"
            "Continuing without file logging.",
            file=sys.stderr,
        )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

T = TypeVar("T")


def _get_env_value(env_var: str, default: T, cast_func: Callable[[str], T]) -> T:
    """Get value from environment variable with type casting or return default.

    Generic helper function for parsing environment variables with type conversion.
    Attempts to cast the environment variable value using the provided cast function.
    If the value is missing or casting fails, returns the default value.

    Args:
        env_var: Environment variable name.
        default: Default value if env var is not set or invalid.
        cast_func: Function to cast the string value (e.g., int, float).

    Returns:
        Casted value from environment variable or default.
    """
    env_value = os.getenv(env_var)
    if env_value is not None:
        try:
            return cast_func(env_value)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid value for environment variable {env_var}: {env_value}. "
                f"Using default: {default}"
            )
    return default


def _get_env_int(env_var: str, default: int) -> int:
    """Get integer value from environment variable or return default.

    Args:
        env_var: Environment variable name.
        default: Default value if env var is not set or invalid.

    Returns:
        Integer value from environment variable or default.
    """
    return _get_env_value(env_var, default, int)


def _get_env_float(env_var: str, default: float) -> float:
    """Get float value from environment variable or return default.

    Args:
        env_var: Environment variable name.
        default: Default value if env var is not set or invalid.

    Returns:
        Float value from environment variable or default.
    """
    return _get_env_value(env_var, default, float)


# Configuration constants (configurable via environment variables)
DEFAULT_MAX_RETRIES = _get_env_int("FOOD_DB_UPDATE_MAX_RETRIES", 3)
DEFAULT_INITIAL_DELAY = _get_env_float("FOOD_DB_UPDATE_INITIAL_DELAY", 1.0)  # seconds
DEFAULT_BACKOFF_MULTIPLIER = _get_env_float("FOOD_DB_UPDATE_BACKOFF_MULTIPLIER", 2.0)
DEFAULT_MAX_DELAY = _get_env_float("FOOD_DB_UPDATE_MAX_DELAY", 60.0)  # seconds
DEFAULT_JITTER_FACTOR = _get_env_float("FOOD_DB_UPDATE_JITTER_FACTOR", 0.1)  # 10% jitter
DEFAULT_TIMEOUT_PER_ATTEMPT = _get_env_float(
    "FOOD_DB_UPDATE_TIMEOUT_PER_ATTEMPT", 300
)  # 5 minutes per attempt
DEFAULT_OVERALL_TIMEOUT = _get_env_float(
    "FOOD_DB_UPDATE_OVERALL_TIMEOUT", 1200
)  # 20 minutes total budget


def _validate_config(
    max_retries: int,
    timeout_per_attempt: float,
    overall_timeout: float,
    initial_delay: float,
    max_delay: float,
    jitter_factor: float,
) -> None:
    """Validate configuration parameters for consistency and range checks.

    RU: Проверить параметры конфигурации на согласованность и диапазоны.
    EN: Validate configuration parameters for consistency and range checks.

    Args:
        max_retries: Maximum number of retry attempts.
        timeout_per_attempt: Timeout for each individual attempt in seconds.
        overall_timeout: Overall timeout budget for all attempts in seconds.
        initial_delay: Initial delay before first retry in seconds.
        max_delay: Maximum delay between retries in seconds.
        jitter_factor: Jitter factor for randomization (0.0 to 1.0).

    Raises:
        ValueError: If any parameter is out of valid range.
    """
    # Validate max_retries >= 0
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")

    # Validate timeout_per_attempt > 0
    if timeout_per_attempt <= 0:
        raise ValueError(f"timeout_per_attempt must be > 0, got {timeout_per_attempt}")

    # Validate overall_timeout > 0
    if overall_timeout <= 0:
        raise ValueError(f"overall_timeout must be > 0, got {overall_timeout}")

    # Validate initial_delay >= 0
    if initial_delay < 0:
        raise ValueError(f"initial_delay must be >= 0, got {initial_delay}")

    # Validate max_delay >= 0
    if max_delay < 0:
        raise ValueError(f"max_delay must be >= 0, got {max_delay}")

    # Validate jitter_factor between 0.0 and 1.0
    if not (0.0 <= jitter_factor <= 1.0):
        raise ValueError(f"jitter_factor must be between 0.0 and 1.0, got {jitter_factor}")

    # Warn if overall_timeout < timeout_per_attempt (makes multiple attempts unlikely)
    if overall_timeout < timeout_per_attempt:
        logger.warning(
            f"overall_timeout ({overall_timeout}s) is less than "
            f"timeout_per_attempt ({timeout_per_attempt}s). "
            f"This makes multiple attempts unlikely."
        )


@dataclass
class OperationalMetrics:
    """Operational metrics tracker for retry operations.

    RU: Трекер операционных метрик для операций с повторными попытками.
    EN: Operational metrics tracker for retry operations.
    """

    failure_count: int = 0
    retry_count: int = 0
    total_attempts: int = 0
    last_error: str | None = None
    last_return_code: int | None = None

    def record_attempt(self) -> None:
        """Record an attempt."""
        self.total_attempts += 1

    def record_failure(self, error: str, return_code: int | None = None) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_error = error
        self.last_return_code = return_code

    def record_retry(self) -> None:
        """Record a retry attempt."""
        self.retry_count += 1

    def record_success(self) -> None:
        """Record success."""
        self.last_error = None
        self.last_return_code = 0

    def reset(self) -> None:
        """Reset all metrics."""
        self.failure_count = 0
        self.retry_count = 0
        self.total_attempts = 0
        self.last_error = None
        self.last_return_code = None


def calculate_backoff_delay(
    attempt: int,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
) -> float:
    """Calculate exponential backoff delay with jitter.

    RU: Вычислить задержку экспоненциального отката с джиттером.
    EN: Calculate exponential backoff delay with jitter.

    Args:
        attempt: Current attempt number (0-indexed).
        initial_delay: Initial delay in seconds.
        multiplier: Backoff multiplier.
        max_delay: Maximum delay in seconds. If max_delay < initial_delay,
            it will be clamped to initial_delay and a warning will be logged.
        jitter_factor: Jitter factor (0.0 to 1.0).

    Returns:
        Delay in seconds.

    Raises:
        ValueError: If input parameters are invalid.
        OverflowError: If the computed delay would overflow (should be caught internally).
    """
    # Input validation
    if attempt < 0:
        raise ValueError(f"attempt must be non-negative, got {attempt}")
    if initial_delay < 0:
        raise ValueError(f"initial_delay must be non-negative, got {initial_delay}")
    if max_delay < 0:
        raise ValueError(f"max_delay must be non-negative, got {max_delay}")
    if multiplier <= 0:
        raise ValueError(f"multiplier must be > 0, got {multiplier}")
    if not (0.0 <= jitter_factor <= 1.0):
        raise ValueError(f"jitter_factor must be between 0.0 and 1.0, got {jitter_factor}")

    # Ensure max_delay >= initial_delay
    if max_delay < initial_delay:
        original_max_delay = max_delay
        logger.warning(
            f"max_delay ({original_max_delay}) < initial_delay ({initial_delay}); "
            f"adjusting max_delay to {initial_delay}"
        )
        max_delay = initial_delay

    # Compute exponential safely with overflow protection
    # multiplier > 0 is guaranteed by validation above
    try:
        # Calculate safe cap before powering to avoid overflow
        # If multiplier^attempt would exceed max_allowed, cap at max_delay directly
        if initial_delay > 0:
            max_allowed_power = max_delay / initial_delay
            # Avoid taking log of 0 or negative, and handle very large values
            if multiplier > 1 and max_allowed_power > 0:
                max_safe_attempt = math.log(max_allowed_power) / math.log(multiplier)
                if attempt > max_safe_attempt:
                    delay = max_delay
                else:
                    delay = initial_delay * math.pow(multiplier, attempt)
            elif multiplier < 1:
                # For multiplier < 1, values decrease, so no overflow risk
                delay = initial_delay * math.pow(multiplier, attempt)
            else:
                # multiplier == 1, so delay is constant
                delay = initial_delay
        else:
            # initial_delay is 0, so delay is 0
            delay = 0.0
    except OverflowError:
        # If overflow occurs, cap at max_delay
        delay = max_delay

    # Cap at max_delay (safety check)
    delay = min(delay, max_delay)

    # Add jitter: random value between -jitter_factor and +jitter_factor
    jitter = delay * jitter_factor * (2 * random.random() - 1)  # nosec B311
    delay_with_jitter = delay + jitter

    # Ensure non-negative and clamp between 0.0 and max_delay
    return max(0.0, min(delay_with_jitter, max_delay))


def emit_operational_signal(
    signal_type: str,
    metrics: OperationalMetrics,
    attempt: int | None = None,
    delay: float | None = None,
    monitoring_hook: Callable[[str, dict], None] | None = None,
) -> None:
    """Emit operational signal for monitoring/alerting.

    RU: Отправить операционный сигнал для мониторинга/алертинга.
    EN: Emit operational signal for monitoring/alerting.

    Args:
        signal_type: Type of signal ('failure', 'retry', 'success', 'final_failure').
        metrics: Current operational metrics.
        attempt: Current attempt number (if applicable).
        delay: Delay before next attempt (if applicable).
        monitoring_hook: Optional monitoring hook to call.
    """
    signal_data = {
        "signal_type": signal_type,
        "failure_count": metrics.failure_count,
        "retry_count": metrics.retry_count,
        "total_attempts": metrics.total_attempts,
        "last_error": metrics.last_error,
        "last_return_code": metrics.last_return_code,
    }

    if attempt is not None:
        signal_data["attempt"] = attempt
    if delay is not None:
        signal_data["delay_seconds"] = delay

    # Log the signal
    logger.info(f"Operational signal: {signal_type}", extra=signal_data)

    # Call monitoring hook if provided
    if monitoring_hook:
        try:
            monitoring_hook(signal_type, signal_data)
        except Exception as e:
            logger.warning(f"Monitoring hook failed: {e}", exc_info=True)


def _should_retry_and_calculate_delay(
    attempt: int,
    max_retries: int,
    start_time: float,
    overall_timeout: float,
    initial_delay: float,
    backoff_multiplier: float,
    max_delay: float,
    jitter_factor: float,
) -> tuple[bool, float]:
    """Determine if retry should occur and calculate delay.

    RU: Определить, должна ли произойти повторная попытка, и вычислить задержку.
    EN: Determine if retry should occur and calculate delay.

    Checks elapsed time against overall timeout budget, calculates exponential backoff delay,
    and adjusts it to fit within remaining budget with a 1s buffer.

    Args:
        attempt: Current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.
        start_time: Start time of the operation (timestamp).
        overall_timeout: Overall timeout budget for all attempts in seconds.
        initial_delay: Initial delay before first retry in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
        max_delay: Maximum delay between retries in seconds.
        jitter_factor: Jitter factor (0.0 to 1.0) for randomization.

    Returns:
        Tuple of (should_retry: bool, delay: float). If should_retry is False, delay is 0.0.
    """
    # Check if we have retries left
    if attempt >= max_retries:
        return (False, 0.0)

    # Calculate elapsed time and remaining budget
    elapsed_time = time.time() - start_time
    remaining_budget = overall_timeout - elapsed_time

    # Need at least 1s buffer for the retry attempt itself
    if remaining_budget <= 1.0:
        return (False, 0.0)

    # Calculate backoff delay
    delay = calculate_backoff_delay(
        attempt, initial_delay, backoff_multiplier, max_delay, jitter_factor
    )

    # Adjust delay to fit within remaining budget (leave 1s buffer)
    delay = min(delay, remaining_budget - 1.0)

    # If delay becomes non-positive, we cannot retry
    if delay <= 0:
        return (False, 0.0)

    return (True, delay)


def _handle_retry_or_fail(
    error_msg: str,
    metrics: "OperationalMetrics",
    attempt: int,
    max_retries: int,
    start_time: float,
    overall_timeout: float,
    initial_delay: float,
    backoff_multiplier: float,
    max_delay: float,
    jitter_factor: float,
    monitoring_hook: Callable[[str, dict], None] | None,
    return_code: int | None = None,
) -> tuple[bool, float]:
    """Handle retry decision and execution logic.

    RU: Обработать логику принятия решения о повторной попытке и выполнение.
    EN: Handle retry decision and execution logic.

    Records the failure, checks if retry should occur, and emits appropriate
    operational signals. Returns whether to retry and the delay to wait.

    Args:
        error_msg: Error message to record.
        metrics: Operational metrics instance to record failure/retry.
        attempt: Current attempt number (0-indexed).
        max_retries: Maximum number of retry attempts.
        start_time: Start time of the operation (timestamp).
        overall_timeout: Overall timeout budget for all attempts in seconds.
        initial_delay: Initial delay before first retry in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
        max_delay: Maximum delay between retries in seconds.
        jitter_factor: Jitter factor (0.0 to 1.0) for randomization.
        monitoring_hook: Optional callable(signal_type: str, data: dict) for monitoring/alerting.
        return_code: Return code from subprocess (None if not applicable).

    Returns:
        Tuple of (should_retry: bool, delay: float). If should_retry is False, delay is 0.0.
    """
    # Record the failure
    metrics.record_failure(error_msg, return_code=return_code)

    # Check if we should retry and calculate delay
    should_retry, delay = _should_retry_and_calculate_delay(
        attempt,
        max_retries,
        start_time,
        overall_timeout,
        initial_delay,
        backoff_multiplier,
        max_delay,
        jitter_factor,
    )

    if should_retry:
        metrics.record_retry()
        emit_operational_signal(
            "retry",
            metrics,
            attempt=attempt,
            delay=delay,
            monitoring_hook=monitoring_hook,
        )
        return (True, delay)
    else:
        emit_operational_signal(
            "final_failure", metrics, attempt=attempt, monitoring_hook=monitoring_hook
        )
        return (False, 0.0)


def update_food_database(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
    timeout_per_attempt: float = DEFAULT_TIMEOUT_PER_ATTEMPT,
    overall_timeout: float = DEFAULT_OVERALL_TIMEOUT,
    monitoring_hook: Callable[[str, dict], None] | None = None,
) -> bool:
    """Update food database with retry logic and operational resiliency.

    RU: Обновить базу данных продуктов с логикой повторных попыток и операционной устойчивостью.
    EN: Update food database with retry logic and operational resiliency.

    Args:
        max_retries: Maximum number of retry attempts (total attempts = max_retries + 1).
        initial_delay: Initial delay before first retry in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
        max_delay: Maximum delay between retries in seconds.
        jitter_factor: Jitter factor (0.0 to 1.0) for randomization.
        timeout_per_attempt: Timeout for each individual attempt in seconds.
        overall_timeout: Overall timeout budget for all attempts in seconds.
        monitoring_hook: Optional callable(signal_type: str, data: dict) for monitoring/alerting.

    Returns:
        True if update succeeded, False otherwise.
    """
    # Validate configuration parameters early
    _validate_config(
        max_retries=max_retries,
        timeout_per_attempt=timeout_per_attempt,
        overall_timeout=overall_timeout,
        initial_delay=initial_delay,
        max_delay=max_delay,
        jitter_factor=jitter_factor,
    )

    logger.info("Starting food database update with operational resiliency...")
    logger.info(
        f"Retry configuration: max_retries={max_retries}, "
        f"timeout_per_attempt={timeout_per_attempt}s, overall_timeout={overall_timeout}s"
    )

    metrics = OperationalMetrics()
    build_script = os.path.join(project_root, "scripts", "build_food_db.py")
    start_time = time.time()

    # Fast-fail check: validate build script exists before entering retry loop
    if not os.path.isfile(build_script):
        error_msg = (
            f"Build script not found: {build_script}. " f"Cannot proceed with food database update."
        )
        logger.error(error_msg)
        metrics.record_failure(error_msg, return_code=None)
        return False

    for attempt in range(max_retries + 1):
        # Check overall timeout budget
        elapsed_time = time.time() - start_time
        remaining_budget = overall_timeout - elapsed_time

        if remaining_budget <= 0:
            logger.error(
                f"Overall timeout budget exhausted after {elapsed_time:.2f}s. "
                f"Cancelling remaining attempts."
            )
            emit_operational_signal(
                "final_failure",
                metrics,
                attempt=attempt,
                monitoring_hook=monitoring_hook,
            )
            return False

        # Adjust timeout for this attempt to fit within remaining budget
        attempt_timeout = min(timeout_per_attempt, remaining_budget)

        metrics.record_attempt()
        logger.info(
            f"Attempt {attempt + 1}/{max_retries + 1}: "
            f"Starting food database update (timeout={attempt_timeout:.1f}s, "
            f"remaining_budget={remaining_budget:.1f}s)"
        )

        try:
            # Run the build script
            result = subprocess.run(  # nosec B603
                [sys.executable, build_script],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=attempt_timeout,
            )

            if result.returncode == 0:
                elapsed_total = time.time() - start_time
                logger.info(
                    f"Food database update completed successfully on attempt {attempt + 1} "
                    f"(total_time={elapsed_total:.2f}s)"
                )
                # Log summary at INFO level for successful runs
                stdout_summary = ""
                if result.stdout:
                    stdout_lines = [line for line in result.stdout.strip().split("\n") if line]

                    if stdout_lines:
                        summary_lines = [stdout_lines[0]]
                        # Append last three lines that are not already in summary_lines
                        for line in stdout_lines[-3:]:
                            if line not in summary_lines:
                                summary_lines.append(line)

                        # Join up to 4 lines with " | "
                        stdout_summary = " | ".join(summary_lines[:4])

                        # Truncate to 300 characters adding "..." if trimmed
                        if len(stdout_summary) > 300:
                            stdout_summary = f"{stdout_summary[:297]}..."
                logger.info(
                    f"Build script success summary: return_code={result.returncode}, "
                    f"stdout_summary='{stdout_summary}'"
                )
                # Keep full stdout at DEBUG for detailed troubleshooting
                logger.debug(f"Full output: {result.stdout}")
                metrics.record_success()
                emit_operational_signal(
                    "success", metrics, attempt=attempt, monitoring_hook=monitoring_hook
                )
                return True
            else:
                # Non-zero return code - transient failure possible
                error_msg = (
                    f"Food database update failed with return code {result.returncode} "
                    f"on attempt {attempt + 1}"
                )
                logger.warning(error_msg)
                logger.debug(f"Error output: {result.stderr}")

                should_retry, delay = _handle_retry_or_fail(
                    error_msg=error_msg,
                    metrics=metrics,
                    attempt=attempt,
                    max_retries=max_retries,
                    start_time=start_time,
                    overall_timeout=overall_timeout,
                    initial_delay=initial_delay,
                    backoff_multiplier=backoff_multiplier,
                    max_delay=max_delay,
                    jitter_factor=jitter_factor,
                    monitoring_hook=monitoring_hook,
                    return_code=result.returncode,
                )

                if should_retry:
                    elapsed_time = time.time() - start_time
                    remaining_budget = overall_timeout - elapsed_time
                    logger.info(
                        f"Retrying after {delay:.2f}s delay (attempt {attempt + 1}/{max_retries + 1} failed, "
                        f"remaining_budget={remaining_budget:.1f}s)"
                    )
                    time.sleep(delay)
                else:
                    elapsed_total = time.time() - start_time
                    logger.error(
                        f"Food database update failed after {attempt + 1} attempts. "
                        f"Final return code: {result.returncode}"
                    )
                    return False

        except subprocess.TimeoutExpired:
            # Timeout on this attempt
            error_msg = f"Food database update timed out on attempt {attempt + 1} (timeout={attempt_timeout:.1f}s)"
            logger.warning(error_msg)

            should_retry, delay = _handle_retry_or_fail(
                error_msg=error_msg,
                metrics=metrics,
                attempt=attempt,
                max_retries=max_retries,
                start_time=start_time,
                overall_timeout=overall_timeout,
                initial_delay=initial_delay,
                backoff_multiplier=backoff_multiplier,
                max_delay=max_delay,
                jitter_factor=jitter_factor,
                monitoring_hook=monitoring_hook,
                return_code=None,
            )

            if should_retry:
                elapsed_time = time.time() - start_time
                remaining_budget = overall_timeout - elapsed_time
                logger.info(
                    f"Retrying after {delay:.2f}s delay (attempt {attempt + 1}/{max_retries + 1} timed out, "
                    f"remaining_budget={remaining_budget:.1f}s)"
                )
                time.sleep(delay)
            else:
                elapsed_total = time.time() - start_time
                remaining_budget = overall_timeout - elapsed_total
                if remaining_budget <= 1:
                    logger.error(
                        f"Food database update timed out - no time remaining for retry "
                        f"(remaining_budget={remaining_budget:.1f}s, elapsed={elapsed_total:.2f}s)"
                    )
                else:
                    logger.error(
                        f"Food database update timed out after {attempt + 1} attempts "
                        f"(total_time={elapsed_total:.2f}s)"
                    )
                return False

        except Exception as e:
            # Unexpected exception - transient failure possible
            error_msg = f"Food database update failed with exception on attempt {attempt + 1}: {e}"
            logger.warning(error_msg, exc_info=True)

            should_retry, delay = _handle_retry_or_fail(
                error_msg=error_msg,
                metrics=metrics,
                attempt=attempt,
                max_retries=max_retries,
                start_time=start_time,
                overall_timeout=overall_timeout,
                initial_delay=initial_delay,
                backoff_multiplier=backoff_multiplier,
                max_delay=max_delay,
                jitter_factor=jitter_factor,
                monitoring_hook=monitoring_hook,
                return_code=None,
            )

            if should_retry:
                logger.info(
                    f"Retrying after {delay:.2f}s delay "
                    f"(attempt {attempt + 1}/{max_retries + 1} failed with exception)"
                )
                time.sleep(delay)
            else:
                elapsed_total = time.time() - start_time
                remaining_budget = overall_timeout - elapsed_total
                if remaining_budget <= 1:
                    logger.error(
                        f"Food database update failed with exception - no time remaining for retry "
                        f"(remaining_budget={remaining_budget:.1f}s, elapsed={elapsed_total:.2f}s)"
                    )
                else:
                    logger.error(
                        f"Food database update failed after {attempt + 1} attempts "
                        f"with exception (total_time={elapsed_total:.2f}s)"
                    )
                return False

    # Should not reach here, but handle edge case
    logger.error("Unexpected end of retry loop")
    emit_operational_signal("final_failure", metrics, monitoring_hook=monitoring_hook)
    return False


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments with environment variable fallbacks.

    RU: Разобрать аргументы командной строки с резервными значениями из переменных окружения.
    EN: Parse command-line arguments with environment variable fallbacks.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Food Database Update Scheduler with retry and timeout configuration.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Parse max_retries
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=(
            "Maximum number of retry attempts (total attempts = max_retries + 1). "
            "Can be set via FOOD_DB_UPDATE_MAX_RETRIES environment variable."
        ),
    )

    # Parse timeout_per_attempt (with --timeout as alias)
    parser.add_argument(
        "--timeout-per-attempt",
        "--timeout",
        dest="timeout_per_attempt",
        type=float,
        default=DEFAULT_TIMEOUT_PER_ATTEMPT,
        help=(
            "Timeout for each individual attempt in seconds. "
            "Can be set via FOOD_DB_UPDATE_TIMEOUT_PER_ATTEMPT environment variable."
        ),
    )

    # Parse overall_timeout
    parser.add_argument(
        "--overall-timeout",
        type=float,
        default=DEFAULT_OVERALL_TIMEOUT,
        help=(
            "Overall timeout budget for all attempts in seconds. "
            "Can be set via FOOD_DB_UPDATE_OVERALL_TIMEOUT environment variable."
        ),
    )

    # Parse initial_delay
    parser.add_argument(
        "--initial-delay",
        type=float,
        default=DEFAULT_INITIAL_DELAY,
        help=(
            "Initial delay before first retry in seconds. "
            "Can be set via FOOD_DB_UPDATE_INITIAL_DELAY environment variable."
        ),
    )

    # Parse backoff_multiplier
    parser.add_argument(
        "--backoff-multiplier",
        type=float,
        default=DEFAULT_BACKOFF_MULTIPLIER,
        help=(
            "Multiplier for exponential backoff. "
            "Can be set via FOOD_DB_UPDATE_BACKOFF_MULTIPLIER environment variable."
        ),
    )

    # Parse max_delay
    parser.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY,
        help=(
            "Maximum delay between retries in seconds. "
            "Can be set via FOOD_DB_UPDATE_MAX_DELAY environment variable."
        ),
    )

    # Parse jitter_factor
    parser.add_argument(
        "--jitter-factor",
        type=float,
        default=DEFAULT_JITTER_FACTOR,
        help=(
            "Jitter factor (0.0 to 1.0) for randomization. "
            "Can be set via FOOD_DB_UPDATE_JITTER_FACTOR environment variable."
        ),
    )

    args = parser.parse_args()

    # Validate parsed arguments
    _validate_config(
        max_retries=args.max_retries,
        timeout_per_attempt=args.timeout_per_attempt,
        overall_timeout=args.overall_timeout,
        initial_delay=args.initial_delay,
        max_delay=args.max_delay,
        jitter_factor=args.jitter_factor,
    )

    return args


def main() -> None:
    """Main scheduler function.

    RU: Основная функция планировщика.
    EN: Main scheduler function.
    """
    logger.info("Food database update scheduler started")

    # Parse command-line arguments
    args = parse_args()

    # Log configuration being used
    logger.info(
        f"Configuration: max_retries={args.max_retries}, "
        f"timeout_per_attempt={args.timeout_per_attempt}s, "
        f"overall_timeout={args.overall_timeout}s, "
        f"initial_delay={args.initial_delay}s, "
        f"backoff_multiplier={args.backoff_multiplier}, "
        f"max_delay={args.max_delay}s, "
        f"jitter_factor={args.jitter_factor}"
    )

    # Update the food database with parsed arguments
    success = update_food_database(
        max_retries=args.max_retries,
        initial_delay=args.initial_delay,
        backoff_multiplier=args.backoff_multiplier,
        max_delay=args.max_delay,
        jitter_factor=args.jitter_factor,
        timeout_per_attempt=args.timeout_per_attempt,
        overall_timeout=args.overall_timeout,
    )

    if success:
        logger.info("Food database update scheduler completed successfully")
        sys.exit(0)
    else:
        logger.error("Food database update scheduler failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
