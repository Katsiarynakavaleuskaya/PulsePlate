# PR-WS-EXPANSION: Realtime Expansion Package Audit

<!-- markdownlint-disable MD013 -->

**Status:** Planning audit (pre-implementation, evidence-based)
**Branch:** `docs/audit-nextstep-ws-expansion`
**Date:** 2026-02-16
**Source backlog item:** `docs/roadmap/BACKLOG_LEDGER.md` (P1: WebSocket foundation follow-up)

---

## Scope

### IN

- Next-step package definition for `P1: WebSocket foundation follow-up (realtime expansion package)`.
- Brainstorm synthesis from coordinated agent team (architecture, backend, security, frontend, innovation, trend, GTM, claim semantics).
- Implementation direction for versioned realtime contracts and thin-adapter client integration.
- Deterministic test and verification strategy aligned with project gates.

### OUT

- Direct runtime code changes in this document PR.
- Expanding to medical/diagnostic claims.
- Introducing business logic into client adapters.
- Any merge-readiness claim for runtime PR (this is planning/audit only).

---

## Why This Is The Next Step (Evidence)

The backlog explicitly marks the websocket expansion package as the immediate planned follow-up after foundation delivery.

| Claim | Evidence anchor |
| --- | --- |
| Next open item is websocket expansion package | `docs/roadmap/BACKLOG_LEDGER.md:500` |
| Target PR placeholder exists for this package | `docs/roadmap/BACKLOG_LEDGER.md:503` |
| Required DoD includes versioned event contract | `docs/roadmap/BACKLOG_LEDGER.md:512` |
| Required DoD includes thin-adapter client integration scope | `docs/roadmap/BACKLOG_LEDGER.md:513` |
| Required DoD includes deterministic integration tests | `docs/roadmap/BACKLOG_LEDGER.md:514` |

---

## Baseline Invariants From Foundation (Must Keep)

| INV | Rule | Evidence anchor |
| --- | --- | --- |
| INV-1 | Single canonical `/ws` route remains registered from `app.main` | `app/main.py:17`, `app/main.py:36`, `app/routers/realtime_ws.py:173` |
| INV-2 | Duplicate `/ws` registration guard remains fail-fast | `app/main.py:25-32`, `app/main.py:35` |
| INV-3 | Auth remains fail-closed (`auth_required` / `auth_invalid`) | `app/routers/realtime_ws.py:115-130` |
| INV-4 | Policy close code and reason constants stay centralized | `app/routers/realtime_ws.py:22-30` |
| INV-5 | Runtime guardrails stay active (flag, payload limit, burst limiter, allowlist) | `app/routers/realtime_ws.py:41`, `app/routers/realtime_ws.py:54-74`, `app/routers/realtime_ws.py:204-224` |
| INV-6 | Structured policy-close/disconnect logging remains in place | `app/routers/realtime_ws.py:119`, `app/routers/realtime_ws.py:128`, `app/routers/realtime_ws.py:179`, `app/routers/realtime_ws.py:230` |

---

## Cross-Agent Brainstorm Synthesis

### Architecture and Backend Direction

1. Keep one canonical websocket entrypoint and scale via versioned message routing, not endpoint sprawl.
2. Preserve adapter boundaries: websocket loop in `app/routers/*`, domain decisions in `core/*`.
3. Introduce message envelope versioning (`version` or `event_schema_version`) and explicit unsupported-version behavior.
4. Add sustained-rate policy on top of current burst guard to reduce abuse surface during expansion.
5. Expand event catalog in phases (foundation-compatible first, product events second, advanced fan-out third).

### Security and Reliability Direction

1. Enforce auth and tier checks before subscription or event delivery.
2. Keep strict message shape validation and type allowlist for every incoming frame.
3. Add deterministic tests for connection limits, message rate limits, and close-code contracts.
4. Prevent cross-user event leakage with tenant/user-scoped fan-out keys.
5. Keep logs metadata-safe (no token/PII leakage in realtime traces).

### Frontend Thin-Adapter Direction

