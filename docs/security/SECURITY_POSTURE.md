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
  isolation, and `tests/security/_api_authz_contracts.py:144` registers the
  adherence routes as PRO, auth-derived-subject routes.
- Remaining follow-up: first-class user-authentication mapping and related
  operational alerting remain tracked in `docs/roadmap/BACKLOG_LEDGER.md`.

## API Auth, Tier, and BOLA Contract Pack

- Current posture: sensitive API routes are classified by method/path,
  authentication class, tier, principal source, ownership policy, and OpenAPI
  exposure in `tests/security/_api_authz_contracts.py`.
- Evidence: `tests/security/test_api_auth_tier_contract_pack.py:32` validates
  live route classification, `tests/security/test_api_auth_tier_contract_pack.py:81`
  validates dependency drift, and `tests/security/test_api_bola_contract_pack.py:49`
  validates nutrition/feedback owner derivation plus cross-principal
  idempotency.
- Scope: this is a contract and regression-test control only. Runtime auth,
  OpenAPI, DB, frontend, and iOS behavior remain unchanged by the contract pack.
