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

## Split Justification

This PR exceeds the default size threshold because the original Node24 path-filter migration exposed the same `test-main` Python 3.12 timeout/leakage class already visible on `main` and Nightly Full. Keeping the runner stabilization in this PR is intentional: the failing surface is the same canonical CI lane needed to validate the Node24 fix, and splitting would leave PR #1748 unable to produce current-head evidence for its own required checks. Scope remains limited to CI workflow/runner contracts, tests, and review governance; no runtime/product behavior, OpenAPI, package proxy, backend, frontend, or iOS app behavior is changed.

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
- Current-head CI finding: FIXED by `a59c5c7e9bdd3cccfc05f066b765d39797cb783c`
  - Finding: `test-main (3.11, 60)` failed because pytest-xdist worker `gw0` crashed while running `tests/test_food_source_preference_recipe_mapping.py::test_preference_recipe_mapping_rejects_notes_that_contradict_policy[recipe text allowed]`; failed workers returned no coverage data, dropping total coverage to `29.88%`.
  - Evidence: CI job `75939635310` reported `1 failed, 13172 passed, 26 skipped` and `The following workers failed to return coverage data`, with `coverage.xml` still uploaded from partial data.
  - Evidence: `.github/workflows/ci.yml` now runs Python 3.11 `test-main` through the existing process-level shard runner instead of pytest-xdist while preserving the required check name and 97% coverage gate.
  - Evidence: `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.11 --shard-count 4 --max-parallel 4 --list-shards` produced balanced shard weights `2367885`, `2367530`, `2367530`, and `2367817`.
  - Evidence: `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` passes and full pre-commit passes.
- Current-head CI finding: FIXED by `bd1331c44769f046ec440d13db09126d5138a0a9`
  - Finding: `test-main (3.12, 90)` still hit the job timeout after the three-shard rebalance; the job ran from `2026-05-14T07:02:01Z` to `2026-05-14T08:32:39Z`.
  - Evidence: JUnit artifact `junit-main-3.12` contained completed shard 1 (`4376` tests, `0` failures/errors, `time="1569.179"`) and shard 3 (`4559` tests, `0` failures/errors, `time="2096.330"`), but no shard 2 XML.
  - Evidence: `.github/workflows/ci.yml` now uses the same four process-shard plan for Python 3.12 that passed current-head Python 3.11, while preserving the `test-main (3.12, 90)` required-check identity.
  - Evidence: `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 4 --max-parallel 4 --list-shards` produced balanced shard weights `2367885`, `2367530`, `2367530`, and `2367817`.
  - Evidence: `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` passes and full pre-commit passes.
- Current-head/main/Nightly CI finding: FIXED by `d7f31a62362f411fc4fd7f8c51ca194ececd1888`
  - Finding: further sharding did not close the failure mode; the evidence points to post-pytest process leakage where a shard writes JUnit after tests complete but the Python process/job remains alive until timeout.
  - Evidence: PR current-head run `25861580104` still had `test-main (3.12, 90)` in progress at branch head `3bacf84344989f78fe7495cb07da2a25982b99c1` while other required checks had completed.
  - Evidence: `main` CI run `25860402769` at `e91e00daad5d21e6b0690fbb2dbbd48b8fd44474` showed the same pattern: `test-main (3.12, 60)` stayed in progress while 3.11 and 3.13 completed successfully; earlier job `75988571210` uploaded `junit-3.12/results-py312-shard-2.xml` with `6334` tests, `0` failures, `0` errors, and `time="1942.042"` before cancellation.
  - Evidence: Nightly Full run `25844026393` at `17db1118d215d0ffecd5e09a8d254db03db336e4` failed after coverage output with repeated faulthandler dumps in `execnet/gateway_base.py` receiver threads, independently matching a test-runner cleanup/leakage class rather than a Node24 paths-filter behavior change.
  - Fix: `scripts/ci/run_main_test_shards.py` now runs each shard through an explicit child interpreter invocation and the child calls `os._exit(exit_code)` immediately after `pytest.main(...)` returns and stdout/stderr are flushed, so leaked non-daemon threads or pytest/coverage cleanup hooks cannot keep the CI job alive after shard artifacts are written.
  - Evidence: `tests/test_main_test_shards.py` now asserts both parent-to-child invocation and forced child exit after `pytest.main(...)` returns.
  - Evidence: local gates passed: `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py`; `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_app_extended_coverage.py::TestPremiumEndpoints::test_premium_bmr_runtime_patch_returns_stub_response`; guard tests for `nosec` and subprocess policy; `make validate-changed`; `pre-commit run --all-files`.
  - Premortem disposition: FIXED. The most likely failure was treating the timeout as only a shard-sizing problem; the fix changes runner isolation while preserving coverage/JUnit output and current required-check names.
  - Codex Security disposition: NOT-A-BUG after validation. The new subprocess use is bounded to the current Python interpreter and the repo-local runner path, uses `shell=False`, carries policy-compliant `nosec` TTL/ref comments for B404/B603, and is covered by guard tests.
