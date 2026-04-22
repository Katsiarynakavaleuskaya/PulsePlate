#!/usr/bin/env python3
"""Cursor-local MCP setup helper for the PulsePlate server."""

import json
import shutil
import sys
import time
from pathlib import Path


def setup_custom_mcp(argv: list[str] | None = None) -> None:
    """Setup Cursor-local MCP configuration for PulsePlate.

    Args:
        argv: Command line arguments to parse. If None, uses sys.argv.
              This allows tests to pass empty list to avoid pytest arg conflicts.
    """
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Setup Cursor-local MCP configuration for the PulsePlate MCP server"
    )
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

        # Preserve the original files before in-place merge.
        for file_path, description in existing_files:
            backup_path = _backup_file(file_path)
            print(f"💾 Backup created: {backup_path}")

    elif existing_files and args.force:
        for file_path, description in existing_files:
            backup_path = _backup_file(file_path)
            print(f"💾 Backup created: {backup_path}")

    mcp_file = cursor_dir / "mcp.json"
    mcp_config = _load_json_config(mcp_file)
    mcp_config.setdefault("$schema", "https://modelcontextprotocol.io/schemas/mcp.json")
    mcp_config["_warning"] = (
        "⚠️ SECURITY WARNING: This file contains API key placeholders. Replace "
        "'your_openai_api_key_here' with your actual API key and DO NOT commit "
        "this file to version control!"
    )
    mcp_config.setdefault("mcpServers", {})
    mcp_config["mcpServers"]["pulseplate-chatgpt"] = {
        "command": sys.executable,
        "args": [str(Path.cwd() / "mcp_pulseplate_server.py")],
        "env": {"OPENAI_API_KEY": "your_openai_api_key_here"},
    }

    _write_json_config(cursor_dir, "mcp.json", mcp_config, "✅ MCP configuration created at ")

    env_file = cursor_dir / ".env"
    env_updates = {
        "OPENAI_API_KEY": "your_openai_api_key_here",
        "MCP_ENABLED": "true",
    }
    env_content = _merge_env_content(
        env_file.read_text() if env_file.exists() else "",
        env_updates,
    )
    with open(env_file, "w") as f:
        f.write(env_content)

    print(f"✅ Environment file created at {env_file}")

    settings_file = cursor_dir / "settings.json"
    cursor_settings = _load_json_config(settings_file)
    cursor_settings["_warning"] = (
        "⚠️ SECURITY WARNING: This file contains API key placeholders. Replace "
        "'your_openai_api_key_here' with your actual API key and DO NOT commit "
        "this file to version control!"
    )
    cursor_settings["cursor.ai.enabled"] = True
    cursor_settings["cursor.ai.primaryModel"] = "gpt-4"
    cursor_settings["cursor.ai.secondaryModel"] = "gpt-3.5-turbo"
    cursor_settings["cursor.ai.openaiApiKey"] = "your_openai_api_key_here"
    cursor_settings["cursor.ai.openaiBaseUrl"] = "https://api.openai.com/v1"
    cursor_settings["mcp.enabled"] = True
    existing_servers = cursor_settings.get("mcp.servers", [])
    cursor_settings["mcp.servers"] = _merge_setting_list(existing_servers, "pulseplate-chatgpt")

    _write_json_config(
        cursor_dir,
        "settings.json",
        cursor_settings,
        "✅ Cursor settings created at ",
    )
    print("\n🎉 Cursor-local MCP setup complete!")
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


def _backup_file(file_path: Path) -> Path:
    """Create a timestamped backup without removing the original file."""

    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup.{int(time.time())}")
    shutil.copy2(file_path, backup_path)
    return backup_path


def _load_json_config(file_path: Path) -> dict:
    """Load existing JSON config or return an empty mapping."""

    if not file_path.exists():
        return {}
    with open(file_path, "r") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {file_path}")
    return data


def _merge_setting_list(existing_values: object, required_value: str) -> list[str]:
    """Return a stable string list that includes the required value once."""

    merged = (
        [item for item in existing_values if isinstance(item, str)]
        if isinstance(existing_values, list)
        else []
    )
    if required_value not in merged:
        merged.append(required_value)
    return merged


def _merge_env_content(existing_content: str, updates: dict[str, str]) -> str:
    """Preserve unrelated .env lines while upserting managed keys."""

    if not existing_content:
        lines = [
            "# ⚠️ WARNING: This file contains sensitive API keys!",
            "# DO NOT commit this file to version control.",
            "# Replace placeholder values before use.",
            "",
            "# OpenAI API Configuration",
            "",
            "# MCP Configuration",
        ]
    else:
        lines = existing_content.splitlines()

    remaining_updates = dict(updates)
    merged_lines: list[str] = []

    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            merged_lines.append(line)
            continue

        key, _value = line.split("=", 1)
        if key in remaining_updates:
            merged_lines.append(f"{key}={remaining_updates.pop(key)}")
        else:
            merged_lines.append(line)

    if merged_lines and merged_lines[-1] != "":
        merged_lines.append("")

    for key, value in remaining_updates.items():
        merged_lines.append(f"{key}={value}")

    return "\n".join(merged_lines).rstrip() + "\n"


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
