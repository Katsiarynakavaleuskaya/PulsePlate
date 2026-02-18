# PR-P1: WebSocket Idle Timeout Work-Package Plan

<!-- markdownlint-disable MD013 -->

**Status:** Planned and executing in one runtime PR
**Branch:** `feat/ws-idle-timeout-pr`
**Date:** 2026-02-16

---

## Scope

### IN

- Add idle-timeout policy to `/ws` using `WS_IDLE_TIMEOUT_SECONDS`.
- Keep default as explicit disabled mode (`0`) for backward compatibility.
- When enabled (`>0`), close idle connections with policy close (`1008`, reason `idle_timeout`).
- Keep existing connection cap, auth, message-size, and burst-limit invariants unchanged.
- Add deterministic tests for timeout path without `sleep()`.
- Update canonical docs (`BACKLOG_LEDGER`, websocket audit, `app/AGENTS.md`) with the new invariant.

### OUT

- Heartbeat scheduler or server-initiated ping loop.
- Frontend/iOS behavior changes.
- Any new websocket channels or protocol expansions.
- Broker/fan-out/distributed realtime architecture work.

---

## Implementation Plan

### Phase 1 - Backend policy extension

1. Extend `WsPolicy` in `app/routers/realtime_ws.py` with:
   - `idle_timeout_seconds` (default: `0`)
2. Extend env loading with non-negative parser:
   - `WS_IDLE_TIMEOUT_SECONDS` supports `0` (disabled) and positive values.
3. Add receive helper with timeout branch:
   - Wrap `ws.receive()` with `asyncio.wait_for(...)` when timeout enabled.
   - On timeout: close with `1008` and reason `idle_timeout`.

### Phase 2 - Deterministic testing

1. Keep existing websocket happy/fail-closed tests green.
2. Add timeout-path API test:
   - Patch `asyncio.wait_for` to raise `TimeoutError` deterministically.
   - Verify close behavior (`1008`) without wall-clock waits.
3. Add disabled-mode test:
   - `WS_IDLE_TIMEOUT_SECONDS=0` bypasses timeout wrapper and preserves `ping -> pong`.

### Phase 3 - Documentation and quality gates

1. Update `docs/roadmap/BACKLOG_LEDGER.md` with in-progress execution metadata and links.
2. Add audit with file:line evidence and threat-model summary.
3. Update `app/AGENTS.md` websocket invariant section.
4. Run test/lint/coverage gates and prepare PR body mapping for review bots.

---

## Worst-Case Scenario Model

### Scenario

High volume of authenticated but silent websocket clients opens and holds `/ws` connections near max cap, starving active users. Under bursty load, this becomes capacity exhaustion and can cascade into degraded realtime service.

### Consequences

- Elevated connection rejection rate for legitimate clients.
- Increased resource retention per worker/process.
- Higher operational toil during incidents due to long-lived idle sockets.

### Mitigation in this PR

- Deterministic idle close policy (`1008`, `idle_timeout`) when timeout enabled.
- Keep fail-closed semantics and current cap/limiter invariants unchanged.
- Add explicit tests to guard against regressions in timeout and disabled modes.

---

## External Evidence Register

- OWASP WebSocket Security Cheat Sheet:
  - Recommends idle timeout and connection/resource limits for DoS resistance.
  - <https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html>
- RFC 6455:
  - Defines close status codes and policy-violation semantics.
  - <https://datatracker.ietf.org/doc/html/rfc6455>
- Python asyncio docs:
  - `asyncio.wait_for` timeout behavior for awaitables.
  - <https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for>
- Starlette WebSocket docs:
  - Canonical receive/close behavior in ASGI websocket handlers.
  - <https://www.starlette.io/websockets/>

---

## Deterministic Test Commands

```bash
pytest -q tests/test_websocket_burst_limiter_unit.py -v
pytest -q tests/test_websocket_security_api.py -v
pytest -q tests/test_main_ws_registration_guard.py -v
pytest -q tests/test_repo_policy_guards.py -v
make test-fast
make lint
```

---

## DoD Checklist

- [ ] `WS_IDLE_TIMEOUT_SECONDS` is implemented with default disabled mode (`0`).
- [ ] Enabled timeout closes idle `/ws` with deterministic policy close (`1008`, `idle_timeout`).
- [ ] No regressions in existing `/ws` guardrails (auth, cap, limiter, versioned events).
- [ ] Timeout test path is deterministic and uses no `sleep()`.
- [ ] Audit includes file:line anchors and external evidence links.
- [ ] `app/AGENTS.md` websocket invariants updated.
- [ ] Quality gates pass for PR scope.