1. Add a single websocket adapter module in frontend API layer; forbid raw websocket usage in feature components.
2. Keep client behavior transport-only: no BMI thresholds, no domain recomputation from event payloads.
3. Expose minimal connection state (`connecting/open/closed/error`) for UX observability.
4. Reuse existing auth/config handling; avoid ad-hoc credentials to external origins.
5. Add thin-client guard tests to enforce adapter-only websocket usage.

### Innovation and Product Levers (Low-Risk First)

1. Live dashboard sync events (multi-tab/device freshness).
2. In-app realtime progress/streak nudges.
3. Background job status channel (exports/plan generation readiness).
4. Streaming AI insight chunks only after core safeguards are proven.
5. Optional collaborative plate/plan editing as later phase.

### Wellness-Safe Language Constraints

- Realtime claims must remain wellness-only and non-diagnostic.
- Use attributed and bounded language ("based on your recent entries"), avoid absolute health claims.
- Forbidden phrasing includes diagnosis/treatment assertions; safe alternatives must be suggestive, not prescriptive.

---

## Team-Orchestrated Execution Map (All Agents In Command)

| Agent | Role in WS expansion package | Primary deliverable |
| --- | --- | --- |
| `agent-coordinator` | Orchestration and gate synthesis | Task analysis + DoD decision sheet |
| `AGENTS` | Policy alignment control | Invariant checklist + instruction sync proposal |
| `architecture-specialist` | Canonical topology and boundaries | Route/contracts architecture note |
| `ai-app-architect` | AI subsystem seam control | AI event integration boundaries |
| `backend-engineer` | Runtime implementation and tests | WS event routing + deterministic test suite |
| `bug-hunter` | Regression and edge-case discovery | Defect list with reproduction |
| `security-auditor` | Threat model and controls | Threat-control-test matrix |
| `logic-agent` | Contract consistency checks | Contradiction/ambiguity list |
| `bayesian-uq-agent` | Confidence policy (if AI stream events) | UQ degrade rules for high uncertainty |
| `data-scientist-agent` | Evaluation design | Offline/online metrics for event quality |
| `ml-engineer-agent` | Production constraints for AI events | Latency/cost/reliability plan |
| `rag-systems-agent` | Grounding/citation policy (if RAG stream) | RAG realtime contract constraints |
| `ai-innovation-specialist` | Feature innovation options | Prioritized low-risk innovation slate |
| `ai-trend-reporter` | Market trend context | 2026 realtime trend snapshot |
| `marketing-strategist` | GTM and conversion strategy | Positioning + rollout + conversion hypotheses |
| `frontend-engineer` | Thin adapter integration (web) | Adapter API + connection-state UX spec |
| `creative-designer` | UX polish and trust visuals | Realtime state design guidance |
| `cbt-psychologist-agent` | Safe coaching language boundaries | Realtime coaching phrasing policy |
| `nutritionist-agent` | Nutrition-domain claim constraints | Allowed/forbidden nutrition phrasing |
| `philosophy-agent` | Claim semantics and falsifiability | Wellness-safe claim semantics table |
| `cv-agent` | CV event pipeline constraints (if used) | Photo pipeline realtime contract note |
| `physics-sensor-agent` | Sensor plausibility guardrails | Sensor-based event invariants |
| `epistemology-discovery-agent` | Hypothesis rigor and promotion rules | Falsifiable hypothesis checklist |
| `dev-operator` | Deterministic command evidence | Verification logs and exit-code registry |
| `web-research-agent` | Bounded external references (if requested) | External claims register |
| `algorithmic-art` | Not runtime-critical for this package | Optional visuals-only exploration (out of scope for runtime PR) |

---

## Proposed Implementation Phases

### Phase 1 - Contract and Routing Stabilization

- Define versioned websocket envelope and event-type registry.
- Keep `/ws` entrypoint and fail-closed behavior unchanged.
- Add deterministic tests for unsupported version, unknown event type, and auth/tier deny paths.

### Phase 2 - Thin Client Integration

- Introduce frontend websocket adapter with strict transport-only contract.
- Add connection-state UX indicators without domain logic recomputation.
- Verify thin-adapter guard tests for frontend websocket surface.

### Phase 3 - Expansion Features and Hardening

- Add first product event families (live sync/status updates).
- Add sustained-rate controls and connection caps.
- Extend observability and reliability checks (close reason distributions, reconnect safety).

