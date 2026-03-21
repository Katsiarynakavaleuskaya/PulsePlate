# PR 1209 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
No review threads yet; artifact initialized before first human/bot review wave.

## Merge Readiness
- Review status: draft.
- Merge status: not ready to merge.
- Current fix commits:
  - `a9d9f65f` — `chore(pre-commit): refresh secrets baseline`
  - `472c4afd` — `fix(ci): align frontend openapi sync with node 22`
- Current scope discipline:
  - align touched frontend/OpenAPI-sync workflows to Node `22.22.1`
  - align frontend engine contract to Node `>=22.0.0 <23.0.0`
  - harden touched CI/frontend `npm ci` steps with bounded retry flags for transient registry resets
  - add scoped frontend agent-doc note so local OpenAPI/type-generation paths match the new runtime contract
  - no backend API or schema contract change intended
- Carryover / deferred context:
  - this PR is an explicit stopgap/hygiene slice ahead of the broader Node 24/cache-warning cleanup track still recorded in [`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md#ledger-p2-gha-node24-cache-warning-cleanup)
- Local validation executed on this lane:
  - `python3 -m scripts.orchestration.check_preflight`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `pre-commit run --all-files`
  - `cd frontend && npm ci`
  - `cd frontend && npm run build`
  - `make openapi`
  - `python -m pytest -q tests/test_openapi_determinism.py`
  - `make verify`
- Required before merge:
  - [ ] refresh this artifact after each human/bot review wave
  - [ ] mirror required sections into the PR body after artifact updates
  - [ ] confirm current-head required checks are green with no pending required jobs
  - [ ] run `python scripts/orchestration/check_merge_ready.py --pr-number 1209 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
  - [ ] confirm no actionable bot comments or unresolved threads remain
  - [ ] observe the mandatory wait-window before merge
