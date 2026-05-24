# PR 1810 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810
- Branch: `codex/dependency-pin-alignment`
- Initial implementation commit: `45e60478db829c4cecd2af06d04f946638f380c5`
- Canonical packet: `artifacts/orchestration/task_packets/815d997c665c.json`
- Local agent summary: `artifacts/agent_runs/dependency-pin-alignment-summary.json` (gitignored)

## Lane Start Provenance

- Fresh isolated worktree was created with `scripts/orchestration/start_pr_lane.sh`.
- Preflight passed in analyze mode for the declared path scope.
- Agent consistency passed.
- Final role order: `agent-coordinator -> security-auditor -> dev-operator -> frontend-engineer -> architecture-specialist -> qa-engineer-agent -> bug-hunter -> security-auditor final`.

## Discussion Thread Pass

- No GitHub review threads existed at PR open.
- New human or bot comments must be classified as `FIXED`, `NOT-A-BUG`, or `DEFERRED` here before merge.

## Fixed in Commit Mapping

### Dependency Pin Drift

- Finding: `ios/Package.swift` declared `lottie-ios` from `4.4.0` while repo-resolved SwiftPM state was already `4.5.2`.
  - Disposition: `FIXED`
  - Commit: `45e60478db829c4cecd2af06d04f946638f380c5`
  - Evidence: `ios/Package.swift`, `ios/LOTTIE_INSTALL_STEPS.md`, `ios/LOTTIE_SETUP_GUIDE.md`, `ios/Scripts/open_xcode_with_lottie.sh`, `ios/add_lottie_package.swift`, `ios/install_lottie.sh`, `ios/open_xcode_with_lottie.sh`
  - Validation: `xcodebuild -resolvePackageDependencies -workspace ios/PulsePlate.xcworkspace -scheme PulsePlate` PASS

- Finding: Storybook addon packages were pinned to `8.6.14` while core Storybook packages were `8.6.17`.
  - Disposition: `FIXED`
  - Commit: `45e60478db829c4cecd2af06d04f946638f380c5`
  - Evidence: `frontend/package.json`, `frontend/package-lock.json`
  - Validation: `npm install --package-lock-only` PASS, `npm run build-storybook` PASS, `npm run build` PASS

- Finding: canonical Python workflow defaults floated on `3.13` while local toolchain files pinned `3.13.6`.
  - Disposition: `FIXED`
  - Commit: `45e60478db829c4cecd2af06d04f946638f380c5`
  - Evidence: `.github/workflows/ci.yml`, `.github/workflows/frontend-ci.yml`, `tests/test_ci_workflow_pr_size_governance_contract.py`
  - Validation: workflow contract tests PASS

### Advisory Agent Findings

- Finding: coordinator scope initially missed expanded Lottie helper surfaces and workflow contract test coverage.
  - Disposition: `FIXED`
  - Evidence: refreshed packet `artifacts/orchestration/task_packets/815d997c665c.json`

- Finding: architecture-specialist flagged stale coverage artifact expectations after the Python pin change.
  - Disposition: `FIXED`
  - Commit: `45e60478db829c4cecd2af06d04f946638f380c5`
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py`

- Finding: bug-hunter flagged that changing matrix labels to `3.13.6` would break required check identity.
  - Disposition: `FIXED`
  - Commit: `1e6020cd0187b25e978e030b264c5e3a45a6a867`
  - Evidence: `.github/workflows/ci.yml` preserves `3.13` matrix labels and uses the `PYTHON_VERSION` env only in the Python setup expression for the exact `3.13.6` runtime.
  - Validation: `tests/test_current_head_pr_checks.py::test_fallback_ci_allowlist_matches_canonical_pr_workflow_jobs` PASS

- Finding: post-open QA agent found that `runtime-python-version` leaked into the live GitHub check name as `test-main (3.13, 3.13.6, 90)`.
  - Disposition: `FIXED`
  - Commit: `1e6020cd0187b25e978e030b264c5e3a45a6a867`
  - Evidence: `.github/workflows/ci.yml` no longer has `runtime-python-version`; `tests/test_ci_workflow_pr_size_governance_contract.py` asserts the setup expression while preserving matrix labels.
  - Validation: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_current_head_pr_checks.py::test_fallback_ci_allowlist_matches_canonical_pr_workflow_jobs -o cache_dir=/tmp/pulseplate-pytest-cache-dependency-pin-final` PASS

- Finding: `npm audit --audit-level=moderate` reports two dev-only vulnerabilities.
  - Disposition: `NOT-A-BUG`
  - Evidence: same findings are present on `origin/main`; `npm audit --omit=dev --audit-level=moderate` PASS
  - Reason: this PR does not introduce production dependency exposure.

