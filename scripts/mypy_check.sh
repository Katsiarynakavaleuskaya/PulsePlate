#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT_DIR/.venv/bin/python"
PY_BIN="${PY_BIN:-python3}"

if [[ -x "$VENV_PY" ]]; then
  PY_CMD="$VENV_PY"
else
  PY_CMD="$PY_BIN"
fi

export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/core:$ROOT_DIR/app:$ROOT_DIR/tests"
export VIP_MODULE_ENABLED="${VIP_MODULE_ENABLED:-true}"

exec "$PY_CMD" -m mypy \
  --config-file="$ROOT_DIR/pyproject.toml" \
  --install-types \
  --non-interactive \
  app core tests "$@"
