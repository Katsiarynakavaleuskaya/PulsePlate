# Main CI Python 3.12 Timeout Root-Cause Packet

Date: 2026-04-23
Branch: `codex/main-ci-py312-timeout-root-cause`
Scope: `.github/workflows/ci.yml`, `scripts/ci/ci_risk_profile.py`,
`scripts/ci/run_py312_main_shards.py`,
`tests/test_ci_workflow_pr_size_governance_contract.py`,
`tests/test_ci_risk_profile.py`, `tests/test_py312_main_shards.py`, and this
packet/backlog wiring.

## Coordinator Scope Lock

Use the Tier 1 CI/CD lane order:

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `backend-engineer`
5. `dev-operator`
6. `qa-engineer-agent`
7. `bug-hunter`

Mandatory post-open review remains `qa-engineer-agent -> bug-hunter`.

## Evidence

- PR #1494 reduced Python 3.12 xdist pressure but did not stabilize main.
- PR #1501 split serial tests but did not stabilize main.
- PR #1505 fully disabled xdist for Python 3.12 as containment.
- Main run `24843626627` cancelled `test-main (3.12, 60)` while the test
  step was running from `2026-04-23T15:26:19Z`.
- Main run `24849990678` still had `test-main (3.12, 60)` in progress from
  `2026-04-23T19:02:48Z` when this lane was scoped; `3.11` already passed.
- Main run `24854923154` later failed `test-main (3.12, 60)` at roughly 20%
  with `Segmentation fault (core dumped)` in the sequential no-xdist command:
  `python -X faulthandler -m pytest "${PYTEST_XDIST_ARGS[@]}" -m "not slow"`
  with coverage enabled.

## Decision

Do not raise the timeout and do not rename the required check.

For Python 3.12 only, keep pytest-xdist disabled but regain wall-clock budget
with two isolated pytest processes in the same `test-main (3.12, 60)` job.
Each process receives:

- a deterministic file shard balanced by file size;
- `-p no:xdist`;
- a unique `PY312_MAIN_SHARD` value while intentionally removing
  `PYTEST_XDIST_WORKER` so xdist-only DB routing is not faked;
- a unique coverage data file;
- a shard-specific JUnit XML file;
- `faulthandler_timeout=300` and expanded duration reporting.

After all shards pass, the runner combines coverage and enforces the existing
97% coverage threshold. Any shard failure fails the job.

If a shard process exits via native crash and breaks the worker pool, the parent
runner emits `PY312_SHARD_EXCEPTION index=<n> ...` before failing the job. This
preserves the failing shard boundary for the next root-cause pass instead of
turning the crash into an unscoped job-level failure.

PR CI normally skips `test-main` because the comprehensive matrix is main-only.
For this lane class, `ci_risk_profile.py` emits `run_main_ci_diagnostic=true`
when the diff touches the Python 3.12 main-CI runner/workflow contract; `test-main`
then runs on the PR head as an explicit diagnostic proof path.

## Non-Goals

- No runtime API, OpenAPI, product UI, Cloudflare, deployment, or customer-facing
  changes.
- No `continue-on-error`, ignored pytest failures, or coverage weakening.
- No broad timeout bump as the primary mitigation.

## Acceptance

- Local workflow contract tests pass.
- `make test-fast` passes before push.
- `make cov-check` passes before push.
- `make validate-changed` passes before push.
- `pre-commit run --all-files` passes before push.
- Draft PR current-head CI proves `test-main (3.12, 60)` completes without
  timeout and without xdist worker-node termination before any non-draft or
  merge-ready claim.

For any `tests/**/*.py` changes made while fixing red CI:

1. Identify the failing test cohort and the exact GitHub/local command.
2. Reproduce the cohort locally before changing behavior where feasible.
3. Fix code and tests in the same PR; update the nearest `AGENTS.md` only when
   the test contract itself changes.
4. Re-run `make test-fast` and `make cov-check` before push.
