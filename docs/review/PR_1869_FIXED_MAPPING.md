# PR #1869 - Fixed in Commit Mapping

**Title:** `fix(ci): isolate main test shard temp dirs`
**Branch:** `codex/main-ci-py313-shard-temp-isolation`
**Scope:** CI/tooling hotfix for main `test-main (3.13, 90)` shard temp
isolation. The PR changes only the main-suite shard runner and its focused
tests; it does not change Experiment Runner product behavior, workflows,
coverage policy, JUnit output, shard parallelism, or application runtime code.
**Primary commits:** `9cc75668d65b6d0bb01b8c3fa662c47145828774`,
`f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open bot/human review disposition completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1869#discussion_r3346781565 -> 737469a05ba95320806fea291c78a4ea8253814d
Disposition: FIXED
Commit: 737469a05ba95320806fea291c78a4ea8253814d
Evidence: `docs/review/PR_1869_FIXED_MAPPING.md` replaces the PR-level-only fixed mapping with per-review-thread entries, including this CodeRabbit thread URL, disposition, post-comment commit SHA proof, and evidence text.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1869#discussion_r3346782834 -> 737469a05ba95320806fea291c78a4ea8253814d
Disposition: FIXED
Commit: 737469a05ba95320806fea291c78a4ea8253814d
Evidence: `docs/review/PR_1869_FIXED_MAPPING.md` now records the final branch commit `f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd` for the bug-hunter final-path collision fix and keeps implementation evidence tied to branch commits rather than a synthetic reviewed commit surface.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1869 -> 9cc75668d65b6d0bb01b8c3fa662c47145828774
Disposition: FIXED
Commit: 9cc75668d65b6d0bb01b8c3fa662c47145828774
Evidence: Initial implementation passed a deterministic external `--basetemp` to each child pytest shard, rejected repo-local configured temp roots, created the basetemp parent before `pytest.main(...)`, and preserved existing coverage/JUnit behavior; focused tests covered external unique basetemps, repo-local temp fallback, child pytest args, and parent creation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1869 -> f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd
Disposition: FIXED
Commit: f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd
Evidence: `scripts/ci/run_main_test_shards.py` now rechecks the final computed basetemp path after appending the PulsePlate shard container and falls back to `pulseplate-main-test-shards-external` if the primary final path would land inside the checkout; `tests/test_main_test_shards.py` adds a regression for a checkout named like the primary temp container.

## Implementation Evidence

Disposition: FIXED
Commit: `9cc75668d65b6d0bb01b8c3fa662c47145828774`
Evidence:

- `scripts/ci/run_main_test_shards.py` adds `external_temp_root(...)` to keep
  pytest basetemp roots outside the repository.
- `scripts/ci/run_main_test_shards.py` adds `shard_basetemp_dir(...)`, keyed by
  resolved repo-root hash, artifact label, and shard index.
- `scripts/ci/run_main_test_shards.py` passes `--basetemp` into each child
  pytest argument list and creates the basetemp parent before `pytest.main(...)`.
- `tests/test_main_test_shards.py` proves basetemps are deterministic, unique
  per shard, external to the repo, and still wired into child pytest args.
- Existing `TestShard.coverage_file`, `TestShard.junit_file`,
  `build_shard_env(...)`, coverage combine/report, and shard parallelism
  contracts are unchanged.

Disposition: FIXED
Commit: `f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd`
Evidence:

- `scripts/ci/run_main_test_shards.py` rechecks final basetemp candidates after
  appending the primary/fallback PulsePlate shard container.
- `scripts/ci/run_main_test_shards.py` falls back to
  `pulseplate-main-test-shards-external` when the primary final path would be
  inside the checkout.
- `tests/test_main_test_shards.py` covers the final-path collision case where
  the repository root is itself named `pulseplate-main-test-shards`.

## Role-Agent / Premortem Pass

Pre-open role order completed from packet
`artifacts/orchestration/task_packets/d61404beb69c.json`:

- `agent-coordinator` - completed; approved the narrow two-file CI/tooling
  scope and required current-head PR CI evidence because the original failure
  was GitHub-only.
- `qa-engineer-agent` - completed; defined acceptance criteria for per-shard
  external `--basetemp`, unchanged coverage/JUnit behavior, unchanged
  parallelism, and focused regression tests.
- `bug-hunter` - completed; identified the missing pytest temp isolation as the
  likely defect and preserved Experiment Runner/product behavior as out of
  scope.
- `security-auditor` - completed; first found and then verified the fix for
  repo-local temp-root risk. Final closure found no actionables.

Post-open role order completed from packet
`artifacts/orchestration/task_packets/318f23d86dd8.json`:

- `qa-engineer-agent` - completed; found a PR-body file-list omission for the
  mapping artifact. The live PR body now lists
  `docs/review/PR_1869_FIXED_MAPPING.md`.
- `bug-hunter` - completed; found the final-path collision edge case after
  appending the PulsePlate temp container. Commit
  `f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd` fixed it and the bug-hunter
  closure pass found no remaining actionables.
- `security-auditor` - completed; found no additional code security
  actionables. It required committing/pushing the bug-hunter fix and mapping
  the CodeRabbit/Codex connector review threads before readiness.

Premortem:

- Frame: 48 hours from now this hotfix made things worse.
- Decision: proceed with changes.
- Finding closed as FIXED: environment-controlled temp roots could point inside
  the checkout. `external_temp_root(...)` now rejects repo-local configured temp
  roots and tests cover the fallback.
- Residual risk: current-head PR CI remains required evidence for the original
  GitHub-only py313 shard path.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-6c5981dd7108.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-6c5981dd7108.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracle command:
  `python3 -m pytest -q tests/test_main_test_shards.py tests/test_experiment_runner.py::test_main_writes_oracle_only_governance_reviewer_artifact`
- Oracle return code: 0.
- `source_diff_paths`:
  - `scripts/ci/run_main_test_shards.py`
  - `tests/test_main_test_shards.py`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `coauthor_required=true`
- Commit trailer used on `9cc75668d65b6d0bb01b8c3fa662c47145828774`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

- Packet: `artifacts/orchestration/experiments/exp-aa444fd80390.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-aa444fd80390.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracle command:
  `python3 -m pytest -q tests/test_main_test_shards.py tests/test_experiment_runner.py::test_main_writes_oracle_only_governance_reviewer_artifact`
