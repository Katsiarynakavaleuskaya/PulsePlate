# PR Body Skeleton: WS Observability Hardening

## Summary

- Add bounded WS observability metrics for `/ws`:
  `ws_connect_total`, `ws_messages_total`, `ws_active_connections`.
- Add structured policy-close logs with normalized reasons.
- Add deterministic negative-path tests
  (no `sleep()`).
- Evidence anchors: `app/middleware/metrics.py:213`, `app/routers/realtime_ws.py:270`.

## Scope

### IN

- `app/middleware/metrics.py` (WS observability helpers and bounded labels)
- `app/routers/realtime_ws.py` (metric hooks + structured close logs)
- `tests/test_websocket_security_api.py` (deterministic assertions)
- docs updates for plan/audit evidence

### OUT

- WS protocol redesign
- frontend runtime changes
- distributed realtime architecture changes

## Risks / Mitigations

- Gauge mismatch on abnormal exits -> single decrement path in `finally`.
- Label cardinality drift -> reason/path normalization helpers + tests.
- Metrics failure affecting runtime -> best-effort observability path.
- Hidden regressions -> negative scenario matrix covered by tests.

## Test Plan

- `pytest -q tests/test_websocket_security_api.py -v`
- `pytest -q tests/test_main_ws_registration_guard.py -v`
- `pytest -q tests/test_repo_policy_guards.py -v`
- `make lint`
- `make test-fast`
- `make verify`

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

- [ ] WS metric hooks + bounded label contract
- [ ] Structured policy-close logging normalization
- [ ] Deterministic negative-path WS tests
- [ ] Docs plan/audit updates with evidence anchors

## Deferred / Follow-ups

- [ ] Optional WS latency histogram (if needed after baseline)
- [ ] Optional alert threshold tuning after first production baseline window
