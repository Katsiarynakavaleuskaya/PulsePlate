#!/usr/bin/env bash
# Unified Bandit CI script
# - Runs Bandit once with consistent options
# - Supports optional strict mode to fail on findings
# Usage:
#   scripts/ci_bandit.sh [--strict] [--exclude path1,path2] [--output file]

set -euo pipefail

STRICT=false
EXCLUDES="tests,tests_strict,htmlcov"
OUTPUT="bandit-report.json"
BANDIT_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT=true
      shift
      ;;
    --exclude)
      EXCLUDES="${2:-$EXCLUDES}"
      shift 2
      ;;
    --output)
      OUTPUT="${2:-$OUTPUT}"
      shift 2
      ;;
    --)
      shift
      BANDIT_ARGS+=("$@")
      break
      ;;
    *)
      BANDIT_ARGS+=("$1")
      shift
      ;;
  esac
done

if ! command -v bandit >/dev/null 2>&1; then
  echo "[ci_bandit] bandit not installed; skipping" >&2
  exit 0
fi

echo "[ci_bandit] Running Bandit scan (strict=${STRICT})..." >&2

# Run bandit recursively; in non-strict mode do not fail pipeline on findings
set +e
bandit -r . -x "$EXCLUDES" -f json -o "$OUTPUT" "${BANDIT_ARGS[@]}"
RC=$?
set -e

if [[ "$STRICT" == "true" ]]; then
  if [[ $RC -ne 0 ]]; then
    echo "[ci_bandit] Findings detected; failing due to strict mode" >&2
    exit $RC
  fi
else
  if [[ $RC -ne 0 ]]; then
    echo "[ci_bandit] Findings detected; continuing (non-strict)" >&2
  fi
fi

echo "[ci_bandit] Report saved to $OUTPUT" >&2
echo "[ci_bandit] Done" >&2
