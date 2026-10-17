#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# PulsePlate devcontainer tooling smoke
# ---------------------------------------------------------------------------
# Lightweight check that the devcontainer image provides the expected
# developer tooling baseline.  Does NOT install application dependencies,
# does NOT require secrets or package proxy, and does NOT run backend tests.
# ---------------------------------------------------------------------------
set -euo pipefail

echo "== PulsePlate devcontainer tooling smoke =="

# --- Workdir assumption ---
if [ "$(pwd)" != "/workspaces/PulsePlate" ]; then
  echo "FAIL: expected workdir /workspaces/PulsePlate, got $(pwd)" >&2
  exit 1
fi

# --- Python 3.13 baseline ---
python3 --version
python3 - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) != (3, 13):
    raise SystemExit(f"Expected Python 3.13, got {major}.{minor}")
print("Python baseline OK")
PY

# --- Core CLI tools ---
make --version | head -1
git --version
jq --version
curl --version | head -1
sqlite3 --version
psql --version

# --- OpenCode wrapper syntax (if present) ---
if [ -f scripts/opencode/run_pulseplate_mcp.sh ]; then
  bash -n scripts/opencode/run_pulseplate_mcp.sh
  echo "OpenCode wrapper syntax OK"
fi

echo "Devcontainer tooling smoke passed."