- Current-head CI finding: FIXED by `af9ca1a9d2d9937acc75ed95108311af7a86aa65`
  - Finding: current-head CI run `25865119409` proved the child-exit fix worked for completed Python 3.12 shards 1, 2, and 3, but shard 4 itself did not complete before the 90-minute job timeout.
  - Evidence: job `76005934903` logged `MAIN_TEST_SHARD_FINISHED` for shard indexes 1, 2, and 3, but not index 4; uploaded JUnit contained only `results-py312-shard-1.xml`, `results-py312-shard-2.xml`, and `results-py312-shard-3.xml`.
  - Evidence: shard 4 started at `2026-05-14T14:24:35Z`, reached only about `54%` by `2026-05-14T15:34:09Z`, and the `Run tests with coverage` step was cancelled at `2026-05-14T15:52:07Z`.
  - Fix: `.github/workflows/ci.yml` now splits Python 3.12 into eight deterministic shards with `MAIN_TEST_MAX_PARALLEL=4`, creating two bounded batches instead of one overloaded four-shard wave.
  - Evidence: `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 8 --max-parallel 4 --list-shards` produced eight balanced shard weights between `1183920` and `1184358`.
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` now locks the Python 3.12 `MAIN_TEST_SHARDS=8` / `MAIN_TEST_MAX_PARALLEL=4` contract.
  - Evidence: local focused workflow/runner pytest, `make validate-changed`, full pre-commit, and commit hooks pass.
- Current-head CI finding: FIXED by `a1fb059e10f9c975626ec50162be5952ba79fd49`
  - Finding: live job `76028705577` showed the first Python 3.12 batch did not advance to shard indexes 5-8 after shard indexes 1, 2, and 3 finished; shard index 4 printed a pytest success summary but did not print `MAIN_TEST_SHARD_FINISHED`.
  - Evidence: the open job log showed `MAIN_TEST_SHARD_FINISHED` for indexes 1, 2, and 3, while index 4 had already printed `1575 passed, 18 deselected in 867.94s (0:14:27)` without returning control to the parent scheduler.
  - Fix: `scripts/ci/run_main_test_shards.py` now uses slot-based scheduling with `FIRST_COMPLETED`, so the next shard starts as soon as any active shard returns instead of waiting for an entire batch.
  - Fix: each child shard subprocess has a bounded watchdog and the parent schedules by freed slots. The later security-auditor pass superseded the initial timeout-after-artifacts path in `efc598e6eebf2d5084318e9d80d5f728f4a06c7f`; all subprocess timeouts now fail closed.
  - Security validation: Bandit, `nosec`, and subprocess guard tests pass; the XML parser dependency and timeout-as-success branch were removed in later commits.
  - Evidence: local focused workflow/runner/security tests, `make validate-changed`, full pre-commit, and commit hooks pass.
- Current-head CI finding: FIXED by `bcfee31164158da560c1850fc0954ef57972ff3e`
  - Finding: current-head Python 3.12 job on stale head `5b6f73e851574e7c2c3236e2bec5b4f23919ae44` failed immediately because the CI `ci-test` profile does not install `defusedxml`.
  - Evidence: job `76050358649` failed at import time with `ModuleNotFoundError: No module named 'defusedxml'` before shard execution.
  - Fix: `scripts/ci/run_main_test_shards.py` no longer imports an external XML parser. The later security pass removed the artifact-proof timeout-success path entirely, so no XML/JUnit parsing is needed on timeout.
  - Security validation: this removes the XML parser dependency and Bandit XML finding instead of suppressing it; focused runner/workflow/security guard tests and full pre-commit pass.
- Current-head CI finding: FIXED by `efc598e6eebf2d5084318e9d80d5f728f4a06c7f`
  - Finding: current-head run `25878540629` proved cleanup now runs, but the new per-shard watchdog exposed a different issue: live shards were being killed at the 1800s subprocess timeout before completion.
  - Evidence: job `76052252136` (`test-main (3.12, 90)`) started shards 5-8 and reached cleanup, but logged `MAIN_TEST_SHARD_TIMEOUT_FAILED label=py312 index=4 timeout_seconds=1800`; job `76052252031` (`test-main (3.13, 90)`) logged `MAIN_TEST_SHARD_TIMEOUT_FAILED` for shard indexes 1 and 2.
  - Evidence: the logs showed active pytest progress before timeout (`py312` shard 4 around 39%, `py313` shards around 57%/64%), so this was workload sizing under the watchdog rather than the old post-summary cleanup leak or the removed `defusedxml` import failure.
  - Fix: `.github/workflows/ci.yml` now right-sizes main-suite shards to Python 3.12 `MAIN_TEST_SHARDS=16` / `MAIN_TEST_MAX_PARALLEL=4` and Python 3.13 `MAIN_TEST_SHARDS=8` / `MAIN_TEST_MAX_PARALLEL=4`, while Python 3.11 remains at the already-passing `4/4`.
  - Fix: `scripts/ci/run_main_test_shards.py` now treats every subprocess timeout as fail-closed, even if partial JUnit/coverage artifacts exist, and prints each timed-out shard file path with `MAIN_TEST_SHARD_TIMEOUT_FILE` diagnostics.
  - Evidence: `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 16 --list-shards` produced sixteen balanced shard weights around `592k`; `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.13 --shard-count 8 --list-shards` produced eight balanced shard weights around `1184k`.
  - Evidence: local focused workflow/runner/security guard pytest, `make validate-changed`, full `pre-commit run --all-files`, and commit hooks pass.
  - Agent-coordinator/QA/bug-hunter/security disposition: FIXED. Coordinator classified the issue as shard watchdog/plan sizing, QA recommended rebalance over timeout loosening, bug-hunter identified the 1800s watchdog as the active failure, and security-auditor required removing timeout-as-success.
- Current-head CI finding: FIXED by `f46e2a49acb2cc385b15fa141c3ec6e56e6065db`
  - Finding: current-head run `25881278346` proved the fail-closed diagnostics and finer shard topology worked, but two live shards still exceeded the default 1800s subprocess watchdog.
  - Evidence: `test-main (3.11, 60)` passed. `test-main (3.12, 90)` failed on shard 13 after all other py312 shards finished, with `MAIN_TEST_SHARD_TIMEOUT_FAILED label=py312 index=13 timeout_seconds=1800`; `test-main (3.13, 90)` failed on shard 4, while shard 8 later completed and the job reached cleanup.
  - Evidence: cleanup ran and JUnit artifacts uploaded for the failed jobs, proving the original post-test cleanup hang is no longer the active failure. The timeout diagnostics listed the exact timed-out shard file membership for follow-up triage.
  - Fix: `.github/workflows/ci.yml` now sets an explicit bounded `MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800` for Python 3.12 and 3.13 only, while keeping all timeout paths fail-closed and preserving the 90-minute job cap.
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` locks the explicit 4800-second py312/py313 watchdog and log echo contract.
  - Evidence: local focused workflow/runner tests, subprocess/nosec guard tests, `make validate-changed`, full `pre-commit run --all-files`, and commit hooks pass.
