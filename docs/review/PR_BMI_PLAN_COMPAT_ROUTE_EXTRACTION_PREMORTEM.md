# BMI/Plan Compatibility Route Extraction Premortem

Date: 2026-06-15

Task packet: `artifacts/orchestration/task_packets/af6261186dc5.json`

Branch: `codex/extract-bmi-plan-compat-routes-from-legacy`

Mode: `pr-premortem`

## Summary

Plan: extract `POST /bmi`, `POST /plan`, and `POST /api/v1/bmi` from
`legacy_app.py` into canonical BMI compatibility route ownership while
preserving request validation, response shape, OpenAPI visibility, and legacy
growth guard shrink.

Failure frame: six months from now, the extraction looked like a small legacy
shrink but changed the public BMI compatibility contract or made legacy route
ownership easy to reintroduce.

Decision: proceed with changes. All premortem findings below are fixed or
dispositioned in the current PR diff before PR open.

## Findings And Closure

### PM-BMI-COMPAT-001: Compatibility routes duplicate or shadow each other

Failure story: the new compat router is registered while legacy decorators are
still active. FastAPI retains multiple `POST` handlers for `/bmi`, `/plan`, or
`/api/v1/bmi`, and route order decides which handler production serves.

Underlying assumption: deleting code from `legacy_app.py` and adding a router
cannot create a mixed ownership state.

Early warning signs: more than one `POST` route exists for any extracted path,
or a route endpoint module is still `legacy_app`.

Disposition: FIXED.

Evidence:

- `legacy_app.py` retains only direct-call shims for `bmi_endpoint`,
  `plan_endpoint`, and `bmi_endpoint_v1`; the three `@app.post(...)`
  decorators are removed.
- `app/main.py` registers the BMI compatibility route family atomically and
  fails closed on partial state, wrong methods, duplicate paths, or foreign
  handlers.
- `tests/test_bmi_compat_router.py` asserts exactly one `POST` route for each
  extracted path and verifies ownership by `app.routers.bmi_compat`.
- `tests/test_main_paywall_bootstrap.py` covers idempotent bootstrap plus
  partial, wrong-method, foreign-handler, visibility-drift, and duplicate-router
  failures.

### PM-BMI-COMPAT-002: `/bmi` or `/plan` leaks into public OpenAPI

Failure story: moving the compatibility endpoints into a canonical router makes
`/bmi` and `/plan` appear in generated OpenAPI. Clients then treat legacy
compatibility routes as public contract truth, adding generated schema churn and
making later shim removal harder.

Underlying assumption: OpenAPI filtering will keep behaving the same after route
ownership moves.

Early warning signs: `/bmi` or `/plan` appears in `app.openapi()["paths"]`, or
`frontend/src/api/openapi.json` changes for those paths.

Disposition: FIXED.

Evidence:

- `app/routers/bmi_compat.py` registers `/bmi` and `/plan` with
  `include_in_schema=False`.
- `app/main.py` rejects BMI compatibility routers or existing canonical handlers
  that do not preserve expected OpenAPI visibility.
- `tests/test_bmi_compat_router.py`,
  `tests/test_openapi_namespace_guards.py`, and
  `tests/test_app_openapi_coverage.py` assert `/bmi` and `/plan` remain absent
  from public OpenAPI.
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH make openapi-check`
  passed and reported no generated OpenAPI/client diff.

### PM-BMI-COMPAT-003: `/api/v1/bmi` OpenAPI contract drifts

Failure story: the public compatibility route keeps working at runtime but its
OpenAPI operation id, request schema component, description, or visibility
changes. Generated clients and schema guards then see a contract change for a
route this PR intended to preserve.

Underlying assumption: moving the endpoint function to a new router preserves
OpenAPI output automatically.

Early warning signs: `/api/v1/bmi` operation id differs from
`bmi_endpoint_v1_api_v1_bmi_post`, or the request body no longer references
`#/components/schemas/BMIRequestV1`.

Disposition: FIXED.

Evidence:

- `app/routers/bmi_compat.py` preserves the endpoint function name
  `bmi_endpoint_v1` and request model `BMIRequestV1`.
- `tests/test_bmi_compat_router.py` asserts the operation id and
  `BMIRequestV1` request schema ref.
- Focused OpenAPI inspection after the diff confirmed `/api/v1/bmi` remains
  visible with operation id `bmi_endpoint_v1_api_v1_bmi_post` and
  `#/components/schemas/BMIRequestV1`.

