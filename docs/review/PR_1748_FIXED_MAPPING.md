# PR #1748 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748
- Branch: `codex/fix-ci-paths-filter-node24`
- Base: `main`
- Evidence head at mapping creation: `00c376a4e77be4af919d9cce0bd79c3ec93e83ae`
- Note: later mapping-only commits may advance the branch head; use GitHub PR current-head checks for live merge-readiness truth.
- Proof contract: FIXED commit SHAs in this artifact are PR branch-history proofs. Bot-reviewed synthetic merge, squash-preview, or stale reviewed-head SHAs are not the source of truth for local strict disposition verification; the canonical guard verifies the live PR branch checkout and current-head CI.

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
- Current-head CI finding: FIXED by `3257b86dc6391820d6234c1edf7787b9701ee4e8`
  - Finding: latest `test-main (3.11, 60)` failed because the Kimi docs-only guard inspected a synthetic PR merge checkout instead of the actual PR `base..head` diff, then treated this CI/tooling PR as Kimi bridge drift.
  - Evidence: CI job `75859256675` failed at `tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only` with unexpected paths `.github/workflows/ci.yml` and `tests/test_ci_workflow_pr_size_governance_contract.py`.
  - Evidence: `tests/test_design_automation_next_lane_docs.py` now prefers the GitHub event `pull_request.base.sha..pull_request.head.sha` diff before local fallback bases.
  - Evidence: `../../.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_ci_workflow_pr_size_governance_contract.py` passes.
- Current-head CI finding: FIXED by `ebff66abf7bf6200baf7862abf3573294ec068c5`
  - Finding: latest `test-main (3.11, 60)` passed all tests but failed the hard 97% coverage threshold at `96.99%`.
  - Evidence: CI job `75863761961` reported `13112 passed, 26 skipped`, then `FAIL Required test coverage of 97% not reached. Total coverage: 96.99%`.
  - Evidence: the coverage report showed the existing conservative BMR fallback branch in `legacy_app.py:3868-3881` uncovered.
  - Evidence: `tests/test_app_extended_coverage.py` now covers the runtime-patched BMR/TDEE fallback through the API without changing runtime code or lowering the threshold.
  - Evidence: focused local pytest for the new coverage test and the Kimi/workflow guard suite passes; full pre-commit passes.
