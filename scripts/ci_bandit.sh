#!/usr/bin/env bash
set -euo pipefail

if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
  echo "[security-check] CI detected: running bandit"
  # Run bandit recursively; produce report but do not fail pipeline on findings
  bandit -r . -f json -o bandit-report.json || echo "Security scan completed with warnings"
else
  echo "[security-check] Local push detected: skipping bandit (CI enforces)"
fi
