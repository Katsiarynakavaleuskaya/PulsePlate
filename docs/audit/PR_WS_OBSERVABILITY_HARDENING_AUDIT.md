# PR-P1: WebSocket Observability Hardening Audit

<!-- markdownlint-disable MD013 -->

**Status:** Pre-implementation audit skeleton
**Branch:** `feat/ws-observability-hardening-skeleton`
**Date:** 2026-02-19

---

## Scope Validation

### IN

- Low-cardinality websocket observability for canonical `/ws`.
- Structured policy-close logs for incident diagnostics.
- Deterministic tests and guard compatibility.

### OUT

- Transport redesign.
- New websocket endpoint surface.
- Frontend/iOS runtime changes.

---

## Architecture Invariants to Preserve

| INV | Rule | Evidence Anchor |
| --- | --- | --- |
| INV-1 | Canonical websocket route stays `/ws` | `app/routers/realtime_ws.py:252` |
| INV-2 | Connection cap remains fail-closed before auth | `app/routers/realtime_ws.py:263` |
| INV-3 | Burst/message limit policy remains unchanged | `app/routers/realtime_ws.py:293` |
| INV-4 | Idle-timeout policy path remains deterministic | `app/routers/realtime_ws.py:238` |
| INV-5 | Observability labels remain low-cardinality | `app/middleware/metrics.py:1` |

---

## Risk Register (Negative Scenario First)

1. **High-cardinality label regression**
   - Risk: labels include user/session identifiers, exploding cardinality.
   - Control: bounded reason enums only; explicit test assertions on label keys.
2. **Metric/log drift from policy paths**
   - Risk: policy close path emits log without metric (or inverse).
   - Control: branch-by-branch deterministic tests (auth/cap/idle/burst).
3. **False confidence due to flaky tests**
   - Risk: time-based assertions create non-deterministic green.
   - Control: no `sleep()`; mock-driven deterministic assertions.
4. **Guardrail regression during instrumentation**
   - Risk: auth/cap/limiter logic changes while adding metrics/logs.
   - Control: re-run existing websocket guard suites unchanged.

---

## External Evidence Register

- OWASP WebSocket Security Cheat Sheet
  - Observability and abuse controls are required for resilience.
  - <https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html>
- RFC 6455
  - Close semantics and policy-driven close handling.
  - <https://datatracker.ietf.org/doc/html/rfc6455>
- Prometheus instrumentation best practices
  - Keep labels bounded; avoid high cardinality dimensions.
  - <https://prometheus.io/docs/practices/instrumentation/>

---

## Evidence Commands (Execution Phase)

```bash
rg -n "ws_connect_total|ws_messages_total|ws_active_connections" app/routers/realtime_ws.py app/middleware/metrics.py
rg -n "policy_close|close_reason|idle_timeout|connection_cap|burst_limit" app/routers/realtime_ws.py
pytest -q tests/test_websocket_security_api.py -v
pytest -q tests/test_websocket_burst_limiter_unit.py -v
pytest -q tests/test_main_ws_registration_guard.py -v
make test-fast
make lint
```

---

## DoD Checklist

- [ ] Runtime observability metrics are implemented with bounded labels.
- [ ] Structured policy-close logs are present and deterministic.
- [ ] Negative scenarios are covered by deterministic tests.
- [ ] Existing websocket guard behavior is preserved.
- [ ] CI checks and bot threads are fully resolved before merge.
