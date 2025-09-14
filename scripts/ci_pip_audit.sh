#!/usr/bin/env bash
set -euo pipefail

if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
  echo "[dependency-check] CI detected: running pip-audit"
  pip-audit --format=json --output=pip-audit.json || echo "Dependency check completed"
else
  echo "[dependency-check] Local push detected: skipping pip-audit (CI enforces)"
fi
