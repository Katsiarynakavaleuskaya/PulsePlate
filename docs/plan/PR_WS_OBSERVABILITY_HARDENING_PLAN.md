# PR-P1: WebSocket Observability Hardening Work-Package Plan

<!-- markdownlint-disable MD013 -->

**Status:** Planned (runtime work-package)
**Branch:** `feat/ws-observability-hardening-skeleton`
**Date:** 2026-02-19

---

## Scope

### IN

- Add low-cardinality websocket metrics for canonical `/ws`:
  - `ws_connect_total`
  - `ws_messages_total`
  - `ws_active_connections`
- Add structured policy-close logs for deterministic incident triage.
- Preserve existing auth/cap/limiter/idle-timeout behavior unchanged.
- Add deterministic tests for metric increments and policy-close log events.
- Keep this PR runtime-scoped (no docs-heavy expansion, no transport redesign).

### OUT

- New websocket channels/events.
- Frontend/iOS websocket protocol changes.
- New telemetry backend/storage pipeline.
- Retry queues, distributed fan-out, or broker architecture work.

---

## Implementation Skeleton (7 Steps Max)

1. Add metric definitions and bounded label contract in websocket runtime path.
2. Wire counter/gauge updates at connect/message/close lifecycle points.
3. Add structured policy-close logging for guard closes and timeout closes.
4. Ensure labels stay low-cardinality (no user ids, no session ids in labels).
5. Add deterministic tests for metric increments/decrements and structured logs.
6. Run targeted verification and guard suites.
7. Prepare PR acceptance report with first-fail evidence format.

---

## Files (Planned)

- `app/routers/realtime_ws.py`
- `app/middleware/metrics.py`
- `tests/test_websocket_security_api.py`
- `tests/test_websocket_burst_limiter_unit.py`
- `tests/test_main_ws_registration_guard.py`
- `docs/plan/PR_WS_OBSERVABILITY_HARDENING_PLAN.md`
- `docs/audit/PR_WS_OBSERVABILITY_HARDENING_AUDIT.md`

---

## Worst-Case Scenario Model

### Scenario

Under load, websocket policy closes increase but observability remains too
coarse, making triage ambiguous (cannot distinguish auth/cap/idle/burst causes).
This can delay mitigation and increase false-attribution during incidents.

### Mitigations in this Work-Package

- Structured close logs with explicit reason code and close category.
- Low-cardinality counters by bounded reason enum.
- Deterministic tests for each policy-close path to avoid drift.

---

## Deterministic Validation Commands

```bash
pytest -q tests/test_websocket_security_api.py -v
pytest -q tests/test_websocket_burst_limiter_unit.py -v
pytest -q tests/test_main_ws_registration_guard.py -v
pytest -q tests/test_repo_policy_guards.py -v
make test-fast
make lint
```

---

## Acceptance Gates

- [ ] `ws_connect_total`, `ws_messages_total`, `ws_active_connections` wired on `/ws`.
- [ ] Structured policy-close logs include deterministic reason/category fields.
- [ ] No high-cardinality metric labels introduced.
- [ ] Deterministic tests cover connect/message/close and policy-close branches.
- [ ] Existing websocket security invariants stay green.
- [ ] Runtime scope remains narrow (no transport/perimeter expansion).
