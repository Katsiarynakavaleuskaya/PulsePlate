#!/usr/bin/env python3
"""Secure stdin-based API key updater. / Безопасный обновитель API-ключа через stdin."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from update_api_key import DEFAULT_PROFILE, update_api_key  # noqa: E402

# API Key validation constants (can be overridden via environment variables)
# Константы валидации API-ключа (можно переопределить через переменные окружения)
API_KEY_PREFIX: str = os.environ.get("API_KEY_PREFIX", "sk-")
API_KEY_MIN_LENGTH: int = int(os.environ.get("API_KEY_MIN_LENGTH", "20"))
API_KEY_MAX_LENGTH: int = int(os.environ.get("API_KEY_MAX_LENGTH", "256"))
API_KEY_ALLOWED_CHARS: str = os.environ.get(
    "API_KEY_ALLOWED_CHARS", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)


def _read_api_key(
    api_key_prefix: str | None = None,
    api_key_min_length: int | None = None,
    api_key_max_length: int | None = None,
    api_key_allowed_chars: str | None = None,
) -> str:
    """Read API key from stdin or OPENAI_API_KEY env var. / Читает API-ключ из stdin или переменной окружения OPENAI_API_KEY.

    Args:
        api_key_prefix: API key prefix to validate against (defaults to API_KEY_PREFIX constant).
        api_key_min_length: Minimum API key length (defaults to API_KEY_MIN_LENGTH constant).
        api_key_max_length: Maximum API key length (defaults to API_KEY_MAX_LENGTH constant).
        api_key_allowed_chars: String of allowed characters (defaults to API_KEY_ALLOWED_CHARS constant).

    Returns:
        Validated API key string.
    """
    # Use provided parameters or fall back to module constants
    prefix = api_key_prefix if api_key_prefix is not None else API_KEY_PREFIX
    min_len = api_key_min_length if api_key_min_length is not None else API_KEY_MIN_LENGTH
    max_len = api_key_max_length if api_key_max_length is not None else API_KEY_MAX_LENGTH
    allowed_chars_str = (
        api_key_allowed_chars if api_key_allowed_chars is not None else API_KEY_ALLOWED_CHARS
    )

    env_key: str = os.environ.get("OPENAI_API_KEY", "").strip()
    key_source = "OPENAI_API_KEY environment variable"
    if env_key:
        os.environ.pop("OPENAI_API_KEY", None)
        api_key = env_key
    else:
        stdin_data: str = sys.stdin.read().strip()
        if stdin_data:
            api_key = stdin_data
            key_source = "stdin"
        else:
            raise RuntimeError(
                "API key not provided via stdin or OPENAI_API_KEY environment variable."
                " / API-ключ не передан через stdin или переменную окружения OPENAI_API_KEY."
            )

    # Check if verbose errors are enabled (for debugging/development)
    verbose_errors = os.getenv("API_KEY_VERBOSE_ERRORS", "").lower() in (
        "1",
        "true",
        "on",
        "yes",
    ) or os.getenv("DEBUG", "").lower() in ("1", "true", "on", "yes")

    # Import logger for detailed diagnostics
    import logging

    logger = logging.getLogger(__name__)

    # Validate API key format
    if not api_key:
        detailed_msg = (
            f"Invalid API key from {key_source}: key is empty. "
            f"API key must be non-empty, start with '{prefix}', be between {min_len}-{max_len} characters, "
            "and contain only allowed characters."
        )
        logger.debug("API key validation failed: key is empty")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    if not api_key.startswith(prefix):
        detailed_msg = (
            f"Invalid API key from {key_source}: key does not start with '{prefix}'. "
            f"API key length: {len(api_key)} characters. "
            f"API keys must start with '{prefix}' prefix."
        )
        logger.debug("API key validation failed: invalid prefix")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    if len(api_key) < min_len:
        detailed_msg = (
            f"Invalid API key from {key_source}: key is too short ({len(api_key)} characters). "
            f"API key must be at least {min_len} characters long."
        )
        logger.debug("API key validation failed: key too short")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    if len(api_key) > max_len:
        detailed_msg = (
            f"Invalid API key from {key_source}: key is too long ({len(api_key)} characters). "
            f"API key must be no longer than {max_len} characters."
        )
        logger.debug("API key validation failed: key too long")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    # Check allowed characters
    allowed_chars = set(allowed_chars_str)
    invalid_chars = [c for c in api_key if c not in allowed_chars]
    if invalid_chars:
        detailed_msg = (
            f"Invalid API key from {key_source}: contains invalid characters. "
            f"Found invalid characters: {set(invalid_chars)}. "
            f"API key must contain only allowed characters: {allowed_chars_str}."
        )
        logger.debug("API key validation failed: invalid characters detected")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    return api_key


def main() -> None:
    """Entrypoint for secure key update flow. / Точка входа для безопасного обновления ключа."""
    try:
        # Read and validate API key
        try:
            api_key = _read_api_key()
        except RuntimeError as error:
            print(f"❌ {error}")
            sys.exit(1)

        # Update API key with error handling
        try:
            success = update_api_key(api_key, profile=DEFAULT_PROFILE, use_encryption=True)
            if not success:
                print("❌ Failed to update API key. Check error messages above for details.")
                sys.exit(1)
        except RuntimeError as error:
            print(f"❌ Error updating API key: {error}")
            sys.exit(1)
        except (IOError, OSError, PermissionError) as error:
            print(f"❌ File system error while updating API key: {error}")
            sys.exit(1)
        except Exception as error:
            print(f"❌ Unexpected error while updating API key: {type(error).__name__}: {error}")
            sys.exit(1)

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
        sys.exit(130)
    except Exception as error:
        print(f"❌ Unexpected error: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