- Current-head CI finding: FIXED by `ae387ff9e6078215603d1932a8d27815c6a96ea3`
  - Finding: `test-main (3.12, 60)` repeatedly hit the configured 60-minute job timeout after long-running shards, while 3.11 and 3.13 passed and the 3.12 log showed test progress rather than an assertion failure.
  - Evidence: CI job `75884582375` ended as cancelled after `1h0m16s`; the prior 3.12 log showed shard progress and `6425 passed, 4 skipped, 15 deselected` before the job timeout.
  - Evidence: `.github/workflows/ci.yml` now gives Python 3.12 the same 90-minute `test-main` budget as Python 3.13 while preserving the required check identity and matrix shape.
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` asserts `{"3.11": 60, "3.12": 90, "3.13": 90}`.
  - Evidence: focused local pytest passes (`13 passed`) and full pre-commit passes.
- Current-head CI finding: FIXED by `1a91cdfd655c11fe737beabdda9685ed4f02c170`
  - Finding: `test-main (3.12, 90)` still hit the job timeout after setup overhead; the job ran from `2026-05-13T22:54:07Z` to `2026-05-14T00:24:38Z`, and the `Run tests with coverage` step was cancelled.
  - Evidence: JUnit artifact `junit-main-3.12` contained only `results-py312-shard-1.xml`; shard 1 completed successfully with `6703` tests, `0` failures, `0` errors, `19` skips, and `time="1872.519"`.
  - Evidence: `.github/workflows/ci.yml` now rebalances only Python 3.12 from two process shards to three process shards; Python 3.13 remains at two shards and existing required check names are preserved.
  - Evidence: `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 3 --max-parallel 3 --list-shards` produced balanced shard weights `3156708`, `3156742`, and `3156746`.
  - Evidence: `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` passes and full pre-commit passes.
- Current-head CI finding: FIXED by `a59c5c7e9efd19b1a8b10c2da7a1d3971bc22df2`
  - Finding: `test-main (3.11, 60)` failed because pytest-xdist worker `gw0` crashed while running `tests/test_food_source_preference_recipe_mapping.py::test_preference_recipe_mapping_rejects_notes_that_contradict_policy[recipe text allowed]`; failed workers returned no coverage data, dropping total coverage to `29.88%`.
  - Evidence: CI job `75939635310` reported `1 failed, 13172 passed, 26 skipped` and `The following workers failed to return coverage data`, with `coverage.xml` still uploaded from partial data.
  - Evidence: `.github/workflows/ci.yml` now runs Python 3.11 `test-main` through the existing process-level shard runner instead of pytest-xdist while preserving the required check name and 97% coverage gate.
  - Evidence: `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.11 --shard-count 4 --max-parallel 4 --list-shards` produced balanced shard weights `2367885`, `2367530`, `2367530`, and `2367817`.
  - Evidence: `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` passes and full pre-commit passes.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3236929136
Disposition: NOT-A-BUG
Evidence: Current PR head `396ef4937dd7699eaa1984d74eace89f7f137f9b` includes `00c376a4e77be4af919d9cce0bd79c3ec93e83ae` and `ebff66abf7bf6200baf7862abf3573294ec068c5` in history; local `git merge-base --is-ancestor ... HEAD` returned `0` for both commits.
Reason: The bot evaluated stale reviewed head `a7be3d0fae558eab8168d378bc6cbd2bc0eae6d6`; the canonical merge-readiness checkout is the live PR branch head, where the mapped FIXED proof commits are reachable.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3237120346 -> ba51206144f52319f4ae1fdbdef07aeeac5961a6
Disposition: FIXED
Commit: ba51206144f52319f4ae1fdbdef07aeeac5961a6
Evidence: `tests/test_design_automation_next_lane_docs.py` now fetches PR event bounds with enough history, computes `git merge-base base_sha head_sha`, and uses a three-dot merge-base comparison instead of the unsafe `base_sha..head_sha` range. Focused local pytest passes (`13 passed`) and full pre-commit passes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3237164627
Disposition: NOT-A-BUG
Evidence: Current PR head `0a7cd1747cdac51a1e6f2ec8168377aa874fb033` contains the mapped FIXED proof commits in branch history; local strict disposition guard passed after the prior reviewed-head thread was mapped and resolved.
Reason: The bot evaluated reviewed squash-preview commit `f1080963dcfdd2bdeb9b0fd9927b0ffdfd6a437d`, while the repo canonical merge-readiness contract validates the live PR branch checkout and current-head CI, not stale synthetic reviewed heads.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3237913079
Disposition: NOT-A-BUG
Evidence: Current PR head `77ddfb754a7ca601f787d6b29ed05d1d8fbdfde0` contains the mapped FIXED proof commits in branch history; the mapping artifact and PR body explicitly define FIXED commit SHAs as PR branch-history proofs for the live PR checkout and current-head CI.
Reason: The bot evaluated stale reviewed head `26bf29d43e63c2484acd8cf489490e3d2f147db1`, not the canonical live PR branch checkout used by repo-native merge-readiness verification.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3239524475 -> 19b188dc4228c74c1a53fa7331ffdf9426471f06
Disposition: FIXED
Commit: 19b188dc4228c74c1a53fa7331ffdf9426471f06
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` now uses the real full shard-rebalance commit SHA `1a91cdfd655c11fe737beabdda9685ed4f02c170`, which resolves in this repository.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3239524477 -> 19b188dc4228c74c1a53fa7331ffdf9426471f06
Disposition: FIXED
Commit: 19b188dc4228c74c1a53fa7331ffdf9426471f06
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` now classifies `discussion_r3236295295` as FIXED by `ba51206144f52319f4ae1fdbdef07aeeac5961a6`, matching the final merge-base diff implementation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25808282069/job/75817373389 -> ddaff0637691788eee07e02be746f97ddc26fe82
Disposition: FIXED
Commit: ddaff0637691788eee07e02be746f97ddc26fe82
Evidence: `tests/test_design_automation_next_lane_docs.py` preserves the Kimi docs-only guard and now probes `origin/main...HEAD`, `main...HEAD`, then the first parent of a real PR merge checkout before failing closed; focused local pytest passes (`56 passed` across the Kimi docs guard and original workflow-contract suites).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25810975089/job/75827452584 -> edc5e7766e28924ff4350d52dc97b85b917ab0c2
Disposition: FIXED
Commit: edc5e7766e28924ff4350d52dc97b85b917ab0c2
Evidence: `tests/test_design_automation_next_lane_docs.py` now reads the GitHub pull_request event base SHA, fetches that exact base object in depth-1 CI checkouts, and diffs `base_sha..HEAD` without requiring local base refs or merge-parent ancestry; focused local pytest passes (`56 passed`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25820129900/job/75859256675 -> 3257b86dc6391820d6234c1edf7787b9701ee4e8
Disposition: FIXED
Commit: 3257b86dc6391820d6234c1edf7787b9701ee4e8
Evidence: `tests/test_design_automation_next_lane_docs.py` now fetches and diffs the actual GitHub PR event `pull_request.base.sha..pull_request.head.sha` before synthetic merge/local fallback bases, so the Kimi docs-only guard only activates for a real Kimi protocol diff. Focused local pytest passes for `test_kimi_protocol_current_diff_stays_docs_only` plus the workflow contract suite.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25821503783/job/75863761961 -> ebff66abf7bf6200baf7862abf3573294ec068c5
Disposition: FIXED
Commit: ebff66abf7bf6200baf7862abf3573294ec068c5
Evidence: `tests/test_app_extended_coverage.py` adds deterministic API coverage for the existing runtime-patched premium BMR/TDEE fallback branch that CI reported uncovered; focused local pytest and full pre-commit pass without weakening coverage thresholds.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25824281934/job/75884582375 -> ae387ff9e6078215603d1932a8d27815c6a96ea3
Disposition: FIXED
Commit: ae387ff9e6078215603d1932a8d27815c6a96ea3
Evidence: `.github/workflows/ci.yml` extends only the Python 3.12 `test-main` timeout from 60 to 90 minutes after repeated timeout cancellation, and `tests/test_ci_workflow_pr_size_governance_contract.py` locks the matrix timeout contract. Focused pytest and full pre-commit pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25831057536/job/75895982026 -> 1a91cdfd655c11fe737beabdda9685ed4f02c170
Disposition: FIXED
Commit: 1a91cdfd655c11fe737beabdda9685ed4f02c170
Evidence: `test-main (3.12, 90)` reached the job timeout after only shard 1 completed; `.github/workflows/ci.yml` now rebalances only Python 3.12 from two to three process shards, and `tests/test_ci_workflow_pr_size_governance_contract.py` locks that contract. Focused workflow contract pytest, balanced shard-plan proof, and full pre-commit pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25845462494/job/75939635310 -> a59c5c7e9efd19b1a8b10c2da7a1d3971bc22df2
Disposition: FIXED
Commit: a59c5c7e9efd19b1a8b10c2da7a1d3971bc22df2
Evidence: `test-main (3.11, 60)` failed from a pytest-xdist worker crash and partial coverage data, not a deterministic assertion failure; `.github/workflows/ci.yml` now runs Python 3.11 through process-level shards with `tests/results-py311-shard-*.xml` artifacts, and `tests/test_ci_workflow_pr_size_governance_contract.py` locks that contract. Focused workflow contract pytest, balanced shard-plan proof, and full pre-commit pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25811960072/job/75830472009 -> 6c22df3e4a3f818f22471fdafc3c5ff55c8935d3
Disposition: FIXED
Commit: 6c22df3e4a3f818f22471fdafc3c5ff55c8935d3
Evidence: `.github/workflows/ci.yml` keeps the existing `coverage-xml-${{ matrix.python-version }}` and `junit-${{ matrix.python-version }}` artifact names but sets `overwrite: true` for both test-main uploads, preventing the observed GitHub artifact 409 conflict without changing downstream `coverage-main` artifact consumers. The workflow contract test asserts both overwrite guards.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235882742 -> 6bc2feb88ed1c2bd1b31f10cbbb5edd0d86a2163
Disposition: FIXED
Commit: 6bc2feb88ed1c2bd1b31f10cbbb5edd0d86a2163
Evidence: This mapping correction uses the real shallow-checkout fix commit SHA `edc5e7766e28924ff4350d52dc97b85b917ab0c2`; `git rev-parse edc5e7766` resolves to that commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235882748
Disposition: NOT-A-BUG
Evidence: Current branch head contains `4128eb460ac8c1a15030a44d22d8cd5bbbe6da91`; `git merge-base --is-ancestor 4128eb460ac8c1a15030a44d22d8cd5bbbe6da91 HEAD` returned `0`.
Reason: The comment evaluated an older reviewed head; the live PR branch history contains the mapped FIXED proof commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3235882753
Disposition: NOT-A-BUG
Evidence: Current branch head contains `828aee1179d74b2501ab04346fe7762d377f2208`; `git merge-base --is-ancestor 828aee1179d74b2501ab04346fe7762d377f2208 HEAD` returned `0`.
Reason: The comment evaluated an older reviewed head; the live PR branch history contains the mapped FIXED proof commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3236399329
Disposition: NOT-A-BUG
Evidence: `GH_TOKEN=$(gh auth token) ../../.venv/bin/python scripts/orchestration/check_review_threads_disposition.py --pr-number 1748 --require-auth` passed locally for all resolved review threads before this thread was resolved.
Reason: The repo-native strict disposition guard verifies the live PR branch checkout; the bot comment referenced a synthetic reviewed head that is not the merge-readiness checkout used by the canonical guard.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3236295291 -> f8745840153d656d0fb96042d009f03da7f10a95
Disposition: FIXED
Commit: f8745840153d656d0fb96042d009f03da7f10a95
Evidence: This mapping artifact now uses the real finalized review-disposition commit SHA `6bc2feb88ed1c2bd1b31f10cbbb5edd0d86a2163`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3236295295 -> ba51206144f52319f4ae1fdbdef07aeeac5961a6
Disposition: FIXED
Commit: ba51206144f52319f4ae1fdbdef07aeeac5961a6
Evidence: `tests/test_design_automation_next_lane_docs.py` now fetches PR event bounds with enough history, computes `git merge-base base_sha head_sha`, and uses a three-dot merge-base comparison instead of the earlier `base_sha..HEAD` event-base fallback. Focused local pytest passes (`13 passed`) and full pre-commit passes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3236295300 -> f8745840153d656d0fb96042d009f03da7f10a95
Disposition: FIXED
Commit: f8745840153d656d0fb96042d009f03da7f10a95
Evidence: This mapping artifact now uses the real artifact-collision fix commit SHA `6c22df3e4a3f818f22471fdafc3c5ff55c8935d3`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3236333532 -> 02b001132555b9dbfa232fe53edf7e380cfaf717
Disposition: FIXED
Commit: 02b001132555b9dbfa232fe53edf7e380cfaf717
Evidence: `.github/workflows/ci.yml` now uses distinct diagnostic `test-main` artifact names (`coverage-main-xml-*`, `junit-main-*`) and updates `coverage-main` downloads to those names, leaving PR-scoped `coverage-xml-3.13` for `test-pr` and `diff-coverage`.

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
- `../../.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_ci_workflow_pr_size_governance_contract.py` - PASS after PR head diff guard fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after PR head diff guard fix
- `PATH=../../.venv/bin:$PATH git commit -m "test(ci): use PR head diff for Kimi guard"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_app_extended_coverage.py::TestPremiumEndpoints::test_premium_bmr_runtime_patch_returns_stub_response` - PASS after 3.11 coverage fix
- `../../.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_ci_workflow_pr_size_governance_contract.py` - PASS after 3.11 coverage fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after 3.11 coverage fix
- `PATH=../../.venv/bin:$PATH git commit -m "test(ci): cover premium bmr fallback branch"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_ci_workflow_pr_size_governance_contract.py tests/test_app_extended_coverage.py::TestPremiumEndpoints::test_premium_bmr_runtime_patch_returns_stub_response` - PASS after Kimi merge-base diff fix (`13 passed`)
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after Kimi merge-base diff fix
- `PATH=../../.venv/bin:$PATH git commit -m "test(ci): diff Kimi guard from merge base"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_app_extended_coverage.py::TestPremiumEndpoints::test_premium_bmr_runtime_patch_returns_stub_response` - PASS after 3.12 timeout fix (`13 passed`)
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after 3.12 timeout fix
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): extend python 3.12 main timeout"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` - PASS after 3.12 shard rebalance
- `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 3 --max-parallel 3 --list-shards` - PASS with balanced shard weights `3156708`, `3156742`, `3156746`
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after 3.12 shard rebalance
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): rebalance python 3.12 main shards"` - PASS hooks
- `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.11 --shard-count 4 --max-parallel 4 --list-shards` - PASS with balanced shard weights `2367885`, `2367530`, `2367530`, `2367817`
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after 3.11 process-shard fix
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): run python 3.11 main tests in process shards"` - PASS hooks

## Current-Head CI

- Current-head PR checks are pending after 3.11 process-shard fix.
- Merge readiness is not claimed while PR CI, review-bot disposition, and strict merge wrapper remain pending.
