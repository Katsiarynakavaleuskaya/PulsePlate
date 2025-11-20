#!/usr/bin/env python3
"""Secure stdin-based API key updater. / Безопасный обновитель API-ключа через stdin.

This script reads the API key from either:
- OPENAI_API_KEY environment variable (read-only, not modified)
- stdin input

The script does NOT modify or remove environment variables to avoid side effects
for other tools running in the same process. The OPENAI_API_KEY environment
variable is read once and used for validation and storage, but remains unchanged
in the process environment.

RU: Этот скрипт читает API-ключ из переменной окружения OPENAI_API_KEY или stdin.
Переменные окружения не изменяются, чтобы избежать побочных эффектов для других
инструментов, работающих в том же процессе.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from types import ModuleType

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
sys.modules.setdefault("update_api_key", sys.modules[__name__])

secure_config: ModuleType | None
try:
    import secure_config as _secure_config
except ImportError:  # pragma: no cover - optional dependency
    secure_config = None
else:
    secure_config = _secure_config

ENCRYPTION_AVAILABLE = (
    getattr(secure_config, "ENCRYPTION_AVAILABLE", False) if secure_config else False
)
encrypt_value = getattr(secure_config, "encrypt_value", None) if secure_config else None


def _encryption_available() -> bool:
    """Return True when encryption helpers are available."""
    module_flag = getattr(secure_config, "ENCRYPTION_AVAILABLE", None) if secure_config else None
    global_flag = globals().get("ENCRYPTION_AVAILABLE", False)
    if module_flag is None:
        return bool(global_flag)
    return bool(global_flag) and bool(module_flag)


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


def _validate_api_key_value(
    api_key: str,
    *,
    key_source: str,
    prefix: str,
    min_len: int,
    max_len: int,
    allowed_chars_str: str,
    verbose_errors: bool,
    logger: logging.Logger,
) -> None:
    """Validate API key format and raise RuntimeError when invalid."""
    if not api_key:
        detailed_msg = (
            f"Invalid API key from {key_source}: key is empty. "
            f"API key must be non-empty, start with '{prefix}', be between {min_len}-{max_len} characters, "
            "and contain only allowed characters."
        )
        logger.warning("API key validation failed: key is empty")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    if not api_key.startswith(prefix):
        detailed_msg = (
            f"Invalid API key from {key_source}: key does not start with '{prefix}'. "
            f"API key length: {len(api_key)} characters. "
            f"API keys must start with '{prefix}' prefix."
        )
        logger.warning("API key validation failed: invalid prefix")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    if len(api_key) < min_len:
        detailed_msg = (
            f"Invalid API key from {key_source}: key is too short ({len(api_key)} characters). "
            f"API key must be at least {min_len} characters long."
        )
        logger.warning("API key validation failed: key too short")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    if len(api_key) > max_len:
        detailed_msg = (
            f"Invalid API key from {key_source}: key is too long ({len(api_key)} characters). "
            f"API key must be no longer than {max_len} characters."
        )
        logger.warning("API key validation failed: key too long")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)

    allowed_chars = set(allowed_chars_str)
    invalid_chars = [c for c in api_key if c not in allowed_chars]
    if invalid_chars:
        detailed_msg = (
            f"Invalid API key from {key_source}: contains invalid characters. "
            f"Found invalid characters: {set(invalid_chars)}. "
            f"API key must contain only allowed characters: {allowed_chars_str}."
        )
        logger.warning("API key validation failed: invalid characters detected")
        raise RuntimeError("Invalid API key" if not verbose_errors else detailed_msg)


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
        # Read-only access: we read the value but do NOT modify os.environ
        # to avoid side effects for other tools running in the same process
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

    _validate_api_key_value(
        api_key=api_key,
        key_source=key_source,
        prefix=prefix,
        min_len=min_len,
        max_len=max_len,
        allowed_chars_str=allowed_chars_str,
        verbose_errors=os.getenv("API_KEY_VERBOSE_ERRORS", "").lower()
        in (
            "1",
            "true",
            "on",
            "yes",
        ),
        logger=logger,
    )

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

    try:
        _validate_api_key_value(
            api_key=api_key,
            key_source="parameter",
            prefix=API_KEY_PREFIX,
            min_len=API_KEY_MIN_LENGTH,
            max_len=API_KEY_MAX_LENGTH,
            allowed_chars_str=API_KEY_ALLOWED_CHARS,
            verbose_errors=False,
            logger=logger,
        )
    except RuntimeError:
        print("❌ Invalid API key format")
        return False
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error validating API key: %s", exc)
        print(f"❌ Error: {exc}")
        return False

    # Validate encryption availability
    if use_encryption and encrypt_value is None:
        logger.error("Encryption requested but encrypt_value helper is unavailable")
        print("Encryption helper is not available")
        return False

    if not _encryption_available():
        logger.error("Encryption requested but cryptography library not installed")
        print("❌ Encryption not available. Please install 'cryptography' and retry.")
        return False

    try:
        # Security: Encrypt the key if requested, otherwise validate production environment
        encrypted_key: str | None = None
        if use_encryption and ENCRYPTION_AVAILABLE:
            try:
                encrypted_key = encrypt_value(api_key)  # type: ignore[misc]
                if encrypted_key is None or not encrypted_key.startswith("encrypted:"):
                    logger.error("Encryption failed: output does not start with 'encrypted:'")
                    print("❌ Encryption failed: invalid output format")
                    return False
                env_key_value = encrypted_key
                print("API key will be stored encrypted")
            except RuntimeError as e:
                logger.error("Encryption failed: %s", e)
                print(f"❌ Encryption failed: {e}")
                print(f"Error: {e}")
                return False
        else:
            # Store plaintext key only when explicitly requested (dev/test mode)
            # In production, this should never happen - use_encryption=True is default
            app_env = os.getenv("APP_ENV", "").strip().lower()
            is_production = app_env not in {"", "local", "dev", "development", "test"}
            if is_production:
                logger.error(
                    "Cannot store API key in plaintext in production. "
                    "Set use_encryption=True or use development environment."
                )
                print("❌ Cannot store API key in plaintext in production environment")
                return False
            env_key_value = api_key
            logger.warning(
                "API key stored in plaintext (use_encryption=False). "
                "This should only be used in local development/test environments."
            )

        # Security: Use encrypted value for MCP and settings.json if encryption was used
        # Never store API keys in plaintext in configuration files when encryption is available
        if encrypted_key is not None:
            mcp_key_value = encrypted_key
            settings_key_value = encrypted_key
        else:
            # Only allow plaintext in dev/test environments (already validated above)
            mcp_key_value = api_key
            settings_key_value = api_key

        # Update MCP configuration
        mcp_file = Path.home() / ".cursor" / "mcp.json"
        try:
            mcp_exists = mcp_file.exists()
        except OSError as e:
            logger.warning("Failed to access MCP config %s: %s", mcp_file, e)
            mcp_exists = True

        if mcp_exists:
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
            mcp_config["mcpServers"][server_name]["env"][env_key_name] = mcp_key_value

            try:
                with open(mcp_file, "w", encoding="utf-8") as f:
                    json.dump(mcp_config, f, indent=2)
                logger.info("Updated MCP configuration")
            except (IOError, OSError) as e:
                logger.warning("Failed to write MCP config: %s", e)

        # Update .env file if it exists
        env_file = Path.home() / ".cursor" / ".env"
        try:
            env_exists = env_file.exists()
        except OSError as e:
            logger.warning("Failed to access .env file %s: %s", env_file, e)
            env_exists = True

        if env_exists:
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
                line_stripped = line.strip()
                normalized_line = line if line.endswith("\n") else line + "\n"
                if line_stripped.startswith(f"{env_key_name}="):
                    # env_key_value is encrypted when use_encryption=True (checked above)
                    # When use_encryption=False, production check above prevents plaintext storage
                    new_lines.append(f"{env_key_name}={env_key_value}\n")
                    updated = True
                else:
                    new_lines.append(normalized_line)

            if not updated:
                # env_key_value is encrypted when use_encryption=True (checked above)
                # When use_encryption=False, production check above prevents plaintext storage
                new_lines.append(f"{env_key_name}={env_key_value}\n")

            # Security: Final check before writing - ensure we never write plaintext in production
            # This explicit check helps CodeQL understand the security guarantee
            if not use_encryption:
                app_env_check = os.getenv("APP_ENV", "").strip().lower()
                is_production_check = app_env_check not in {
                    "",
                    "local",
                    "dev",
                    "development",
                    "test",
                }
                if is_production_check:
                    logger.error(
                        "Security violation: Attempted to write plaintext API key in production"
                    )
                    return False

            try:
                # Security: env_key_value is encrypted when use_encryption=True (checked above)
                # When use_encryption=False, explicit production check above prevents plaintext storage
                # Only write if data is encrypted or in dev/test environment (validated above)
                with open(env_file, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                logger.info("Updated .env file")
            except (IOError, OSError) as e:
                logger.warning("Failed to write .env file: %s", e)

        # Update settings.json if it exists
        settings_file = Path.home() / ".cursor" / "settings.json"
        try:
            settings_exists = settings_file.exists()
        except OSError as e:
            logger.warning("Failed to access settings.json %s: %s", settings_file, e)
            settings_exists = True

        if settings_exists:
            import json

            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to read settings.json: %s", e)
                settings = {}

            # Security: Store encrypted key if encryption was used, otherwise plaintext (dev/test only)
            settings["cursor.ai.openaiApiKey"] = settings_key_value

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


def main() -> None:
    """Interactive CLI entrypoint for updating API keys."""
    description = "PulsePlate API key management utilities"
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update_api_key.py --api-key sk-your-key-here
  python update_api_key.py --profile free --api-key sk-your-free-key
""",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (if omitted, you will be prompted interactively)",
    )
    parser.add_argument(
        "--profile",
        choices=list(PROFILE_CONFIG.keys()),
        default=DEFAULT_PROFILE,
        help=f"Profile to update (default: {DEFAULT_PROFILE})",
    )

    use_argparse = bool(sys.argv and sys.argv[0].endswith("update_api_key.py"))
    args = parser.parse_args(sys.argv[1:] if use_argparse else [])

    print("🔑 PulsePlate API Key Configuration")
    print("=" * 45)

    api_key = args.api_key
    if not api_key:
        profile_desc = PROFILE_CONFIG[args.profile]["description"]
        try:
            api_key = input(f"Enter your {profile_desc} OpenAI API key (sk-...): ").strip()
        except EOFError:
            api_key = ""

    if not api_key:
        print("❌ No API key provided")
        return

    if encrypt_value is None:
        print("❌ Encryption helper is not available")
        return

    if not _encryption_available():
        print("❌ Encryption not available. Please install 'cryptography' and retry.")
        return

    success = update_api_key(api_key, profile=args.profile, use_encryption=True)
    if success:
        print("🎉 API key updated successfully!")
        profile_desc = PROFILE_CONFIG[args.profile]["description"]
        print(f"✅ {profile_desc} key configuration updated successfully!")
    else:
        print("❌ Failed to update configuration")


if __name__ == "__main__":
    main()
