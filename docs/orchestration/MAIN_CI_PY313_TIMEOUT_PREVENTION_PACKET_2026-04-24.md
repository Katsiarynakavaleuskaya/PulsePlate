# Main CI Python 3.13 Timeout Prevention Packet

Date: 2026-04-24
Branch: `codex/main-ci-py313-timeout-prevention`
Base: `origin/main` after PR #1511 merge

## Scope

- Prevent `test-main (3.13, 90)` from timing out as the test suite grows.
- Generalize the Python 3.12 main-suite shard runner into a version-neutral
  no-xdist process shard runner.
- Route Python 3.13 through the shared runner while preserving the required
  check identity, 90-minute timeout, JUnit artifact, coverage XML artifact, and
  `--fail-under=97` coverage behavior.
- Update governance so machine-heavy CI/tooling PRs do not run full local
  project `make verify` by default when the operator explicitly defers it.

## Evidence

- PR #1511 current-head CI proved the Python 3.12 fix.
- The same run showed `test-main (3.13, 90)` passing in about 88m44s, leaving
  almost no budget under the 90-minute job timeout.
- Python 3.13 xdist remains out of scope because prior evidence included
  xdist/coverage instability and segmentation faults.

## Role Order

1. `agent-coordinator` - scope lock, packet/governance alignment, final synthesis.
2. `dev-operator` - current-head CI evidence, required-check identity, artifacts.
3. `backend-engineer` - runner, workflow, tests.
4. `security-auditor` - no CI bypass, no permission/secret broadening.
5. `qa-engineer-agent` - local narrow gates and PR evidence quality.
6. `bug-hunter` - post-open regression review for shard isolation, coverage, JUnit.
7. `agent-coordinator` - merge-readiness synthesis.

## Out Of Scope

- Runtime API, UI, Cloudflare, deploy, iOS, or customer-facing changes.
- Broad timeout increase as the primary fix.
- `continue-on-error`, ignored pytest failures, weakened coverage, or skipped
  required CI.
- Restoring pytest-xdist on Python 3.12 or Python 3.13 without new evidence.

## Local Validation Contract

For this machine-heavy lane, full local `make verify` is intentionally deferred
unless the operator requests it. Required local gates are:

- `python3 scripts/orchestration/check_preflight.py` with touched paths.
- `python3 scripts/orchestration/check_agent_consistency.py`.
- Focused shard runner and workflow/risk contract tests.
- `make validate-changed`.
- `pre-commit run --all-files`.

Merge readiness must use canonical current-head GitHub CI parity as the heavy
signal: `lint`, `typecheck`, the relevant `test-main` matrix, `diff-coverage`
at >=97%, applicable security/governance checks, and the strict merge wrapper.
The PR body and fixed-mapping artifact must document this local `make verify`
deferral.

## Acceptance

- `test-main (3.13, 90)` completes on the PR head with meaningful headroom.
- `test-main (3.12, 60)` remains green and keeps the shared sharded policy.
- Python 3.11 stays on the fast xdist baseline.
- Coverage XML and JUnit artifacts remain uploadable for each matrix version.
- Review threads and bot actionables are mapped in
  `docs/review/PR_<N>_FIXED_MAPPING.md`.
