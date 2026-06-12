# Legal Publication Route Extraction Premortem

Date: 2026-06-12

Task packet: `artifacts/orchestration/task_packets/54b7e6ad7501.json`

Branch: `codex/extract-legal-publication-routes-from-legacy`

Mode: `pr-premortem`

## Summary

Plan: extract `/privacy` and `/terms` from `legacy_app.py` into canonical
`app.routers.legal`, with registration owned by `app/main.py`.

Failure frame: six months from now, the extraction made the legacy seam look
smaller while creating route ownership or contract drift.

Decision: proceed with changes. All premortem findings below are closed in the
current PR diff before PR open.

## Findings And Closure

### PM-LEGAL-001: Legal routes leak into public OpenAPI

Failure story: `/privacy` or `/terms` becomes visible in generated public
OpenAPI after moving into `app.routers.legal`. Frontend type generation then
treats legal publication pages as canonical product API paths, causing contract
noise and future client churn.

Underlying assumption: moving a route into a canonical router does not change
schema visibility.

Early warning signs: `app.openapi()["paths"]` contains `/privacy` or `/terms`,
or generated OpenAPI/client files change for legal publication routes.

Disposition: FIXED.

Evidence:

- `app/routers/legal.py` keeps both legal endpoints `include_in_schema=False`.
- `tests/test_app_endpoints_combined.py` asserts `/privacy` and `/terms` remain
  absent from public OpenAPI.
- Focused pytest includes `tests/test_app_endpoints_combined.py` and passed.

### PM-LEGAL-002: Duplicate or foreign legal route handlers survive bootstrap

Failure story: a reload or test rehydration path already has legal routes
registered by a non-canonical handler. The bootstrap sees the path and silently
accepts it, leaving route order to determine the effective handler.

Underlying assumption: route path presence is enough to prove canonical route
ownership.

Early warning signs: more than one GET route exists for `/privacy` or `/terms`,
or the route endpoint module is not `app.routers.legal`.

Disposition: FIXED.

Evidence:

- `app/main.py` now registers legal routes as an atomic family and requires
  exactly one canonical GET route per legal path when routes already exist.
- `tests/test_main_paywall_bootstrap.py` covers partial legal state, malformed
  legal router state, foreign handlers, and canonical-plus-foreign duplicate
  routes.

### PM-LEGAL-003: Legacy seam shrink remains reversible through stale allowlist

Failure story: the route handlers move out of `legacy_app.py`, but the growth
guard still allowlists reintroduced `/privacy`, `/terms`, or legal helper
imports. A later PR can accidentally put legal publication ownership back into
legacy while passing the seam guard.

Underlying assumption: deleting legacy code is enough without shrinking the
guard baseline.

Early warning signs: `scripts/ci/check_legacy_growth_guard.py` still contains
allowed facts for `/privacy`, `/terms`, or `app.routers.legal`.

Disposition: FIXED.

Evidence:

- `scripts/ci/check_legacy_growth_guard.py` no longer allowlists the legacy
  legal route decorators or legal helper import.
- `tests/test_legacy_growth_guard.py` rejects reintroduced legal routes and the
  legal router import.
- `scripts/ci/check_legacy_growth_guard.py` passed.

### PM-LEGAL-004: Raw `legacy_app:app` compatibility is mistaken for canonical serving

Failure story: an operator imports or serves `legacy_app:app` directly and
expects `/privacy` and `/terms` to remain present after extraction. Because
canonical bootstrap lives in `app/main.py`, those routes are available through
the canonical app entrypoint, not raw legacy ownership.

Underlying assumption: compatibility means raw `legacy_app.py` should keep
owning every historic route forever.

Early warning signs: docs or PR text describe `legacy_app.py` as the product
runtime owner for newly extracted routes, or tests assert direct
`legacy_app.terms()` wrappers after extraction.

Disposition: NOT-A-BUG.

Evidence:

- `docs/architecture/LEGACY_COMPATIBILITY_SEAM.md` defines `legacy_app.py` as a
  compatibility seam that may shrink.
- `app/main.py` is the canonical FastAPI entrypoint and applies additive
  bootstrap over the legacy base.
- Direct legacy wrapper tests were removed or retargeted to canonical route
  behavior.

## Pre-Merge Checklist

- Focused route and guard tests pass.
- `scripts/ci/check_legacy_growth_guard.py` passes.
- `scripts/ci/check_semantic_cache_gate.py` confirms runtime semantic cache
  remains closed.
- `pre-commit run --all-files` passes after hook formatting.
- PR body records lane start provenance, premortem closure, and Experiment
  Runner oracle evidence.
