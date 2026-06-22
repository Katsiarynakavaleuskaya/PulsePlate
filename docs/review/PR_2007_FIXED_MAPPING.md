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

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

No review threads yet.

## Fixed in Commit Mapping

No review threads yet.

## Implementation Commits

- `cfa68539d` - serializes the design-token parity file before process-parallel
  main shards and adds runner regression coverage.

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
