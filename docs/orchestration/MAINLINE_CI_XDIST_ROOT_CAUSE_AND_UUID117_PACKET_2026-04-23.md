# Mainline CI Root-Cause + Dependabot `#117` Packet

## Goal

Bring a new coordinator-owned remediation PR to draft readiness from synced
`main` by:

1. removing the remaining Python `3.12` xdist instability on the canonical
   `CI` `test-main` lane without widening required-check topology or falling
   back to full sequential mode; and
2. closing Dependabot alert `#117` narrowly if the remediation stays inside the
   Storybook dependency carrier surface.

## Current Truth

- Base branch: `main`
- Synced lane start:
  - `git status --short --branch` -> clean
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- Active remediation branch:
  - `codex/main-ci-py312-root-cause-plus-uuid117`
- Python `3.12` CI evidence:
  - PR `#1494` reduced `3.12` from `-n 4` to `-n 2` and kept `3.13`
    sequential, but did not remove the worker-death class completely
  - failing `main` run `24771474555` still showed
    `[gw1] node down: Not properly terminated`
  - later `main` evidence still showed worker death deep into collection /
    teardown, including the user-reported late-zone failure around `80-93%`
    in run `24799632664`, which then sat near `99%` until the job timeout
  - nightly already isolates `serial` tests outside xdist, while `test-main`
    still ran `-m "not slow"` and therefore left `serial` tests eligible for
    xdist on `3.12`
- Dependabot alert `#117` truth as of `23 April 2026`:
  - advisory: `GHSA-w5hq-g745-h8pq`
  - package: `uuid`
  - manifest: `frontend/package-lock.json`
  - first patched version: `14.0.0`
  - current carrier in repo: `@storybook/addon-essentials` ->
    `@storybook/addon-actions` -> `uuid@9`
  - unsafe path rejected for this lane: force `uuid@14` override, because the
    Storybook 8 carrier still expects the CommonJS package shape

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
- `GitHub` is the primary external surface; `CodeRabbit` remains advisory; use
  `Computer Use` only if `gh` is insufficient.

## Scope Lock

### In Scope

- `.github/workflows/ci.yml` `test-main` `3.12` execution policy only
- the workflow contract test that freezes the `3.12` serial split
- narrow governance updates for this continuation lane
- `frontend/.storybook/**`, `frontend/package.json`, and
  `frontend/package-lock.json` only if the Dependabot remediation stays inside
  the Storybook addon carrier surface

### Out of Scope

- full `3.12 -> no xdist` fallback inside this PR
- changes to required-check names, matrix job identity, or branch protection
- broad Storybook major migration, UI behavior refactors, or unrelated frontend
  modernization
- Cloudflare, Hugging Face, Netlify, iOS, or release-ops surfaces

## Coordinator Decision

- Use the repo's existing nightly evidence to isolate the remaining `3.12`
  root cause: keep xdist for `-m "not serial and not slow"` and run
  `-m "serial and not slow"` sequentially inside the same `test-main (3.12, 60)`
  job.
- Keep `3.11` unchanged and keep `3.13` on its existing sequential fallback.
- Remediate alert `#117` only by removing the `addon-actions` carrier from the
  Storybook configuration surface; do not use a `uuid@14` override and do not
  widen to Storybook 9 in this lane.
- If current-head branch evidence still reproduces worker death after the
  `3.12` serial split, open a separate emergency PR for full sequential
  fallback.

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py \
  --path .github/workflows/ci.yml \
  --path tests/test_ci_workflow_pr_size_governance_contract.py \
  --path frontend/package.json \
  --path frontend/package-lock.json \
  --path docs/orchestration \
  --path docs/roadmap/BACKLOG_LEDGER.md
python3 scripts/orchestration/check_agent_consistency.py
PYENV_VERSION=3.12.7 python -X faulthandler -m pytest -q \
  tests/test_ci_workflow_pr_size_governance_contract.py
cd frontend && npm install
cd frontend && npm ls uuid --all --package-lock-only
cd frontend && npm run build-storybook
cd frontend && npm run build
pre-commit run --all-files
make validate-changed
make verify
```

## Acceptance Criteria

- `test-main` keeps the same job identity and required-check topology
- `3.12` excludes `serial` tests from xdist and runs the `serial` cohort in a
  sequential tail inside the same job
- the workflow contract test freezes the `3.12` split and preserves the `3.13`
  sequential branch
- Dependabot alert `#117` is removed without a Storybook major migration
- current-head PR `CI` passes with no unresolved review threads and no unmapped
  actionable bot comments
