#!/usr/bin/env bash
set -euo pipefail

# Temporary PR regression scanner for high-signal, PR-local pre-merge checks.
# This wrapper intentionally runs:
# - pre-flight and agent consistency checks
# - focused local gates (validate-min, validate-changed, pre-commit, lint, typecheck)
# - optional main-suite sharded fallback scan (close to CI test breadth)
# - optional current-head PR check parity (requires GH auth)
# - optional strict merge-readiness check (requires GH auth)
#
# Usage:
#   scripts/ci/pr_regression_scan.sh [PR_NUMBER] [REPO]
# Defaults:
#   PR_NUMBER: from $PR_NUMBER env var
#   REPO: GITHUB_REPOSITORY or Katsiarynakavaleuskaya/PulsePlate

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'EOF'
Usage:
  pr_regression_scan.sh [PR_NUMBER] [REPO]

Environment variables:
  PR_NUMBER (default: from arg or environment)
  GITHUB_REPOSITORY / REPO (default: Katsiarynakavaleuskaya/PulsePlate)
  SKIP_CURRENT_HEAD_CHECK (default: 0)
  RUN_MAIN_SUITE (default: 1)  # run sharded main-suite baseline
  PYTHON_VERSION (default: 3.13)
  MAIN_SHARD_COUNT (default: 2)
  MAIN_MAX_PARALLEL (default: 2)
  CI (if set, passed through for parity compatibility)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

PR_NUMBER="${1:-${PR_NUMBER:-${GH_PR_NUMBER:-}}}"
REPO="${2:-${GITHUB_REPOSITORY:-Katsiarynakavaleuskaya/PulsePlate}}"
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"
RUN_MAIN_SUITE="${RUN_MAIN_SUITE:-1}"
MAIN_SHARD_COUNT="${MAIN_SHARD_COUNT:-2}"
MAIN_MAX_PARALLEL="${MAIN_MAX_PARALLEL:-2}"
SKIP_CURRENT_HEAD_CHECK="${SKIP_CURRENT_HEAD_CHECK:-0}"

if [[ "${2:-}" == "--help" ]]; then
  usage
  exit 0
fi

FAILED=0

run_step() {
  local name="$1"
  shift
  printf '\n=== [START] %s ===\n' "$name"
  set +e
  "$@"
  local status=$?
  set -e
  if [[ $status -ne 0 ]]; then
    printf '[FAIL] %s (exit=%s)\n' "$name" "$status"
    FAILED=1
    return 0
  fi
  printf '[PASS] %s\n' "$name"
}

run_step "check_preflight" python3 scripts/orchestration/check_preflight.py
run_step "check_agent_consistency" python3 scripts/orchestration/check_agent_consistency.py
run_step "make validate-min" make validate-min
run_step "make validate-changed" make validate-changed
run_step "pre-commit run --all-files" pre-commit run --all-files
run_step "make lint" make lint
run_step "make typecheck" make typecheck

if [[ "$RUN_MAIN_SUITE" == "1" ]]; then
  run_step "scripts/ci/run_main_test_shards.py" \
    python3 scripts/ci/run_main_test_shards.py \
      --python-version "${PYTHON_VERSION}" \
      --shard-count "${MAIN_SHARD_COUNT}" \
      --max-parallel "${MAIN_MAX_PARALLEL}"
else
  echo "[SKIP] scripts/ci/run_main_test_shards.py (RUN_MAIN_SUITE=${RUN_MAIN_SUITE})"
fi

if [[ "$SKIP_CURRENT_HEAD_CHECK" != "1" ]]; then
  if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" ]]; then
    if [[ -n "${PR_NUMBER:-}" ]]; then
      run_step "scripts/ci/check_current_head_pr_checks.py" \
        python3 scripts/ci/check_current_head_pr_checks.py \
          --pr-number "${PR_NUMBER}" \
          --repo "${REPO}"
    else
      echo "[SKIP] scripts/ci/check_current_head_pr_checks.py (PR number not provided)"
    fi
  else
    echo "[SKIP] scripts/ci/check_current_head_pr_checks.py (GH_TOKEN / GITHUB_TOKEN not set)"
  fi
else
  echo "[SKIP] scripts/ci/check_current_head_pr_checks.py (SKIP_CURRENT_HEAD_CHECK=${SKIP_CURRENT_HEAD_CHECK})"
fi

if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" ]]; then
  if [[ -n "${PR_NUMBER:-}" ]]; then
    run_step "scripts/ci/check_merge_ready.py" \
        python3 scripts/orchestration/check_merge_ready.py \
        --require-auth \
        --pr-number "${PR_NUMBER}" \
        --repo "${REPO}"
  else
    echo "[SKIP] scripts/ci/check_merge_ready.py (PR number not provided)"
  fi
else
  echo "[SKIP] scripts/ci/check_merge_ready.py (GH_TOKEN / GITHUB_TOKEN not set)"
fi

if [[ $FAILED -ne 0 ]]; then
  printf "\nRegression scan summary: failed"
  echo "Run output above contains details for each step."
  exit 1
fi

printf "\nRegression scan summary: passed"
