# Bodyfat Canonical Bootstrap Premortem

Mode: `pr-premortem`

Skill: `pulseplate-premortem-risk-review`

Task packet: `artifacts/orchestration/task_packets/b1f4071b1aa9.json`

## Summary

Plan: move `POST /api/v1/bodyfat` route ownership from `legacy_app.py` to
canonical `app.main` bootstrap without changing bodyfat formulas, schemas,
response shape, auth/tier policy, or generated OpenAPI/client artifacts.

Frame: it is 6 months from now, this cleanup failed, and we are looking
backward to understand why.

## Failure Modes And Closure

### 1. Legacy route ownership returned through a different import shape

Failure story: removing the obvious `get_bodyfat_router()` include would not be
enough if a later edit reintroduced `app.routers.bodyfat.router`, an alias, or a
module-qualified include in `legacy_app.py`. That would quietly restore duplicate
route ownership and make `legacy_app.py` keep growing as a runtime router owner.

Closure: FIXED. `legacy_app.py` no longer imports or includes
`app.routers.bodyfat`, `scripts/ci/check_legacy_growth_guard.py` no longer
allowlists the bodyfat import/registration facts, and
`tests/test_legacy_growth_guard.py` rejects factory, direct, aliased, and
module-qualified bodyfat re-registration.

### 2. Compatibility callers got the wrong prefix

Failure story: canonicalizing the module-level router could break old direct
inclusion callers if `get_router()` started returning `/api/v1/bodyfat` instead
of the historical unprefixed `/bodyfat` route. That would preserve production
runtime while breaking root shim/direct router compatibility tests and utilities.

Closure: FIXED. `app/routers/bodyfat.py` now has a canonical module-level router
for `/api/v1/bodyfat`, while `get_router()` returns a fresh compatibility router
for `/bodyfat`. `tests/test_main_paywall_bootstrap.py` proves `/bodyfat` works
for direct inclusion and `/api/v1/bodyfat` is not created by that adapter.

### 3. OpenAPI visibility drift leaked bodyfat into generated clients

Failure story: moving ownership to `app.main` could make `/api/v1/bodyfat`
appear in the published OpenAPI schema or generated frontend types, even though
the current runtime contract is hidden-but-routable.

Closure: FIXED. The source route keeps `include_in_schema=True` to preserve
source metadata, the final canonical OpenAPI builder continues filtering the
path, and tests cover both bootstrap visibility drift and final OpenAPI hiding.
`VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" make openapi-check DEV_PYTHON="$VENV_PYTHON"`
passed with no generated artifact diff.

### 4. Validation looked green while changed files were not selected

Failure story: `make validate-changed` can report success without selecting
uncommitted branch changes, creating false confidence if focused tests are not
run against the actual changed surface.

Closure: FIXED for this lane. Focused bodyfat/bootstrap/legacy guard/API tests
passed, `pre-commit run --all-files` passed after formatting hook fixes, and
`make validate-changed` will be repeated after commit so the branch diff exists
for the selector.

## Most Likely Failure

The most likely failure was legacy ownership returning in a different import
shape, because the prior allowlist explicitly accepted the bodyfat factory path.

## Most Dangerous Failure

The most dangerous failure was duplicate runtime ownership with hidden OpenAPI
drift: users would still get 200 responses, but route truth and generated
contract truth would diverge.

## Hidden Assumption

The hidden assumption was that deleting the old include was enough. It was not;
the guard needed to shrink so the same route could not come back under another
import spelling.

## Revised Plan

- Keep the canonical `app.main` bootstrap implementation.
- Keep `get_router()` as an unprefixed compatibility adapter.
- Shrink the legacy growth guard allowlist and add bodyfat-specific negative
  tests.
- Record BMI derivation delegation as a separate backlog item instead of
  changing bodyfat math in this PR.

## Pre-Merge Checklist

- Focused bodyfat API and bootstrap tests pass.
- `scripts/ci/check_legacy_growth_guard.py` passes.
- `make openapi-check` passes with repo venv and no generated artifact diff.
- `make validate-changed` is run after commit so branch diff selection is real.
- `pre-commit run --all-files` passes.
- Full local `make verify` remains explicitly deferred per operator CPU
  constraint, with no merge-ready claim.

## Decision

`proceed with changes`: the risky parts are addressed by code, guards, tests,
documentation, and a backlog follow-up for BMI derivation delegation.
