# Health Readiness Route Extraction Premortem

Date: 2026-06-12

Task packet: `artifacts/orchestration/task_packets/54dec1a9e980.json`

Branch: `codex/extract-health-readiness-routes-from-legacy`

Mode: `pr-premortem`

## Summary

Plan: extract `/health`, `/api/v1/health`, `/health/db`, and `/ready` from
`legacy_app.py` into canonical `app.routers.health`, with idempotent
registration owned by `app/main.py`.

Failure frame: six months from now, the extraction looked like a narrow legacy
shrink but changed probe behavior, route ownership, or operational visibility.

Decision: proceed with changes. All premortem findings below are fixed or
dispositioned in the current PR diff before PR open.

## Findings And Closure

### PM-HEALTH-001: Health routes leak into public OpenAPI

Failure story: moving the operational probe routes into a canonical router makes
them appear in `app.openapi()["paths"]`. Generated clients then start treating
liveness and readiness probes as public product API contract, adding noisy churn
and making future probe-only changes look like client-facing API breaks.

Underlying assumption: changing route ownership does not change OpenAPI
visibility.

Early warning signs: `/health`, `/api/v1/health`, `/health/db`, or `/ready`
appears under `app.openapi()["paths"]`, or generated OpenAPI/client artifacts
change in this route extraction PR.

Disposition: FIXED.

Evidence:

- `app/routers/health.py` registers all four routes with
  `include_in_schema=False`.
- `app/main.py` rejects a health router that exposes any route in OpenAPI.
- `tests/test_app_endpoints_combined.py` asserts the four health/readiness paths
  remain absent from public OpenAPI.

### PM-HEALTH-002: Bootstrap accepts duplicate or foreign probe handlers

Failure story: a reload path, test fixture, or future router includes one of the
probe paths before canonical bootstrap. The app silently accepts the path as
present, leaving route order to decide whether the legacy, foreign, or canonical
handler serves production health checks.

Underlying assumption: path presence is enough to prove canonical ownership.

Early warning signs: more than one GET route exists for any health/readiness
path, or a route endpoint module is not `app.routers.health`.

Disposition: FIXED.

Evidence:

- `app/main.py` registers health/readiness as an atomic route family and fails
  closed on partial state, malformed canonical routers, duplicate canonical
  routes, or foreign handlers.
- `tests/test_main_paywall_bootstrap.py` covers idempotent registration,
  partial-state rejection, foreign handler rejection, OpenAPI-visible router
  rejection, and duplicate route rejection.
- `tests/test_app_endpoints_combined.py` asserts route ownership is
  `app.routers.health`.

### PM-HEALTH-003: DB readiness semantics drift during extraction

Failure story: `/health/db` stops honoring fallback detection,
`DB_HEALTH_DEGRADED`, missing `session.execute`, missing `session.bind`, or the
`SELECT 1` connectivity check. Infrastructure probes report healthy while the DB
is unavailable, or fail in a new way that operators have not configured.

Underlying assumption: copying the route body is enough without focused parity
coverage.

Early warning signs: readiness tests stop exercising fallback mode, degraded
mode, or session shape failures; response detail changes from
`Database unavailable`.

Disposition: FIXED.

Evidence:

- `app/routers/health.py` preserves the existing fallback, degraded env var,
  session shape, `SELECT 1`, and `503 Database unavailable` behavior.
- `tests/test_health_db.py` covers `/health/db` and `/ready` success/failure
  behavior.
- Focused pytest includes `tests/test_health_db.py` and passed before PR open.

### PM-HEALTH-004: `/ready` insight runtime fallback becomes fail-closed

Failure story: `/ready` starts returning 500 or dropping its additive
`insight_runtime` fallback when the insight runtime readiness helper raises.
Orchestrators that depend on DB readiness get coupled to an unrelated LLM
runtime status path.

Underlying assumption: readiness is only DB behavior, so the additive runtime
payload can be moved without a negative fallback test.

Early warning signs: logs no longer include the readiness warning, or `/ready`
returns anything other than `{"status": "unavailable"}` for the insight runtime
fallback.

Disposition: FIXED.

Evidence:

- `app/routers/health.py` preserves fail-soft insight runtime readiness handling.
- `tests/test_health_db.py` and `tests/test_legacy_app_diff_coverage.py` assert
  the fallback payload and warning behavior against `app.routers.health`.

### PM-HEALTH-005: Legacy guard still permits probe route ownership to return

Failure story: the handlers move out of `legacy_app.py`, but the legacy growth
guard keeps allowlisted facts for `/health`, `/api/v1/health`, `/health/db`, and
`/ready`. A later change can reintroduce the decorators in legacy while the guard
still passes.

Underlying assumption: deleting the handlers is enough to make the migration
durable.

Early warning signs: `scripts/ci/check_legacy_growth_guard.py` still contains
allowed route facts for the extracted health/readiness paths.

Disposition: FIXED.

Evidence:

- `scripts/ci/check_legacy_growth_guard.py` removes the allowed legacy route
  facts for all four extracted paths.
- `tests/test_legacy_growth_guard.py` rejects reintroduced health/readiness
  decorators.
- `scripts/ci/check_legacy_growth_guard.py` passed before PR open.

### PM-HEALTH-006: Raw `legacy_app:app` direct serving loses probe routes

Failure story: an operator serves raw `legacy_app:app` directly instead of the
canonical `app.main:app` entrypoint and sees the extracted routes disappear. The
production entrypoint still works, but the operational blast radius is higher
for health/readiness than it was for legal publication pages.

Underlying assumption: all runtime serving goes through `app.main:app`.

Early warning signs: Docker, Kubernetes, Make, Caddy, or deployment docs point
health/readiness traffic at raw `legacy_app:app`.

Disposition: NOT-A-BUG.

Evidence:

- The PR scope intentionally keeps canonical route registration in `app/main.py`
  and does not preserve raw legacy decorator ownership.
- `docs/deploy/OPERATIONAL_SIGNALS.md` now names `app/routers/health.py` and
  `app/main.py` as the health/readiness source of truth.
- `docs/architecture/LEGACY_COMPATIBILITY_SEAM.md` documents operational
  health/readiness route ownership outside `legacy_app.py`.

## Pre-Merge Checklist

- Focused health/readiness, bootstrap, OpenAPI, and legacy guard tests pass.
- `scripts/ci/check_legacy_growth_guard.py` passes.
- `make validate-changed VENV_PYTHON=.venv/bin/python` passes after branch
  commit creation.
- `pre-commit run --all-files` passes before push.
- PR body records lane start provenance, premortem closure, and Experiment
  Runner oracle evidence.
- Post-open role passes and review governance are completed before any readiness
  claim.
