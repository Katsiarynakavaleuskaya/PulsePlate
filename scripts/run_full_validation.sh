#!/usr/bin/env bash
# Run complete validation suite locally before pushing changes.
#
# - Ensures branch merges cleanly with origin/main
# - Executes all pre-commit hooks (lint, format, smoke tests)
# - Executes full pytest + coverage run (matching pre-push hook)
#
# Usage: scripts/run_full_validation.sh

set -euo pipefail

if ! command -v pre-commit >/dev/null 2>&1; then
  echo "pre-commit is required. Install with 'pip install pre-commit'." >&2
  exit 1
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" == "HEAD" ]]; then
  echo "Detached HEAD detected. Please checkout a branch." >&2
  exit 1
fi

echo "Fetching latest origin/main..."
git fetch origin main >/dev/null

merge_aborted=false
trap 'if [[ $merge_aborted == false ]]; then git merge --abort >/dev/null 2>&1 || true; fi' EXIT

echo "Simulating merge with origin/main..."
git merge --no-commit --no-ff origin/main >/dev/null 2>&1 || {
  echo "Merge conflicts detected. Resolve before running validation." >&2
  exit 1
}

# Run all configured pre-commit hooks
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Running pre-commit hooks across the repository..."
  pre-commit run --all-files
  echo "Running pre-push pytest suite..."
  SKIP=pytest,pytest-smoke pre-commit run --hook-stage pre-push
fi

# Explicit smoke test invocation (mirrors hook configuration)
echo "Running smoke tests..."
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -m smoke --maxfail=1

# Full pytest + coverage (match pre-push hook)
echo "Running full pytest + coverage..."
PYTHONDONTWRITEBYTECODE=1 python -m pytest \
  tests/ \
  --ignore=tests/edges \
  --ignore=tests/test_api.py \
  --ignore=tests/test_app_cover.py \
  --cov=. \
  --cov-config=.coveragerc \
  --cov-fail-under=95 \
  -q \
  --maxfail=5

echo "Validation successful."
merge_aborted=true

# Clean up simulated merge state
git merge --abort >/dev/null 2>&1 || true
