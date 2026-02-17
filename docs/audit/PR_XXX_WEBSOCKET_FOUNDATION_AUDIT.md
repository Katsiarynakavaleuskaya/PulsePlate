# PR-P1: WebSocket Foundation Audit

**Status:** Pre-merge evidence checklist
**Branch:** `feat/p1-secure-websocket-foundation`
**Date:** 2026-02-16

---

## Scope

### IN

- Runtime WebSocket endpoint `/ws` with mandatory auth.
- Server-side guardrails: rate limit, message size limit, event allowlist.
- Deterministic tests: auth reject/accept, rate limit, size limit, event allowlist.
- Audit evidence and DoD checklist.

### OUT

- Frontend and iOS integration.
- Business event expansion beyond `ping -> pong`.
- Legacy app broad refactors.
- Bayesian/CBT/RAG feature expansion.

---

## Architectural Invariants

| INV | Rule | Evidence anchor |
|-----|------|-----------------|
| INV-1 | Route registration is unconditional; feature flag checked at request time | `app/main.py:40`, `app/routers/realtime_ws.py:153` |
| INV-2 | `ws.accept()` runs before any `ws.close()` branch | `app/routers/realtime_ws.py:151` |
| INV-3 | Verifier is not a WS handler argument | `app/routers/realtime_ws.py:150` |
| INV-4 | WebSocket env values are read call-time (no import freeze) | `app/routers/realtime_ws.py:22`, `app/routers/realtime_ws.py:43` |
| INV-5 | `_BurstLimiter` supports injectable clock for deterministic tests | `app/routers/realtime_ws.py:114` |

---

## Contract

### Endpoint

`GET /ws` (WebSocket upgrade)

### Auth

- `Authorization: Bearer <token>` preferred.
- `?token=<value>` fallback.
- Missing token -> close `1008` with `auth_required`.
- Invalid token -> close `1008` with `auth_invalid`.

### Message format

```json
{"type":"<event_type>","payload":{}}
```

### Allowed events (v1)

- `ping` -> `{"type":"pong"}`

### Close codes

| Code | Reason | Trigger |
|------|--------|---------|
| 1008 | `ws_disabled` | `FEATURE_WEBSOCKET_ENABLED != true` |
| 1008 | `auth_required` | token missing |
| 1008 | `auth_invalid` | verifier rejected token |
| 1008 | `payload_too_large` | message bytes > policy limit |
| 1008 | `rate_limited` | burst over policy window |
| 1008 | `invalid_json` | non-JSON or non-object message |
| 1008 | `event_type_not_allowed` | event type not on allowlist |

### Policy defaults

| Variable | Default |
|----------|---------|
| `FEATURE_WEBSOCKET_ENABLED` | `false` |
| `WS_MAX_MESSAGE_BYTES` | `4096` |
| `WS_WINDOW_SECONDS` | `10` |
| `WS_MAX_MESSAGES_PER_WINDOW` | `20` |

---

## Evidence Commands

```bash
pytest -q tests/test_websocket_burst_limiter_unit.py -v
pytest -q tests/test_websocket_security_api.py -v
rg -n 'websocket\("/ws"\)|\.websocket\("/ws"\)' app tests
rg -n 'FEATURE_WEBSOCKET_ENABLED|WS_MAX_MESSAGE_BYTES|WS_WINDOW_SECONDS|WS_MAX_MESSAGES_PER_WINDOW' app/routers/realtime_ws.py
pre-commit run --all-files
make verify
```

---

## DoD Checklist

- [ ] `/ws` endpoint exists and is authenticated.
- [ ] Unauthenticated access is fail-closed.
- [ ] Deterministic limiter tests pass.
- [ ] Deterministic websocket security tests pass.
- [ ] No runtime scope expansion beyond `/ws` foundation.
- [ ] `pre-commit run --all-files` passes.
- [ ] `make verify` passes.
