# PR 1209 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
### FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969442865 -> 5fa9db40
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969444773 -> eab0e344
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478121 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478126 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478129 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969478130 -> 5c0c40bb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969494692 -> 9d16d47d

### NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209#discussion_r2969494473
  Evidence: [scripts/frontend_npm.sh](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/ci_main_openapi_sync_node22/scripts/frontend_npm.sh#L4), [scripts/frontend_npm.sh](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/ci_main_openapi_sync_node22/scripts/frontend_npm.sh#L27), [Makefile](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/ci_main_openapi_sync_node22/Makefile#L420), [Makefile](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/ci_main_openapi_sync_node22/Makefile#L427); local repro on 21 March 2026: `node -p 'process.versions.node'` => `25.6.1`, `npx -y node@22.22.1 -p 'process.versions.node'` => `22.22.1`, `./scripts/frontend_npm.sh --version` => `11.9.0`.
  Reason: CodeRabbit's claim that `npx -y node@<version>` cannot switch the runtime is not reproduced in this repository's environment. The current helper executes npm-cli.js under the exact `.nvmrc` runtime, and CodeRabbit did not re-raise this issue on current head `9d16d47d22fe0f439a09725c895dd91ce6ef1ff5`.

## Merge Readiness
- Review status: draft.
- Merge status: not ready to merge.
- Current fix commits:
  - `9d16d47d` — `fix(ci): tighten node22 frontend bootstrap`
  - `5c0c40bb` — `fix(ci): track node22 workflow inputs`
  - `eab0e344` — `fix(ci): enforce local frontend node22 parity`
  - `5fa9db40` — `fix(ci): centralize node22 frontend runtime`
- Current scope discipline:
  - align touched frontend/OpenAPI-sync workflows to Node `22.22.1`
  - align frontend engine contract to Node `>=22.0.0 <23.0.0`
  - harden touched CI/frontend `npm ci` steps with bounded retry flags for transient registry resets
  - enforce exact `.nvmrc` matching in the local frontend npm helper before allowing direct `npm`
  - tighten local frontend install path to `npm ci` lockfile semantics
  - remove unnecessary `actions: write` from accessibility workflow and constrain composite-action `working-directory` input
  - no backend API or schema contract change intended
- Carryover / deferred context:
  - this PR is an explicit stopgap/hygiene slice ahead of the broader Node 24/cache-warning cleanup track still recorded in [`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md#ledger-p2-gha-node24-cache-warning-cleanup)
- Local validation executed on this lane:
  - `python3 -m scripts.orchestration.check_preflight`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `./scripts/frontend_npm.sh --version`
  - `./scripts/frontend_npm.sh --prefix frontend ci --no-audit --no-fund`
  - `./scripts/frontend_npm.sh --prefix frontend run build`
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