- Oracle return code: 0.
- `source_diff_paths`:
  - `scripts/ci/run_main_test_shards.py`
  - `tests/test_main_test_shards.py`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `coauthor_required=true`
- Commit trailer used on `f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/d61404beb69c.json`

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path scripts/ci/run_main_test_shards.py --path tests/test_main_test_shards.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `. .venv/bin/activate && python -m pytest -q tests/test_main_test_shards.py tests/test_experiment_runner.py::test_main_writes_oracle_only_governance_reviewer_artifact` - PASS; 37 tests after the final-path collision regression.
- `. .venv/bin/activate && python -m bandit -q scripts/ci/run_main_test_shards.py` - PASS.
- `python3 scripts/orchestration/experiment_runner.py --packet artifacts/orchestration/experiments/exp-6c5981dd7108.json --contribution-kind oracle_review --coauthor-required ...` - PASS; result accepted.
- `pre-commit run --all-files` - PASS.
- `make validate-changed` after implementation commit - PASS; ran
  `tests/test_main_test_shards.py`.
- Commit hooks for `9cc75668d65b6d0bb01b8c3fa662c47145828774` - PASS.
- Commit hooks for `f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd` - PASS.
- `make validate-changed` after `f74d0af80e96b7ab1aa6b8d29640fd7668bb04bd` - PASS; ran
  `tests/test_main_test_shards.py`.
- Pre-push hooks - PASS, including changed-file mypy, `pip-audit`, backend
  pre-push tests, full-repo Bandit, and docker build test.

## Machine-Heavy Local Shard Note

- Attempted:
  `. .venv/bin/activate && python scripts/ci/run_main_test_shards.py --python-version 3.13 --shard-count 8 --max-parallel 4`
- First attempt exposed and fixed a real parent-directory issue for the new
  `--basetemp` path.
- Final attempt got past basetemp setup and later failed in shard 8 on a
  separate cross-shard repo-local `worktrees` race:
  `tests/test_no_bmi_math_outside_core.py::test_no_whtr_formula_outside_core`
  walked a `worktrees/dirty-origin-main-test-*` path while
  `tests/test_start_pr_lane.py` ran in concurrent shard 7.
- Confirming focused command passed:
  `. .venv/bin/activate && python -m pytest -q tests/test_start_pr_lane.py tests/test_no_bmi_math_outside_core.py`
  - PASS; 44 tests.
- This PR does not claim to fix that separate cross-shard `worktrees` race.

## Current CI Status

Current-head PR CI has not completed yet. Do not claim green, ready, done, or
mergeable until current-head checks, post-open role passes, external bot review
disposition, and strict merge-readiness gates pass.

## Codex Security Diff Scan

Pending post-open.

## PulsePlate PR Review

Pending post-open.

## Merge Readiness

Not claimed. Green CI alone will not be sufficient; strict merge-readiness,
review-thread disposition, fixed-mapping completion, and the mandatory wait
window still apply.
