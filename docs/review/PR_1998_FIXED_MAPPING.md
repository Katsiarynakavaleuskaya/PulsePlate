# PR 1998 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1998

Branch: `codex/shrink-legacy-shoplist-export-registration-seam`

## Summary

This PR moves canonical `shoplist_export` router registration ownership from
`legacy_app.py` into canonical `app/main.py` bootstrap. It preserves the public
runtime route family, legacy API-key dependency, export 429 metadata, route-level
OpenAPI visibility, and final public OpenAPI hiding.

## Scope

- Remove only the `shoplist_export` router import and registration from
  `legacy_app.py`.
- Add `SHOPLIST_ROUTE_SPECS` in `app/routers/shoplist_export_routes.py`.
- Register `shoplist_export_router` from `app/main.py` through an idempotent
  fail-closed helper.
- Tighten `scripts/ci/check_legacy_growth_guard.py` so reintroduced legacy
  imports/includes fail.
- Add focused bootstrap, guard, shoplist export runtime, auth/dependency, 429
  metadata, and OpenAPI-hiding tests.
- Update `docs/architecture/backend_routing_map.md` for route ownership truth.

## Out Of Scope

No `AuthenticatedPrincipal` work, OAuth/OIDC rewrite, auth rewrite, tier
semantics change, dependency update, semantic cache, FoodDB, frontend/iOS work,
or broad legacy refactor.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/ceae68a814ad.json`
- Runtime dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/ceae68a814ad.json --pretty`
- Pre-open role order executed:
  `agent-coordinator -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Starter: `check_preflight.py`, `check_agent_consistency.py`, and
  `task_bootstrap.py`; packet creation was treated as provenance only, not role
  execution.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `. .venv/bin/activate && python -m pytest -q tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_shoplist_export.py tests/security/test_api_auth_tier_contract_pack.py`
- PASS: `PATH=.venv/bin:$PATH make openapi-check`
- PASS: runtime probe confirmed three `/api/v1/shoplist*` routes with `GET`,
  429 metadata, `app.routers.shoplist_export` handlers, and no final OpenAPI
  shoplist paths.
- PASS with caveat: `PATH=.venv/bin:$PATH make validate-changed` selected no
  files, so it is not treated as sufficient changed-surface evidence for this
  PR.
- PASS: `pre-commit run --all-files` after black formatting.
- PASS: commit hooks.
- PASS: pre-push hooks, including changed-file mypy, backend pytest pre-push,
  full-repo Bandit, and docker build test.

## Machine-Heavy Verification Deferral

Operator override applies: no deliberate full local `make verify` for this PR.
Current-head CI parity, post-open review disposition, strict merge-readiness,
and the mandatory wait-window still apply before any merge claim.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/pr1998_shoplist_export_oracle_packet_v2.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-0dfcbf0eb4b1.json`
- Status: accepted.
- Oracles passed:
  - `python3 scripts/ci/check_legacy_growth_guard.py`
  - `pytest -q tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_shoplist_export.py tests/security/test_api_auth_tier_contract_pack.py`
  - `make openapi-check`
- Attribution: co-author trailer required and present on implementation commit
  `1a4412b356ee545ccfaf0a1e3f693fa2bb37c71a`.

## Premortem Findings

Disposition: FIXED

Finding: `PR6-P1-001` reported that `make validate-changed` could be a
false-green signal because it selected no files.

Commit: `1a4412b356ee545ccfaf0a1e3f693fa2bb37c71a`

Evidence: focused pytest, `make openapi-check`, pre-commit, pre-push hooks, and
Experiment Runner oracles passed on the changed route/guard/OpenAPI surface.

Disposition: FIXED

Finding: `PR6-P1-002` reported that moving registration could accidentally
change shoplist export auth, 429 metadata, runtime paths, or final OpenAPI
visibility.

Commit: `1a4412b356ee545ccfaf0a1e3f693fa2bb37c71a`

Evidence: `app/main.py` fail-closed bootstrap checks, `tests/test_main_paywall_bootstrap.py`
route-family tests, and `tests/test_shoplist_export.py` live route/OpenAPI
contract test preserve the intended behavior.

