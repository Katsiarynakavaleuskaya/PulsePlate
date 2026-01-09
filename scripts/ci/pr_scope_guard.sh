#!/usr/bin/env bash
# PR Scope Guard (CI Enforcement)
#
# Purpose: Machine-checkable guard to prevent PR scope bloat (like PR-494).
# Usage: Run in CI before tests (fails fast, ~2 seconds).
#
# Exit codes:
#   0 = OK (PR scope is valid)
#   1 = BLOCK (PR violates scope rules)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in a PR context
if [ -z "${GITHUB_BASE_REF:-}" ] && [ -z "${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-}" ]; then
    # Not in CI PR context, skip (local dev)
    echo "⚠️  Not in PR context, skipping scope guard"
    exit 0
fi

BASE_REF="${GITHUB_BASE_REF:-${CI_MERGE_REQUEST_TARGET_BRANCH_NAME:-main}}"

echo "🔍 PR Scope Guard: Checking PR scope..."
echo "   Base ref: ${BASE_REF}"
echo "   Head: HEAD ($(git rev-parse --short HEAD 2>/dev/null || echo 'unknown'))"

# Ensure base ref exists locally as origin/<base>
git fetch --no-tags --prune --depth=1 origin "${BASE_REF}:refs/remotes/origin/${BASE_REF}" 2>/dev/null || true

# Fallback fetch if refspec didn't work
if ! git show-ref --verify --quiet "refs/remotes/origin/${BASE_REF}"; then
    echo "   WARN: origin/${BASE_REF} not found after fetch; trying fallback..."
    git fetch --no-tags --prune origin "${BASE_REF}" --depth=1 2>/dev/null || true
fi

# Hard check: if base still not available, fail with diagnostic
if ! git show-ref --verify --quiet "refs/remotes/origin/${BASE_REF}"; then
    echo "ERROR: cannot resolve origin/${BASE_REF}. Checkout/fetch is misconfigured."
    echo "Available refs:"
    git show-ref | head -30
    exit 128
fi

BASE_SHA="$(git rev-parse --short "origin/${BASE_REF}")"
HEAD_SHA="$(git rev-parse --short HEAD)"
echo "   Base sha: ${BASE_SHA}"
echo "   Head sha: ${HEAD_SHA}"

# Get changed files (use HEAD, not branch name)
CHANGED_FILES=$(git diff --name-only "origin/${BASE_REF}"...HEAD)

if [ -z "$CHANGED_FILES" ]; then
    echo "⚠️  No changed files detected, skipping"
    exit 0
fi

# Determine if PR has runtime changes (app/ or core/ Python files)
if echo "$CHANGED_FILES" | rg -q '^(app|core)/.*\.py$'; then
    HAS_RUNTIME=1
    echo "   Runtime PR detected (app/ or core/ Python changes)"
else
    HAS_RUNTIME=0
    echo "   Docs-only PR detected (no app/ or core/ Python changes)"
fi

# Check 1: Python files in docs/pr (ALWAYS BLOCK)
PYTHON_IN_DOCS=$(echo "$CHANGED_FILES" | rg '^docs/pr/.*\.py$' || true)

if [ -n "$PYTHON_IN_DOCS" ]; then
    echo ""
    echo -e "${RED}🛑 BLOCK: Python files found under docs/pr${NC}"
    echo "   Python files must not be placed under docs/pr/."
    echo "   Tests belong in tests/, not in docs/pr/."
    echo ""
    echo "   Found:"
    echo "$PYTHON_IN_DOCS" | sed 's/^/     - /'
    echo ""
    echo "   See: docs/policy/PR_SCOPE_RULES.md"
    exit 1
fi

# Check 2: Planning docs in runtime PR (BLOCK only if HAS_RUNTIME)
if [ "$HAS_RUNTIME" -eq 1 ]; then
    # Regex aligned with Section 2 of docs/policy/PR_SCOPE_RULES.md
    PLANNING_DOCS=$(echo "$CHANGED_FILES" | rg '^docs/pr/PR_[0-9]+_(READY|ROADMAP|HANDOFF|AUDIT_REPORT|REVIEW_CHECKLIST)\.md$' || true)

    if [ -n "$PLANNING_DOCS" ]; then
        echo ""
        echo -e "${RED}🛑 BLOCK: Planning docs found in runtime PR${NC}"
        echo "   Planning docs (READY, ROADMAP, HANDOFF, AUDIT_REPORT, REVIEW_CHECKLIST) are not allowed in runtime PRs."
        echo "   Move them to a separate docs-only PR."
        echo ""
        echo "   Found:"
        echo "$PLANNING_DOCS" | sed 's/^/     - /'
        echo ""
        echo "   See: docs/policy/PR_SCOPE_RULES.md"
        exit 1
    fi
fi

# Check 3: File count warning (INFO only, not blocking)
FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l | tr -d ' ')

if [ "$FILE_COUNT" -gt 30 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  WARNING: PR has ${FILE_COUNT} files changed${NC}"
    echo "   Consider splitting the PR (target: <15 files for runtime PRs)."
    echo "   See: docs/policy/PR_SCOPE_RULES.md"
    echo ""
elif [ "$FILE_COUNT" -gt 15 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  INFO: PR has ${FILE_COUNT} files changed${NC}"
    echo "   Review scope carefully (target: <15 files for runtime PRs)."
    echo ""
fi

# Check 4: Mixed concerns warning (INFO only, not blocking)
PY_COUNT=$(echo "$CHANGED_FILES" | rg -c '\.py$' || echo 0)
MD_COUNT=$(echo "$CHANGED_FILES" | rg -c '\.md$' || echo 0)
PY_COUNT=$(echo "$PY_COUNT" | tr -d ' ')
MD_COUNT=$(echo "$MD_COUNT" | tr -d ' ')

if [ "$PY_COUNT" -gt 0 ] && [ "$MD_COUNT" -gt 2 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  INFO: Runtime PR has ${MD_COUNT} markdown files${NC}"
    echo "   Runtime PRs should have max 1-2 contract/spec md files."
    echo "   Review scope: are all md files contract/spec for this change?"
    echo ""
fi

# All checks passed
echo -e "${GREEN}✅ PR scope guard passed${NC}"
echo "   File count: ${FILE_COUNT}"
echo "   Python files: ${PY_COUNT}"
echo "   Markdown files: ${MD_COUNT}"
exit 0
