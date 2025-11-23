#!/usr/bin/env bash

# Lightweight pre-commit smoke suite to avoid OOM during local runs.
# Runs a small, representative subset of fast tests with conservative settings.

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [[ "${SKIP_PRECOMMIT_TESTS:-0}" == "1" ]]; then
  echo "⚠️  SKIP_PRECOMMIT_TESTS=1 set, skipping smoke tests."
  exit 0
fi

if [[ "${CI:-}" == "true" ]]; then
  # CI has its own pipelines; avoid double-running here.
  exit 0
fi

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "❌ .venv not found. Create it with: python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt"
  exit 1
fi
source .venv/bin/activate

export PYTHONPATH=".:core:app:tests"
export VIP_MODULE_ENABLED="true"
export FEATURE_PREMIUM_NUTRITION="true"
export API_KEY="test_key"
export APP_ENV="test"
export ENVIRONMENT="test"
# Avoid inherited -n/other flags from PYTEST_ADDOPTS
export PYTEST_ADDOPTS=""

WORKERS="${PYTEST_XDIST_WORKERS:-2}"
PYTEST_ARGS=()

# Use xdist if available
if python - <<'PY' >/dev/null 2>&1
import importlib.util
import sys
spec = importlib.util.find_spec("xdist")
sys.exit(0 if spec else 1)
PY
then
  PYTEST_ARGS+=("-n" "${WORKERS}" "--dist=loadscope")
fi

echo "🧪 Running smoke tests (workers=${WORKERS})..."
PYTEST_XDIST_MAX_WORKERS="${WORKERS}" \
pytest \
  -o addopts= \
  -q \
  --maxfail=1 \
  -p no:cov \
  --disable-warnings \
  "${PYTEST_ARGS[@]}" \
  test_quick_check.py \
  test_pro_access.py \
  test_ascii_logging.py \
  tests/quick \
  tests/utils

echo "✅ Smoke suite passed."