## Post-Open Review Evidence

- CodeRabbit: FIXED unexpected source-router path finding in
  `37b3754f3`. Evidence: `app/main.py` now rejects unexpected
  `shoplist_export_router` paths before including the whole router, and
  `tests/test_main_paywall_bootstrap.py` asserts the fail-closed behavior.
- Sourcery: NOT-A-BUG broader shared-helper extraction suggestion. Evidence:
  this PR intentionally mirrors the already-governed PR #1997 seam pattern for
  one narrow route family; extracting a generic bootstrap framework would widen
  the PR beyond the registration-ownership lane.
- qa-engineer-agent: PASS on `ec57ad08c`. Evidence: CodeRabbit finding was
  fixed in `37b3754f3`, the review thread is resolved/outdated, focused pytest,
  OpenAPI, PR body, and mapping guards pass, and the worktree is clean.
- bug-hunter: PASS on `ec57ad08c`. Evidence: runtime probe confirmed exactly
  three shoplist export routes with protected dependency, 429 metadata, hidden
  final OpenAPI paths, and the advisory disposition guard passed locally.
- security-auditor: PASS on `ec57ad08c`. Evidence: auth remains fail-closed,
  unexpected source-router paths fail closed, no new secret or subprocess surface
  was introduced, security CI passed on current-head run `27864230408`, and
  strict local disposition parity was blocked only by missing local `GH_TOKEN`.
- Codex Security diff/finding discovery: PASS/no findings. Evidence:
  plugin callable scan tools were unavailable in this runtime, so a bounded
  diff-focused security pass reviewed the changed auth, rate-limit metadata,
  OpenAPI hiding, subprocess/suppression, and guard surfaces.
- pulseplate-pr-review: NOT-A-BUG advisory large-diff planning note. Evidence:
  the diff is intentionally test-heavy for one route-family migration, operator
  scope approval applies, `make validate-changed` was run and treated as
  non-sufficient because it selected no files, and focused deterministic pytest,
  OpenAPI, pre-commit, and pre-push hooks cover the changed surface.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Pass completed for bot activity available through CodeRabbit review
`4535586272` and Sourcery review `4535567071`. Review threads must not be
resolved without disposition evidence and this pass must be repeated after any
new bot or human review activity.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 37b3754f3c57da0f4de3bd955565a55924f3c6bd
Evidence: `app/main.py` rejects unexpected `shoplist_export_router` paths before including the router; `tests/test_main_paywall_bootstrap.py` covers the regression.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1998#discussion_r3444778679 -> 37b3754f3c57da0f4de3bd955565a55924f3c6bd

Disposition: FIXED
Commit: 37b3754f3c57da0f4de3bd955565a55924f3c6bd
Evidence: same CodeRabbit finding as the inline discussion above; fixed in code and covered by focused bootstrap tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1998#pullrequestreview-4535586272 -> 37b3754f3c57da0f4de3bd955565a55924f3c6bd

Disposition: NOT-A-BUG
Evidence: `app/main.py` keeps this lane aligned with the established PR #1997 route-family bootstrap pattern, and `tests/test_main_paywall_bootstrap.py` covers the concrete shoplist invariants without introducing a broad generic bootstrap abstraction.
Reason: Extracting shared route-family helpers is valid future cleanup but would broaden this narrow legacy-registration PR beyond the reviewed scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1998#pullrequestreview-4535567071

## Deferred / Follow-Ups

- No code follow-up is deferred by this artifact. Readiness remains unclaimed
  until current-head required CI, strict merge readiness, and the mandatory
  wait-window are satisfied.

## Merge Readiness

Not claimed.

Required before merge:
- [ ] Current-head required CI is green with no pending required jobs.
- [x] Post-open role-agent review loop is complete.
- [ ] CodeRabbit, Sourcery, and Cubic are PASS / no-actionables.
- [ ] All actionable review threads are dispositioned and mapped here.
- [ ] Strict merge-readiness wrapper passes.
- [ ] Mandatory wait-window after latest review activity has elapsed.
