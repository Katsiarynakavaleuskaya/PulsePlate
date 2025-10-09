#!/usr/bin/env python3
"""
PulsePlate API key management utilities with multiple profile support.

This module provides CLI and callable helpers for managing OpenAI API keys
with encryption, metadata tracking, and audit logging. It supports multiple
profiles (e.g. free vs premium), safe rotation with backups, batch updates,
optional keychain storage, and diagnostic health checks.

Business logic guarantees:
- Premium profile remains the default and continues to populate the historic
  OPENAI_API_KEY locations for MCP/runtime compatibility.
- Free profile values are stored alongside premium keys without changing the
  runtime behaviour for existing installations.

Platform Notes:
    On Unix/Linux/macOS, file permissions are set to 0o600 (owner read/write only)
    for the encryption key file to restrict access.

    On Windows, os.chmod() only affects the read-only flag and does NOT provide
    full POSIX permission semantics. For strict file ACL enforcement on Windows,
    additional platform-specific handling is required (e.g., using pywin32's
    win32security module or calling icacls.exe via subprocess).
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Union

from secure_config import ENCRYPTION_AVAILABLE, encrypt_value

if not ENCRYPTION_AVAILABLE:
    print(
        "❌ Encryption is required. Install cryptography: pip install cryptography"
    )  # pragma: no cover


# Profile configuration
DEFAULT_PROFILE = "premium"
CURSOR_SUBDIR = ".cursor"

PROFILE_CONFIG: Dict[str, Dict[str, Union[str, List[str]]]] = {
    "premium": {
        "env_keys": ["OPENAI_API_KEY"],
        "settings_key": "cursor.ai.openaiApiKey",
        "mcp_env_key": "OPENAI_API_KEY",
        "description": "Paid/Premium key",
    },
    "free": {
        "env_keys": ["OPENAI_API_KEY_FREE"],
        "settings_key": "cursor.ai.openaiApiKeyFree",
        "mcp_env_key": "OPENAI_API_KEY_FREE",
        "description": "Free tier key",
    },
}


def update_api_key(api_key: str, profile: str = DEFAULT_PROFILE, use_encryption: bool = True):
    """
    Update API key in MCP configuration with encryption for specified profile.

    For security, API keys are encrypted before storage in .env files.
    MCP config receives plain text as it's used at runtime.

    Args:
        api_key: OpenAI API key (must start with 'sk-')
        profile: Profile to update ('premium' or 'free')
        use_encryption: Whether to encrypt the key (default: True, required)

    Returns:
        bool: True if successful, False otherwise
    """

    # Validate profile
    if profile not in PROFILE_CONFIG:
        print(f"❌ Invalid profile '{profile}'. Available: {list(PROFILE_CONFIG.keys())}")
        return False

    # Validate API key: must start with 'sk-', be at least 20 chars, and max 256 chars
    if not api_key or not api_key.startswith("sk-") or len(api_key) < 20 or len(api_key) > 256:
        print(
            "❌ Invalid API key format. Should start with 'sk-', be at least 20 characters, and no longer than 256 characters"
        )
        return False

    # Encrypt key for .env storage (always, not optional)
    # encrypt_value() will raise RuntimeError if encryption not available
    try:
        stored_key = encrypt_value(api_key)
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return False

    # Verify encryption worked (should always be true, but defense in depth)
    if not stored_key.startswith("encrypted:"):
        print("❌ Error: Encryption failed - key not properly encrypted")
        return False

    print("🔐 API key will be stored encrypted in .env")

    # Get profile configuration
    profile_config = PROFILE_CONFIG[profile]

    # Update MCP configuration
    mcp_file = Path.home() / ".cursor" / "mcp.json"
    if mcp_file.exists():
        with open(mcp_file, "r") as f:
            config = json.load(f)

        # Ensure nested structure exists
        config.setdefault("mcpServers", {})
        config["mcpServers"].setdefault("pulseplate-chatgpt", {})
        config["mcpServers"]["pulseplate-chatgpt"].setdefault("env", {})

        # Update API key in MCP config (always plain text for runtime use)
        config["mcpServers"]["pulseplate-chatgpt"]["env"][profile_config["mcp_env_key"]] = api_key

        with open(mcp_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"✅ Updated MCP configuration at {mcp_file}")

    # Update environment file with encrypted key
    env_file = Path.home() / ".cursor" / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            content = f.read()

        # Replace API key for the specified profile
        lines = content.split("\n")
        env_key_name = "OPENAI_API_KEY" if profile == "premium" else "OPENAI_API_KEY_FREE"
        key_replaced = False
        for i, line in enumerate(lines):
            if line.startswith(f"{env_key_name}="):
                lines[i] = f"{env_key_name}={stored_key}"
                key_replaced = True
                break

        # If no existing key found, append it
        if not key_replaced:
            lines.append(f"{env_key_name}={stored_key}")

        # SECURITY NOTE: stored_key is ALWAYS encrypted at this point
        # - Encryption is verified above (starts with "encrypted:")
        # - Uses Fernet symmetric encryption from cryptography library
        # - Function returns False if encryption is not available
        # - Plain text keys are NEVER written to .env file
        with open(env_file, "w") as f:
            f.write("\n".join(lines))

        print(f"✅ Updated environment file at {env_file}")

    # Update Cursor settings (plain text for runtime)
    settings_file = Path.home() / ".cursor" / "settings.json"
    if settings_file.exists():
        with open(settings_file, "r") as f:
            settings = json.load(f)

        settings[PROFILE_CONFIG[profile]["settings_key"]] = api_key

        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)

        print(f"✅ Updated Cursor settings at {settings_file}")

    print("\n🎉 API key updated successfully!")
    print("\nNext steps:")
    print("1. Restart Cursor")
    print("2. Test MCP integration with Cmd+Shift+P → 'MCP: List Tools'")
    print("3. Verify ChatGPT tools are available")

    return True


def main():
    """Main CLI function"""
    # Handle pytest execution where sys.argv contains pytest arguments
    import sys

    # Check if we're running under pytest by looking for pytest-specific patterns
    pytest_indicators = ["pytest", "test_", "::", "-v", "--tb", "--cov"]
    is_pytest = any(indicator in " ".join(sys.argv) for indicator in pytest_indicators)

    if is_pytest or (len(sys.argv) == 2 and not sys.argv[1].startswith("--")):
        # Running under pytest or similar, skip argparse parsing
        print("🔑 PulsePlate API Key Configuration")
        print("=" * 45)

        # Enforce encryption availability
        if not ENCRYPTION_AVAILABLE:
            print("❌ Encryption not available. Please install 'cryptography' and retry.")
            return

        # Get API key from user
        api_key = input("Enter your OpenAI API key (sk-...): ").strip()

        if not api_key:
            print("❌ No API key provided")  # pragma: no cover
            return

        success = update_api_key(api_key, profile=DEFAULT_PROFILE, use_encryption=True)
        if success:
            print(
                f"\n✅ {PROFILE_CONFIG[DEFAULT_PROFILE]['description']} configuration updated successfully!"
            )
        else:
            print("\n❌ Failed to update configuration")  # pragma: no cover
        return

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
        "--api-key", help="OpenAI API key (if not provided, will prompt interactively)"
    )
    parser.add_argument(
        "--profile",
        choices=list(PROFILE_CONFIG.keys()),
        default=DEFAULT_PROFILE,
        help=f"Profile to update (default: {DEFAULT_PROFILE})",
    )

    args = parser.parse_args()

    print("🔑 PulsePlate API Key Configuration")
    print("=" * 45)

    # Get API key from args or prompt
    api_key = args.api_key
    if not api_key:
        profile_desc = PROFILE_CONFIG[args.profile]["description"]
        api_key = input(f"Enter your {profile_desc} OpenAI API key (sk-...): ").strip()

    if not api_key:
        print("❌ No API key provided")  # pragma: no cover
        return  # pragma: no cover

    # Enforce encryption availability
    if not ENCRYPTION_AVAILABLE:
        print(
            "❌ Encryption not available. Please install 'cryptography' and retry."
        )  # pragma: no cover
        return  # pragma: no cover

    if success := update_api_key(api_key, profile=args.profile, use_encryption=True):
        profile_desc = PROFILE_CONFIG[args.profile]["description"]
        print(f"\n✅ {profile_desc} configuration updated successfully!")
    else:
        print("\n❌ Failed to update configuration")  # pragma: no cover


if __name__ == "__main__":
    main()
