# Legacy Premium Weekly-Plan Route Extraction Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Frame: It is 6 months after merge. This route extraction failed. We are looking
backward to understand why.

## Summary

Plan: move hidden legacy `POST /api/v1/premium/plan/week` route ownership from
`legacy_app.py` to `app/routers/legacy_premium_weekly_plan.py` while preserving
legacy API-key auth, VIP feature gating, canonical VIP delegation, hidden
OpenAPI visibility, and current error envelopes.

Success means one registered runtime owner, unchanged alias behavior, no
`/week-flexible` absorption, and a growth guard that rejects reintroduced
`legacy_app.py` decorators.

## Findings And Closure

### 1. Duplicate Route Ownership Reappeared

Failure story: The new router was registered but the old `@app.post` owner stayed
in `legacy_app.py`. FastAPI selected one handler depending on registration order,
tests passed against the convenient owner, and the app carried two different
behavior surfaces for the same method/path.

Underlying assumption: route movement is complete once the new router exists.

Early warning signs: route table shows more than one `POST
/api/v1/premium/plan/week`; endpoint module is not
`app.routers.legacy_premium_weekly_plan`.

Containment action: block merge and remove the extra owner.

Disposition: FIXED. The legacy decorator/function block was removed from
`legacy_app.py`, the new router owns `api_weekly_menu`, and
`tests/test_legacy_premium_weekly_plan_registration_bootstrap.py` asserts exact
single-owner registration, idempotency, duplicate rejection, and foreign-handler
rejection.

### 2. Auth Semantics Drifted From Legacy Credential To Paid-Tier Guard

Failure story: During cleanup the alias was "modernized" to use PRO/VIP tier
dependencies instead of `_get_api_key_dynamic`. Existing legacy API-key clients
started receiving entitlement failures even though the route contract classifies
the alias as legacy credential compatibility.

Underlying assumption: a VIP-backed alias should use VIP auth middleware.

Early warning signs: route dependencies no longer include `_get_api_key_dynamic`;
`tests/security/_api_authz_contracts.py` no longer matches runtime behavior.

Containment action: restore the legacy dependency and keep any paid-tier
redesign for a separate migration PR.

Disposition: FIXED. The new route keeps
`dependencies=[Depends(_get_api_key_dynamic)]`, `app/main.py` requires that
dependency in the `RouteMemberContract`, and the new bootstrap test verifies
missing/invalid API keys return 403 while the valid key reaches the VIP gate.

### 3. Hidden Alias Leaked Into OpenAPI Or Generated Clients

Failure story: The route moved into a regular router and accidentally defaulted
to `include_in_schema=True`. Generated clients started seeing a deprecated hidden
compatibility endpoint as if it were a supported API surface.

Underlying assumption: router extraction does not affect OpenAPI visibility.

Early warning signs: `/api/v1/premium/plan/week` appears in dynamic OpenAPI or
generated frontend schema diffs.

Containment action: restore `include_in_schema=False`, regenerate OpenAPI, and
verify no generated artifact drift.

Disposition: FIXED. The new router source route is hidden, the route-family
member contract requires hidden visibility, the bootstrap test rejects visibility
drift, `tests/test_app_openapi_coverage.py` covers the hidden path, and
`make openapi-check` plus generated-artifact diff check passed with repo Python.

### 4. `/week-flexible` Or PRO Weekly Logic Was Accidentally Absorbed

Failure story: The new family was named too broadly and began registering or
testing `/api/v1/premium/plan/week-flexible` together with the legacy weekly
alias. That mixed legacy credential behavior with the PRO bridge and made
authz/debugging ambiguous.

Underlying assumption: all premium weekly routes belong in one extraction.

Early warning signs: new route spec has more than one member; tests mention
`premium_week.py` behavior changes; PRO parity tests change.

Containment action: split the scope back to one method/path and leave
`/week-flexible` untouched.

Disposition: FIXED. `LEGACY_PREMIUM_WEEKLY_PLAN_ROUTE_SPECS` has exactly one
member, the new bootstrap test asserts `/week-flexible` and
`/api/v1/pro/meal/weekly` are not absorbed, and no `premium_week.py` code changed.

### 5. Legacy Growth Guard Became A False Negative

Failure story: The route moved, but the old allowlist entry stayed in
`check_legacy_growth_guard.py`. A later PR could reintroduce the legacy decorator
without failing the guard, undoing the extraction.

Underlying assumption: removing the decorator is enough; governance allowlists
do not need to shrink with route ownership.

Early warning signs: `ALLOWED_LEGACY_ROUTE_FACTS` still contains
`/api/v1/premium/plan/week`.

Containment action: remove the allowlist entry and add a regression proving the
decorator is rejected.

Disposition: FIXED. The allowlist entry was removed, and
`tests/test_legacy_growth_guard.py` now rejects a reintroduced
`api_weekly_menu` decorator.

## Most Likely Failure

The most likely failure was stale test/direct-call ownership pointing at
`legacy_app.api_weekly_menu`. That was addressed by updating current direct-call
coverage to call `app.routers.legacy_premium_weekly_plan.api_weekly_menu`.

## Most Dangerous Failure

The most dangerous failure was auth semantic drift away from the legacy API-key
contract, because it could break existing compatibility clients or fail open/closed
in a way reviewers miss. This is covered by route dependency assertions, a
behavior test for invalid/valid API keys, and unchanged authz contract metadata.

## Hidden Assumption

The hidden assumption was that route extraction is only a file move. In this
repo, a route extraction also has governance state: bootstrap registration,
OpenAPI hiding, auth contract preservation, direct-call tests, and growth-guard
shrinkage all have to move together.

## Revised Plan

- Keep the new router as the only handler owner.
- Keep legacy models/helpers in `legacy_app.py` for this PR only.
- Require `_get_api_key_dynamic` in both source route metadata and
  `RouteMemberContract`.
- Use exact one-member route specs and reject duplicate, foreign, partial,
  missing-dependency, and visibility-drift registrations.
- Keep `/week-flexible` and PRO weekly routes out of this diff.

## Pre-Merge Checklist

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- Focused weekly-plan registration, alias, growth-guard, OpenAPI, premium-week,
  and auth contract tests
- `python3 scripts/ci/check_legacy_growth_guard.py`
- `make openapi-check`
- `make validate-changed`
- `pre-commit run --all-files`
- Current-head GitHub CI and post-open review chain before readiness claims

## Decision

Proceed with changes. The real failure modes are closed in code, tests,
governance guard updates, and validation evidence; merge readiness still depends
on current-head CI, post-open role/security review, bot dispositions, and strict
merge-readiness checks.
