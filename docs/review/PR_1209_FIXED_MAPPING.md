# PR 1209 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `.github/workflows/ci.yml:134`, `.github/workflows/frontend-ci.yml:15`, `.github/workflows/accessibility.yml:1`, `.github/actions/npm-ci-with-retry/action.yml:20`, `frontend/package.json:29`, `frontend/package-lock.json:1`, `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md:40`, `frontend/AGENTS.md:8`, `scripts/frontend_npm.sh:6`, `Makefile:427`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#pullrequestreview-3985902115 -> 5fa9db40
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#pullrequestreview-3985928654 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#pullrequestreview-3985929753 -> 9d16d47d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#pullrequestreview-3985943334 -> 9d16d47d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#pullrequestreview-3985943493 -> 9d16d47d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#pullrequestreview-3985996931 -> 3815c555
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#pullrequestreview-3985999056 -> 3815c555
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969442865 -> 5fa9db40
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969444773 -> eab0e344
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478121 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478126 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478129 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478130 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969494473 -> 3815c555
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969494692 -> 9d16d47d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969550044 -> 3815c555
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969550505 -> 3815c555

## Merge Readiness
- Review status: ready for review.
- Merge status: waiting on current-head CI and final strict merge gate.
- Current fix commits:
  - `3815c555` — `fix(ci): harden node helper and action`
  - `40f47b01` — `docs(review): map pr1209 latest reviews`
  - `9d16d47d` — `fix(ci): tighten node22 frontend bootstrap`
  - `5c0c40bb` — `fix(ci): track node22 workflow inputs`
  - `eab0e344` — `fix(ci): enforce local frontend node22 parity`
  - `5fa9db40` — `fix(ci): centralize node22 frontend runtime`
- Current scope discipline:
  - align touched frontend/OpenAPI-sync workflows to Node `22.22.1`
  - align frontend engine contract to Node `>=22.0.0 <23.0.0`
  - harden touched CI/frontend `npm ci` steps with bounded retry flags for transient registry resets
  - fail fast when local `node`/`npm` are missing, block too-old Node runtimes, and avoid implicit registry bootstrap for newer local shells
  - tighten local frontend install path to `npm ci` lockfile semantics
  - remove unnecessary `actions: write` from accessibility workflow and normalize/comprehensively guard composite-action `working-directory` input against traversal
  - no backend API or schema contract change intended
- Carryover / deferred context:
  - this PR is an explicit stopgap/hygiene slice ahead of the broader Node 24/cache-warning cleanup track still recorded in [`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md#ledger-p2-gha-node24-cache-warning-cleanup)
- Local validation executed on this lane:
  - `python3 -m scripts.orchestration.check_preflight`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `./scripts/frontend_npm.sh --version`
  - `cd frontend && npm ci`
  - `cd frontend && npm run build`
  - `make openapi`
  - `. .venv/bin/activate && python -m pytest -q tests/test_openapi_determinism.py`
  - `pre-commit run --all-files`
  - `make verify`
- Required before merge:
  - [ ] refresh this artifact after each human/bot review wave
  - [ ] mirror required sections into the PR body after artifact updates
  - [ ] confirm current-head required checks are green with no pending required jobs
  - [ ] run `python scripts/orchestration/check_merge_ready.py --pr-number 1209 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
  - [ ] confirm no actionable bot comments or unresolved threads remain
  - [ ] observe the mandatory wait-window before merge