---

## Risks and Mitigations

| Risk ID | Risk | Severity | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| R1 | Scope creep beyond package DoD | P1 | Freeze phase boundaries and enforce backlog-linked scope | `agent-coordinator` |
| R2 | Client business-logic drift | P0 | Thin-adapter guard tests + adapter-only websocket surface | `frontend-engineer` |
| R3 | Auth/tier bypass via new event path | P0 | Reuse canonical verifier path and deny-by-default routing | `backend-engineer`, `security-auditor` |
| R4 | Cross-user event leakage | P0 | User/tenant-scoped channels and isolation tests | `backend-engineer`, `bug-hunter` |
| R5 | Nondeterministic CI failures | P1 | Clock injection, fixed fixtures, deterministic order assertions | `dev-operator`, `bug-hunter` |
| R6 | Unsafe wellness language in realtime cues | P1 | Claim-semantic lint checklist and copy review gate | `philosophy-agent`, `cbt-psychologist-agent`, `nutritionist-agent` |

---

## Evidence Commands (Observed)

### Command Set

```bash
rg -n "WebSocket foundation follow-up \(realtime expansion package\)|Target PR: PR-WS-EXPANSION|Define versioned event contract|thin-adapter policy|deterministic integration tests" docs/roadmap/BACKLOG_LEDGER.md
rg -n "@router.websocket\(\"/ws\"\)|await ws.accept\(|FEATURE_WEBSOCKET_ENABLED|ALLOWED_EVENT_TYPES|POLICY_CLOSE_CODE|logger.info\(" app/routers/realtime_ws.py
rg -n "_assert_no_duplicate_ws_route|include_router\(realtime_ws.router\)|import app.routers.realtime_ws" app/main.py
rg -n "test_ws_|ws_client|WebSocketDisconnect|payload_too_large|rate_limited|event_type_not_allowed" tests/test_websocket_security_api.py
```

### Observed Output Snippets

- Backlog next-step anchors (exit code `0`):
  - `docs/roadmap/BACKLOG_LEDGER.md:500`
  - `docs/roadmap/BACKLOG_LEDGER.md:503`
  - `docs/roadmap/BACKLOG_LEDGER.md:512-514`
- WS foundation runtime anchors (exit code `0`):
  - `app/routers/realtime_ws.py:173`, `app/routers/realtime_ws.py:176`
  - `app/routers/realtime_ws.py:21-23`, `app/routers/realtime_ws.py:41`
  - `app/routers/realtime_ws.py:119-130`, `app/routers/realtime_ws.py:179-223`
- Router registration guard anchors (exit code `0`):
  - `app/main.py:17`, `app/main.py:25`, `app/main.py:35-36`
- Existing deterministic security test anchors (exit code `0`):
  - `tests/test_websocket_security_api.py:24`
  - `tests/test_websocket_security_api.py:156-186`
  - `tests/test_websocket_security_api.py:234`

---

## Definition of Done for PR-WS-EXPANSION

- [ ] Versioned realtime event contract is defined and documented.
- [ ] Expansion keeps canonical `/ws` route and fail-closed auth behavior.
- [ ] Thin-adapter integration scope is implemented for web/iOS clients (no business logic drift).
- [ ] Deterministic integration tests cover expanded event flow and close-code contracts.
- [ ] Security controls include auth/tier checks, shape validation, isolation, and rate controls.
- [ ] `pre-commit run --all-files` passes.
- [ ] `make verify` passes.
- [ ] `docs/roadmap/BACKLOG_LEDGER.md` item is updated with concrete PR number and status at merge.

---

## Security Notes

- Realtime expansion must remain wellness-only; no diagnostic/medical claim output.
- Any AI streamed content must degrade safely on high uncertainty and never bypass policy guards.
- No secrets or auth tokens in logs; only structured operational metadata.

## Marketing and GTM Notes

- External positioning should emphasize user value ("instant sync", "live updates"), not protocol details.
- Prioritize low-risk conversion surfaces: live sync freshness, status updates, and retention nudges.
- Launch should be staged behind feature flags with clear metric checkpoints (activation, retention, upgrade conversion).
