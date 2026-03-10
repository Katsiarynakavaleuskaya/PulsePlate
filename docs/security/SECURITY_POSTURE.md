# Security Posture Notes

## Cloudflare Worker Proxy

- Current posture: the Cloudflare Worker runtime is supported only as a bounded first-party API proxy, not as a generic forward proxy.
- Evidence:
  - `worker.js:1` defines `/api/*`-only path gating, `GET/POST/OPTIONS`-only method scope, explicit `TARGET_BASE` validation, trusted-origin enforcement via `WORKER_ALLOWED_ORIGINS`, bounded forwarded headers, preserved client-IP headers for backend rate limiting, and `redirect: "manual"`.
  - `tests/test_worker_proxy_contract.py:1` prevents wildcard CORS, redirect-follow behavior, wholesale header cloning, and missing path/origin guardrails from reappearing.

## Bayesian Adherence Endpoints

- Current posture: user identity is derived from the authenticated API key via `get_current_user`,
  and request payloads forbid `user_id` to prevent horizontal privilege escalation.
- Planned remediation timeline (SEC-001): implement per-API-key rate limiting, logging/alerting,
  and full user authentication mapping by 2026-Q1 (deferred pending subscription DB).
