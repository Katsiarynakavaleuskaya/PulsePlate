#!/usr/bin/env python3
"""Food Database Update Scheduler.

RU: Планировщик обновления базы данных продуктов.
EN: Food database update scheduler.
"""

import argparse
import logging
import os
import random
import subprocess  # nosec B404 - controlled execution of internal script
import sys
import time
from typing import Callable

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

# Configure logging
# Ensure logs directory exists before configuring file handler
logs_dir_path = os.path.join(project_root, "logs")
logs_dir: str | None = None
logs_dir_created = False

try:
    os.makedirs(logs_dir_path, exist_ok=True)
    logs_dir = logs_dir_path
    logs_dir_created = True
except Exception as e:
    print(
        f"Warning: Failed to create logs directory '{logs_dir_path}': {e}\n"
        "Continuing without file logging.",
        file=sys.stderr,
    )

# Configure handlers - only add FileHandler if logs directory was created
handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
if logs_dir_created and logs_dir:
    try:
        log_file_path = os.path.join(logs_dir, "food_db_update.log")
        handlers.append(logging.FileHandler(log_file_path))
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


def _get_env_int(env_var: str, default: int) -> int:
    """Get integer value from environment variable or return default.

    Args:
        env_var: Environment variable name.
        default: Default value if env var is not set or invalid.

    Returns:
        Integer value from environment variable or default.
    """
    env_value = os.getenv(env_var)
    if env_value is not None:
        try:
            return int(env_value)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid value for environment variable {env_var}: {env_value}. "
                f"Using default: {default}"
            )
    return default


def _get_env_float(env_var: str, default: float) -> float:
    """Get float value from environment variable or return default.

    Args:
        env_var: Environment variable name.
        default: Default value if env var is not set or invalid.

    Returns:
        Float value from environment variable or default.
    """
    env_value = os.getenv(env_var)
    if env_value is not None:
        try:
            return float(env_value)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid value for environment variable {env_var}: {env_value}. "
                f"Using default: {default}"
            )
    return default


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


