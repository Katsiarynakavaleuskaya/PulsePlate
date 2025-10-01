#!/usr/bin/env python3
"""
Update API key in MCP configuration
"""
import json
from pathlib import Path


def update_api_key(api_key: str):
    """Update API key in MCP configuration"""

    # Validate API key: must start with 'sk-', be at least 20 chars, and max 256 chars
    if not api_key or not api_key.startswith("sk-") or len(api_key) < 20 or len(api_key) > 256:
        print(
            "❌ Invalid API key format. Should start with 'sk-', be at least 20 characters, and no longer than 256 characters"
        )
        return False

    # Update MCP configuration
    mcp_file = Path.home() / ".cursor" / "mcp.json"
    if mcp_file.exists():
        with open(mcp_file, "r") as f:
            config = json.load(f)

        # Ensure nested structure exists
        config.setdefault("mcpServers", {})
        config["mcpServers"].setdefault("pulseplate-chatgpt", {})
        config["mcpServers"]["pulseplate-chatgpt"].setdefault("env", {})

        # Update API key in MCP config
        config["mcpServers"]["pulseplate-chatgpt"]["env"]["OPENAI_API_KEY"] = api_key

        with open(mcp_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"✅ Updated MCP configuration at {mcp_file}")

    # Update environment file
    env_file = Path.home() / ".cursor" / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            content = f.read()

        # Replace API key
        lines = content.split("\n")
        key_replaced = False
        for i, line in enumerate(lines):
            if line.startswith("OPENAI_API_KEY="):
                lines[i] = f"OPENAI_API_KEY={api_key}"
                key_replaced = True
                break

        # If no existing key found, append it
        if not key_replaced:
            lines.append(f"OPENAI_API_KEY={api_key}")

        # SECURITY NOTE: API keys stored in plain text for local development only
        # .env file is in .gitignore and never committed to repository
        # For production, use encrypted secret storage (AWS Secrets Manager, etc.)
        with open(env_file, "w") as f:  # nosec B108 (local dev only)
            f.write("\n".join(lines))

        print(f"✅ Updated environment file at {env_file}")

    # Update Cursor settings
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

    if success := update_api_key(api_key):
        print("\n✅ Configuration updated successfully!")
    else:
        print("\n❌ Failed to update configuration")


if __name__ == "__main__":
    main()
