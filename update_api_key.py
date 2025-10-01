#!/usr/bin/env python3
"""
Update API key in MCP configuration with encryption support

Platform Notes:
    On Unix/Linux/macOS, file permissions are set to 0o600 (owner read/write only)
    for the encryption key file to restrict access.

    On Windows, os.chmod() only affects the read-only flag and does NOT provide
    full POSIX permission semantics. For strict file ACL enforcement on Windows,
    additional platform-specific handling is required (e.g., using pywin32's
    win32security module or calling icacls.exe via subprocess).
"""
import json
from pathlib import Path

from secure_config import ENCRYPTION_AVAILABLE, encrypt_value

if not ENCRYPTION_AVAILABLE:
    print("⚠️  Warning: cryptography not installed. Keys will be stored in plain text.")
    print("   Install with: pip install cryptography")


def update_api_key(api_key: str, use_encryption: bool = True):
    """
    Update API key in MCP configuration with encryption.

    For security, API keys are encrypted before storage in .env files.
    MCP config receives plain text as it's used at runtime.

    Args:
        api_key: OpenAI API key (must start with 'sk-')
        use_encryption: Whether to encrypt the key (default: True, required)

    Returns:
        bool: True if successful, False otherwise
    """

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
        config["mcpServers"]["pulseplate-chatgpt"]["env"]["OPENAI_API_KEY"] = api_key

        with open(mcp_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"✅ Updated MCP configuration at {mcp_file}")

    # Update environment file with encrypted key
    env_file = Path.home() / ".cursor" / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            content = f.read()

        # Replace API key
        lines = content.split("\n")
        key_replaced = False
        for i, line in enumerate(lines):
            if line.startswith("OPENAI_API_KEY="):
                lines[i] = f"OPENAI_API_KEY={stored_key}"
                key_replaced = True
                break

        # If no existing key found, append it
        if not key_replaced:
            lines.append(f"OPENAI_API_KEY={stored_key}")

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

        settings["cursor.ai.openaiApiKey"] = api_key

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
    """Main function"""
    print("🔑 OpenAI API Key Configuration")
    print("=" * 40)

    # Get API key from user
    api_key = input("Enter your OpenAI API key (sk-...): ").strip()

    if not api_key:
        print("❌ No API key provided")
        return

    # Ask about encryption
    if ENCRYPTION_AVAILABLE:
        choice = input("Use encryption for stored key? (Y/n): ").strip().lower()
        use_encryption = choice != "n"
    else:
        print("❌ Encryption not available. Keys will be stored in plain text.")
        use_encryption = False

    success = update_api_key(api_key, use_encryption=use_encryption)
    if success:
        print("\n✅ Configuration updated successfully!")
    else:
        print("\n❌ Failed to update configuration")


if __name__ == "__main__":
    main()
