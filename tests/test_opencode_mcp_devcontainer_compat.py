"""Deterministic guard tests for OpenCode MCP devcontainer compatibility.

Validates that opencode.json uses the launcher wrapper instead of hardcoded
.venv/bin/python and that the wrapper follows the safe fallback pattern.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENCODE_JSON = REPO_ROOT / "opencode.json"
WRAPPER = REPO_ROOT / "scripts" / "opencode" / "run_pulseplate_mcp.sh"


def test_opencode_uses_wrapper_for_pulseplate_chatgpt() -> None:
    """pulseplate-chatgpt command must use the launcher wrapper."""
    data = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    command = data["mcp"]["pulseplate-chatgpt"]["command"]

    assert command == ["scripts/opencode/run_pulseplate_mcp.sh"]


def test_opencode_preserves_secret_env_reference() -> None:
    """OPENAI_API_KEY must be an env reference, not a literal secret."""
    data = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))
    environment = data["mcp"]["pulseplate-chatgpt"]["environment"]

    assert environment["OPENAI_API_KEY"] == "{env:OPENAI_API_KEY}"
    assert "sk-" not in OPENCODE_JSON.read_text(encoding="utf-8")


def test_opencode_does_not_change_figma_or_cloudflare_posture() -> None:
    """Figma must stay enabled; Cloudflare must stay disabled."""
    data = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))

    assert data["mcp"]["figma"]["enabled"] is True
    assert data["mcp"]["cloudflare"]["enabled"] is False


def test_pulseplate_mcp_wrapper_is_executable_and_fallback_order_is_safe() -> None:
    """Wrapper must be executable and follow venv-first, python3-fallback pattern."""
    text = WRAPPER.read_text(encoding="utf-8")
    mode = WRAPPER.stat().st_mode

    assert mode & stat.S_IXUSR, "Wrapper must be executable (user)"
    assert "set -euo pipefail" in text, "Wrapper must use strict bash mode"
    assert '[ -x ".venv/bin/python" ]' in text, "Wrapper must check .venv/bin/python"
    assert "command -v python3" in text, "Wrapper must check python3 fallback"
    assert "exec .venv/bin/python mcp_pulseplate_server.py" in text
    assert "exec python3 mcp_pulseplate_server.py" in text
    assert "eval " not in text, "Wrapper must not use eval"
    assert "source " not in text, "Wrapper must not source files"


def test_opencode_has_no_direct_venv_python_command() -> None:
    """No MCP server in opencode.json should hardcode .venv/bin/python."""
    data = json.loads(OPENCODE_JSON.read_text(encoding="utf-8"))

    for name, server in data["mcp"].items():
        command = server.get("command", [])
        assert (
            ".venv/bin/python" not in command
        ), f"MCP server {name!r} still hardcodes .venv/bin/python"


def test_wrapper_targets_correct_mcp_server_script() -> None:
    """Wrapper must launch mcp_pulseplate_server.py (repo root)."""
    text = WRAPPER.read_text(encoding="utf-8")
    assert "mcp_pulseplate_server.py" in text
    # Verify the server script exists at repo root
    assert (REPO_ROOT / "mcp_pulseplate_server.py").is_file()
