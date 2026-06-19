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

- Packet: `artifacts/orchestration/experiments/pr6_shoplist_export_oracle_packet.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-d6352c44add9.json`
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

Pending. Mandatory post-open pass remains:
`qa-engineer-agent -> bug-hunter -> security-auditor -> Codex Security diff/finding discovery -> pulseplate-pr-review`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Initial pass completed with no actionable review comments available at this
snapshot. Review threads must not be resolved without disposition evidence and
this pass must be repeated after any new bot or human review activity.

## Fixed in Commit Mapping

- No actionable review comments

## Deferred / Follow-Ups

- Complete post-open role-agent review loop and disposition every finding before
  any readiness or merge claim.

## Merge Readiness

Not claimed.

Required before merge:
- [ ] Current-head required CI is green with no pending required jobs.
- [ ] Post-open role-agent review loop is complete.
- [ ] CodeRabbit, Sourcery, and Cubic are PASS / no-actionables.
- [ ] All actionable review threads are dispositioned and mapped here.
- [ ] Strict merge-readiness wrapper passes.
- [ ] Mandatory wait-window after latest review activity has elapsed.