class OperationalMetrics:
    """Operational metrics tracker for retry operations.

    RU: Трекер операционных метрик для операций с повторными попытками.
    EN: Operational metrics tracker for retry operations.
    """

    def __init__(self) -> None:
        """Initialize metrics."""
        self.failure_count = 0
        self.retry_count = 0
        self.total_attempts = 0
        self.last_error: str | None = None
        self.last_return_code: int | None = None

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
        max_delay: Maximum delay in seconds.
        jitter_factor: Jitter factor (0.0 to 1.0).

    Returns:
        Delay in seconds.
    """
    # Exponential backoff: initial_delay * (multiplier ^ attempt)
    delay = initial_delay * (multiplier**attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter: random value between -jitter_factor and +jitter_factor
    jitter = delay * jitter_factor * (2 * random.random() - 1)  # nosec B311 - not used for crypto
    delay_with_jitter = delay + jitter

    # Ensure non-negative
    return max(0.0, delay_with_jitter)


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
    logger.info("Starting food database update with operational resiliency...")
    logger.info(
        f"Retry configuration: max_retries={max_retries}, "
        f"timeout_per_attempt={timeout_per_attempt}s, overall_timeout={overall_timeout}s"
    )

    metrics = OperationalMetrics()
    build_script = os.path.join(project_root, "scripts", "build_food_db.py")
    start_time = time.time()

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
            result = subprocess.run(  # nosec B603 - static arguments invoke trusted build script
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
                    stdout_lines = result.stdout.strip().split("\n")
                    if len(stdout_lines) <= 5:
                        # If output is short, show all lines
                        stdout_summary = " | ".join(stdout_lines)
                    else:
                        # Show last 3 lines as summary
                        stdout_summary = " | ".join(stdout_lines[-3:])
                    # Limit total summary length
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
                metrics.record_failure(error_msg, return_code=result.returncode)

                # Check if we have retries left
                if attempt < max_retries:
                    delay = calculate_backoff_delay(
                        attempt, initial_delay, backoff_multiplier, max_delay, jitter_factor
                    )
                    logger.info(
                        f"Retrying after {delay:.2f}s delay (attempt {attempt + 1}/{max_retries + 1} failed)"
                    )
                    metrics.record_retry()
                    emit_operational_signal(
                        "retry",
                        metrics,
                        attempt=attempt,
                        delay=delay,
                        monitoring_hook=monitoring_hook,
                    )
                    time.sleep(delay)
                else:
                    # Final failure
                    logger.error(
                        f"Food database update failed after {max_retries + 1} attempts. "
                        f"Final return code: {result.returncode}"
                    )
                    emit_operational_signal(
                        "final_failure", metrics, attempt=attempt, monitoring_hook=monitoring_hook
                    )
                    return False

        except subprocess.TimeoutExpired:
            # Timeout on this attempt
            error_msg = f"Food database update timed out on attempt {attempt + 1} (timeout={attempt_timeout:.1f}s)"
            logger.warning(error_msg)
            metrics.record_failure(error_msg, return_code=None)

            # Check if we have retries left and budget remaining
            elapsed_time = time.time() - start_time
            remaining_budget = overall_timeout - elapsed_time

            if attempt < max_retries and remaining_budget > 0:
                delay = calculate_backoff_delay(
                    attempt, initial_delay, backoff_multiplier, max_delay, jitter_factor
                )
                # Adjust delay to fit within remaining budget
                delay = min(delay, remaining_budget - 1)  # Leave 1s buffer

                if delay > 0:
                    logger.info(
                        f"Retrying after {delay:.2f}s delay (attempt {attempt + 1}/{max_retries + 1} timed out, "
                        f"remaining_budget={remaining_budget:.1f}s)"
                    )
                    metrics.record_retry()
                    emit_operational_signal(
                        "retry",
                        metrics,
                        attempt=attempt,
                        delay=delay,
                        monitoring_hook=monitoring_hook,
                    )
                    time.sleep(delay)
                else:
                    # No time left for retry
                    logger.error("No time remaining in overall timeout budget for retry")
                    emit_operational_signal(
                        "final_failure", metrics, attempt=attempt, monitoring_hook=monitoring_hook
                    )
                    return False
            else:
                # Final failure - timeout
                elapsed_total = time.time() - start_time
                logger.error(
                    f"Food database update timed out after {attempt + 1} attempts "
                    f"(total_time={elapsed_total:.2f}s)"
                )
                emit_operational_signal(
                    "final_failure", metrics, attempt=attempt, monitoring_hook=monitoring_hook
                )
                return False

        except Exception as e:
            # Unexpected exception - transient failure possible
            error_msg = f"Food database update failed with exception on attempt {attempt + 1}: {e}"
            logger.warning(error_msg, exc_info=True)
            metrics.record_failure(error_msg, return_code=None)

            # Check if we have retries left
            if attempt < max_retries:
                elapsed_time = time.time() - start_time
                remaining_budget = overall_timeout - elapsed_time

                if remaining_budget > 0:
                    delay = calculate_backoff_delay(
                        attempt, initial_delay, backoff_multiplier, max_delay, jitter_factor
                    )
                    # Adjust delay to fit within remaining budget
                    delay = min(delay, remaining_budget - 1)  # Leave 1s buffer

                    if delay > 0:
                        logger.info(
                            f"Retrying after {delay:.2f}s delay "
                            f"(attempt {attempt + 1}/{max_retries + 1} failed with exception)"
                        )
                        metrics.record_retry()
                        emit_operational_signal(
                            "retry",
                            metrics,
                            attempt=attempt,
                            delay=delay,
                            monitoring_hook=monitoring_hook,
                        )
                        time.sleep(delay)
                    else:
                        # No time left for retry
                        logger.error("No time remaining in overall timeout budget for retry")
                        emit_operational_signal(
                            "final_failure",
                            metrics,
                            attempt=attempt,
                            monitoring_hook=monitoring_hook,
                        )
                        return False
                else:
                    # Budget exhausted
                    logger.error("Overall timeout budget exhausted")
                    emit_operational_signal(
                        "final_failure", metrics, attempt=attempt, monitoring_hook=monitoring_hook
                    )
                    return False
            else:
                # Final failure - exception
                elapsed_total = time.time() - start_time
                logger.error(
                    f"Food database update failed after {max_retries + 1} attempts "
                    f"with exception (total_time={elapsed_total:.2f}s)"
                )
                emit_operational_signal(
                    "final_failure", metrics, attempt=attempt, monitoring_hook=monitoring_hook
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

    # Helper function to get value from env or use default
    def get_env_or_default(
        env_var: str, default: int | float, type_func: type[int] | type[float] = int
    ) -> int | float:
        """Get value from environment variable or return default."""
        env_value = os.getenv(env_var)
        if env_value is not None:
            try:
                converted = type_func(env_value)
                # Type checker can't infer the exact type, but we know it's int or float
                return converted if isinstance(converted, (int, float)) else default
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid value for environment variable {env_var}: {env_value}. "
                    f"Using default: {default}"
                )
        return default

    # Parse max_retries
    default_max_retries = get_env_or_default("FOOD_DB_UPDATE_MAX_RETRIES", DEFAULT_MAX_RETRIES)
    parser.add_argument(
        "--max-retries",
        type=int,
        default=default_max_retries,
        help=(
            "Maximum number of retry attempts (total attempts = max_retries + 1). "
            "Can be set via FOOD_DB_UPDATE_MAX_RETRIES environment variable."
        ),
    )

    # Parse timeout_per_attempt (with --timeout as alias)
    default_timeout_per_attempt = get_env_or_default(
        "FOOD_DB_UPDATE_TIMEOUT_PER_ATTEMPT", DEFAULT_TIMEOUT_PER_ATTEMPT, float
    )
    parser.add_argument(
        "--timeout-per-attempt",
        "--timeout",
        dest="timeout_per_attempt",
        type=float,
        default=default_timeout_per_attempt,
        help=(
            "Timeout for each individual attempt in seconds. "
            "Can be set via FOOD_DB_UPDATE_TIMEOUT_PER_ATTEMPT environment variable."
        ),
    )

    # Parse overall_timeout
    default_overall_timeout = get_env_or_default(
        "FOOD_DB_UPDATE_OVERALL_TIMEOUT", DEFAULT_OVERALL_TIMEOUT, float
    )
    parser.add_argument(
        "--overall-timeout",
        type=float,
        default=default_overall_timeout,
        help=(
            "Overall timeout budget for all attempts in seconds. "
            "Can be set via FOOD_DB_UPDATE_OVERALL_TIMEOUT environment variable."
        ),
    )

    # Parse initial_delay
    default_initial_delay = get_env_or_default(
        "FOOD_DB_UPDATE_INITIAL_DELAY", DEFAULT_INITIAL_DELAY, float
    )
    parser.add_argument(
        "--initial-delay",
        type=float,
        default=default_initial_delay,
        help=(
            "Initial delay before first retry in seconds. "
            "Can be set via FOOD_DB_UPDATE_INITIAL_DELAY environment variable."
        ),
    )

    # Parse backoff_multiplier
    default_backoff_multiplier = get_env_or_default(
        "FOOD_DB_UPDATE_BACKOFF_MULTIPLIER", DEFAULT_BACKOFF_MULTIPLIER, float
    )
    parser.add_argument(
        "--backoff-multiplier",
        type=float,
        default=default_backoff_multiplier,
        help=(
            "Multiplier for exponential backoff. "
            "Can be set via FOOD_DB_UPDATE_BACKOFF_MULTIPLIER environment variable."
        ),
    )

    # Parse max_delay
    default_max_delay = get_env_or_default("FOOD_DB_UPDATE_MAX_DELAY", DEFAULT_MAX_DELAY, float)
    parser.add_argument(
        "--max-delay",
        type=float,
        default=default_max_delay,
        help=(
            "Maximum delay between retries in seconds. "
            "Can be set via FOOD_DB_UPDATE_MAX_DELAY environment variable."
        ),
    )

    # Parse jitter_factor
    default_jitter_factor = get_env_or_default(
        "FOOD_DB_UPDATE_JITTER_FACTOR", DEFAULT_JITTER_FACTOR, float
    )
    parser.add_argument(
        "--jitter-factor",
        type=float,
        default=default_jitter_factor,
        help=(
            "Jitter factor (0.0 to 1.0) for randomization. "
            "Can be set via FOOD_DB_UPDATE_JITTER_FACTOR environment variable."
        ),
    )

    return parser.parse_args()


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
