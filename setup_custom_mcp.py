#!/usr/bin/env python3
"""
Custom MCP setup for PulsePlate with ChatGPT integration
"""
import json
import os
import sys
import time
from pathlib import Path


def setup_custom_mcp():
    """Setup custom MCP configuration for PulsePlate"""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Setup custom MCP configuration for PulsePlate")
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite existing files without prompting"
    )
    args = parser.parse_args()

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

    existing_files = []
    for file_path, description in files_to_check:
        if file_path.exists():
            existing_files.append((file_path, description))

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
            return False

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
        "mcpServers": {
            "pulseplate-chatgpt": {
                "command": "python",
                "args": [str(Path.cwd() / "mcp_pulseplate_server.py")],
                "env": {"OPENAI_API_KEY": "your_openai_api_key_here"},
            }
        }
    }

    # Write MCP configuration
    mcp_file = cursor_dir / "mcp.json"
    with open(mcp_file, "w") as f:
        json.dump(mcp_config, f, indent=2)

    print(f"✅ MCP configuration created at {mcp_file}")

    # Create environment file
    env_file = cursor_dir / ".env"
    env_content = """# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# MCP Configuration
MCP_ENABLED=true
"""

    with open(env_file, "w") as f:
        f.write(env_content)

    print(f"✅ Environment file created at {env_file}")

    # Create Cursor settings
    cursor_settings = {
        "cursor.ai.enabled": True,
        "cursor.ai.primaryModel": "gpt-4",
        "cursor.ai.secondaryModel": "gpt-3.5-turbo",
        "cursor.ai.openaiApiKey": "your_openai_api_key_here",
        "cursor.ai.openaiBaseUrl": "https://api.openai.com/v1",
        "mcp.enabled": True,
        "mcp.servers": ["pulseplate-chatgpt"],
    }

    settings_file = cursor_dir / "settings.json"
    with open(settings_file, "w") as f:
        json.dump(cursor_settings, f, indent=2)

    print(f"✅ Cursor settings created at {settings_file}")

    print("\n🎉 Custom MCP setup complete!")
    print("\nNext steps:")
    print("1. Edit ~/.cursor/.env and add your OpenAI API key")
    print("2. Edit ~/.cursor/mcp.json and update the API key")
    print("3. Restart Cursor")
    print("4. Test MCP integration with Cmd+Shift+P → 'MCP: List Tools'")

    return True


if __name__ == "__main__":
    success = setup_custom_mcp()
    if not success:
        sys.exit(1)
