# PR #2007 Fixed in Commit Mapping

## Summary

PR: `fix(ci): serialize design token parity in main shards`

Branch: `codex/fix-main-token-parity-shard-toolchain`

Implementation commit: `cfa68539d`

This PR restores post-merge `main` CI health by running
`tests/test_design_token_parity.py` as a serial pre-shard in the main test
runner, while preserving fail-closed toolchain validation and coverage
enforcement.

## Lane Start Provenance

- Base branch: `main`
- Start head: `92a28aa6739a876eb3127c4adcd089592c22a7ef`
- Packet: `artifacts/orchestration/task_packets/e7266cc0a9cc.json`
- Dispatch manifest:
  `agent-coordinator -> qa-engineer-agent -> security-auditor -> backend-engineer -> bug-hunter`

## Scope

- Added a serial main-test shard for `tests/test_design_token_parity.py`.
- Excluded that file from process-parallel main shard partitioning.
- Combined serial shard coverage before regular shard coverage.
- Added regression tests for serial discovery, fail-before-parallel behavior,
  coverage combine wiring, and `main()` orchestration.

## Out Of Scope

No product/runtime behavior, OpenAPI, auth, billing, nutrition, frontend
runtime, iOS, npm install, dependency, skip/xfail, or coverage-threshold change.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Sourcery review-level feedback is mapped below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2007#pullrequestreview-4547611166 -> e2b99c1c0
Disposition: FIXED
Commit: e2b99c1c0
Evidence: `scripts/ci/run_main_test_shards.py` now uses shared `build_test_file(...)` metadata construction from both regular and serial test discovery paths; `tests/test_main_test_shards.py` adds `test_build_test_file_normalizes_relative_path_and_weight`. Focused pytest and targeted mypy passed.

## PulsePlate PR Review Disposition

Finding: `large-diff-risk` advisory from `pulseplate-pr-review`.

Disposition: NOT-A-BUG
Evidence: The line count is driven by focused runner regression tests and the canonical review artifact. Production scope is limited to CI/test orchestration; focused pytest, targeted mypy, `make validate-changed`, `pre-commit run --all-files`, pre-push hooks, and `git diff --check` passed.
Reason: The PR is intentionally narrow despite crossing the dry-run line-count threshold; no runtime product, API, dependency, coverage-threshold, skip/xfail, auth, billing, nutrition, frontend runtime, or iOS scope is included.

## CI Failure Disposition

Finding: Current-head `lint` / `backend-tests` failed because `tests/test_main_test_shards.py` imported `coverage.cmdline` at module import time, but CI lint uses the `ci-lite` dependency profile where `coverage` is not installed.

Disposition: FIXED
Commit: 90f943239
Evidence: `scripts/ci/run_main_test_shards.py` now allows `run_coverage_command(...)` to receive an injected `coverage_main`, and `tests/test_main_test_shards.py` no longer imports `coverage.cmdline` during collection. `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" BRANCH_DIFF_MODE=1 bash scripts/run-backend-tests-pre-commit.sh` passed.

## Implementation Commits

- `cfa68539d` - serializes the design-token parity file before process-parallel
  main shards and adds runner regression coverage.
- `e2b99c1c0` - shares test-file metadata construction between regular and
  serial main test discovery in response to Sourcery feedback.
- `90f943239` - removes the top-level `coverage.cmdline` test import so CI
  lint's `ci-lite` backend-tests hook can collect `tests/test_main_test_shards.py`.

## Premortem Evidence

- Artifact:
  `artifacts/orchestration/premortem/pr2007-main-shard-token-parity-premortem.md`
- Findings closed before PR open:
  - Avoid skip/xfail or toolchain weakening: FIXED by preserving the existing
    fail-closed token parity test path.
  - Avoid losing coverage: FIXED by combining serial shard coverage before
    regular shard coverage.
  - Avoid missing JUnit artifacts: NOT-A-BUG because the serial shard uses the
    existing `tests/results-<label>-shard-0.xml` pattern covered by workflow
    artifact globs.
  - Avoid wasting parallel shard time after serial failure: FIXED by returning
    serial status before `run_all_shards`.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/pr2007-main-shard-token-parity-v2.json`
- Artifact:
  `artifacts/orchestration/experiments/results/pr2007-main-shard-token-parity-result-v2.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Contribution kind: `oracle_review`
- Co-author required: yes
- Co-author trailer included in `cfa68539d`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Validation

Passed locally:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `. .venv/bin/activate && pytest -q tests/test_main_test_shards.py tests/test_design_token_parity.py::test_token_build_script_is_deterministic`
- `. .venv/bin/activate && mypy scripts/ci/run_main_test_shards.py`
- `. .venv/bin/activate && python scripts/ci/run_main_test_shards.py --python-version 3.11 --shard-count 4 --max-parallel 4 --list-shards | rg "MAIN_TEST_SERIAL_PLAN|MAIN_TEST_SHARD_PLAN|test_design_token_parity.py"`
- `make validate-changed`
- `pre-commit run --all-files`
- `git diff --check`
- Pre-push hooks: changed-files mypy, backend tests, full-repo Bandit, Docker
  build test.

Full local `make verify` was not run for this CI/tooling hotfix. The lane uses
the operator-preferred narrow bundle plus current-head CI as the heavy signal.

## Merge Readiness

Not merge-ready yet.

Required before merge:
- [ ] Current-head CI passes.
- [ ] Bot/human review comments dispositioned.
- [ ] Post-open role passes completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan/finding discovery run if available.
- [ ] `pulseplate-pr-review` passed.
- [ ] Strict merge-readiness checks passed.
