#!/bin/bash
# Discover mypy targets for non-PR branch checks
# This script discovers all Python packages, modules, and root-level files
# that should be checked by mypy, preserving the exact logic from the workflow.

set -euo pipefail

# Base targets that are always checked
TARGETS="app core providers"

# Add additional directories if they exist and contain Python files
for dir in scripts tools alembic; do
  if [ -d "$dir" ] && find "$dir" -maxdepth 1 -name "*.py" -print -quit 2>/dev/null | grep -q .; then
    TARGETS="$TARGETS $dir"
  fi
done

# Add root-level Python files (exclude those that conflict with packages)
ROOT_FILES="$(find . -maxdepth 1 -type f -name "*.py" ! -name "__init__.py" ! -name "app.py" 2>/dev/null | sed 's|^\./||' | tr '\n' ' ')"

if [ -n "$ROOT_FILES" ]; then
  TARGETS="$TARGETS $ROOT_FILES"
fi

# Print the final space-separated target list
echo "$TARGETS"
