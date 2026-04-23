# Main CI Python 3.12 Timeout Root-Cause Packet

Date: 2026-04-23
Branch: `codex/main-ci-py312-timeout-root-cause`
Scope: `.github/workflows/ci.yml`, `scripts/ci/run_py312_main_shards.py`,
`tests/test_ci_workflow_pr_size_governance_contract.py`,
`tests/test_py312_main_shards.py`, and this packet/backlog wiring.

## Coordinator Scope Lock

Use the Tier 1 CI/CD lane order:

1. `agent-coordinator`
2. `dev-operator`
3. `architecture-specialist`
4. `backend-engineer`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`
8. `agent-coordinator`

Mandatory post-open review remains `qa-engineer-agent -> bug-hunter`.

## Evidence

- PR #1494 reduced Python 3.12 xdist pressure but did not stabilize main.
- PR #1501 split serial tests but did not stabilize main.
- PR #1505 fully disabled xdist for Python 3.12 as containment.
- Main run `24843626627` cancelled `test-main (3.12, 60)` while the test
  step was running from `2026-04-23T15:26:19Z`.
- Main run `24849990678` still had `test-main (3.12, 60)` in progress from
  `2026-04-23T19:02:48Z` when this lane was scoped; `3.11` already passed.

## Decision

Do not raise the timeout and do not rename the required check.

For Python 3.12 only, keep pytest-xdist disabled but regain wall-clock budget
with two isolated pytest processes in the same `test-main (3.12, 60)` job.
Each process receives:

- a deterministic file shard balanced by file size;
- `-p no:xdist`;
- a unique `PYTEST_XDIST_WORKER` value for DB isolation;
- a unique coverage data file;
- a shard-specific JUnit XML file;
- `faulthandler_timeout=300` and expanded duration reporting.

After all shards pass, the runner combines coverage and enforces the existing
97% coverage threshold. Any shard failure fails the job.

## Non-Goals

- No runtime API, OpenAPI, product UI, Cloudflare, deployment, or customer-facing
  changes.
- No `continue-on-error`, ignored pytest failures, or coverage weakening.
- No broad timeout bump as the primary mitigation.

## Acceptance

- Local workflow contract tests pass.
- `make validate-changed` passes before push.
- `pre-commit run --all-files` passes before push.
- Draft PR current-head CI proves `test-main (3.12, 60)` completes without
  timeout and without xdist worker-node termination before any non-draft or
  merge-ready claim.
