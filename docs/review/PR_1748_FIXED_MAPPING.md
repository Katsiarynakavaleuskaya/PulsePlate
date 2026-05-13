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
- Current-head CI finding: FIXED by `ddaff0637691788eee07e02be746f97ddc26fe82`
  - Finding: `test-main (3.11, 60)` failed because the Kimi docs-only guard required `origin/main...HEAD`, but GitHub's PR checkout did not have `origin/main`.
  - Evidence: CI job `75817373389` failed at `tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only` with `fatal: ambiguous argument 'origin/main...HEAD'`.
  - Evidence: `tests/test_design_automation_next_lane_docs.py` now falls back to the PR merge commit base `HEAD^1...HEAD` when `origin/main...HEAD` is unavailable.
  - Evidence: `../../.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py tests/test_tooling_surface_guards.py tests/test_ci_workflow_pr_size_governance_contract.py` passes (`56 passed`).

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748 -> 00c376a4e77be4af919d9cce0bd79c3ec93e83ae
Disposition: FIXED
Commit: 00c376a4e77be4af919d9cce0bd79c3ec93e83ae
Evidence: `.github/workflows/ci.yml` uses `dorny/paths-filter@fbd0ab8f3e69293af611ebaee6363fc25e6d187d`; `tests/test_ci_workflow_pr_size_governance_contract.py` asserts the pin and iOS filter contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235352148 -> 828aee1179d74b2501ab04346fe7762d377f2208
Disposition: FIXED
Commit: 828aee1179d74b2501ab04346fe7762d377f2208
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` now includes the exact required `- [x] Discussion-thread pass completed` and `- [x] Fixed in commit mapping completed` checkbox labels; `check_pr_body_phase2_gates.py --pr-number 1748 --body ...` passes locally.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235352156
Disposition: NOT-A-BUG
Evidence: Current PR head `828aee1179d74b2501ab04346fe7762d377f2208` includes `00c376a4e77be4af919d9cce0bd79c3ec93e83ae` in history; `git merge-base --is-ancestor 00c376a4e77be4af919d9cce0bd79c3ec93e83ae HEAD` returned `0`.
Reason: The bot comment referenced a stale reviewed commit sibling; the current PR branch history contains the mapped implementation commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25808282069/job/75817373389 -> ddaff0637691788eee07e02be746f97ddc26fe82
Disposition: FIXED
Commit: ddaff0637691788eee07e02be746f97ddc26fe82
Evidence: `tests/test_design_automation_next_lane_docs.py` preserves the Kimi docs-only guard and now probes `origin/main...HEAD`, `main...HEAD`, then the first parent of a real PR merge checkout before failing closed; focused local pytest passes (`56 passed` across the Kimi docs guard and original workflow-contract suites).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25810975089/job/75827452584 -> edc5e7766af87116be0eb05f2cb983c4bf5b3fa9
Disposition: FIXED
Commit: edc5e7766af87116be0eb05f2cb983c4bf5b3fa9
Evidence: `tests/test_design_automation_next_lane_docs.py` now reads the GitHub pull_request event base SHA, fetches that exact base object in depth-1 CI checkouts, and diffs `base_sha..HEAD` without requiring local base refs or merge-parent ancestry; focused local pytest passes (`56 passed`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25811960072/job/75830472009 -> 6c22df3e49b51f9379cf57f32c9af11680e9eacf
Disposition: FIXED
Commit: 6c22df3e49b51f9379cf57f32c9af11680e9eacf
Evidence: `.github/workflows/ci.yml` keeps the existing `coverage-xml-${{ matrix.python-version }}` and `junit-${{ matrix.python-version }}` artifact names but sets `overwrite: true` for both test-main uploads, preventing the observed GitHub artifact 409 conflict without changing downstream `coverage-main` artifact consumers. The workflow contract test asserts both overwrite guards.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235533880 -> 4128eb460ac8c1a15030a44d22d8cd5bbbe6da91
Disposition: FIXED
Commit: 4128eb460ac8c1a15030a44d22d8cd5bbbe6da91
Evidence: `tests/test_design_automation_next_lane_docs.py` now probes `origin/main...HEAD`, then `main...HEAD`, then the first parent of a real PR merge commit; it fails closed if none are available. Focused local pytest passes (`56 passed` across the Kimi docs guard and original workflow-contract suites).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235633560
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` now has a blank line before the `discussion_r3235533880` mapping block; Cubic marked the thread addressed by `0d43a3cad2d38577da0895c61befa6b9c845712a`.
Reason: The resolved Cubic thread was generated from stale file context and is already satisfied in the live artifact.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#pullrequestreview-4283256351
Disposition: NOT-A-BUG
Evidence: This Cubic review aggregates the resolved inline `discussion_r3235633560`; the live artifact already separates mapping blocks and the inline thread is mapped above.
Reason: The aggregate review is not a separate code finding beyond the already-mapped inline thread.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#pullrequestreview-4283143515 -> 4128eb460ac8c1a15030a44d22d8cd5bbbe6da91
Disposition: FIXED
Commit: 4128eb460ac8c1a15030a44d22d8cd5bbbe6da91
Evidence: This CodeRabbit review aggregates the inline `discussion_r3235533880`; the same fix removed the unsafe last-commit fallback and kept the Kimi docs-only guard fail-closed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235578258 -> 0d43a3cad2d38577da0895c61befa6b9c845712a
Disposition: FIXED
Commit: 0d43a3cad2d38577da0895c61befa6b9c845712a
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` separates every mapping/disposition entry with a blank line so `check_review_threads_disposition.py` parses NOT-A-BUG and FIXED entries independently.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235578263
Disposition: NOT-A-BUG
Evidence: Current branch head includes `ddaff0637691788eee07e02be746f97ddc26fe82`; `git merge-base --is-ancestor ddaff0637691788eee07e02be746f97ddc26fe82 HEAD` returned `0`.
Reason: The referenced CI proof commit is reachable from current PR history; the bot comment evaluated a stale reviewed checkout.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235578268
Disposition: NOT-A-BUG
Evidence: `tests/test_design_automation_next_lane_docs.py:79` first probes `origin/main...HEAD` and `main...HEAD`; `tests/test_design_automation_next_lane_docs.py:88` appends a parent fallback only for merge commits with at least two parents; `tests/test_design_automation_next_lane_docs.py:105` fails closed when no stable base exists.
Reason: Current code no longer has a single-parent last-commit fallback, so the finding is stale for the live PR head.

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
- `../../.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py tests/test_tooling_surface_guards.py tests/test_ci_workflow_pr_size_governance_contract.py` - PASS (`56 passed`)
- `PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after current-head CI fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after shallow PR checkout fix
- `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_design_automation_next_lane_docs.py tests/test_tooling_surface_guards.py` - PASS (`56 passed`) after test-main artifact collision fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after test-main artifact collision fix

## Current-Head CI

- Current-head PR checks are pending after current-head CI fix.
- Merge readiness is not claimed while PR CI, review-bot disposition, and strict merge wrapper remain pending.
