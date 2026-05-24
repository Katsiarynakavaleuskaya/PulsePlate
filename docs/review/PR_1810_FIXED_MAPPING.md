# PR 1810 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810
- Branch: `codex/dependency-pin-alignment`
- Initial implementation commit: `45e60478db829c4cecd2af06d04f946638f380c5`
- Mapping artifact commit: `aecb033c7`
- Check-label and env-name fix commit: `1e6020cd0187b25e978e030b264c5e3a45a6a867`

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/815d997c665c.json`
- Packet: `artifacts/orchestration/task_packets/ab3e2c58ee23.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Final role order: `agent-coordinator -> security-auditor -> dev-operator -> frontend-engineer -> architecture-specialist -> qa-engineer-agent -> bug-hunter -> security-auditor final`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810#discussion_r3294156243
Disposition: FIXED
Commit: see mapping entries below
Evidence: docs/review/PR_1810_FIXED_MAPPING.md now records validation-scope evidence without an invalid DEFERRED/Backlog-not-applicable disposition.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810#discussion_r3294156243 -> PLACEHOLDER_FIX_COMMIT

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810#issuecomment-4527871977
Disposition: NOT-A-BUG
Evidence: CodeRabbit reported review quota/usage limits and did not provide a code finding.
Reason: No actionable code or governance change was requested by this comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810#issuecomment-4527872086
Disposition: NOT-A-BUG
Evidence: Sourcery reviewer-guide comment summarized the PR and did not contain an actionable code finding beyond the separate review mapped below.
Reason: Generated review-guide prose is advisory context, not an actionable thread.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1810#pullrequestreview-4352041465
Disposition: FIXED
Commit: 1e6020cd0187b25e978e030b264c5e3a45a6a867
Evidence: .github/workflows/ci.yml now uses PYTHON_VERSION instead of COVERAGE_PY; tests/test_ci_workflow_pr_size_governance_contract.py was updated for that contract.

## Dependency Drift Evidence

- Lottie: `ios/Package.swift` and touched helper/docs surfaces now use `4.5.2`; `xcodebuild -resolvePackageDependencies -workspace ios/PulsePlate.xcworkspace -scheme PulsePlate` passed.
- Storybook: `frontend/package.json` addon packages and `frontend/package-lock.json` now use `8.6.17`; `npm install --package-lock-only`, `npm run build-storybook`, and `npm run build` passed.
- Python: `.github/workflows/ci.yml` and `.github/workflows/frontend-ci.yml` now use `PYTHON_VERSION: "3.13.6"` for canonical runtime setup while CI matrix labels remain `3.13`.
- Full local `make verify`: not run by operator instruction; validation scope is changed-scope gates plus current-head CI before merge.

## Advisory Agent Findings

- Coordinator scope mismatch: fixed by refreshed packet `artifacts/orchestration/task_packets/815d997c665c.json`.
- Architecture stale artifact expectation: fixed in `tests/test_ci_workflow_pr_size_governance_contract.py`.
- Bug-hunter required-check label concern: fixed in `1e6020cd0187b25e978e030b264c5e3a45a6a867`.
- Post-open QA check-name leak: fixed in `1e6020cd0187b25e978e030b264c5e3a45a6a867`; current CI shows `test-main (3.13, 90)`.
- Lottie literal centralization: not a bug for this PR; adding a generator/config surface would widen the dependency-pin alignment scope.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-b4f8bf88ca30.json`
- Diagnostic rejected artifacts:
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
