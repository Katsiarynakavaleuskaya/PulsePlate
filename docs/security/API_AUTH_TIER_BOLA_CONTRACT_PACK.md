# API Auth, Tier, and BOLA Contract Pack

## Purpose

This contract pack records the current security boundary for authenticated API
routes without changing runtime behavior. It is a tests/docs control for PR-3 in
the legacy and architecture cleanup sequence.

## Contract Surface

The source of truth for the test registry is
`tests/security/_api_authz_contracts.py`. Each sensitive route is classified by:

- method and path;
- authentication class;
- minimum tier;
- principal source;
- ownership policy;
- OpenAPI exposure;
- foreign-object negative status when the route accepts an object identifier.

Sensitive route discovery is dependency- and shape-driven: routes are included
when they belong to known paid/auth families, use known auth dependencies, are
hidden mutating routes, or expose path-parameter object identifiers. The
registry is method-and-path based because the live router table can contain
duplicate registrations for the same path, including VIP shoplist routes. A new
sensitive route must be added to the registry before the contract test passes.

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
- Nutrition and feedback ownership tests assert persisted owner fields come from
  the authenticated subject, not from ignored payload fields.

## Related Standards

This pack maps to OWASP API Security concerns around broken object-level
authorization, broken authentication, and broken function-level authorization.
It also supports ASVS-style controls for authenticated subject derivation and
fail-closed route authorization checks. The pack is evidence of current
contract coverage, not a medical, diagnostic, treatment, or user-safety claim.

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

If a contract test exposes a real authorization bypass, that failure must be
split into a separate runtime fix PR instead of being silently fixed inside the
contract-pack PR.
