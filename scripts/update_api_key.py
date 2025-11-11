#!/usr/bin/env python3
"""Secure stdin-based API key updater. / Безопасный обновитель API-ключа через stdin."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from update_api_key import DEFAULT_PROFILE, update_api_key  # noqa: E402


def _read_api_key() -> str:
    """Read API key from stdin or OPENAI_API_KEY env var. / Читает API-ключ из stdin или переменной окружения OPENAI_API_KEY."""
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

    # Validate API key format
    if not api_key:
        raise RuntimeError(
            f"Invalid API key from {key_source}: key is empty. "
            "API key must be non-empty, start with 'sk-', be between 20-256 characters, "
            "and contain only alphanumeric characters, hyphens, and underscores."
        )

    if not api_key.startswith("sk-"):
        raise RuntimeError(
            f"Invalid API key from {key_source}: key does not start with 'sk-'. "
            f"Received key starts with: '{api_key[:5]}...' (first 5 characters shown). "
            "OpenAI API keys must start with 'sk-' prefix."
        )

    if len(api_key) < 20:
        raise RuntimeError(
            f"Invalid API key from {key_source}: key is too short ({len(api_key)} characters). "
            "API key must be at least 20 characters long."
        )

    if len(api_key) > 256:
        raise RuntimeError(
            f"Invalid API key from {key_source}: key is too long ({len(api_key)} characters). "
            "API key must be no longer than 256 characters."
        )

    # Check allowed characters: alphanumeric, hyphens, underscores, dots
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    invalid_chars = [c for c in api_key if c not in allowed_chars]
    if invalid_chars:
        raise RuntimeError(
            f"Invalid API key from {key_source}: contains invalid characters. "
            f"Found invalid characters: {set(invalid_chars)}. "
            "API key must contain only alphanumeric characters, hyphens, underscores, and dots."
        )

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

        # Success message
        print("✅ API key updated successfully!")
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
        sys.exit(130)
    except Exception as error:
        print(f"❌ Unexpected error: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
