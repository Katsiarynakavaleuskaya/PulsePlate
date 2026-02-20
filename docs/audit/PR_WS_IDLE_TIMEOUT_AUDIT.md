# PR-P1: WebSocket Idle Timeout Audit

<!-- markdownlint-disable MD013 -->

**Status:** In progress (runtime work-package)
**Branch:** `feat/ws-idle-timeout-pr`
**Date:** 2026-02-16

---

## Scope Validation

### IN

- Idle-timeout policy for existing `/ws` endpoint.
- Deterministic timeout enforcement and tests.
- Documentation updates for ledger and websocket invariants.

### OUT

- Heartbeat/ping scheduler design.
- Frontend/iOS websocket contract changes.
- New event catalog/channels.

---

## Architecture and Invariants

| INV | Rule | Evidence |
| --- | --- | --- |
| INV-1 | `/ws` remains the only canonical realtime endpoint | `app/routers/realtime_ws.py:252` |
| INV-2 | Connection cap remains fail-closed before auth | `app/routers/realtime_ws.py:263` |
| INV-3 | Idle timeout is explicit policy with disabled default | `app/routers/realtime_ws.py:23`, `app/routers/realtime_ws.py:84`, `app/routers/realtime_ws.py:118` |
| INV-4 | Timeout branch closes with policy semantics (`1008`) | `app/routers/realtime_ws.py:248` |
| INV-5 | Existing deterministic event serialization is preserved | `app/routers/realtime_ws.py:234` |
| INV-6 | Timeout tests avoid wall-clock sleeps | `tests/test_websocket_security_api.py:323`, `tests/test_websocket_security_api.py:343` |

---

## Threat Model (Worst-Case First)

1. **Connection-slot starvation (capacity DoS):**
   many authenticated but silent clients hold sockets, blocking active users.
2. **Idle-timeout regression:**
   timeout branch accidentally disabled due to parser/default mistakes.
3. **Flaky tests from wall-clock timing:**
   non-deterministic test behavior obscures real regressions.
4. **Policy drift in close semantics:**
   non-policy close code leaks behavior inconsistency across runtimes.
5. **Guardrail regression under change pressure:**
   cap/auth/limiter/version checks accidentally altered while adding timeout.

Mitigations in PR:

- Explicit `WS_IDLE_TIMEOUT_SECONDS` policy with disabled default.
- Deterministic timeout branch via `asyncio.wait_for` and fail-closed `1008`.
- Timeout tests use mocking (no `sleep()`).
- Existing websocket guard paths retained and re-tested.

---

## Hidden Regression Checklist

- [x] `WS_MAX_CONNECTIONS` behavior still enforced before auth.
- [x] `ping -> pong` behavior remains stable when timeout disabled.
- [x] Version/channel policy close paths remain unchanged.
- [x] Tracker release remains in `finally`.
- [x] Deterministic serialization (`sort_keys=True`) remains enabled.

---

## External Evidence Register

- OWASP WebSocket Security Cheat Sheet:
  DoS protections include connection limits + idle/dead-connection handling.
  <https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html>
- RFC 6455:
  close-handshake/status code semantics for policy-driven closes.
  <https://datatracker.ietf.org/doc/html/rfc6455>
- Python `asyncio.wait_for` docs:
  deterministic timeout behavior and `TimeoutError`.
  <https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for>
- Starlette websocket docs:
  canonical `receive`/`close` mechanics for ASGI handlers.
  <https://www.starlette.io/websockets/>

---

## Evidence Commands

```bash
pytest -q tests/test_websocket_security_api.py -v
pytest -q tests/test_websocket_burst_limiter_unit.py -v
pytest -q tests/test_main_ws_registration_guard.py -v
rg -n "WS_IDLE_TIMEOUT_SECONDS|idle_timeout|_receive_frame_with_idle_timeout|@router.websocket\\(\"/ws\"\\)" app/routers/realtime_ws.py
rg -n "idle timeout|WS_IDLE_TIMEOUT_SECONDS|wait_for" tests/test_websocket_security_api.py
make test-fast
make lint
```

---

## DoD Checklist

- [ ] Backlog item moved from deferred to execution-linked state with docs links.
- [ ] Idle timeout implemented and tested deterministically.
- [ ] Existing websocket security invariants unchanged.
- [ ] No flaky time-based tests introduced.
- [ ] Lint/test gates for changed scope pass.
