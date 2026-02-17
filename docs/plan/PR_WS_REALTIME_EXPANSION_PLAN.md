# PR-P1: WebSocket Realtime Expansion Work-Package Plan

<!-- markdownlint-disable MD013 -->

**Status:** Planned and executing in one runtime PR
**Branch:** `feat/websocket-realtime-expansion`
**Date:** 2026-02-16

---

## Scope

### IN

- Expand `/ws` from foundation heartbeat to a small versioned realtime package.
- Add explicit protocol version handling (`v1`) and policy close on unsupported versions.
- Add `subscribe(progress)` event with explicit channel allowlist.
- Keep auth/rate-limit/message-size fail-closed behavior from foundation.
- Add frontend thin WebSocket adapter (`wsClient`) for transport-only integration scope.
- Add deterministic backend and frontend tests; keep guard policies intact.

### OUT

- iOS consumer integration.
- Multi-channel broker/fan-out architecture.
- AI/RAG/CBT payload streaming and uncertainty policy wiring.
- CV/image streaming, sensor calibration, and advanced telemetry rollout.

---

## Implementation Plan

### Phase 1 - Backend protocol expansion

1. Introduce protocol constants and policy fields:
   - `PROTOCOL_VERSION`
   - `ALLOWED_EVENT_TYPES` (`ping`, `subscribe`)
   - `ALLOWED_CHANNELS` (`progress`)
2. Add message version resolver:
   - Require `version=="1"` for expanded events.
   - Preserve legacy `ping` compatibility for smooth transition.
3. Add event handlers:
   - `ping` -> `pong` with `server_time_ms`
   - `subscribe(progress)` -> `subscribed(progress)`
4. Add deterministic close branches:
   - `unsupported_version`
   - `channel_not_allowed`

### Phase 2 - Frontend thin adapter scope

1. Create `frontend/src/api/wsClient.ts` transport adapter:
   - URL builder (http->ws / https->wss)
   - central socket creation
   - optional callbacks for state and parsed messages
2. Keep adapter transport-only:
   - no BMI/risk/business logic
   - no domain interpretation

### Phase 3 - Guard and tests

1. Backend tests (`tests/test_websocket_security_api.py`):
   - `subscribe(progress)` happy path
   - unsupported version reject
   - unknown channel reject
   - legacy ping compatibility
2. Frontend tests (`frontend/src/api/__tests__/wsClient.test.ts`):
   - URL conversion and token query behavior
   - state transitions and message parsing
3. Thin guard extension:
   - prevent raw `new WebSocket(...)` outside adapter

---

## Deterministic Test Plan

```bash
pytest -q tests/test_websocket_burst_limiter_unit.py
pytest -q tests/test_websocket_security_api.py
cd frontend && npm test -- --run src/api/__tests__/wsClient.test.ts src/api/__tests__/thin-client-guards.test.ts
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make verify
```

Determinism notes:

- No sleeps for realtime assertions.
- Stable event payload assertions for response type/version/channel.
- `server_time_ms` validated as type (`int`), not exact wall-clock value.

---

## Risks and Mitigations

- **Risk:** Contract break for existing simple ping clients.
  **Mitigation:** Legacy `{"type":"ping"}` accepted and normalized to `v1` response.

- **Risk:** Scope creep into heavy realtime features.
  **Mitigation:** Strict allowlist (`progress` only), explicit OUT scope, no broker/pub-sub.

- **Risk:** Thin-adapter drift on frontend.
  **Mitigation:** Add guard to enforce socket creation only in `api/wsClient.ts`.

---

## Definition of Done

- `/ws` supports versioned v1 messages for `ping` and `subscribe(progress)`.
- Unsupported protocol versions and unknown channels are rejected deterministically.
- Frontend has one transport-only WS adapter with tests.
- Thin-client guard remains green with new websocket boundary checks.
- Audit is updated with file:line evidence anchors.
- `pre-commit run --all-files` and `make verify` pass.
