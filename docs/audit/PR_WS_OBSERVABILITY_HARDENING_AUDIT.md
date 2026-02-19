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
   - Risk: labels include user/session identifiers, exploding metric cardinality.
   - Control: bounded reason enums only; explicit test assertions on label keys.
2. **Metric/log drift from policy paths**
   - Risk: policy close path emits log without metric (or inverse).
   - Control: branch-by-branch deterministic tests (auth/cap/idle/burst).
3. **False confidence due to flaky tests**
   - Risk: time-based assertions cause non-deterministic green.
   - Control: no `sleep()`; mock-driven deterministic assertions.
4. **Guardrail regression during instrumentation**
   - Risk: auth/cap/limiter logic changes while adding metrics/logs.
   - Control: re-run existing websocket guard suites unchanged.

---

## External Evidence Register

- OWASP WebSocket Security Cheat Sheet
  - Observability and abuse controls are required for operational resilience.
  - <https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html>
- RFC 6455
  - Close semantics and policy-driven close handling.
  - <https://datatracker.ietf.org/doc/html/rfc6455>
- Prometheus instrumentation best practices
  - Favor low-cardinality labels and explicit bounded dimensions.
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
# PR-P1: WebSocket Observability Hardening Audit

<!-- markdownlint-disable MD013 -->

**Status:** Skeleton audit ready (pre-implementation)
**Branch:** `feat/ws-observability-skeleton`
**Date:** 2026-02-18

---

## Scope Validation

### In scope

- WS observability hardening for `/ws` endpoint.
- Bounded metrics + structured policy-close logs.
- Deterministic tests for negative scenarios.

### Out of scope

- Protocol redesign and additional WS channels.
- Frontend runtime changes.
- Non-WS observability refactors.

---

## Evidence Anchors (Current Baseline)

- WS endpoint and policy-close reasons: `app/routers/realtime_ws.py:264`
- Close reasons enum block: `app/routers/realtime_ws.py:30`
- Policy-close logging call sites: `app/routers/realtime_ws.py:270`
- Existing HTTP metrics/bounded route template logic: `app/middleware/metrics.py:220`
- Existing deterministic WS timeout tests without sleep: `tests/test_websocket_security_api.py:324`

---

## Optimal Solution (From Multi-Agent Brainstorming)

### Recommended implementation shape

1. Add WS metrics in one bounded contract:
   - `ws_connect_total`
   - `ws_messages_total`
   - `ws_active_connections`
2. Add normalization helper for close reason labels (`unknown` fallback).
3. Keep all WS metric/gauge lifecycle hooks in transport layer only.
4. Use single close/decrement path to avoid gauge drift.
5. Keep observability best-effort: metrics/log failures must not break WS runtime.

### Why this is optimal for this repo

- Minimal diff in existing WS transport path.
- Deterministic testing is straightforward.
- Aligns with repo constraints on bounded labels and guard-first quality.
- Avoids architectural scope creep while closing the biggest observability gaps.

---

## Negative PR Scenario Modeling (Holes and Guards)

| Scenario | Potential hole | Guardrail |
| --- | --- | --- |
| Auth reject not counted | blind auth failure rate | counter increment on reject path |
| Wrong-tier close reason drift | unstable dashboards | normalized reason enum |
| Burst close unlogged | no abuse visibility | structured policy-close on rate-limit close |
| Exception path leaks active gauge | false capacity saturation | decrement in `finally` only |
| Non-text frame close missing reason | incident ambiguity | explicit reason for text-frame-required |
| Unknown reason label explosion | cardinality risk | map to `unknown` |
| Timeout close path not observable | false "network issue" narrative | timeout reason metric + log |
| Double-close negative gauge | broken SLO telemetry | idempotent decrement floor |
| Metrics backend failure breaks WS | observability causes outage | swallow/log metrics failures safely |
| Token/PII appears in logs | security violation | log sanitization test |

---

## Deterministic Test Strategy (No Sleep)

- Use explicit event sequences (connect -> message -> close).
- Use monkeypatch for timeout/error branches instead of wall-clock waits.
- Assert deltas for counters and baseline restoration for gauge.
- Assert structured log fields with capture fixture (reason/code present, secrets absent).

---

## Command Evidence Skeleton (to fill during implementation)

```bash
pytest -q tests/test_websocket_security_api.py -v
pytest -q tests/test_main_ws_registration_guard.py -v
pytest -q tests/test_repo_policy_guards.py -v
make lint
make test-fast
make verify
```

Expected audit completion format per command:

- exact command
- 1-3 raw output lines
- exit code

---

## Risks and Mitigations

- **Risk:** metric cardinality drift
  **Mitigation:** bounded label contract + normalization test.

- **Risk:** gauge mismatch after exceptional exits
  **Mitigation:** single decrement path + explicit exception-path test.

- **Risk:** noisy/non-actionable operator logs
  **Mitigation:** structured and blameless policy-close wording template.

- **Risk:** false confidence from partial scenarios
  **Mitigation:** negative-scenario matrix is mandatory in this PR.

---

## Go/No-Go Criteria

- [ ] Metrics and logs wired with bounded contract.
- [ ] Negative scenario tests are deterministic and green.
- [ ] No secret/PII leakage in observability payloads.
- [ ] Guard + lint + test-fast + verify pass.
- [ ] Audit evidence block completed with raw outputs and exit codes.
