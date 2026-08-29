# API Auth, Tier, and BOLA Contract Pack

## Purpose

This contract pack records the current security boundary for authenticated API
routes without changing runtime behavior. It combines a declarative route
inventory with a finite executable BOLA evidence matrix.

## Contract Surface

The source of truth for the test registry is
`tests/security/_api_authz_contracts.py:91`. Each sensitive route is classified by:

- method and path;
- authentication class;
- minimum tier;
- principal source;
- ownership policy;
- OpenAPI exposure;
- foreign-object negative status when the route accepts an object identifier;
- one `bola_oracle_id` when the route belongs to the finite BOLA v1 universe.

The finite v1 eligibility predicate is defined once at
`tests/security/_api_authz_contracts.py:140`: a contract is eligible when
`foreign_object_status` is present and `ownership_policy` is either
`AUTHENTICATED_SUBJECT` or `ISSUER_SCOPED`. The current base census is seven
routes and every route has exact foreign-principal status `403`. The count is
derived from the registry rather than frozen as a permanent assertion.

Sensitive route discovery is dependency- and shape-driven: routes are included
when they belong to known paid/auth families, use known auth dependencies, are
hidden mutating routes, or expose path-parameter object identifiers. The
registry is method-and-path based because the live router table can contain
duplicate registrations for the same path, including VIP shoplist routes. A new
sensitive route must be added to the registry before the contract test passes.

Executable evidence is bound through the literal `BOLA_SCENARIOS` tuple at
`tests/security/test_api_bola_cross_principal_matrix.py:559`. The existing
finite AST recognizer proves the contract/scenario bijection at
`tests/security/test_api_authz_contract_static.py:168`, while the live contract
pack rejects missing, duplicate, or out-of-cohort IDs at
`tests/security/test_api_auth_tier_contract_pack.py:182`.

Each executable scenario:

1. creates or seeds an owned object and uses a real validated requester;
2. proves the exact owner-authorized route operation succeeds;
3. snapshots the declared authorization-relevant object state;
4. calls the same scenario-bound route against a foreign-owned object, using a
   second valid principal for PRO/VIP routes or the one unchanged configured
   requester for the manual rail;
5. asserts the exact denial status and JSON envelope;
6. proves the complete declared state is byte-for-value unchanged.

The target operation method and path are derived only from the scenario's
`RouteKey` by the bound request helper. The execution guard requires exactly one
owner call and one foreign-object call recorded against that same key; an
executor/callback mismatch or an executor that ignores the helper fails closed.

For the manual rail, the configured requester key is never rotated: one owned
intent proves `200`, a distinct valid service issuer owns the target intent, and
the unchanged requester receives exact `403` for that target. Payment snapshots
serialize every column of every `Subscription` and
`SubscriptionActivationAudit` row using fresh sessions
(`tests/security/test_api_bola_cross_principal_matrix.py:109`). Restaurant
snapshots deep-copy the router issuer map plus orders, create events, confirm
events, and shares under their owning locks
(`tests/security/test_api_bola_cross_principal_matrix.py:136`). Both PRO and VIP
issuer mappings are established through valid route activity and proved
distinct before the denied snapshot, so lazy cache insertion cannot be mistaken
for a denied-operation side effect.
Mutating scenarios use separate authorized controls and denied targets, so the
control mutation cannot hide a denied-target side effect.

Additional evidence anchors:

- Registry: `tests/security/_api_authz_contracts.py:169`
- Sensitive-route discovery: `tests/security/_api_authz_contracts.py:796`
- Auth dependency matching: `tests/security/_api_authz_contracts.py:817`
- Inventory invariants: `tests/security/test_api_auth_tier_contract_pack.py:50`
- Dependency guard invariant: `tests/security/test_api_auth_tier_contract_pack.py:124`
- Object ownership invariant:
  `tests/security/test_api_auth_tier_contract_pack.py:147`
- Foreign-object status invariant:
  `tests/security/test_api_auth_tier_contract_pack.py:161`
- Same-principal, exact-denial, and zero-side-effect execution:
  `tests/security/test_api_bola_cross_principal_matrix.py:270` and
  `tests/security/test_api_bola_cross_principal_matrix.py:623`
- BOLA/idempotency regressions:
  `tests/security/test_api_bola_contract_pack.py:49`,
  `tests/security/test_api_bola_contract_pack.py:86`, and
  `tests/security/test_api_bola_contract_pack.py:124`

## Security Guarantees

- Canonical PRO and VIP routes retain `require_pro_tier` or `require_vip_tier`
  unless they are documented pre-entitlement or deprecated-alias exceptions.
- Pre-entitlement billing routes are explicit exceptions and remain separated
  from canonical paid-tier route requirements.
- Hidden runtime routes stay hidden from public OpenAPI.
- Hidden mutating compatibility routes are classified even when they do not yet
  have a FastAPI dependency graph.
- Routes with object identifiers cannot use an empty ownership policy.
- Subject-owned object routes document the expected foreign-object status so
  BOLA negative coverage remains visible.
- Every finite v1 eligible object route is bound to exactly one literal
  executable oracle, and non-eligible contracts cannot carry an oracle ID.
- Each v1 oracle proves an owner-authorized success and an exact foreign-object
  denial. PRO/VIP routes use a second validated principal; the manual rail uses
  one unchanged validated requester against a separately service-owned target.
  Both shapes prove zero changes to the scenario's declared
  authorization-relevant subscription/audit or restaurant state, including the
  restaurant issuer map.
- Nutrition and feedback ownership tests assert persisted owner fields come from
  the authenticated subject, not from ignored payload fields.

## Related Standards

This pack maps to OWASP API Security concerns around broken object-level
authorization, broken authentication, and broken function-level authorization.
It also supports ASVS-style controls for authenticated subject derivation and
fail-closed route authorization checks. This is evidence for the frozen finite
v1 route universe, not a claim that the application is universally or "100%"
BOLA-secure, and not a medical, diagnostic, treatment, or user-safety claim.

## Scope Boundaries

In scope:

- tests under `tests/security/`;
- shared test helper reuse for FastAPI dependency graph inspection;
- docs describing the current contract and deferred authentication follow-ups.

Out of scope:

- runtime auth or tier implementation changes;
- OpenAPI or generated client changes;
- database migrations;
- frontend or iOS behavior;
- route movement or legacy route removal.
- first-class authenticated-principal mapping or mismatch telemetry.

If a contract test exposes a real authorization bypass, that failure must be
split into a separate runtime fix PR instead of being silently fixed inside the
contract-pack PR.
