# CI Lint And Runner Timeout Triage — March 27, 2026

## Summary

This packet records the current CI failure pattern around lint instability,
runner pressure, and timeout risk in the canonical `PulsePlate` GitHub Actions
lanes.

Scope of this packet:

- root-cause analysis only
- no runtime/API/product behavior changes
- no merge-governance relaxation
- no hidden infra assumptions

This is a docs-first triage lane that exists to make the follow-up
implementation PR narrow and auditable.

## Symptoms

### Lint lane

Current `CI` job `lint` is budgeted at `15` minutes but runs the full
repository `pre-commit --all-files` gate after Python bootstrap. In practice,
this means the job is not a narrow static-lint lane; it is a repo-wide hygiene
and hook-execution lane.

### Test and timeout pressure

Additional pressure exists in the heavy test lanes:

- `test-pr`, `test-feature`, `test-main` run full or near-full pytest suites
  with coverage gates
- Python `3.13` is intentionally forced into a more conservative execution path
  due to prior xdist/coverage instability
- `nightly-tests.yml` remains a heavyweight lane with Python, Node, coverage,
  and full-suite execution
- `ios-tests` and `ios-ui-smoke` run on standard GitHub-hosted macOS runners,
  which are materially smaller than Linux public runners

## Repo-Grounded Evidence

### 1. CI lint is not equivalent to local `make lint`

Local `make lint` runs `flake8 .`.

GitHub Actions `lint` runs:

- checkout
- `.github/actions/python-setup`
- `pre-commit run --all-files --show-diff-on-failure`

That means the CI lane carries more than static linting and can fail or stall on
repo-wide hook execution unrelated to a narrow style check.

### 2. Python bootstrap is expensive before lint even begins

The composite Python setup path calls
`scripts/ci/install_locked_python_requirements.py`, which validates the
approved package proxy, performs guarded installation logic, and can build a
wheelhouse/staging environment before the job reaches the lint step.

### 3. Nightly already demonstrated runtime/bootstrap drift

The canonical nightly triage from March 22, 2026 recorded a failure where the
workflow was running frontend/OpenAPI logic against Node `20.20.1` while the
repo contract had already moved to Node `22.22.1+`.

That incident proves the repo has already seen CI drift that looks like a
runner failure from the outside but is actually a workflow/bootstrap mismatch.

### 4. macOS budget is tight for iOS lanes

The iOS jobs currently rely on booting simulators, building for testing,
running smoke UI flows, and then running test-without-building on standard
hosted macOS runners. This is the highest runner-pressure surface in the repo.

## Root Cause

The current failures are best explained by a combined CI budget problem rather
than a single broken runner:

1. the `lint` lane is overloaded relative to its name and timeout budget
2. dependency bootstrap through the approved private Python proxy adds material
   startup cost
3. some workflows historically drifted from the canonical Node/Python bootstrap
   contract
4. heavy macOS/iOS lanes are running on small standard GitHub-hosted runners
5. Python `3.13` test stability constraints already reduce available parallelism

## Decision

The chosen remediation path is:

1. keep governance strict
2. do **not** relax coverage or security gates
3. do **not** treat this as a generic GitHub outage
4. split CI responsibilities so that each lane has a clear and honest budget

## Follow-Up Implementation Plan

### PR A — workflow decomposition

Narrow the current `lint` job into a true static-lint lane:

- workflow/YAML validation
- formatter check
- Ruff/static lint
- no repo-wide `pre-commit --all-files`

Create a separate repo-hygiene lane for the slower full pre-commit execution.

### PR B — bootstrap parity

Normalize shared Node/Python bootstrap so every workflow that needs frontend or
OpenAPI generation uses the same contract and runtime floor.

### PR C — iOS budget review

Reassess whether the iOS smoke/build/test chain should remain on standard macOS
runners as a single lane or be split further before escalating to larger
runners.

## Security Notes

- No security gate should be weakened to mask runner pressure.
- Private package proxy enforcement remains canonical.
- Timeout fixes must preserve fail-closed behavior.

## Marketing & GTM

None. This packet is engineering-governance only.

## Decision Log

- Chosen first artifact: docs-first triage
- Follow-up implementation should be a narrow CI PR
- No product/runtime scope change is authorized by this packet

## Next Actions

1. Open a focused implementation PR for CI decomposition only.
   Owner: CI maintainers. Target date: 2026-03-29.
2. Keep PR body and mapping artifacts aligned with merge-governance rules.
   Owner: PR owner. Target date: 2026-03-27.
3. Update AGENTS/process notes after the implementation PR lands so future
   agents do not re-expand `lint` into a hidden repo-wide verify lane.
   Owner: Orchestration maintainers. Target date: 2026-03-31.

## References

- `.github/workflows/ci.yml`
- `.github/workflows/nightly-tests.yml`
- `.github/workflows/frontend-ci.yml`
- `.github/actions/python-setup/action.yml`
- `scripts/ci/install_locked_python_requirements.py`
- `docs/ci/triage_nightly_2026-03-22.md`