- Current-head CI finding: FIXED by `a8311433022510dda70347a276373402af280f78`
  - Finding: current-head run `25884379741` proved the bounded watchdog override was only a shell-local assignment, not an exported environment variable read by `scripts/ci/run_main_test_shards.py`.
  - Evidence: the py312 and py313 logs echoed `MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800`, but the runner still emitted `MAIN_TEST_SHARD_TIMEOUT_FAILED ... timeout_seconds=1800` for py312 shard 13 and py313 shard 4.
  - Fix: `.github/workflows/ci.yml` now exports `MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800` in the Python 3.12 and 3.13 branches before invoking the Python shard runner.
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` now asserts the exported watchdog contract rather than a shell-local assignment.
  - Evidence: focused workflow/runner tests, subprocess/nosec guard tests, `make validate-changed`, full `pre-commit run --all-files`, and commit hooks pass.
- Main regression investigation finding: FIXED by `9e9d842d4c375d21fe3e660be0f7e3001e3b3b91`
  - Finding: the main-suite slowdown began after PR #1745/#1747; direct timing cleared #1745 (`tests/test_design_component_registry.py` completed in `3.7s`) and identified PR #1747's `tests/test_food_source_preference_recipe_mapping.py` as the dominant new test cost (`237` tests, about `103s` locally before the fix).
  - Evidence: the expensive PR #1747 note-policy parameter matrix called `parse_preference_recipe_mapping_governance(...)` for each phrase, forcing full PR11/PR14 handoff validation hundreds of times even though the behavior under test was the note guard.
  - Fix: note-policy cases now call the unit seam `_require_safe_notes(...)`; full governance parse coverage remains in the existing integration tests for top-level notes, PR11 notes, PR14 notes, schema, safety flags, CLI, and report generation.
  - Regression guard: the broad note phrase matrix remains in place, but is now tied to the bounded unit-level validator rather than full governance parsing; immutable fixture helpers are cached and mutable JSON payloads are returned as deep copies.
  - Evidence: `../../.venv/bin/python -m pytest -q --durations=50 --durations-min=0.2 tests/test_food_source_preference_recipe_mapping.py` passes with the file reduced to about `41s`.
  - Evidence: `../../.venv/bin/python -m pytest -q tests/test_food_source_preference_recipe_mapping.py tests/test_design_component_registry.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_main_test_shards.py` passes.
  - Evidence: `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` and `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` pass.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3239683637 -> c2abf5dab25da49f4220aa5170e652dfc65b62bc
Disposition: FIXED
Commit: c2abf5dab25da49f4220aa5170e652dfc65b62bc
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` now uses the real full Python 3.11 shard-fix commit SHA `a59c5c7e9bdd3cccfc05f066b765d39797cb783c`, which resolves in this repository.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3241365081
Disposition: NOT-A-BUG
Evidence: Current PR head `c445782e3629533a2c34172609918b2995b5498d` contains the mapped FIXED proof commits in branch history, and the mapping artifact/PR body explicitly define FIXED commit SHAs as PR branch-history proofs for the live PR checkout and current-head CI.
Reason: The bot evaluated squash-preview reviewed commit `c24ab3d5064cd1a48fb68c2aee1affd4b2eb314b`, not the canonical live PR branch checkout used by repo-native merge-readiness verification.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3241495641
Disposition: NOT-A-BUG
Evidence: CI merge-readiness job `75991358535` on final-head run `25861221326` reached the review-governance parser and failed only on unmapped CodeRabbit review-level URL `pullrequestreview-4290015131`; it did not reject the existing branch-history proof SHAs. That review-level URL is now mapped in this artifact.
Reason: The bot evaluated squash-preview reviewed commit `0c10ada6e61b5c95e4f5493b33b81aae07c3a476`, while the repo-native merge-readiness check validates the live PR branch/merge checkout and currently accepts branch-history proof SHAs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3241365086 -> bb20cab788961df809fad8fa5e058528283f5fb3
Disposition: FIXED
Commit: bb20cab788961df809fad8fa5e058528283f5fb3
Evidence: `tests/test_design_automation_next_lane_docs.py` now fetches PR endpoint commits with progressively deeper history (`100`, `500`, `2000`) before accepting merge-base failure and fallback diff bases. Focused local pytest and full pre-commit pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3241411361 -> bb20cab788961df809fad8fa5e058528283f5fb3
Disposition: FIXED
Commit: bb20cab788961df809fad8fa5e058528283f5fb3
Evidence: `tests/test_app_extended_coverage.py` now annotates `test_premium_bmr_runtime_patch_returns_stub_response` with `-> None`. Focused local pytest and full pre-commit pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3241411369 -> bb20cab788961df809fad8fa5e058528283f5fb3
Disposition: FIXED
Commit: bb20cab788961df809fad8fa5e058528283f5fb3
Evidence: `tests/test_app_extended_coverage.py` now asserts the response content type starts with `application/json` before calling `response.json()`. Focused local pytest and full pre-commit pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#pullrequestreview-4290015131 -> bb20cab788961df809fad8fa5e058528283f5fb3
Disposition: FIXED
Commit: bb20cab788961df809fad8fa5e058528283f5fb3
Evidence: CodeRabbit review-level actionable aggregated the inline findings `discussion_r3241411361` and `discussion_r3241411369`, both fixed by the same premium test assertion hardening commit.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25845462494/job/75939635310 -> a59c5c7e9bdd3cccfc05f066b765d39797cb783c
Disposition: FIXED
Commit: a59c5c7e9bdd3cccfc05f066b765d39797cb783c
Evidence: `test-main (3.11, 60)` failed from a pytest-xdist worker crash and partial coverage data, not a deterministic assertion failure; `.github/workflows/ci.yml` now runs Python 3.11 through process-level shards with `tests/results-py311-shard-*.xml` artifacts, and `tests/test_ci_workflow_pr_size_governance_contract.py` locks that contract. Focused workflow contract pytest, balanced shard-plan proof, and full pre-commit pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25846637782/job/75943642347 -> bd1331c44769f046ec440d13db09126d5138a0a9
Disposition: FIXED
Commit: bd1331c44769f046ec440d13db09126d5138a0a9
Evidence: `test-main (3.12, 90)` still timed out with three process shards after shards 1 and 3 completed successfully and shard 2 produced no JUnit XML; `.github/workflows/ci.yml` now uses four process shards for Python 3.12, and `tests/test_ci_workflow_pr_size_governance_contract.py` locks that contract. Focused workflow contract pytest, balanced shard-plan proof, and full pre-commit pass.

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
Evidence: `tests/test_design_automation_next_lane_docs.py` probes the PR event merge-base, `origin/main...HEAD`, and `main...HEAD`, then fails closed when no stable base exists. `test_kimi_diff_fails_closed_without_first_parent_fallback` prevents reintroducing a first-parent fallback.
Reason: Current code no longer has a single-parent or first-parent fallback, so the finding is stale for the live PR head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3242779268 -> 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Disposition: FIXED
Commit: 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` now uses the resolvable Python 3.12 batch-split proof SHA `af9ca1a9d2d9937acc75ed95108311af7a86aa65`; `git cat-file -t af9ca1a9d2d9937acc75ed95108311af7a86aa65` returns `commit`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3243477611 -> bcfee31164158da560c1850fc0954ef57972ff3e
Disposition: FIXED
Commit: bcfee31164158da560c1850fc0954ef57972ff3e
Evidence: `scripts/ci/run_main_test_shards.py` no longer imports `defusedxml` or any external XML parser. Current-head `test-main (3.12, 90)` and `test-main (3.13, 90)` passed on run `25891747917`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3243844705 -> 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Disposition: FIXED
Commit: 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Evidence: `scripts/ci/run_main_test_shards.py` stops refilling pending shards after any completed shard returns nonzero, and `tests/test_main_test_shards.py::test_run_all_shards_stops_refilling_after_first_failure` locks that fail-fast behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3244159778 -> a8311433022510dda70347a276373402af280f78
Disposition: FIXED
Commit: a8311433022510dda70347a276373402af280f78
Evidence: `.github/workflows/ci.yml` exports `MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800` before invoking the shard runner for Python 3.12 and 3.13; current-head `test-main (3.12, 90)` and `test-main (3.13, 90)` passed on run `25891747917`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3244505277 -> 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Disposition: FIXED
Commit: 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Evidence: `tests/test_design_automation_next_lane_docs.py` now bounds PR endpoint `git fetch` probes with `GIT_FETCH_TIMEOUT_SECONDS`, and `test_kimi_diff_fetch_has_timeout_before_local_fallback` verifies timeout handling before local fallback.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#pullrequestreview-4293727717 -> 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Disposition: FIXED
Commit: 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Evidence: This CodeRabbit review-level duplicate asked to remove the first-parent fallback from the Kimi docs-only guard. `tests/test_design_automation_next_lane_docs.py` no longer constructs a `parent...HEAD` diff base, and `test_kimi_diff_fails_closed_without_first_parent_fallback` covers the regression.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#pullrequestreview-4294204794 -> 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Disposition: FIXED
Commit: 77e35170a1fdbb5191113b7ce449d4fa2ef70968
Evidence: This CodeRabbit review-level duplicate repeated the first-parent fallback issue on current head `83cfcbd5e302387421f39f7b5658310d46ca3737`. The guard now relies on PR event merge-base, `origin/main...HEAD`, or `main...HEAD` only, and fails closed when none is available.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3245995064 -> 8274fc72b4199dfee198956cf969be645ccf7f8e
Disposition: FIXED
Commit: 8274fc72b4199dfee198956cf969be645ccf7f8e
Evidence: `docs/review/PR_1748_FIXED_MAPPING.md` now uses the resolvable PR #1747 test-cost proof SHA `9e9d842d4c375d21fe3e660be0f7e3001e3b3b91`; `git cat-file -t 9e9d842d4c375d21fe3e660be0f7e3001e3b3b91` returns `commit`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1748#discussion_r3245995069 -> 8274fc72b4199dfee198956cf969be645ccf7f8e
Disposition: FIXED
Commit: 8274fc72b4199dfee198956cf969be645ccf7f8e
Evidence: `scripts/ci/run_main_test_shards.py` now cancels submitted in-flight shard futures, terminates process-pool workers, and shuts the executor down with `cancel_futures=True` after the first nonzero shard result. `tests/test_main_test_shards.py::test_run_all_shards_stops_refilling_after_first_failure` verifies the `MAIN_TEST_SHARD_CANCELLED ... reason=fail_fast` path, and `run_shard(...)` now starts shard subprocesses in a process group so worker termination can stop child pytest processes instead of waiting for the shard watchdog.

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
- `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 4 --max-parallel 4 --list-shards` - PASS with balanced shard weights `2367885`, `2367530`, `2367530`, `2367817`
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after 3.12 four-shard fix
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): rebalance python 3.12 into four shards"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_app_extended_coverage.py::TestPremiumEndpoints::test_premium_bmr_runtime_patch_returns_stub_response tests/test_ci_workflow_pr_size_governance_contract.py` - PASS after latest review fixes (`13 passed`)
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after latest review fixes
- `PATH=../../.venv/bin:$PATH git commit -m "test(ci): harden Kimi diff and premium assertions"` - PASS hooks
- `../../.venv/bin/python scripts/orchestration/task_bootstrap.py --goal "Fix main-suite test shard post-pytest process leakage after Node24 paths-filter PR exposed CI timeout" --task-class ci_fix --path scripts/ci/run_main_test_shards.py --path tests/test_main_test_shards.py --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review` - PASS (`task_packet_id: c4a01b307e33`)
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py` - PASS after shard-exit isolation fix (`29 passed`)
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_app_extended_coverage.py::TestPremiumEndpoints::test_premium_bmr_runtime_patch_returns_stub_response` - PASS after shard-exit isolation fix (`42 passed`)
- `../../.venv/bin/python -m flake8 scripts/ci/run_main_test_shards.py tests/test_main_test_shards.py` - PASS after shard-exit isolation fix
- `../../.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_main_test_shards.py` - PASS after shard-exit isolation fix (`34 passed`)
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after shard-exit isolation fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after shard-exit isolation fix
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): isolate main test shard exits"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_main_test_shards.py` - PASS after Python 3.12 batch split (`40 passed`)
- `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 8 --max-parallel 4 --list-shards` - PASS with balanced shard weights `1183920`, `1184286`, `1184275`, `1184352`, `1184306`, `1184283`, `1184358`, and `1184218`
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after Python 3.12 batch split
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after Python 3.12 batch split
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): split python 3.12 main shard batches"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` - PASS after dynamic shard scheduling/watchdog (`49 passed`)
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after dynamic shard scheduling/watchdog
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after dynamic shard scheduling/watchdog
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): advance main shards past cleanup hangs"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` - PASS after removing external XML parser dependency (`49 passed`)
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after removing external XML parser dependency
- `PATH=../../.venv/bin:$PATH git commit -m "fix(ci): remove shard watchdog xml dependency"` - PASS hooks
- `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.12 --shard-count 16 --list-shards` - PASS with balanced shard weights around `592k`
- `../../.venv/bin/python scripts/ci/run_main_test_shards.py --python-version 3.13 --shard-count 8 --list-shards` - PASS with balanced shard weights around `1184k`
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` - PASS after fail-closed watchdog plan fix (`48 passed`)
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after fail-closed watchdog plan fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after fail-closed watchdog plan fix
- `PATH=../../.venv/bin:$PATH VENV_PYTHON=../../.venv/bin/python git commit -m "fix(ci): right-size main shard watchdog plan"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_main_test_shards.py` - PASS after bounded py312/py313 watchdog override (`43 passed`)
- `../../.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` - PASS after bounded py312/py313 watchdog override (`5 passed`)
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after bounded py312/py313 watchdog override
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after bounded py312/py313 watchdog override
- `PATH=../../.venv/bin:$PATH VENV_PYTHON=../../.venv/bin/python git commit -m "fix(ci): bound slow main shard watchdog"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_main_test_shards.py` - PASS after exporting the bounded py312/py313 watchdog override (`43 passed`)
- `../../.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` - PASS after exporting the bounded py312/py313 watchdog override (`5 passed`)
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after exporting the bounded py312/py313 watchdog override
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after exporting the bounded py312/py313 watchdog override
- `PATH=../../.venv/bin:$PATH VENV_PYTHON=../../.venv/bin/python git commit -m "fix(ci): export main shard watchdog timeout"` - PASS hooks
- `../../.venv/bin/python -m pytest -q --durations=50 --durations-min=0.2 tests/test_food_source_preference_recipe_mapping.py` - PASS after PR #1747 test-cost fix; local file runtime dropped from about `103s` to about `41s`
- `../../.venv/bin/python -m pytest -q tests/test_food_source_preference_recipe_mapping.py tests/test_design_component_registry.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_main_test_shards.py` - PASS after PR #1747 test-cost fix
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after PR #1747 test-cost fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after PR #1747 test-cost fix
- `PATH=../../.venv/bin:$PATH VENV_PYTHON=../../.venv/bin/python git commit -m "test(food-data): trim preference mapping note guard cost"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py::test_run_all_shards_stops_refilling_after_first_failure tests/test_design_automation_next_lane_docs.py::test_kimi_diff_fetch_has_timeout_before_local_fallback tests/test_design_automation_next_lane_docs.py::test_kimi_diff_fails_closed_without_first_parent_fallback` - PASS after latest review fixes
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only tests/test_design_automation_next_lane_docs.py::test_kimi_diff_fetch_has_timeout_before_local_fallback tests/test_design_automation_next_lane_docs.py::test_kimi_diff_fails_closed_without_first_parent_fallback tests/test_ci_workflow_pr_size_governance_contract.py` - PASS after latest review fixes
- `../../.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` - PASS after latest review fixes
- `../../.venv/bin/python -m flake8 scripts/ci/run_main_test_shards.py tests/test_main_test_shards.py tests/test_design_automation_next_lane_docs.py` - PASS after latest review fixes
- `git diff --check` - PASS after latest review fixes
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH git commit -m "fix(ci): fail fast shard and Kimi diff guards"` - PASS hooks
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py::test_run_shard_invokes_explicit_child_interpreter tests/test_main_test_shards.py::test_run_shard_fails_timeout_even_with_clean_artifacts tests/test_main_test_shards.py::test_run_shard_fails_timeout_without_clean_artifacts tests/test_main_test_shards.py::test_run_all_shards_stops_refilling_after_first_failure` - PASS after fail-fast cancellation fix
- `../../.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py` - PASS after fail-fast cancellation fix (`49 passed`)
- `../../.venv/bin/python -m flake8 scripts/ci/run_main_test_shards.py tests/test_main_test_shards.py` - PASS after fail-fast cancellation fix
- `../../.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null scripts/ci/run_main_test_shards.py` - PASS after fail-fast cancellation fix
- `git diff --check` - PASS after fail-fast cancellation fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH git commit -m "fix(ci): cancel main shards after first failure"` - PASS hooks
- `DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH make validate-changed` - PASS after fail-fast cancellation fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH pre-commit run --all-files` - PASS after fail-fast cancellation fix
- `VENV_PYTHON=../../.venv/bin/python PATH=../../.venv/bin:$PATH git commit -m "docs(review): map fail-fast shard reviews"` - PASS hooks

## Current-Head CI

- Current-head PR checks are pending after syncing with `origin/main` and trimming the PR #1747 preference-mapping note guard test cost.
- Merge readiness is not claimed while PR CI, review-bot disposition, and strict merge wrapper remain pending.
