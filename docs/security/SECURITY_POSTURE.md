# Security Posture Notes

## Cloudflare Worker Proxy

- Current posture: the Cloudflare Worker runtime is supported only as a bounded first-party API proxy, not as a generic forward proxy.
- Evidence:
  - `worker.js:1` defines `/api/*`-only path gating, `GET/POST/OPTIONS`-only method scope, explicit `TARGET_BASE` validation, trusted-origin enforcement via `WORKER_ALLOWED_ORIGINS`, bounded forwarded headers, stripping/ignoring spoofable forwarding headers, and `redirect: "manual"`.
  - `tests/test_worker_proxy_contract.py:1` prevents wildcard CORS, redirect-follow behavior, wholesale header cloning, and missing path/origin guardrails from reappearing.

## Bayesian Adherence Endpoints

- Current posture: user identity is derived from the authenticated API key via
  `get_current_user`; request payload/query ownership is not accepted as the
  effective subject for adherence reads or writes.
- Evidence: `tests/test_bayes_adherence_api.py:171` covers `user_id`
  rejection, `tests/test_bayes_adherence_api.py:252` covers API-key state
  isolation, and `tests/security/_api_authz_contracts.py:170` registers the
  adherence routes as PRO, auth-derived-subject routes.
- Remaining follow-up: first-class user-authentication mapping and related
  operational alerting remain tracked in `docs/roadmap/BACKLOG_LEDGER.md`.

## API Auth, Tier, and BOLA Contract Pack

- Declarative posture: sensitive API routes are classified by method/path,
  authentication class, tier, principal source, ownership policy, OpenAPI
  exposure, foreign-object status, and optional executable-oracle identity in
  `tests/security/_api_authz_contracts.py:91`.
- Executable posture: the finite v1 predicate at
  `tests/security/_api_authz_contracts.py:140` currently derives seven
  `AUTHENTICATED_SUBJECT` or `ISSUER_SCOPED` object routes. The literal matrix at
  `tests/security/test_api_bola_cross_principal_matrix.py:566` proves exact
  owner-authorized success, exact foreign-object responses, and zero changes to
  declared authorization-relevant payment or restaurant state. The bound
  request helper derives target method/path from each scenario's `RouteKey`, the
  expected denial status is read from the canonical contract for that same key
  (currently `403` for all seven routes), and the call ledger fails
  callback/route mismatches closed.
- Principal evidence: PRO/VIP routes use two real validated, distinct
  principals after their restaurant issuer mappings are established through
  valid route activity. The manual rail keeps one configured requester key
  unchanged, proves its owned intent returns `200`, and proves the same requester
  receives `403` for a target intent owned by a distinct service issuer.
- Binding evidence: `tests/security/test_api_authz_contract_static.py:168`
  proves the literal registry/scenario bijection and
  `tests/security/test_api_auth_tier_contract_pack.py:182` validates the live
  finite cohort and rejects oracle IDs outside it.
- Related regression evidence:
  `tests/security/test_api_bola_contract_pack.py:49` continues to validate
  nutrition/feedback owner derivation and cross-principal idempotency.
- Scope: this is a contract and regression-test control only. Runtime auth,
  OpenAPI, DB, frontend, and iOS behavior remain unchanged by the contract pack.
- Claim boundary: this evidence covers the frozen finite v1 cohort; it is not a
  universal or "100% BOLA secure" claim. A discovered admission or denied-state
  mutation blocks this carrier and requires a separate prerequisite runtime-fix
  PR.
- Remaining follow-up: first-class authenticated-principal mapping and
  operational principal-mismatch telemetry remain downstream in
  `docs/roadmap/BACKLOG_LEDGER.md`.
