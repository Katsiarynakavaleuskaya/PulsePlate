# Task Analysis: P1 WS Observability Hardening

---

## Task Analysis

**Task:** Add deterministic and bounded WebSocket observability
(metrics + policy-close logs) for `/ws`.

**Domain(s):** Multiple (Architecture | Backend | Security | Bugs | Docs)

**Complexity:** Moderate

**Priority:** P1

- **Priority track (P0-A / P0-B / P1):** P1

**Expected Outcome:**

- WS runtime exports bounded counters/gauge for connect/message/active states.
- Policy-close logs are structured and normalized by reason.
- Negative scenarios are covered by deterministic tests with no `sleep()`.
- Plan/audit docs include scope, risks, and evidence-ready command blocks.

**Invariants Affected:**

- [ ] One BMI Engine
- [ ] Thin HTTP Adapter Policy
- [x] Layer Separation
- [x] Contract-First
- [x] Other: Bounded observability labels; deterministic WS tests.

**Risks:**

1. Gauge drift on exceptional close paths.
2. Label cardinality explosion from uncontrolled reason/path labels.
3. Metrics failure impacting runtime behavior.
4. Missing negative-path tests producing false confidence.

**Proposed Approach:**

1. Add bounded WS metric helpers in `app/middleware/metrics.py`.
2. Wire helpers into `app/routers/realtime_ws.py` with single decrement path and structured close logs.
3. Extend `tests/test_websocket_security_api.py` with deterministic metric/log assertions.
4. Run targeted tests + `make verify`; update audit evidence section.

**Agent Assignment:**

- **Primary:** `backend-engineer` - implement minimal runtime diff.
- **Secondary:** `security-auditor`, `bug-hunter`, `architecture-specialist`
  - negative scenarios, deterministic tests, invariant checks.
- **Dependencies:** Existing WS guardrails must stay behaviorally unchanged.

**Constraints:**

- No changes in other worktrees/branches.
- No `sleep()` in new tests.
- No unbounded labels or sensitive data in logs
  (cardinality + privacy guard).
- Keep scope to WS observability hardening only.

---

**Analysis by:** agent-coordinator (synthesized)
**Date:** 2026-02-18
