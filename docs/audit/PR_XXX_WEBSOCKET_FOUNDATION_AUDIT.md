# PR-P1: WebSocket Foundation Audit

<!-- markdownlint-disable MD013 -->

**Status:** Pre-merge evidence checklist
**Branch:** `feat/ws-foundation-workpackage`
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
| ----- | ------ | ----------------- |
| INV-1 | Route registration is unconditional; feature flag checked at request time | `app/main.py:36`, `app/routers/realtime_ws.py:173`, `app/routers/realtime_ws.py:178` |
| INV-2 | `ws.accept()` runs before any `ws.close()` branch | `app/routers/realtime_ws.py:176` |
| INV-3 | Verifier is not a WS handler argument | `app/routers/realtime_ws.py:174` |
| INV-4 | WebSocket env values are read call-time (no import freeze) | `app/routers/realtime_ws.py:33`, `app/routers/realtime_ws.py:54` |
| INV-5 | `_BurstLimiter` supports injectable clock for deterministic tests | `app/routers/realtime_ws.py:136`, `app/routers/realtime_ws.py:140` |

---

## Contract

### Endpoint

`GET /ws` (WebSocket upgrade)

Evidence: `app/routers/realtime_ws.py:173-176`

### Auth

- `Authorization: Bearer <token>` preferred.
- `?token=<value>` fallback.
- Missing token -> close `1008` with `auth_required`.
- Invalid token -> close `1008` with `auth_invalid`.

Evidence: `app/routers/realtime_ws.py:102-112`, `app/routers/realtime_ws.py:115-130`, `app/routers/realtime_ws.py:83-99`

### Message format

```json
{"type":"<event_type>","payload":{}}
```

Evidence: `app/routers/realtime_ws.py:165-170`, `app/routers/realtime_ws.py:214-224`

### Allowed events (v1)

- `ping` -> `{"type":"pong"}`

Evidence: `app/routers/realtime_ws.py:226-227`

### Close codes

| Code | Reason | Trigger | Evidence |
| ------ | -------- | --------- | ---------- |
| 1008 | `ws_disabled` | `FEATURE_WEBSOCKET_ENABLED != true` | `app/routers/realtime_ws.py:178-181` |
| 1008 | `auth_required` | token missing | `app/routers/realtime_ws.py:118-121` |
| 1008 | `auth_invalid` | verifier rejected token | `app/routers/realtime_ws.py:127-130` |
| 1008 | `payload_too_large` | message bytes > policy limit | `app/routers/realtime_ws.py:204-207` |
| 1008 | `rate_limited` | burst over policy window | `app/routers/realtime_ws.py:209-212` |
| 1008 | `invalid_json` | non-JSON or non-object message | `app/routers/realtime_ws.py:215-218` |
| 1008 | `event_type_not_allowed` | event type not on allowlist | `app/routers/realtime_ws.py:221-224` |
| 1008 | `text_frame_required` | non-text frame received | `app/routers/realtime_ws.py:199-202` |

### Policy defaults

| Variable | Default |
| ---------- | --------- |
| `FEATURE_WEBSOCKET_ENABLED` | `false` |
| `WS_MAX_MESSAGE_BYTES` | `4096` |
| `WS_WINDOW_SECONDS` | `10` |
| `WS_MAX_MESSAGES_PER_WINDOW` | `20` |

Evidence: `app/routers/realtime_ws.py:18-30`, `app/routers/realtime_ws.py:41`, `app/routers/realtime_ws.py:68-72`

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

## Plan and Follow-ups

- Work-package plan: `docs/plan/PR_XXX_WEBSOCKET_FOUNDATION_PLAN.md`
- Deferred follow-ups: `docs/roadmap/BACKLOG_LEDGER.md` (WebSocket realtime expansion item)

---

## DoD Checklist

- [ ] `/ws` endpoint exists and is authenticated.
- [ ] Unauthenticated access is fail-closed.
- [ ] Deterministic limiter tests pass.
- [ ] Deterministic websocket security tests pass.
- [ ] No runtime scope expansion beyond `/ws` foundation.
- [ ] `pre-commit run --all-files` passes.
- [ ] `make verify` passes.