- Finding: full local `make verify` was not completed.
  - Disposition: `DEFERRED`
  - Evidence: operator explicitly constrained this lane to changed-scope validation only.
  - Backlog: not applicable; this is an operator-approved lane-level validation constraint, with current-head CI required before merge.

### Bot Review Comments

- Comment: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810#issuecomment-4527871977
  - Source: CodeRabbit
  - Disposition: `NOT-A-BUG`
  - Evidence: comment reports review quota/usage limit and contains no actionable code finding.

- Comment: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810#issuecomment-4527872086
  - Source: Sourcery reviewer guide
  - Disposition: `NOT-A-BUG`
  - Evidence: generated guide summarized the PR and included no actionable review finding beyond the separate Sourcery review comment mapped below.

- Review: Sourcery high-level feedback, submitted 2026-05-24T08:44:43Z
  - Finding: repeated Lottie `4.5.2` literals across SwiftPM manifest, helper scripts, and setup docs could be centralized later.
  - Disposition: `NOT-A-BUG`
  - Evidence: this PR aligns existing duplicated repo surfaces without changing their architecture; SwiftPM manifest syntax and user-facing install docs still require explicit version text.
  - Reason: introducing a new Lottie single-source generator/config would widen this dependency-pin alignment PR beyond the declared scope.

- Review: Sourcery high-level feedback, submitted 2026-05-24T08:44:43Z
  - Finding: `COVERAGE_PY` conflated canonical Python runtime naming with coverage artifact naming.
  - Disposition: `FIXED`
  - Commit: `1e6020cd0187b25e978e030b264c5e3a45a6a867`
  - Evidence: `.github/workflows/ci.yml` now uses `PYTHON_VERSION: "3.13.6"` consistently; `tests/test_ci_workflow_pr_size_governance_contract.py` was updated accordingly.

## Experiment Runner Evidence

- Accepted oracle-only evidence: `artifacts/orchestration/experiments/results/exp-b4f8bf88ca30.json`
  - Status: accepted
  - Oracle return codes: `0, 0, 0`
  - Mutated paths: `[]`
  - Shared tree untouched: `true`
- Diagnostic rejected evidence:
  - `artifacts/orchestration/experiments/results/exp-604ee9b449cd.json`: rejected before refreshed scope packet.
  - `artifacts/orchestration/experiments/results/exp-12a0bc35ab9b.json`: rejected due oracle shell quoting, not due diff failure.
  - `artifacts/orchestration/experiments/results/exp-ac0b9a7cb4ae.json`: rejected due oracle shell quoting, not due diff failure.

## Local Validation

- `npm install --package-lock-only` PASS
- `npm install` PASS
- `npm run build-storybook` PASS
- `npm run build` PASS
- `npm audit --omit=dev --audit-level=moderate` PASS
- `xcodebuild -resolvePackageDependencies -workspace ios/PulsePlate.xcworkspace -scheme PulsePlate` PASS
- `python3 scripts/orchestration/check_preflight.py --mode analyze --path ...` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `git diff --check` PASS
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_ci_workflow_pr_size_governance_contract.py -o cache_dir=/tmp/pulseplate-pytest-cache-dependency-pin-workflow` PASS (`18 passed`)
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_current_head_pr_checks.py::test_fallback_ci_allowlist_matches_canonical_pr_workflow_jobs tests/test_ci_workflow_pr_size_governance_contract.py::test_main_branch_python_sharded_runner_preserves_required_check_policy tests/test_ci_workflow_pr_size_governance_contract.py::test_node24_artifact_migration_preserves_download_contracts -o cache_dir=/tmp/pulseplate-pytest-cache-dependency-pin-bughunter` PASS
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_current_head_pr_checks.py::test_fallback_ci_allowlist_matches_canonical_pr_workflow_jobs -o cache_dir=/tmp/pulseplate-pytest-cache-dependency-pin-final` PASS (`19 passed`)
- `make validate-changed` PASS
- `pre-commit run --all-files` PASS
- Commit hooks PASS
- Pre-push hooks PASS, including backend pre-push pytest and full-repo Bandit

## Merge Readiness

- Current state: not merge-ready.
- Required before merge:
  - Current-head CI complete.
  - Bot comments and review threads checked and dispositioned.
  - PR body mirror updated from this artifact after any review activity.
  - Strict merge wrapper passes with auth.
  - Mandatory wait-window after latest review or bot activity.
