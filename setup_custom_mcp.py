#!/usr/bin/env python3
"""
Custom MCP setup for PulsePlate with ChatGPT integration
"""

import json
import sys
import time
from pathlib import Path


def setup_custom_mcp(argv: list[str] | None = None) -> None:
    """Setup custom MCP configuration for PulsePlate

    Args:
        argv: Command line arguments to parse. If None, uses sys.argv.
              This allows tests to pass empty list to avoid pytest arg conflicts.
    """
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Setup custom MCP configuration for PulsePlate")
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite existing files without prompting"
    )
    args = parser.parse_args(argv)

    # Get home directory
    home = Path.home()
    cursor_dir = home / ".cursor"
    cursor_dir.mkdir(exist_ok=True)

    # Check for existing files
    files_to_check = [
        (cursor_dir / "mcp.json", "MCP configuration"),
        (cursor_dir / ".env", "Environment file"),
        (cursor_dir / "settings.json", "Cursor settings"),
    ]

    existing_files = [
        (file_path, description) for file_path, description in files_to_check if file_path.exists()
    ]

    if existing_files and not args.force:
        print("⚠️  The following files already exist:")
        for file_path, description in existing_files:
            print(f"   - {file_path} ({description})")
        print()

        response = (
            input("Do you want to create backups and overwrite these files? (y/N): ")
            .strip()
            .lower()
        )
        if response not in ["y", "yes"]:
            print("❌ Setup cancelled. Use --force to overwrite without prompting.")
            sys.exit(1)

        # Create backups
        for file_path, description in existing_files:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup.{int(time.time())}")
            file_path.rename(backup_path)
            print(f"💾 Backup created: {backup_path}")

    elif existing_files and args.force:
        # Create backups when using --force
        for file_path, description in existing_files:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup.{int(time.time())}")
            file_path.rename(backup_path)
            print(f"💾 Backup created: {backup_path}")

    # Create MCP configuration
    mcp_config = {
        "$schema": "https://modelcontextprotocol.io/schemas/mcp.json",
        "_warning": "⚠️ SECURITY WARNING: This file contains API key placeholders. Replace 'your_openai_api_key_here' with your actual API key and DO NOT commit this file to version control!",
        "mcpServers": {
            "pulseplate-chatgpt": {
                "command": "python",
                "args": [str(Path.cwd() / "mcp_pulseplate_server.py")],
                "env": {"OPENAI_API_KEY": "your_openai_api_key_here"},
            }
        },
    }

    _write_json_config(cursor_dir, "mcp.json", mcp_config, "✅ MCP configuration created at ")
    # Create environment file
    env_file = cursor_dir / ".env"
    env_content = """# ⚠️ WARNING: This file contains sensitive API keys!
# DO NOT commit this file to version control.
# Replace placeholder values before use.

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# MCP Configuration
MCP_ENABLED=true
"""

    with open(env_file, "w") as f:
        f.write(env_content)

    print(f"✅ Environment file created at {env_file}")

    # Create Cursor settings
    cursor_settings = {
        "_warning": "⚠️ SECURITY WARNING: This file contains API key placeholders. Replace 'your_openai_api_key_here' with your actual API key and DO NOT commit this file to version control!",
        "cursor.ai.enabled": True,
        "cursor.ai.primaryModel": "gpt-4",
        "cursor.ai.secondaryModel": "gpt-3.5-turbo",
        "cursor.ai.openaiApiKey": "your_openai_api_key_here",
        "cursor.ai.openaiBaseUrl": "https://api.openai.com/v1",
        "mcp.enabled": True,
        "mcp.servers": ["pulseplate-chatgpt"],
    }

    _write_json_config(
        cursor_dir,
        "settings.json",
        cursor_settings,
        "✅ Cursor settings created at ",
    )
    print("\n🎉 Custom MCP setup complete!")
    print("\n⚠️  SECURITY WARNING:")
    print("   - All generated files contain PLACEHOLDER API keys")
    print("   - DO NOT commit these files with real API keys to version control")
    print("   - Add ~/.cursor/.env to your global .gitignore")
    print("\nNext steps:")
    print(
        "1. 🔑 Edit ~/.cursor/.env and replace 'your_openai_api_key_here' with your actual API key"
    )
    print("2. 🔑 Edit ~/.cursor/mcp.json and update the API key")
    print("3. 🔄 Restart Cursor")
    print("4. ✅ Test MCP integration with Cmd+Shift+P → 'MCP: List Tools'")

    return


def _write_json_config(cursor_dir: Path, filename: str, data: dict, success_message: str) -> None:
    """Write JSON configuration to a file and print success message.

    Args:
        cursor_dir: Directory where the config file will be written
        filename: Name of the config file
        data: Dictionary to serialize as JSON
        success_message: Message prefix for success output
    """
    config_file = cursor_dir / filename
    with open(config_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"{success_message}{config_file}")


def main() -> None:
    """Module entrypoint.

    Keep this wrapper side-effect free at import time; runtime behavior stays in
    setup_custom_mcp().
    """
    setup_custom_mcp()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)
