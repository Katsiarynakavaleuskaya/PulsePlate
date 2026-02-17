# PR-P1: WebSocket Foundation Work-Package Plan

<!-- markdownlint-disable MD013 -->

**Status:** Planned for implementation in a single runtime PR
**Branch:** `feat/ws-foundation-workpackage`
**Date:** 2026-02-16

---

## Scope

### IN

- Secure WebSocket foundation endpoint at `/ws`.
- Canonical registration in `app/main.py` with duplicate-path fail-fast guard.
- Mandatory auth via existing PRO verification path (`require_pro_tier` adapter).
- Deterministic server-side guardrails:
  - message size cap
  - sliding-window burst limiter
  - strict event allowlist (`ping` -> `pong`)
- Deterministic tests for auth, rate limiting, payload size, invalid payloads, and registration guard.
- Audit and backlog tracking in the same PR.

### OUT

- Frontend/iOS websocket consumers.
- New business events beyond `ping`.
- Pub/sub rooms, fan-out, or broker-backed delivery.
- LLM/RAG/CBT logic over websocket transport.

---

## Architecture Decisions

1. **Single registration point**
   - Register websocket router only in `app/main.py`.
   - Fail fast on duplicate `/ws` route to avoid shadowed behavior.

2. **Fail-closed auth**
   - Endpoint accepts connection and then performs strict auth checks.
   - Missing or invalid token closes with policy code `1008`.

3. **Deterministic policy loading**
   - Read feature flags and policy env vars at request time (no import-time freeze).
   - Keep tests deterministic with `monkeypatch.setenv`.

4. **Minimal event surface**
   - Allow only `ping` in foundation phase.
   - Reject unknown event types with policy close.

---

## Test Plan

### Required tests

- `tests/test_main_ws_registration_guard.py`
  - duplicate `/ws` path raises runtime guard
  - no duplicate route passes
- `tests/test_websocket_security_api.py`
  - websocket disabled path
  - missing/invalid token rejection
  - valid token (`Authorization` and query fallback) acceptance
  - oversized payload rejection
  - rate-limit rejection after configured burst
  - invalid JSON / non-object JSON / unsupported event / binary frame rejection
- `tests/test_websocket_burst_limiter_unit.py`
  - max boundary
  - full-window reset
  - sliding-window behavior
  - exact-boundary behavior
  - per-connection limiter isolation

### Verification commands

```bash
pytest -q tests/test_main_ws_registration_guard.py
pytest -q tests/test_websocket_burst_limiter_unit.py
pytest -q tests/test_websocket_security_api.py
pytest -q tests/test_repo_policy_guards.py
make test-fast
make verify
pre-commit run --all-files
```

---

## Risk Register

- **Risk:** auth bypass due to unguarded websocket surface
  **Mitigation:** fail-closed auth checks + explicit reject-path tests.

- **Risk:** abuse through frame flooding
  **Mitigation:** deterministic sliding-window limiter + burst tests.

- **Risk:** route drift / accidental duplicate mounts
  **Mitigation:** startup guard in `app/main.py` + dedicated guard test.

---

## Definition of Done

- `/ws` exists in canonical app entrypoint and is protected by auth.
- Policy rejections are deterministic and covered by tests.
- No scope creep beyond websocket foundation transport.
- Audit updated and linked.
- Deferred follow-ups tracked in `docs/roadmap/BACKLOG_LEDGER.md`.
- `make verify` and `pre-commit run --all-files` are green.
