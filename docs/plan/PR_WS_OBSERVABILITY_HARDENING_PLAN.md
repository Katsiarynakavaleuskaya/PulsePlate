# PR-P1: WebSocket Observability Hardening Plan

<!-- markdownlint-disable MD013 -->

**Status:** Skeleton ready (coordinator-first, implementation not started)
**Branch:** `feat/ws-observability-skeleton`
**Date:** 2026-02-18

---

## Scope

### IN

- Add WS observability primitives for `/ws` in `app/routers/realtime_ws.py`.
- Add bounded metric contract for WS counters/gauge in `app/middleware/metrics.py`.
- Add structured policy-close logs with bounded reason taxonomy.
- Add deterministic tests for WS observability behavior (no `sleep()`).
- Produce narrow audit evidence with `file:line` anchors and explicit DoD.

### OUT

- No frontend runtime feature work.
- No protocol redesign for WS payloads/channels.
- No LLM/RAG runtime behavior changes.
- No distributed fan-out/broker redesign.

---

## Coordinator-First Execution Skeleton

### Phase 1 - Task analysis and invariants lock

- Confirm invariants:
  - Router remains transport-only (`app/routers/realtime_ws.py`).
  - Metrics labels are bounded (no high-cardinality labels).
  - Close reasons normalized to fixed enum.
  - Existing WS policy-close semantics preserved.
- Freeze narrow implementation boundary and test matrix.

### Phase 2 - Narrow implementation

- Add WS metrics wiring:
  - `ws_connect_total`
  - `ws_messages_total`
  - `ws_active_connections`
- Add structured `ws_policy_close` log payload contract.
- Keep existing close/reject flows unchanged except observability hooks.

### Phase 3 - Deterministic tests

- Add/extend tests under `tests/*ws*` for:
  - metric increments and gauge decrement path,
  - structured policy-close reason emission,
  - no label-cardinality drift.
- Explicitly avoid wall-clock `sleep()` patterns.

### Phase 4 - Validation, audit, and PR gates

- Run targeted WS tests + repo policy guards + lint.
- Update audit evidence with exact commands/raw lines/exit codes.
- Prepare PR body with scope/risks/deferred section.

---

## Multi-Agent Brainstorming Synthesis (Condensed)

Input streams used: `agent-coordinator`, `architecture-specialist`, `backend-engineer`, `security-auditor`, `bug-hunter`, `dev-operator`, `data-scientist-agent`, `ai-app-architect`, `philosophy-agent`, `bayesian-uq-agent`, `epistemology-discovery-agent`, `cbt-psychologist-agent`, `web-research-agent`, `rag-systems-agent`, `nutritionist-agent`, `ai-innovation-specialist`, `ai-trend-reporter`, `creative-designer`, `frontend-engineer`, `AGENTS`.

### Consensus points

- Observability must be additive and deterministic.
- Labels must be bounded and sanitized.
- Gauge lifecycle must be single-path decrement in `finally`.
- Negative scenarios must be first-class in test design.
- Incident wording should be system-centric and blameless.

---

## Negative Scenario Matrix (PR Hole Modeling)

| # | Failure scenario | Hole risk | Required telemetry | Deterministic test hook |
| --- | --- | --- | --- | --- |
| 1 | Missing auth rejected before metrics hook | undercount rejects | `ws_connect_total{result="rejected",reason="auth_failed"}` | open WS without token; assert reject counter +1 |
| 2 | Wrong tier rejected with ambiguous reason | mis-triage | bounded `reason` label | wrong tier handshake; assert exact normalized reason |
| 3 | Message burst triggers close without message counters | invisible abuse path | `ws_messages_total`, policy-close log | send N+1 ping events; assert counter delta then close reason |
| 4 | Active gauge increments but not decremented on exception | false "leak" incident | `ws_active_connections` gauge | force exception path; assert gauge returns baseline |
| 5 | Binary/non-text frame close path not logged | lost forensic trail | structured `ws_policy_close` | send bytes frame; assert log event emitted once |
| 6 | Unknown close reason creates unbounded labels | cardinality blow-up | reason normalization | inject unknown reason; assert fallback label `unknown` |
| 7 | Idle timeout closes but reason omitted in log | unclear incident timeline | policy-close with reason field | timeout branch test via monkeypatch wait_for |
| 8 | Double-close path decrements gauge twice | negative gauge bug | gauge floor invariant | simulate close+finally; assert no negative gauge |
| 9 | Metrics client failure raises and breaks WS path | observability affects runtime | best-effort metrics behavior | monkeypatch metrics inc failure; assert WS behavior intact |
| 10 | PII/token leaks into structured logs | security/compliance risk | sanitized log payload | capture logs; assert token not present |

---

## Minimal File Touch Plan

- `app/routers/realtime_ws.py`
  - add thin observability hook calls at connect/message/close points.
- `app/middleware/metrics.py`
  - define WS counters/gauge and bounded label helpers.
- `tests/test_websocket_security_api.py`
  - extend for metric/log deterministic assertions.
- `tests/test_main_ws_registration_guard.py`
  - keep registration invariants green.
- `docs/plan/PR_WS_OBSERVABILITY_HARDENING_PLAN.md`
- `docs/audit/PR_WS_OBSERVABILITY_HARDENING_AUDIT.md`

---

## Deterministic Validation Commands (Skeleton)

```bash
pytest -q tests/test_websocket_security_api.py -v
pytest -q tests/test_main_ws_registration_guard.py -v
pytest -q tests/test_repo_policy_guards.py -v
make lint
make test-fast
make verify
```

---

## DoD

- [ ] WS observability metrics exist and are bounded.
- [ ] Policy-close structured log reason is normalized and test-covered.
- [ ] Negative scenarios 1-8 have deterministic coverage (no `sleep()`).
- [ ] No guard regression (`tests/test_repo_policy_guards.py` green).
- [ ] Lint/test gates pass for changed scope.
- [ ] Audit file includes command evidence and `file:line` anchors.
