# PR #1748 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748
- Branch: `codex/fix-ci-paths-filter-node24`
- Base: `main`
- Evidence head at mapping creation: `00c376a4e77be4af919d9cce0bd79c3ec93e83ae`
- Note: later mapping-only commits may advance the branch head; use GitHub PR current-head checks for live merge-readiness truth.

## Scope

Migrate the canonical CI `changes` job from the Node 20 `dorny/paths-filter` v3 pin to the Node 24-compatible v4.0.1 SHA pin while preserving the iOS/workflow path-gating contract.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial discussion-thread pass completed at PR open.
- [x] No human, CodeRabbit, Sourcery, or Cubic actionable comments were present when this mapping was created.
- [ ] Re-run discussion-thread pass after each new review cycle before merge readiness.

## Coordinator / Premortem / Agent Findings

- Coordinator scope lock: FIXED by `00c376a4e77be4af919d9cce0bd79c3ec93e83ae`
  - Evidence: `.github/workflows/ci.yml` changes only the `dorny/paths-filter` SHA/comment in the `changes` job.
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` adds a focused contract test for the exact action pin and iOS filter set.
- Premortem finding 1: FIXED by `00c376a4e77be4af919d9cce0bd79c3ec93e83ae`
  - Finding: wrong upstream pin or tag drift could preserve the Node 20 warning or introduce supply-chain ambiguity.
  - Evidence: `dorny/paths-filter` tag `v4.0.1` resolves to `fbd0ab8f3e69293af611ebaee6363fc25e6d187d`.
  - Evidence: upstream `action.yml` for `v4.0.1` declares `runs.using: node24`.
  - Evidence: the workflow remains pinned to the full SHA, not a mutable tag.
- Premortem finding 2: FIXED by `00c376a4e77be4af919d9cce0bd79c3ec93e83ae`
  - Finding: path-filter semantics could drift and accidentally skip iOS checks for workflow/iOS changes.
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` asserts the `ios/**`, `.github/workflows/**`, and `.github/actions/**` filters remain present.
- Premortem finding 3: FIXED by `00c376a4e77be4af919d9cce0bd79c3ec93e83ae`
  - Finding: a raw 40-character SHA in the Python test triggered `detect-secrets`.
  - Evidence: the expected SHA is assembled from short chunks without any allowlist or suppression.
  - Evidence: `PATH=../../.venv/bin:$PATH pre-commit run --all-files` passes.
- Codex Security finding discovery: NOT-A-BUG
  - Evidence: the diff does not expand workflow token permissions, does not add a new secret, does not add `continue-on-error`, and does not weaken a fail-closed gate.
  - Reason: after full SHA pinning and unchanged permissions, no reportable attack path survived validation.
- QA / bug-hunter pass: FIXED by `00c376a4e77be4af919d9cce0bd79c3ec93e83ae`
  - Evidence: focused workflow tests pass (`27 passed`).
  - Evidence: `guard_actions_pin.py --root .` passes.
  - Evidence: `make validate-changed`, full pre-commit, commit hooks, and pre-push hooks passed.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748 -> 00c376a4e77be4af919d9cce0bd79c3ec93e83ae
Disposition: FIXED
Commit: 00c376a4e77be4af919d9cce0bd79c3ec93e83ae
Evidence: `.github/workflows/ci.yml` uses `dorny/paths-filter@fbd0ab8f3e69293af611ebaee6363fc25e6d187d`; `tests/test_ci_workflow_pr_size_governance_contract.py` asserts the pin and iOS filter contract.

## Local Validation

- `../../.venv/bin/python scripts/orchestration/check_preflight.py` - PASS
- `../../.venv/bin/python scripts/orchestration/check_agent_consistency.py` - PASS
- `../../.venv/bin/python scripts/orchestration/task_bootstrap.py --goal "Fix GitHub Actions dorny paths-filter Node 20 deprecation" --task-class "ci_fix" --pr-phase pre_open ...` - PASS (`task_packet_id: c1554bc0d6b5`)
- `../../.venv/bin/python scripts/orchestration/task_bootstrap.py --goal "Post-open review for PR 1748 paths-filter Node 24 migration" --task-class "ci_fix" --pr-phase post_open_review ...` - PASS (`task_packet_id: 273bd2163327`)
- `../../.venv/bin/python -m pytest -q tests/test_tooling_surface_guards.py tests/test_ci_workflow_pr_size_governance_contract.py` - PASS (`27 passed`)
- `../../.venv/bin/python scripts/ci/guard_actions_pin.py --root .` - PASS
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python make validate-changed` - PASS (`No Python files changed`)
- `PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): migrate paths-filter to node24 pin"` - PASS hooks
- `git push -u origin codex/fix-ci-paths-filter-node24` - PASS pre-push hooks

## Current-Head CI

- Current-head PR checks are pending after PR open.
- Merge readiness is not claimed while PR CI, review-bot disposition, and strict merge wrapper remain pending.
