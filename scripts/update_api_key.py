#!/usr/bin/env python3
"""Secure stdin-based API key updater. / Безопасный обновитель API-ключа через stdin."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import from local module (this file is the module)
# DEFAULT_PROFILE and update_api_key are defined in this file below

# API Key validation constants (can be overridden via environment variables)
# Константы валидации API-ключа (можно переопределить через переменные окружения)
API_KEY_PREFIX: str = os.environ.get("API_KEY_PREFIX", "sk-")


def _safe_int_from_env(env_var: str, default: int) -> int:
    """Safely convert environment variable to integer with fallback.

    RU: Безопасно преобразовать переменную окружения в целое число с резервным значением.
    EN: Safely convert environment variable to integer with fallback.

    Args:
        env_var: Environment variable name
        default: Default value to use if conversion fails

    Returns:
        Integer value from environment or default
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger = logging.getLogger(__name__)
        logger.warning(
            "Invalid integer value for %s: '%s', using default: %s",
            env_var,
            value,
            default,
        )
        return default


API_KEY_MIN_LENGTH: int = _safe_int_from_env("API_KEY_MIN_LENGTH", 20)
API_KEY_MAX_LENGTH: int = _safe_int_from_env("API_KEY_MAX_LENGTH", 256)
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

    logger = logging.getLogger(__name__)

    env_key: str = os.environ.get("OPENAI_API_KEY", "").strip()
    key_source = "OPENAI_API_KEY environment variable"
    if env_key:
        # Security: Remove from environment to prevent accidental leakage
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
    )

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


# Profile configuration for API key management
DEFAULT_PROFILE: str = "default"

PROFILE_CONFIG: dict[str, dict[str, str]] = {
    "default": {
        "description": "Paid/Premium",
        "env_key": "OPENAI_API_KEY",
    },
    "free": {
        "description": "Free tier",
        "env_key": "OPENAI_API_KEY_FREE",
    },
}


def update_api_key(
    api_key: str, profile: str = DEFAULT_PROFILE, use_encryption: bool = True
) -> bool:
    """Update API key in configuration files.

    RU: Обновить API-ключ в файлах конфигурации.
    EN: Update API key in configuration files.

    Args:
        api_key: The API key to store
        profile: Profile name (default, free, etc.)
        use_encryption: Whether to encrypt the key (requires cryptography)

    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    # Validate profile
    if profile not in PROFILE_CONFIG:
        logger.error(
            "Invalid profile '%s'. Valid profiles: %s", profile, list(PROFILE_CONFIG.keys())
        )
        print(f"❌ Invalid profile '{profile}'. Valid profiles: {', '.join(PROFILE_CONFIG.keys())}")
        return False

    # Validate encryption availability
    if use_encryption and not ENCRYPTION_AVAILABLE:
        logger.error("Encryption requested but cryptography library not installed")
        print("❌ Encryption not available. Please install 'cryptography' and retry.")
        return False

    try:
        from secure_config import encrypt_value

        # Encrypt the key if requested
        if use_encryption:
            try:
                encrypted_key = encrypt_value(api_key)
                if not encrypted_key.startswith("encrypted:"):
                    logger.error("Encryption failed: output does not start with 'encrypted:'")
                    print("❌ Encryption failed: invalid output format")
                    return False
                key_value = encrypted_key
            except RuntimeError as e:
                logger.error("Encryption failed: %s", e)
                print(f"❌ Encryption failed: {e}")
                return False
        else:
            key_value = api_key

        # Update MCP configuration
        mcp_file = Path.home() / ".cursor" / "mcp.json"
        if mcp_file.exists():
            import json

            try:
                with open(mcp_file, "r", encoding="utf-8") as f:
                    mcp_config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to read MCP config: %s", e)
                mcp_config = {"mcpServers": {}}

            if "mcpServers" not in mcp_config:
                mcp_config["mcpServers"] = {}

            server_name = "pulseplate-chatgpt"
            if server_name not in mcp_config["mcpServers"]:
                mcp_config["mcpServers"][server_name] = {}

            if "env" not in mcp_config["mcpServers"][server_name]:
                mcp_config["mcpServers"][server_name]["env"] = {}

            env_key_name = PROFILE_CONFIG[profile]["env_key"]
            mcp_config["mcpServers"][server_name]["env"][env_key_name] = key_value

            try:
                with open(mcp_file, "w", encoding="utf-8") as f:
                    json.dump(mcp_config, f, indent=2)
                logger.info("Updated MCP configuration")
            except (IOError, OSError) as e:
                logger.warning("Failed to write MCP config: %s", e)

        # Update .env file if it exists
        env_file = Path.home() / ".cursor" / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except IOError as e:
                logger.warning("Failed to read .env file: %s", e)
                lines = []

            env_key_name = PROFILE_CONFIG[profile]["env_key"]
            updated = False
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{env_key_name}="):
                    new_lines.append(f"{env_key_name}={key_value}\n")
                    updated = True
                else:
                    new_lines.append(line)

            if not updated:
                new_lines.append(f"{env_key_name}={key_value}\n")

            try:
                with open(env_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                logger.info("Updated .env file")
            except (IOError, OSError) as e:
                logger.warning("Failed to write .env file: %s", e)

        # Update settings.json if it exists
        settings_file = Path.home() / ".cursor" / "settings.json"
        if settings_file.exists():
            import json

            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to read settings.json: %s", e)
                settings = {}

            settings["cursor.ai.openaiApiKey"] = api_key

            try:
                with open(settings_file, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2)
                logger.info("Updated settings.json")
            except (IOError, OSError) as e:
                logger.warning("Failed to write settings.json: %s", e)

        logger.info("API key updated successfully for profile '%s'", profile)
        return True

    except Exception as e:
        logger.exception("Unexpected error updating API key: %s", e)
        print(f"❌ Error: {e}")
        return False


# Check encryption availability
try:
    from secure_config import ENCRYPTION_AVAILABLE
except ImportError:
    ENCRYPTION_AVAILABLE = False


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
