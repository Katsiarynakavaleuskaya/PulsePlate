#!/usr/bin/env python3
"""
Secure API key updater used by tests and CLI tooling.

The module keeps behaviour intentionally chatty so the CLI and tests can assert
on human-readable messages without re-implementing the business logic.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Iterable, Tuple

import secure_config

# Expose encryption helpers for tests to monkeypatch
ENCRYPTION_AVAILABLE: bool = secure_config.ENCRYPTION_AVAILABLE
encrypt_value = secure_config.encrypt_value

API_KEY_PREFIX: str = os.getenv("API_KEY_PREFIX", "sk-")
API_KEY_MIN_LENGTH: int = int(os.getenv("API_KEY_MIN_LENGTH", "20"))
API_KEY_MAX_LENGTH: int = int(os.getenv("API_KEY_MAX_LENGTH", "256"))
API_KEY_ALLOWED_CHARS: str = os.getenv(
    "API_KEY_ALLOWED_CHARS",
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.",
)

PROFILE_CONFIG: Dict[str, Dict[str, str]] = {
    "premium": {
        "description": "Paid/Premium key configuration",
        "env_var": "OPENAI_API_KEY",
        "settings_key": "cursor.ai.openaiApiKey",
        "mcp_server": "pulseplate-chatgpt",
    },
    "free": {
        "description": "Free tier key configuration",
        "env_var": "OPENAI_API_KEY",
        "settings_key": "cursor.ai.openaiApiKeyFree",
        "mcp_server": "pulseplate-chatgpt-free",
    },
}
DEFAULT_PROFILE = "premium"


def _cursor_home() -> Path:
    return Path.home() / ".cursor"


def _encryption_available() -> bool:
    """Return True only when both secure_config and module flags allow encryption."""
    return bool(getattr(secure_config, "ENCRYPTION_AVAILABLE", False) and ENCRYPTION_AVAILABLE)


def _validate_api_key(api_key: str) -> Tuple[bool, str]:
    if not api_key.startswith(API_KEY_PREFIX):
        return False, "❌ Invalid API key format: expected prefix 'sk-'."
    if not (API_KEY_MIN_LENGTH <= len(api_key) <= API_KEY_MAX_LENGTH):
        return (
            False,
            f"❌ Invalid API key format: length must be between {API_KEY_MIN_LENGTH}"
            f" and {API_KEY_MAX_LENGTH} characters.",
        )
    if not set(api_key) <= set(API_KEY_ALLOWED_CHARS):
        return False, "❌ Invalid API key format: contains unsupported characters."
    return True, ""


def _update_env_file(cursor_root: Path, env_var: str, encrypted_value: str) -> bool:
    env_file = cursor_root / ".env"
    if not env_file.exists():
        return False

    lines = env_file.read_text().splitlines()
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if not line or "=" not in line:
            new_lines.append(line)
            continue
        key, value = line.split("=", 1)
        if key == env_var:
            new_lines.append(f"{env_var}={encrypted_value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{env_var}={encrypted_value}")
    env_file.write_text("\n".join(new_lines) + "\n")
    return True


def _update_settings_json(cursor_root: Path, settings_key: str, api_key: str) -> bool:
    settings_file = cursor_root / "settings.json"
    if not settings_file.exists():
        return False

    try:
        current = json.loads(settings_file.read_text() or "{}")
    except json.JSONDecodeError:
        current = {}
    current[settings_key] = api_key
    settings_file.write_text(json.dumps(current, indent=2, ensure_ascii=False))
    return True


def _update_mcp_config(
    cursor_root: Path,
    server_name: str,
    env_var: str,
    api_key: str,
) -> bool:
    mcp_file = cursor_root / "mcp.json"
    if not mcp_file.exists():
        return False

    try:
        config = json.loads(mcp_file.read_text() or "{}")
    except json.JSONDecodeError:
        config = {}

    servers = config.setdefault("mcpServers", {})
    server = servers.setdefault(server_name, {})
    env_block = server.setdefault("env", {})
    env_block[env_var] = api_key
    mcp_file.write_text(json.dumps(config, indent=2, ensure_ascii=False))
    return True


def update_api_key(
    api_key: str,
    *,
    profile: str = DEFAULT_PROFILE,
    use_encryption: bool = True,
) -> bool:
    """Validate and persist an API key for CLI tooling."""
    profile_entry = PROFILE_CONFIG.get(profile)
    if profile_entry is None:
        print(f"❌ Invalid profile '{profile}'. Available profiles: {', '.join(PROFILE_CONFIG)}")
        return False

    is_valid, error_message = _validate_api_key(api_key)
    if not is_valid:
        print(error_message or "❌ Invalid API key format")
        return False

    if not _encryption_available():
        print("❌ cryptography library not installed - encryption is required for secure storage.")
        return False

    if not use_encryption:
        print("❌ Encryption is required. Please enable encryption.")
        return False

    print("API key will be stored encrypted (cryptography detected).")

    try:
        cipher_text = encrypt_value(api_key)
    except RuntimeError as exc:
        print(f"❌ Error: {exc}")
        return False

    if not cipher_text.startswith("encrypted:"):
        print("❌ Encryption failed: unexpected output format.")
        return False

    cursor_root = _cursor_home()
    env_updated = _update_env_file(cursor_root, profile_entry["env_var"], cipher_text)
    if env_updated:
        print("✅ Updated .env with encrypted key.")

    settings_updated = _update_settings_json(
        cursor_root,
        profile_entry["settings_key"],
        api_key,
    )
    if settings_updated:
        print("✅ settings.json updated with plain text key.")

    mcp_updated = _update_mcp_config(
        cursor_root,
        profile_entry["mcp_server"],
        profile_entry["env_var"],
        api_key,
    )
    if mcp_updated:
        print("✅ MCP configuration updated.")

    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PulsePlate API key management utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set premium API key interactively
  python update_api_key.py

  # Set premium API key directly
  python update_api_key.py --api-key sk-your-key-here

  # Set free tier API key
  python update_api_key.py --profile free --api-key sk-your-free-key-here
""",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (if omitted, an interactive prompt is shown)",
    )
    parser.add_argument(
        "--profile",
        choices=list(PROFILE_CONFIG.keys()),
        default=DEFAULT_PROFILE,
        help=f"Profile to update (default: {DEFAULT_PROFILE})",
    )
    return parser


def main() -> None:
    """CLI entrypoint used by tests and developers."""
    parser = _build_parser()
    args = parser.parse_args()

    print("🔑 PulsePlate API Key Configuration")
    print("=" * 45)

    profile_entry = PROFILE_CONFIG[args.profile]
    api_key = args.api_key
    if not api_key:
        prompt = f"Enter your {profile_entry['description']} OpenAI API key (sk-...): "
        api_key = input(prompt).strip()

    if not api_key:
        print("❌ No API key provided")
        return

    if not _encryption_available():
        print("❌ Encryption not available. Please install 'cryptography' and retry.")
        return

    if update_api_key(api_key, profile=args.profile, use_encryption=True):
        print("🎉 API key updated successfully!")
        print(f"✅ {profile_entry['description']} updated successfully!")
    else:
        print("❌ Failed to update configuration")


if __name__ == "__main__":
    main()
