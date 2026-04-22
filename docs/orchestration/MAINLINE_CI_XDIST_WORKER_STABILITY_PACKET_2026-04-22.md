# Mainline CI Xdist Worker Stability Packet

## Goal

Bring a new remediation PR to current-head draft readiness under
coordinator-owned orchestration by narrowing the repeated
`[gw1] node down: Not properly terminated` instability on the full
`main`-branch `CI` matrix without reopening unrelated nightly or Node 22
surfaces.

## Current Truth

- Base branch: `main`
- Synced lane start:
  - `git status --short --branch` -> clean
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- Active remediation branch: `codex/fix-ci-xdist-worker-stability`
- User-reported stable failure signature:
  - `"[gw1] node down: Not properly terminated"`
  - observed around `54%`-`57%` during the full pytest progress stream
- Live `main` evidence gathered on `22 April 2026`:
  - `CI` run `24771474555`
    - `test-main (3.11, 60)` job `72483386535` succeeded in `7m29s`
    - `test-main (3.12, 60)` job `72483372336` remained inside
      `Run tests with coverage` from `10:14:43Z` until run cancellation at
      `10:38:21Z`
    - `test-main (3.13, 90)` job `72483372298` remained inside the same step
      until the run cancellation; that path is already sequential by policy
  - `Nightly Full Tests` run `24760590280` completed with status `success`, so nightly is
    not the default target for this lane
- Current-head nuance:
  - exact historical GitHub run URL carrying the retained `gw1 node down`
    string was not recoverable from available run history at lane start
  - the lane therefore treats the user-reported signature plus the stalled
    `main` 3.12 job as the narrow live repro anchor until branch/current-head
    evidence supersedes it

## Mandatory Role Order

1. `agent-coordinator`
2. `dev-operator`
3. `architecture-specialist`
4. `backend-engineer`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`
8. `agent-coordinator`

Rules:

- This role order is mandatory for the lane.
- The canonical post-open review pass remains
  `qa-engineer-agent -> bug-hunter`.
- No ad hoc parallel role stack may replace this order.
- `dev-operator` gathers GitHub Actions and local parity evidence; it does not
  replace reviewers.

## Scope Lock

### In Scope

- `test-main` interpreter-specific execution policy inside
  `.github/workflows/ci.yml`
- A narrow workflow contract test that freezes the scoped fallback
- Coordinator packet / review artifact / backlog alignment for this lane
- Branch/current-head evidence proving the former unstable `3.12` full-suite
  path no longer stalls or crashes

### Out of Scope

- `Nightly Full Tests`, Node 22 parity, or release-gate selector work
- `test-pr`, `test-feature`, `coverage-*`, job IDs, or required-check topology
- Product runtime behavior, public APIs, iOS, frontend, Docker, Cloudflare,
  Hugging Face, or Life Science Research surfaces
- Broad repo-wide test cleanup beyond what is needed to stabilize the affected
  `test-main` interpreter path

## Expected Touched Surfaces

- `.github/workflows/ci.yml`
- `tests/test_ci_workflow_pr_size_governance_contract.py`
- `docs/orchestration/MAINLINE_CI_XDIST_WORKER_STABILITY_PACKET_2026-04-22.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_<NEW_PR_NUMBER>_FIXED_MAPPING.md`

## Coordinator Decision

- Start with the smallest fallback boundary: keep `3.11` unchanged, keep `3.13`
  on its existing sequential contract, and reduce `3.12` from `-n 4` to
  `-n 2` while preserving `--dist=loadscope`.
- Full `3.12` sequential mode is an allowed second-step escalation only if the
  new branch/current-head evidence still reproduces the worker instability after
  the narrowed `-n 2` fallback.
- The old nightly/node22 backlog item must not be reused as substitute proof
  for this lane.

## Acceptance Criteria

- `test-main` keeps its existing job identity and required-check topology
- `.github/workflows/ci.yml` scopes the new fallback to `test-main` `3.12`
  only, while preserving the existing `3.13` sequential branch
- A regression test freezes the `3.12 -> -n 2` / `3.13 -> no xdist` contract
- Targeted local workflow contract tests pass
- `pre-commit run --all-files` passes before push
- `make validate-changed` passes before push
- Branch/current-head `CI` completes without `gw1 node down` or a stalled
  `3.12` full-suite worker path
- Post-open `qa-engineer-agent -> bug-hunter` review pass is completed

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py \
  --path .github/workflows/ci.yml \
  --path tests/test_ci_workflow_pr_size_governance_contract.py \
  --path docs/orchestration \
  --path docs/roadmap/BACKLOG_LEDGER.md
python3 scripts/orchestration/check_agent_consistency.py
./.venv/bin/pytest -q \
  tests/test_ci_workflow_pr_size_governance_contract.py \
  tests/test_python_supply_chain_controls.py \
  tests/test_current_head_pr_checks.py
pre-commit run --all-files
make validate-changed
```

## Stop Conditions

- `3.12 -> -n 2` still leaves the branch/current-head `test-main` path unstable
- Any proposed change widens beyond `test-main` interpreter-specific execution
  policy without fresh evidence
- Required check names or PR routing contracts drift
- New actionable review/bot comments remain unresolved or unmapped
