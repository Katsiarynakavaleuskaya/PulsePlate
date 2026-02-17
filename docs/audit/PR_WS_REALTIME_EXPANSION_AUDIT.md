# PR-P1: WebSocket Realtime Expansion Audit

<!-- markdownlint-disable MD013 -->

**Status:** In progress (runtime work-package)
**Branch:** `feat/websocket-realtime-expansion`
**Date:** 2026-02-16

---

## Scope

### IN

- Versioned WebSocket event contract on canonical `/ws`.
- Controlled expansion from `ping`-only to `ping + subscribe(progress)`.
- Deterministic policy closes for unsupported protocol version and unknown channel.
- Thin frontend adapter for WebSocket transport only (`src/api/wsClient.ts`).
- Frontend guard extension to keep raw `new WebSocket(...)` creation isolated to adapter.
- Deterministic backend/frontend tests for the expanded contract.

### OUT

- iOS WebSocket consumer wiring.
- Multi-room fan-out, broker/pub-sub, or distributed delivery guarantees.
- CV/media streaming and sensor calibration logic.
- AI/RAG streaming over WebSocket transport.

---

## Architectural Invariants

| INV | Rule | Evidence anchor |
| ----- | ------ | ----------------- |
| INV-1 | `/ws` remains the canonical endpoint in router layer | `app/routers/realtime_ws.py:204` |
| INV-2 | Request-time feature flag and policy loading remain deterministic | `app/routers/realtime_ws.py:33`, `app/routers/realtime_ws.py:58`, `app/routers/realtime_ws.py:69` |
| INV-3 | Versioned contract is explicit (`PROTOCOL_VERSION="1"`) | `app/routers/realtime_ws.py:21`, `app/routers/realtime_ws.py:55`, `app/routers/realtime_ws.py:257` |
| INV-4 | Allowed event surface is explicit and small (`ping`, `subscribe`) | `app/routers/realtime_ws.py:22`, `app/routers/realtime_ws.py:275` |
| INV-5 | Allowed channels are explicit and constrained (`progress`) | `app/routers/realtime_ws.py:23`, `app/routers/realtime_ws.py:278` |
| INV-6 | Frontend keeps transport-only thin adapter boundary for WS creation | `frontend/src/api/wsClient.ts:35`, `frontend/src/api/__tests__/thin-client-guards.test.ts:307` |

---

## Contract Delta (Foundation -> Expansion)

### Endpoint

`GET /ws` (WebSocket upgrade), unchanged as canonical transport endpoint.

Evidence: `app/routers/realtime_ws.py:204`

### Incoming event contract (v1)

```json
{"version":"1","type":"ping"}
{"version":"1","type":"subscribe","channel":"progress"}
```

Legacy compatibility: `{"type":"ping"}` remains accepted and normalized to v1 response.

Evidence: `app/routers/realtime_ws.py:181`, `app/routers/realtime_ws.py:194`, `app/routers/realtime_ws.py:263`, `tests/test_websocket_security_api.py:139`

### Outgoing event contract (v1)

```json
{"version":"1","type":"pong","server_time_ms":1700000000000}
{"version":"1","type":"subscribed","channel":"progress"}
```

Evidence: `app/routers/realtime_ws.py:267`, `app/routers/realtime_ws.py:287`, `tests/test_websocket_security_api.py:218`

### New policy close reasons (1008)

| Code | Reason | Trigger | Evidence |
| ------ | -------- | --------- | ---------- |
| 1008 | `unsupported_version` | message `version != "1"` or missing for non-legacy event | `app/routers/realtime_ws.py:259-261`, `tests/test_websocket_security_api.py:241` |
| 1008 | `channel_not_allowed` | `subscribe` with unsupported channel | `app/routers/realtime_ws.py:278-280`, `tests/test_websocket_security_api.py:253` |

---

## Thin Adapter Evidence (Frontend)

- Transport URL builder and socket creation are centralized in one adapter file.
- Adapter exposes connection state callbacks and message parsing only (no business logic).
- Guard test enforces policy that raw socket creation stays in the adapter file.

Evidence: `frontend/src/api/wsClient.ts:26`, `frontend/src/api/wsClient.ts:35`, `frontend/src/api/__tests__/thin-client-guards.test.ts:176`, `frontend/src/api/__tests__/thin-client-guards.test.ts:307`

---

## Evidence Commands

```bash
pytest -q tests/test_websocket_burst_limiter_unit.py -v
pytest -q tests/test_websocket_security_api.py -v
cd frontend && npm test -- --run src/api/__tests__/wsClient.test.ts src/api/__tests__/thin-client-guards.test.ts
rg -n "PROTOCOL_VERSION|ALLOWED_EVENT_TYPES|ALLOWED_CHANNELS|unsupported_version|channel_not_allowed|@router.websocket\\(\"/ws\"\\)" app/routers/realtime_ws.py
rg -n "buildRealtimeWsUrl|connectRealtimeWs|new WebSocket" frontend/src/api/wsClient.ts frontend/src/api/__tests__/thin-client-guards.test.ts
pre-commit run --all-files
make verify
```

---

## DoD Checklist

- [ ] Versioned v1 contract implemented and tested (`ping`, `subscribe`).
- [ ] Unsupported version and unknown channel are fail-closed with deterministic `1008`.
- [ ] Legacy `ping` compatibility remains stable.
- [ ] Frontend WebSocket adapter exists and remains thin.
- [ ] Frontend guard enforces single socket-construction boundary.
- [ ] `pre-commit run --all-files` passes.
- [ ] `make verify` passes.
