# Authenticated Principal Mapping Premortem

## Scope

This pre-open premortem covers the docs/tests-only diff for the authenticated
principal mapping contract. It does not cover a runtime auth rewrite, DB
migration, route extraction, dependency update, OpenAPI/client change, Docker
change, or runtime alerting implementation.

Lane provenance:

- Packet: `artifacts/orchestration/task_packets/a0d678a19b80.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/auth-principal-mapping-contract`

## How This Diff Could Make Main Worse Within 48 Hours

### R1: The PR is mistaken for complete object-authorization coverage

Failure story: reviewers or later agents treat the new contract document as full
object-authorization coverage, then skip object-level authorization tests for
new object-id routes. A client-controlled object ID could later enter a route
with no negative ownership case because the current PR sounded broader than it
is.

Closure: the contract says it records current principal mapping only, and
explicitly states it does not complete BOLA. Existing BOLA coverage remains in
`tests/security/test_api_bola_contract_pack.py`; future object authorization
matrix work remains separate.

Disposition: FIXED in docs/tests by scope wording and no-overclaim checks.

### R2: Runtime alerting is represented as implemented

Failure story: the PR documents future alert labels and an operator assumes
production emits `auth_principal_mismatch` or `object_owner_mismatch`. A real
cross-subject probing incident could be missed because the docs overstated
runtime telemetry.

Closure: `docs/security/AUTHENTICATED_PRINCIPAL_MAPPING.md` states that alert
labels are a future observability contract only and that this PR does not emit
production telemetry, runtime alerts, metrics, or logs.

Disposition: FIXED in docs/tests by future-only alert wording and no-overclaim
checks.

### R3: Manual billing transport is confused with paid entitlement

Failure story: a later change sees manual RU/BY billing routes in the same auth
contract and uses PRO/VIP tier keys as manual transport credentials, or treats a
manual billing intent as paid-route entitlement before backend persistence.

Closure: the new tests require manual billing contract routes to stay
`BILLING_ISSUER` + `ISSUER_SCOPED`, and require the manual billing validator to
stay on `validate_app_api_key` rather than tier validators.

Disposition: FIXED in tests.

### R4: Legacy aliases become weaker than canonical paid routes

Failure story: a deprecated paid alias keeps a stale auth class while the
canonical route requires PRO/VIP subject ownership. A user denied by the
canonical path could succeed through a compatibility alias.

Closure: representative legacy/canonical parity test keeps
`/api/v1/premium/plan/week-flexible` aligned with the canonical PRO weekly-plan
route on tier, principal source, and ownership policy.

Disposition: FIXED in tests for representative parity. Full alias matrix remains
owned by the existing auth/tier/BOLA contract pack and future route extraction
work.

### R5: Contract docs accidentally become a new runtime auth model

Failure story: a future PR imports or implements against the document as if
`CurrentUser` were a general user-auth account model or as if the derived
subject were `users.id`.

Closure: the new contract documents `derive_subject_id_from_api_key` as a
temporary API-key-derived subject principal, not `users.id` and not
first-class user authentication. The backlog follow-up remains open at
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-first-class-auth-principal-mapping`.

Disposition: FIXED in docs/tests by terminology and scope-boundary checks.

## Stop Conditions

Stop and split a separate runtime fix if focused tests reveal a real auth bypass
or if the implementation needs to touch runtime auth, dependencies, OpenAPI,
clients, DB migrations, Docker, private proxy, or route registration.
