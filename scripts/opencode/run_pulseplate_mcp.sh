#!/usr/bin/env bash
# Launcher for PulsePlate MCP server (pulseplate-chatgpt).
# Prefers .venv/bin/python on host; falls back to python3 in devcontainer.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

# Ensure app package is importable (needed when .venv is absent).
export PYTHONPATH="${PYTHONPATH:-$(pwd)}"

if [ -x ".venv/bin/python" ]; then
  exec .venv/bin/python mcp_pulseplate_server.py
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 mcp_pulseplate_server.py
fi

echo "Unable to start PulsePlate MCP server: neither .venv/bin/python nor python3 is available." >&2
exit 127
