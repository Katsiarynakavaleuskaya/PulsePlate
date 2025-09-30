#!/usr/bin/env python3
"""
Custom MCP setup for PulsePlate with ChatGPT integration
"""
import json
from pathlib import Path


def setup_custom_mcp():
    """Setup custom MCP configuration for PulsePlate"""

    # Get home directory
    home = Path.home()
    cursor_dir = home / ".cursor"
    cursor_dir.mkdir(exist_ok=True)

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

    _extracted_from_setup_custom_mcp_21(
        cursor_dir, "mcp.json", mcp_config, "✅ MCP configuration created at "
    )
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

    _extracted_from_setup_custom_mcp_21(
        cursor_dir,
        "settings.json",
        cursor_settings,
        "✅ Cursor settings created at ",
    )
    print("\n🎉 Custom MCP setup complete!")
    print("\nNext steps:")
    print("1. Edit ~/.cursor/.env and add your OpenAI API key")
    print("2. Edit ~/.cursor/mcp.json and update the API key")
    print("3. Restart Cursor")
    print("4. Test MCP integration with Cmd+Shift+P → 'MCP: List Tools'")


# TODO Rename this here and in `setup_custom_mcp`
def _extracted_from_setup_custom_mcp_21(cursor_dir, arg1, arg2, arg3):
    # Write MCP configuration
    mcp_file = cursor_dir / arg1
    with open(mcp_file, "w") as f:
        json.dump(arg2, f, indent=2)

    print(f"{arg3}{mcp_file}")


if __name__ == "__main__":
    setup_custom_mcp()