### PM-BMI-COMPAT-004: Legacy request normalization is lost

Failure story: the extracted router accepts only canonical BMI request shapes.
Older clients using `height`, `height_cm`, `sex`, string booleans,
pregnancy/athlete synonyms, or `with_visualization` start receiving validation
errors even though the endpoint paths still exist.

Underlying assumption: canonical `BMICalculateRequest` can replace legacy
compatibility schemas directly.

Early warning signs: tests that validate `BMIRequest` normalization fail, or
`/bmi` no longer accepts legacy payload aliases.

Disposition: FIXED.

Evidence:

- `app/schemas/bmi_compat.py` owns `BMIRequest` and `BMIRequestV1` with the
  legacy normalization and validation behavior moved out of `legacy_app.py`.
- `legacy_app.py` re-exports `BMIRequest`, `BMIRequestV1`, and
  `add_visualization_if_requested` for direct import compatibility.
- `tests/test_legacy_bmi_shims.py`,
  `tests/test_plan_contract_regression.py`, and
  `tests/test_app_public_surface.py` passed after extraction.

### PM-BMI-COMPAT-005: Public/no-auth posture changes

Failure story: the compatibility routes accidentally inherit API key,
subscription, billing, quota, or VIP dependencies during router extraction.
Previously public BMI compatibility clients start receiving `403` responses or
entitlement failures.

Underlying assumption: moving to canonical bootstrap does not affect dependency
posture.

Early warning signs: bad or missing API key headers change successful BMI
compatibility requests into authorization failures.

Disposition: FIXED.

Evidence:

- `app/routers/bmi_compat.py` declares no auth, tier, quota, or billing
  dependencies.
- `tests/test_bmi_compat_router.py` asserts `/api/v1/bmi` remains public even
  with a bad API key header.
- `tests/edges/test_app_branches.py` passed in the focused security regression
  slice.

### PM-BMI-COMPAT-006: Legacy seam guard still allows BMI ownership to return

Failure story: the decorators are removed from `legacy_app.py`, but the growth
guard still allowlists them. A later PR can reintroduce BMI compatibility
decorators in legacy while the guard remains green.

Underlying assumption: route extraction is durable once the source code moves.

Early warning signs: `scripts/ci/check_legacy_growth_guard.py` still contains
allowed decorator facts for `/bmi`, `/plan`, or `/api/v1/bmi`.

Disposition: FIXED.

Evidence:

- `scripts/ci/check_legacy_growth_guard.py` removes only the three BMI/plan
  decorator facts from the legacy allowlist.
- `tests/test_legacy_growth_guard.py` rejects reintroduced `/bmi`, `/plan`, and
  `/api/v1/bmi` decorators.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/ci/check_legacy_growth_guard.py`
  passed.

### PM-BMI-COMPAT-007: Raw `legacy_app:app` serving loses route decorators

Failure story: an operator serves raw `legacy_app:app` directly instead of the
canonical `app.main:app` entrypoint and expects the extracted routes to remain
registered there. The canonical app still works, but raw legacy direct serving
has less route ownership than before.

Underlying assumption: compatibility requires raw `legacy_app.py` to own every
historic route decorator indefinitely.

Early warning signs: deployment docs or runtime commands point BMI traffic at
raw `legacy_app:app` instead of `app.main:app`.

Disposition: NOT-A-BUG.

Evidence:

- Repository architecture already treats `app/main.py` as the canonical FastAPI
  entrypoint and `legacy_app.py` as a shrinking compatibility seam.
- This PR intentionally preserves `legacy_app.py` direct-call/import shims while
  moving runtime route registration to canonical bootstrap.
- `tests/conftest.py` documents that test clients use `app.main:app`, not raw
  `legacy_app.app`.

## Pre-Merge Checklist

- Focused BMI compatibility, `/plan`, OpenAPI, bootstrap, public-surface, and
  legacy-growth tests pass.
- `scripts/ci/check_legacy_growth_guard.py` passes.
- `make openapi-check` passes with the repo-root virtualenv on `PATH` and
  generated OpenAPI/client artifacts remain unchanged.
- `make validate-changed` passes after branch commit creation.
- `pre-commit run --all-files` passes with no hook modifications.
- PR body records lane start provenance, premortem closure, Experiment Runner
  oracle evidence, and operator-approved local full-verify deferral.
- Post-open role passes, Codex Security diff scan, `pulseplate-pr-review`, bot
  review disposition, current-head CI, and merge-readiness checks complete
  before any readiness claim.
